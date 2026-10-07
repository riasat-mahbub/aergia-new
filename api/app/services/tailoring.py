"""Full-history whole-document tailoring and review lifecycle.

Protocol v10 intentionally has one write primitive: a complete CV candidate.
The candidate is rendered and stored as an ordinary, unlinked CV draft.  The
browser owner later accepts or rejects it; the scoped capability can neither
change application linkage nor perform that review action.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import secrets
import asyncio
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_token
from app.document_schema.capabilities import LIMITS, capabilities_hash, renderer_capabilities
from app.document_schema.models import SectionInstance, TemplateManifest
from app.http_schemas.cv import CVCreate
from app.http_schemas.tailoring import (
    PROTOCOL_VERSION,
    TailoringCandidateCV,
    TailoringAcceptRequest,
    TailoringContextResponse,
    TailoringDraftContextResponse,
    TailoringDraftReview,
    TailoringDraftScannerContext,
    TailoringExchangeResponse,
    TailoringJob,
    TailoringPreviewRequest,
    TailoringPreviewReservationRequest,
    TailoringPreviewReservationResponse,
    TailoringPreviewReservationReleaseResponse,
    TailoringPreviewResponse,
    TailoringReviewResponse,
    TailoringReevaluateRequest,
    TailoringReevaluateResponse,
    TailoringSection,
    TailoringSessionCreateResponse,
    TailoringSessionStatusResponse,
    TailoringScannerContext,
    TailoringSubmitRequest,
    TailoringSubmitResponse,
    TailoringTemplate,
    TailoringCodeExchange,
)
from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringEvaluation,
)
from app.http_schemas.tailoring_fit_review import FitReviewReport
from app.http_schemas.profile import UserProfile
from app.models.application import Application
from app.models.cv import CV
from app.models.library import Library, LibraryEntry
from app.models.tailoring_session import TailoringSession
from app.models.tailoring_evaluation import (
    TAILORING_EVALUATION_AGENT_PREVIEW,
    TAILORING_EVALUATION_OWNER_REVIEW,
    TailoringEvaluationRecord,
)
from app.models.tailoring_preview_reservation import (
    TAILORING_PREVIEW_RESERVATION_ACTIVE,
    TAILORING_PREVIEW_RESERVATION_COMPLETED,
    TAILORING_PREVIEW_RESERVATION_EXPIRED,
    TAILORING_PREVIEW_RESERVATION_RELEASED,
    TailoringPreviewReservation,
)
from app.models.template import Template
from app.models.user import User
from app.scanner.freshness import configured_extractor_version, scanner_result_freshness
from app.scanner.results import ScanResult
from app.scanner.service import (
    PDF_RENDERER_VERSION,
    ScannerService,
    canonicalize_scanner_cv,
    scanner_versions_for_extraction,
)
from app.services.cv import CVLinkedToApplicationError, CVService, coerce_customizations
from app.services.pdf import PDFService, pdf_page_count
from app.services.profile import ProfileService
from app.services.quotas import (
    QuotaService,
    ReplacementAlreadyPendingError,
    ReplacementReservationConflictError,
)
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.rich_text import normalize_rich_text_ids, rich_text_fields_for_section
from app.services.tailoring_validation import CandidateValidationError, validate_section_payload
from app.services.tailoring_evaluation import evaluate_tailoring
from app.services.tailoring_fit_review import FitReviewBindingError, validate_fit_review_binding


_FIT_REVIEW_ADAPTER = TypeAdapter(FitReviewReport)


TAILORING_SESSION_TTL = timedelta(hours=1)
TAILORING_SESSION_CREATED = "created"
TAILORING_SESSION_EXCHANGED = "exchanged"
TAILORING_SESSION_DRAFT_READY = "draft_ready"
TAILORING_SESSION_ACCEPTED = "accepted"
TAILORING_SESSION_REJECTED = "rejected"
TAILORING_SESSION_FAILED = "failed"
TAILORING_SESSION_CANCELLED = "cancelled"
TAILORING_SESSION_STALE = "stale"
TAILORING_SESSION_EXPIRED = "expired"
TAILORING_PREVIEW_LEASE_TTL = timedelta(seconds=120)
TAILORING_PREVIEW_TIMEOUT_SECONDS = 90
TAILORING_AGENT_PREVIEW_LIMIT = 5

_FRESH_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("profile", "Profile"),
    ("education", "Education"),
    ("skills", "Skills"),
    ("experience", "Experience"),
    ("languages", "Languages"),
    ("certifications", "Certifications"),
    ("projects", "Projects"),
    ("research", "Research"),
)
_RICH_TEXT_BLOCK_TYPES = frozenset({"paragraph", "bullet_list", "numbered_list"})
_DOSSIER_LABELS = {"id": "ID", "url": "URL", "cv": "CV", "api": "API", "ats": "ATS"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _db_utcnow() -> datetime:
    """Bind a naive UTC value for SQLite's timezone-aware DateTime columns."""

    return _utcnow().replace(tzinfo=None)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _next_lease_fence(value: datetime, now: datetime) -> datetime:
    """Return a lease update timestamp that always advances its fence."""

    current = _as_utc(value)
    return now if now > current else current + timedelta(microseconds=1)


def _content_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strip_none_values(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _strip_none_values(child) for key, child in value.items() if child is not None}
    if isinstance(value, list):
        return [_strip_none_values(child) for child in value]
    return value


def _candidate_content_for_comparison(value: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical candidate fields used to verify a persisted draft."""

    candidate = copy.deepcopy(dict(value))
    candidate.pop("id", None)
    return _strip_none_values(candidate)


def cv_snapshot_hash(cv: CV | None) -> str | None:
    if cv is None:
        return None
    return _content_hash(
        {
            "title": cv.title,
            "description": cv.description,
            "template_id": cv.template_id,
            "customizations": cv.customizations or {},
            "sections": cv.sections or [],
            "is_active": bool(cv.is_active),
            "revision": cv.revision or 1,
        }
    )


def library_entry_content_hash(entry: LibraryEntry | Mapping[str, Any]) -> str:
    if isinstance(entry, Mapping):
        entry_id = entry.get("id")
        kind = entry.get("kind")
        payload = entry.get("payload") or []
    else:
        entry_id = entry.id
        kind = entry.kind
        payload = entry.payload or []
    return _content_hash({"id": entry_id, "kind": kind, "payload": payload})


def profile_snapshot_hash(profile: Mapping[str, Any]) -> str:
    return _content_hash(dict(profile))


def _bounded_label(value: str, limit: int) -> str:
    return value[:limit]


def build_tailoring_prompt(
    session_url: str,
    code: str,
    skill_url: str,
    protocol_version: int = PROTOCOL_VERSION,
) -> str:
    return (
        "Use the Aergia full-history tailoring skill for this session:\n\n"
        f"{session_url}\n\n"
        f"One-time session code: {code}\n\n"
        "The session provides the job and notes, a frozen readable dossier from the profile and every "
        "Library entry, and a clearly labeled readable source CV when one exists. Source-CV-only facts "
        "supplement Library history; fixed identity and contact details remain profile-owned. The "
        "session also provides frozen templates and renderer constraints. Compose one complete "
        "truthful CV from that material. Preview candidates through Aergia, use the canonical candidate "
        "returned by the selected preview exactly as returned, and submit it with that preview's context "
        "and candidate hashes. The context is frozen; if Aergia reports it is stale, start a new session. "
        "Never accept or reject the draft through the agent capability.\n\n"
        "If the aergia-tailor skill is missing or incompatible, ask for my "
        "approval to download and install this official bundle:\n\n"
        f"{skill_url}"
    )


class TailoringNotFoundError(LookupError):
    """The authenticated owner cannot access the requested application."""


class TailoringSessionNotFoundError(LookupError):
    """The authenticated owner cannot access the requested session."""


class TailoringUnauthorizedError(PermissionError):
    """A code or scoped capability is invalid."""

    code = "inactive_capability"
    status_code = 401


class TailoringExpiredError(PermissionError):
    """A tailoring session has passed its expiry time."""

    code = "inactive_capability"
    status_code = 410
    commit_outcome = True


class TailoringStaleError(RuntimeError):
    """The exchanged context is no longer the current context."""

    code = "stale_target"
    status_code = 409

    def __init__(self, message: str, *, code: str | None = None, commit_outcome: bool = False):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.commit_outcome = commit_outcome


class TailoringConflictError(RuntimeError):
    """The session cannot perform the requested one-time action."""

    code = "reservation_conflict"
    status_code = 409

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        commit_outcome: bool = False,
    ):
        super().__init__(message)
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.commit_outcome = commit_outcome


class TailoringUnavailableError(ValueError):
    """The application is not ready for tailoring."""

    code = "application_unavailable"
    status_code = 409


class TailoringCandidateError(ValueError):
    """A complete candidate is structurally or mechanically invalid."""

    code = "candidate_invalid"
    status_code = 422


class _FencedPreviewCompletion(Exception):
    """Internal savepoint signal: the lease changed before ledger insertion."""


class _PreviewLimitReached(Exception):
    """Internal savepoint signal used to preserve the active-reservation index."""


class TailoringPreviewUnavailableError(RuntimeError):
    """Rendering or scanning failed after a reservation was acquired."""

    code = "reservation_conflict"
    status_code = 503
    commit_outcome = True

    def __init__(self, message: str):
        super().__init__(message)


def fresh_tailoring_sections(session_id: str, profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the empty document shown when an account has no source CV."""

    profile_data = copy.deepcopy(dict(profile))
    profile_data.setdefault("summary", "")
    return [
        {
            "id": f"tailoring_{session_id}_{section_type}",
            "type": section_type,
            "title": title,
            "enabled": section_type == "profile",
            "data": profile_data if section_type == "profile" else [],
            "style": None,
        }
        for section_type, title in _FRESH_SECTION_ORDER
    ]


def _sections_as_dicts(sections: list[TailoringSection] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item.model_dump(mode="json", exclude_none=False) if hasattr(item, "model_dump") else copy.deepcopy(item)
        for item in sections
    ]


def _candidate_dict(candidate: TailoringCandidateCV) -> dict[str, Any]:
    return candidate.model_dump(mode="json", exclude_none=False)


def _profile_payload(profile: Any) -> dict[str, Any]:
    return profile.model_dump(mode="json", exclude_none=True, exclude={"photo_url"})


def _dossier_label(value: object) -> str:
    words = str(value).replace("_", " ").split()
    return " ".join(_DOSSIER_LABELS.get(word.casefold(), word.capitalize()) for word in words)


def _is_rich_text_block(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("type") in _RICH_TEXT_BLOCK_TYPES
        and isinstance(value.get("items"), list)
        and all(isinstance(item, Mapping) and isinstance(item.get("text"), str) for item in value["items"])
    )


def _is_rich_text_blocks(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_rich_text_block(block) for block in value)


def _rich_text_item_text(item: Mapping[str, Any]) -> str:
    text = item.get("text", "")
    style = item.get("style")
    link = style.get("link") if isinstance(style, Mapping) else None
    if isinstance(link, str) and link:
        text += f" [link: {link}]"
    extra = {key: value for key, value in item.items() if key not in {"id", "text", "style"}}
    if extra:
        text += f" [additional fields: {json.dumps(extra, ensure_ascii=False, default=str)}]"
    return text


def _append_dossier_text(lines: list[str], label: str, value: str, indent: int) -> None:
    prefix = "  " * indent
    value_lines = value.splitlines() or [""]
    lines.append(f"{prefix}{label}: {value_lines[0]}")
    lines.extend(f"{prefix}  {line}" for line in value_lines[1:])


def _append_rich_text(lines: list[str], label: str, value: list[Any], indent: int) -> None:
    prefix = "  " * indent
    if label:
        lines.append(f"{prefix}{label}:")
        prefix += "  "
    for block in value:
        if not _is_rich_text_block(block):
            continue
        block_type = block["type"]
        rendered_items = [_rich_text_item_text(item) for item in block["items"]]
        if block_type == "paragraph":
            paragraph = "".join(rendered_items)
            if paragraph:
                lines.extend(f"{prefix}{line}" for line in paragraph.splitlines())
        else:
            marker = "- " if block_type == "bullet_list" else None
            for index, item_text in enumerate(rendered_items, start=1):
                if not item_text:
                    continue
                item_marker = marker if marker is not None else f"{index}. "
                lines.extend(f"{prefix}{item_marker}{line}" for line in item_text.splitlines())
        extra = {
            key: child
            for key, child in block.items()
            if key not in {"id", "type", "items", "style"}
        }
        for key, child in extra.items():
            _append_dossier_value(lines, _dossier_label(key), child, indent + (1 if label else 0))


def _append_dossier_value(lines: list[str], label: str, value: Any, indent: int = 0) -> None:
    prefix = "  " * indent
    if value is None:
        return
    if _is_rich_text_block(value):
        _append_rich_text(lines, label, [value], indent)
        return
    if isinstance(value, str):
        if value:
            _append_dossier_text(lines, label, value, indent)
        return
    if isinstance(value, Mapping):
        if not value:
            return
        lines.append(f"{prefix}{label}:")
        for key, child in value.items():
            if key == "style":
                continue
            _append_dossier_value(lines, _dossier_label(key), child, indent + 1)
        return
    if isinstance(value, list):
        if _is_rich_text_blocks(value):
            _append_rich_text(lines, label, value, indent)
            return
        if not value:
            return
        lines.append(f"{prefix}{label}:")
        for index, child in enumerate(value, start=1):
            if isinstance(child, Mapping):
                child_id = child.get("id")
                item_label = f"Entry {index}"
                if child_id is not None:
                    item_label += f" (ID: {child_id})"
                _append_dossier_value(lines, item_label, child, indent + 1)
            elif isinstance(child, (str, int, float, bool)):
                child_lines = str(child).splitlines() or [""]
                lines.append(f"{'  ' * (indent + 1)}- {child_lines[0]}")
                lines.extend(f"{'  ' * (indent + 2)}{line}" for line in child_lines[1:])
            else:
                fallback = json.dumps(child, ensure_ascii=False, indent=2, default=str)
                _append_dossier_text(lines, f"Entry {index}", fallback, indent + 1)
        return
    if isinstance(value, bool):
        _append_dossier_text(lines, label, "true" if value else "false", indent)
        return
    if isinstance(value, (int, float)):
        _append_dossier_text(lines, label, str(value), indent)
        return
    fallback = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    _append_dossier_text(lines, label, fallback, indent)


def _object_value(value: object, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _source_cv_dossier(lines: list[str], source_cv: Mapping[str, Any]) -> None:
    """Append readable source-CV facts without conflating them with Library rows."""

    lines.extend(
        (
            "",
            "## Readable source CV",
            "Facts below come from the linked source document and supplement Library history. "
            "The saved profile remains authoritative for current identity and contact details. "
            "Profile headline and document title are separate from historical employment titles.",
        )
    )
    if source_cv.get("title"):
        _append_dossier_value(lines, "Source CV document title", source_cv["title"], indent=1)
    if source_cv.get("description"):
        _append_dossier_value(lines, "Source CV description", source_cv["description"], indent=1)
    for section in source_cv.get("sections") or []:
        if not isinstance(section, Mapping):
            continue
        section_type = str(section.get("type") or "section")
        data = section.get("data")
        section_title = section.get("title") or section_type.replace("_", " ").title()
        lines.extend(("", f"### Source CV — {section_title}"))
        if isinstance(data, Mapping):
            for key, value in data.items():
                if key in {"id", "style"}:
                    continue
                if section_type == "profile" and key == "title":
                    label = "Professional headline"
                else:
                    label = _dossier_label(key)
                _append_dossier_value(lines, label, value, indent=1)
        elif isinstance(data, list):
            for index, row in enumerate(data, start=1):
                if not isinstance(row, Mapping):
                    _append_dossier_value(lines, f"Entry {index}", row, indent=1)
                    continue
                heading = f"Entry {index}"
                if row.get("id") is not None:
                    heading += f" (ID: {row['id']})"
                lines.append(f"  {heading}:")
                for key, value in row.items():
                    if key in {"id", "style"}:
                        continue
                    label = "Historical official title" if section_type == "experience" and key == "position" else _dossier_label(key)
                    _append_dossier_value(lines, label, value, indent=2)


def _build_dossier(
    profile: Mapping[str, Any],
    entries: Sequence[object],
    source_cv: Mapping[str, Any] | None = None,
) -> str:
    """Render the frozen profile, Library, and optional source CV as readable facts."""

    parts = ["# Candidate dossier", "", "## Profile"]
    for key, value in profile.items():
        label = "Professional headline" if key == "title" else _dossier_label(key)
        _append_dossier_value(parts, label, value, indent=1)
    if not profile:
        parts.append("  No profile fields are available.")
    parts.extend(("", "## Library history"))
    if not entries:
        parts.append("No Library entries are available.")
    for entry in entries:
        kind = str(_object_value(entry, "kind", "entry"))
        entry_id = _object_value(entry, "id", "unknown")
        parts.extend(("", f"### {kind.title()} — Library entry ID: {entry_id}"))
        payload = _object_value(entry, "payload", None) or []
        if not payload:
            parts.append("  No saved rows.")
        for index, row in enumerate(payload, start=1):
            if isinstance(row, Mapping):
                row_id = row.get("id")
                heading = f"  {entry.kind.title()} {index}"
                if row_id is not None:
                    heading += f" — Row ID: {row_id}"
                parts.append(f"{heading}:")
                for key, value in row.items():
                    if key in {"id", "style"}:
                        continue
                    label = "Historical official title" if kind == "experience" and key == "position" else _dossier_label(key)
                    _append_dossier_value(parts, label, value, indent=2)
            else:
                _append_dossier_value(parts, f"Row {index}", row, indent=1)
    if source_cv is not None:
        _source_cv_dossier(parts, source_cv)
    return "\n".join(parts)


def _application_context_snapshot(application: Application) -> dict[str, Any]:
    return {
        "id": application.id,
        "linked_cv_id": application.cv_id,
        "company": application.company,
        "role": application.role,
        "job_url": application.job_url,
        "description": application.job_description,
        "user_instructions": getattr(application, "notes", None),
    }


def _template_manifest(template: Template) -> dict[str, Any] | None:
    if not isinstance(template.manifest, dict):
        return None
    try:
        return TemplateManifest.model_validate(template.manifest).model_dump(mode="json")
    except ValidationError:
        return None


def _source_cv_snapshot(source_cv: CV | Mapping[str, Any] | SimpleNamespace | None) -> dict[str, Any] | None:
    if source_cv is None:
        return None
    return {
        "id": _object_value(source_cv, "id"),
        "revision": _object_value(source_cv, "revision") or 1,
        "title": _object_value(source_cv, "title"),
        "description": _object_value(source_cv, "description"),
        "template_id": _object_value(source_cv, "template_id"),
        "customizations": copy.deepcopy(_object_value(source_cv, "customizations", None) or {}),
        "sections": copy.deepcopy(_object_value(source_cv, "sections", None) or []),
    }


class TailoringService:
    """Own context exchange, complete-candidate persistence, and review."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scanner_service = ScannerService()

    async def _owned_application(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application)
            .where(Application.id == application_id, Application.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def _owned_cv(self, cv_id: str | None, user_id: str) -> CV | None:
        if not cv_id:
            return None
        result = await self.db.execute(
            select(CV)
            .where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def _library_entries(self, user_id: str) -> list[LibraryEntry]:
        result = await self.db.execute(
            select(LibraryEntry)
            .join(Library, LibraryEntry.library_id == Library.id)
            .where(Library.user_id == user_id)
            .order_by(LibraryEntry.created_at.asc(), LibraryEntry.id.asc())
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def _templates(self) -> list[Template]:
        result = await self.db.execute(
            select(Template)
            .order_by(Template.created_at.asc(), Template.id.asc())
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def _context_resources(self, session: TailoringSession) -> dict[str, Any]:
        application = await self._owned_application(session.application_id, session.user_id)
        if application is None:
            raise TailoringConflictError("Tailoring application is no longer available")
        source_cv = await self._owned_cv(session.cv_id, session.user_id)
        if session.cv_id and source_cv is None:
            raise TailoringConflictError("The source CV is no longer available")
        user_result = await self.db.execute(
            select(User).where(User.id == session.user_id).execution_options(populate_existing=True)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise TailoringUnauthorizedError("Invalid tailoring session owner")
        profile = await ProfileService(self.db).get_profile(user)
        profile_data = _profile_payload(profile)
        libraries = await self._library_entries(session.user_id)
        templates = await self._templates()
        capabilities = renderer_capabilities(HTMLDocumentRenderer.support)
        manifest_by_id = {
            template.id: manifest
            for template in templates
            if (manifest := _template_manifest(template)) is not None
        }
        selected_template_id = (
            source_cv.template_id if source_cv and source_cv.template_id in manifest_by_id else next(iter(manifest_by_id), "")
        )
        if not selected_template_id:
            raise TailoringUnavailableError("No renderable templates are available")
        return {
            "application": application,
            "source_cv": source_cv,
            "profile": profile,
            "profile_data": profile_data,
            "libraries": libraries,
            "templates": templates,
            "manifest_by_id": manifest_by_id,
            "selected_template_id": selected_template_id,
            "capabilities": capabilities,
        }

    async def _render_cv_pdf(
        self,
        cv: CV,
        manifest: Mapping[str, Any] | None = None,
    ) -> bytes | None:
        try:
            if manifest is None:
                return None
            service = PDFService(self.db)
            return await service.render_manifest_payload(
                dict(manifest),
                cv.sections or [],
                cv.customizations or {},
            )
        except Exception:  # noqa: BLE001 - scanner branches remain useful without PDF recovery
            return None

    async def _freeze_scanner_context(self, resources: Mapping[str, Any]) -> TailoringScannerContext:
        application: Application = resources["application"]
        source_cv: CV | None = resources["source_cv"]
        if source_cv is None:
            extraction = await asyncio.to_thread(
                self.scanner_service.extract_requirements,
                application.job_description,
            )
            return TailoringScannerContext(
                versions=scanner_versions_for_extraction(extraction),
                requirement_extraction=extraction,
                source_scan=None,
            )

        source_scan: ScanResult | None = None
        existing = application.scanner_result
        source_manifest = resources["manifest_by_id"].get(source_cv.template_id)
        if existing is not None and source_manifest is not None:
            freshness = scanner_result_freshness(
                existing,
                application.job_description,
                source_cv,
                extractor_version=configured_extractor_version(),
                render_manifest=source_manifest,
            )
            if freshness["current"]:
                try:
                    source_scan = ScanResult.model_validate(existing)
                except ValidationError:
                    source_scan = None

        if source_scan is None:
            pdf_bytes = await self._render_cv_pdf(source_cv, source_manifest)
            source_scan = await asyncio.to_thread(
                self.scanner_service.scan,
                application.job_description,
                source_cv,
                pdf_bytes=pdf_bytes,
                render_manifest=source_manifest,
            )

        return TailoringScannerContext(
            versions=source_scan.versions,
            requirement_extraction=source_scan.requirement_extraction,
            source_scan=source_scan,
        )

    @staticmethod
    def _context_basis(resources: Mapping[str, Any], scanner_context: TailoringScannerContext) -> dict[str, Any]:
        application: Application = resources["application"]
        source_cv: CV | None = resources["source_cv"]
        libraries: list[LibraryEntry] = resources["libraries"]
        templates: list[Template] = resources["templates"]
        capabilities: dict[str, Any] = resources["capabilities"]
        return {
            "application": _application_context_snapshot(application),
            "profile": resources["profile"].model_dump(mode="json", exclude_none=True),
            "source_cv": _source_cv_snapshot(source_cv),
            "source_cv_revision": source_cv.revision or 1 if source_cv is not None else None,
            "libraries": [
                {
                    "id": entry.id,
                    "kind": entry.kind,
                    "payload": copy.deepcopy(entry.payload or []),
                }
                for entry in libraries
            ],
            "scanner": scanner_context.model_dump(mode="json"),
            "templates": [
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "preview_image_url": template.preview_image_url,
                    "manifest": resources["manifest_by_id"][template.id],
                    "assets": template.assets,
                    "created_at": template.created_at.isoformat() if template.created_at else None,
                }
                for template in templates
                if template.id in resources["manifest_by_id"]
            ],
            "selected_template_id": resources["selected_template_id"],
            "capabilities": copy.deepcopy(capabilities),
            "evaluation_version": TAILORING_EVALUATION_VERSION,
        }

    @staticmethod
    def _target_guard_basis(
        application: Application,
        source_cv: CV | None,
        capabilities: Mapping[str, Any],
        scanner_context: TailoringScannerContext,
    ) -> dict[str, Any]:
        return {
            "application_owner_id": application.user_id,
            "application": _application_context_snapshot(application),
            "source_cv_id": source_cv.id if source_cv is not None else None,
            "source_cv_revision": source_cv.revision or 1 if source_cv is not None else None,
            # The revision is the public meaningful-change token. The
            # content digest also protects sessions created before CV writes
            # consistently advance that token.
            "source_cv_content_hash": cv_snapshot_hash(source_cv),
            "renderer_capabilities_hash": capabilities_hash(capabilities),
            "pdf_renderer_version": PDF_RENDERER_VERSION,
            "scanner_versions": scanner_context.versions.model_dump(mode="json"),
        }

    async def _current_target_guard(
        self,
        session: TailoringSession,
        scanner_context: TailoringScannerContext,
    ) -> dict[str, Any]:
        """Refresh and validate the live job/source/renderer guard for P05/P07."""

        app_result = await self.db.execute(
            select(Application)
            .where(
                Application.id == session.application_id,
                Application.user_id == session.user_id,
            )
            .execution_options(populate_existing=True)
        )
        application = app_result.scalar_one_or_none()
        if application is None:
            raise TailoringConflictError("Tailoring application is no longer available")
        if application.cv_id != session.cv_id:
            raise TailoringStaleError("The application or source CV changed; start a new session")

        source_cv: CV | None = None
        if session.cv_id is not None:
            source_result = await self.db.execute(
                select(CV)
                .where(CV.id == session.cv_id, CV.user_id == session.user_id)
                .execution_options(populate_existing=True)
            )
            source_cv = source_result.scalar_one_or_none()
            if source_cv is None or not source_cv.is_active:
                raise TailoringStaleError("The source CV changed or is no longer available; start a new session")
            if (source_cv.revision or 1) != session.source_cv_revision:
                raise TailoringStaleError("The source CV changed; start a new session")
        elif session.source_cv_revision is not None:
            raise TailoringStaleError("The source CV changed; start a new session")

        current_capabilities = renderer_capabilities(HTMLDocumentRenderer.support)
        current_versions = scanner_versions_for_extraction(scanner_context.requirement_extraction)
        configured_version = configured_extractor_version()
        if (
            current_versions != scanner_context.versions
            or (configured_version and configured_version != scanner_context.versions.extractor_version)
        ):
            raise TailoringStaleError("The scanner contract changed; start a new tailoring session")

        guard = self._target_guard_basis(application, source_cv, current_capabilities, scanner_context)
        current_hash = _content_hash(guard)
        if not session.target_guard_hash or current_hash != session.target_guard_hash:
            raise TailoringStaleError("The application or source CV changed; start a new session")
        return {
            "application": application,
            "source_cv": source_cv,
            "target_guard_hash": current_hash,
        }

    async def _lock_preview_target_rows(self, session: TailoringSession) -> None:
        """Prevent live application/source edits during the final preview CAS."""

        await self.db.execute(
            select(Application.id)
            .where(
                Application.id == session.application_id,
                Application.user_id == session.user_id,
            )
            .with_for_update()
        )
        if session.cv_id is not None:
            await self.db.execute(
                select(CV.id)
                .where(CV.id == session.cv_id, CV.user_id == session.user_id)
                .with_for_update()
            )

    async def _context_matches(
        self,
        session: TailoringSession,
        expected_context_hash: str | None = None,
    ) -> bool:
        """Return whether a stored v10 context and its live target are current."""

        snapshot = session.context_snapshot
        if not isinstance(snapshot, Mapping):
            return False
        try:
            if (
                session.protocol_version != PROTOCOL_VERSION
                or snapshot.get("protocol_version") != session.protocol_version
                or snapshot.get("evaluation_version") != TAILORING_EVALUATION_VERSION
            ):
                return False
            basis = snapshot["basis"]
            if not isinstance(basis, Mapping):
                return False
            frozen_hash = _content_hash(basis)
            if snapshot.get("context_hash") != frozen_hash:
                return False
            if session.context_hash and session.context_hash != frozen_hash:
                return False
            if expected_context_hash is not None and expected_context_hash != frozen_hash:
                return False
            if snapshot.get("scanner") != basis.get("scanner"):
                return False
            scanner_context = TailoringScannerContext.model_validate(snapshot["scanner"])
            if session.source_cv_revision != basis.get("source_cv_revision"):
                return False
            await self._current_target_guard(session, scanner_context)
        except (KeyError, TypeError, ValidationError, TailoringConflictError, TailoringStaleError):
            return False
        return True

    async def _context_parts(
        self,
        session: TailoringSession,
        *,
        initialize: bool = False,
    ) -> dict[str, Any]:
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringStaleError("This tailoring session uses an older protocol; start a new session")
        if not session.context_snapshot:
            if not initialize:
                raise TailoringStaleError("This tailoring session has no frozen authoring context; start a new session")
            resources = await self._context_resources(session)
            scanner_context = await self._freeze_scanner_context(resources)
            basis = self._context_basis(resources, scanner_context)
            target_guard = self._target_guard_basis(
                resources["application"],
                resources["source_cv"],
                resources["capabilities"],
                scanner_context,
            )
            session.source_cv_revision = basis["source_cv_revision"]
            session.target_guard_hash = _content_hash(target_guard)
            frozen_context_hash = _content_hash(basis)
            session.context_snapshot = {
                "schema_version": f"tailoring-v{session.protocol_version}",
                "protocol_version": session.protocol_version,
                "evaluation_version": TAILORING_EVALUATION_VERSION,
                "scanner": scanner_context.model_dump(mode="json"),
                "basis": basis,
                # Evaluation records share the storage column but never
                # participate in this immutable authoring-context digest.
                "context_hash": frozen_context_hash,
            }
            session.context_hash = frozen_context_hash
        else:
            if not isinstance(session.context_snapshot, Mapping):
                raise TailoringStaleError("The frozen tailoring context is invalid; start a new session")
            try:
                snapshot = session.context_snapshot
                if snapshot.get("protocol_version") != session.protocol_version:
                    raise TailoringStaleError("The tailoring session protocol is no longer supported")
                if snapshot.get("evaluation_version") != TAILORING_EVALUATION_VERSION:
                    raise TailoringStaleError("The tailoring evaluation contract changed; start a new session")
                scanner_context = TailoringScannerContext.model_validate(snapshot["scanner"])
                frozen_basis = snapshot["basis"]
                if not isinstance(frozen_basis, Mapping):
                    raise TypeError("frozen context must be a mapping")
                required_fields = {
                    "application",
                    "profile",
                    "source_cv",
                    "source_cv_revision",
                    "libraries",
                    "scanner",
                    "templates",
                    "selected_template_id",
                    "capabilities",
                    "evaluation_version",
                }
                if not required_fields.issubset(frozen_basis):
                    raise TypeError("frozen context is incomplete")
                if not isinstance(frozen_basis["libraries"], list) or not isinstance(frozen_basis["templates"], list):
                    raise TypeError("frozen evidence collections are invalid")
                if snapshot["scanner"] != frozen_basis["scanner"]:
                    raise TypeError("frozen scanner snapshots disagree")
                if _content_hash(frozen_basis) != snapshot.get("context_hash"):
                    raise TailoringStaleError("The frozen tailoring context is invalid; start a new session")
                if session.source_cv_revision != frozen_basis.get("source_cv_revision"):
                    raise TailoringStaleError("The frozen source CV revision is invalid; start a new session")
            except (KeyError, TypeError, ValidationError) as exc:
                raise TailoringStaleError("The frozen tailoring context is invalid; start a new session") from exc

        context_snapshot = session.context_snapshot
        basis = context_snapshot["basis"]
        live_target = await self._current_target_guard(session, scanner_context)
        source_cv_snapshot = basis.get("source_cv")
        source_cv = SimpleNamespace(**copy.deepcopy(source_cv_snapshot)) if source_cv_snapshot is not None else None
        profile_data = copy.deepcopy(basis["profile"])
        profile = UserProfile.model_validate(profile_data)
        library_entries = [SimpleNamespace(**copy.deepcopy(item)) for item in basis["libraries"]]
        templates = [SimpleNamespace(**copy.deepcopy(item)) for item in basis["templates"]]
        manifest_by_id = {
            item.id: copy.deepcopy(item.manifest)
            for item in templates
        }
        capabilities = copy.deepcopy(basis["capabilities"])
        context_hash = _content_hash(basis)
        if session.context_hash and session.context_hash != context_hash:
            raise TailoringStaleError("The frozen tailoring context is invalid; start a new session")
        return {
            "application": live_target["application"],
            "source_cv": source_cv,
            "source_cv_revision": basis.get("source_cv_revision"),
            "profile": profile,
            "profile_data": {key: value for key, value in profile_data.items() if key != "photo_url"},
            "libraries": library_entries,
            "templates": templates,
            "manifest_by_id": manifest_by_id,
            "selected_template_id": basis["selected_template_id"],
            "capabilities": capabilities,
            # Pass a serialized copy to the pure evaluation service rather
            # than exposing database/ORM access to it.
            "authoritative_library": [
                {
                    "id": entry.id,
                    "kind": entry.kind,
                    "payload": copy.deepcopy(entry.payload or []),
                }
                for entry in library_entries
            ],
            "scanner_context": scanner_context,
            "context_hash": context_hash,
            "target_guard_hash": live_target["target_guard_hash"],
        }

    async def create_session(
        self,
        application_id: str,
        user_id: str,
        session_url_base: str | None = None,
        protocol_version: int = PROTOCOL_VERSION,
    ) -> tuple[TailoringSessionCreateResponse, TailoringSession]:
        if protocol_version != PROTOCOL_VERSION:
            raise TailoringUnavailableError("Unsupported tailoring protocol")
        application = await self._owned_application(application_id, user_id)
        if application is None:
            raise TailoringNotFoundError("Application not found")
        existing_result = await self.db.execute(
            select(TailoringSession).where(
                TailoringSession.application_id == application_id,
                TailoringSession.user_id == user_id,
                TailoringSession.status.in_(
                    (
                        TAILORING_SESSION_CREATED,
                        TAILORING_SESSION_EXCHANGED,
                        TAILORING_SESSION_DRAFT_READY,
                        TAILORING_SESSION_STALE,
                        TAILORING_SESSION_EXPIRED,
                    )
                ),
            )
        )
        now = _utcnow()
        reconcile_stale: list[tuple[TailoringSession, str, str]] = []
        stale_draft_requires_discard = False
        for existing in existing_result.scalars().all():
            if existing.status == TAILORING_SESSION_EXPIRED:
                if existing.draft_cv_id:
                    expired_draft = await self._owned_cv(existing.draft_cv_id, user_id)
                    if expired_draft is not None and expired_draft.application_id == application_id:
                        raise TailoringConflictError(
                            "Discard the expired tailoring draft before starting another session",
                            code="session_in_progress",
                        )
                    reconcile_stale.append((existing, TAILORING_SESSION_STALE, "draft_missing"))
                continue
            if existing.status == TAILORING_SESSION_STALE:
                if existing.draft_cv_id:
                    stale_draft = await self._owned_cv(existing.draft_cv_id, user_id)
                    if stale_draft is not None and stale_draft.application_id == application_id:
                        raise TailoringConflictError(
                            "Discard the stale tailoring draft before starting another session",
                            code="session_in_progress",
                        )
                    reconcile_stale.append((existing, TAILORING_SESSION_STALE, "draft_missing"))
                continue
            if existing.status == TAILORING_SESSION_DRAFT_READY:
                if existing.protocol_version != PROTOCOL_VERSION:
                    raise TailoringConflictError(
                        "Finish or discard the existing tailoring session before starting another",
                        code="session_in_progress",
                    )
                existing_draft = await self._owned_cv(existing.draft_cv_id, user_id)
                if existing_draft is None or existing_draft.application_id != application_id:
                    reconcile_stale.append((existing, TAILORING_SESSION_STALE, "draft_missing"))
                    continue
                try:
                    await self._context_parts(existing)
                except (TailoringConflictError, TailoringUnavailableError, TailoringStaleError):
                    reconcile_stale.append((existing, TAILORING_SESSION_STALE, "draft_target_mismatch"))
                    stale_draft_requires_discard = True
                    continue
                raise TailoringConflictError(
                    "Finish or discard the existing tailoring session before starting another",
                    code="session_in_progress",
                )
            if (
                existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
                and existing.protocol_version != PROTOCOL_VERSION
            ):
                reconcile_stale.append((existing, TAILORING_SESSION_STALE, "protocol_mismatch"))
                continue
            if (
                existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
                and _as_utc(existing.expires_at) <= now
            ):
                reconcile_stale.append((existing, TAILORING_SESSION_EXPIRED, "expired"))
                continue
            if (
                existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
                and not await self._context_matches(existing)
            ):
                reconcile_stale.append((existing, TAILORING_SESSION_STALE, "target_mismatch"))
                continue
            if existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
                raise TailoringConflictError(
                    "Finish or discard the existing tailoring session before starting another",
                    code="session_in_progress",
                )
        if stale_draft_requires_discard:
            await QuotaService(self.db).ensure_write_transaction()
            async with self.db.begin_nested():
                for existing, _, reason in reconcile_stale:
                    if reason != "draft_target_mismatch":
                        continue
                    result = await self.db.execute(
                        update(TailoringSession)
                        .where(
                            TailoringSession.id == existing.id,
                            TailoringSession.status == TAILORING_SESSION_DRAFT_READY,
                        )
                        .values(
                            status=TAILORING_SESSION_STALE,
                            capability_hash=None,
                            owner_review_state="needs_reevaluation",
                            updated_at=now,
                        )
                    )
                    if result.rowcount == 1:
                        existing.status = TAILORING_SESSION_STALE
                        existing.capability_hash = None
                        existing.owner_review_state = "needs_reevaluation"
                        existing.updated_at = now
                        await self._release_session_replacement(existing)
            raise TailoringConflictError(
                "The stale tailoring draft must be discarded before starting a new session",
                code="session_in_progress",
                commit_outcome=True,
            )
        # Validate the owner, profile, and template availability before
        # issuing a capability. A source CV is intentionally optional.
        user_result = await self.db.execute(
            select(User).where(User.id == user_id).execution_options(populate_existing=True)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise TailoringNotFoundError("User not found")
        code = secrets.token_urlsafe(32)
        session = TailoringSession(
            user_id=user_id,
            application_id=application.id,
            cv_id=application.cv_id,
            code_hash=hash_token(code),
            protocol_version=protocol_version,
            status=TAILORING_SESSION_CREATED,
            expires_at=now + TAILORING_SESSION_TTL,
        )
        # Freeze evidence and complete any source rendering/scanning before
        # the session insert obtains a database write lock.
        parts = await self._context_parts(session, initialize=True)
        session.context_hash = parts["context_hash"]
        # Context construction can render and scan the linked source CV. The
        # quota helper starts SQLite's short write transaction only now, after
        # that expensive work, while retaining caller-owned transaction work.
        response_application_id = application.id
        response_source_cv_id = application.cv_id
        response_expires_at = session.expires_at
        await QuotaService(self.db).ensure_write_transaction()
        try:
            async with self.db.begin_nested():
                for existing, stale_status, stale_reason in reconcile_stale:
                    stale_query = update(TailoringSession).where(TailoringSession.id == existing.id)
                    if stale_reason in {"draft_missing", "draft_target_mismatch"}:
                        stale_query = stale_query.where(
                            TailoringSession.status.in_(
                                (
                                    TAILORING_SESSION_DRAFT_READY,
                                    TAILORING_SESSION_STALE,
                                    TAILORING_SESSION_EXPIRED,
                                )
                            ),
                            TailoringSession.draft_cv_id == existing.draft_cv_id,
                        )
                    else:
                        stale_query = stale_query.where(
                            TailoringSession.status.in_((TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED))
                        )
                    if stale_reason == "expired":
                        stale_query = stale_query.where(TailoringSession.expires_at <= _db_utcnow())
                    elif stale_reason == "protocol_mismatch":
                        stale_query = stale_query.where(TailoringSession.protocol_version != PROTOCOL_VERSION)
                    elif stale_reason == "target_mismatch":
                        # A frozen v10 session can be stale because its live
                        # target changed. Keep that reconciliation distinct
                        # from protocol cutover so it releases the blocking
                        # session index too.
                        stale_query = stale_query.where(TailoringSession.protocol_version == PROTOCOL_VERSION)
                    stale_values: dict[str, Any] = {
                        "status": stale_status,
                        "capability_hash": None,
                        "updated_at": now,
                    }
                    if stale_reason == "draft_missing":
                        stale_values.update(
                            owner_review_state="unavailable",
                            owner_cv_revision=None,
                            owner_candidate_hash=None,
                            owner_render_basis_hash=None,
                            owner_evaluation_id=None,
                            owner_pdf_sha256=None,
                        )
                    elif stale_reason == "draft_target_mismatch":
                        stale_values["owner_review_state"] = "needs_reevaluation"
                    await self.db.execute(stale_query.values(**stale_values))
                    await self.db.execute(
                        update(TailoringPreviewReservation)
                        .where(
                            TailoringPreviewReservation.session_id == existing.id,
                            TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                        )
                        .values(state=TAILORING_PREVIEW_RESERVATION_EXPIRED, updated_at=now)
                    )
                    if stale_reason in {"draft_missing", "expired", "protocol_mismatch", "target_mismatch"}:
                        await self.db.execute(
                            update(TailoringEvaluationRecord)
                            .where(TailoringEvaluationRecord.session_id == existing.id)
                            .values(pdf_bytes=None)
                        )
                    if stale_reason in {"draft_missing", "draft_target_mismatch"}:
                        await self._release_session_replacement(existing)
                self.db.add(session)
                await self.db.flush()
        except IntegrityError as exc:
            active_id = await self.db.scalar(
                select(TailoringSession.id)
                .where(
                    TailoringSession.application_id == application_id,
                    TailoringSession.status.in_(
                        (TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED, TAILORING_SESSION_DRAFT_READY)
                    ),
                )
                .limit(1)
            )
            if active_id is not None:
                raise TailoringConflictError(
                    "Finish or discard the existing tailoring session before starting another",
                    code="session_in_progress",
                ) from exc
            raise
        public_origin = session_url_base.rstrip("/") if session_url_base else ""
        session_url = f"{public_origin}/agent/tailor/{session.id}"
        skill_url = f"{public_origin}/api/v1/tailoring/skill.zip"
        response = TailoringSessionCreateResponse(
            protocol_version=protocol_version,
            session_id=session.id,
            application_id=response_application_id,
            source_cv_id=response_source_cv_id,
            cv_id=response_source_cv_id,
            code=code,
            session_url=session_url,
            skill_url=skill_url,
            prompt=build_tailoring_prompt(session_url, code, skill_url, protocol_version),
            expires_at=response_expires_at,
        )
        return response, session

    async def _owned_session(self, session_id: str, user_id: str) -> TailoringSession:
        result = await self.db.execute(
            select(TailoringSession).where(
                TailoringSession.id == session_id,
                TailoringSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringSessionNotFoundError("Tailoring session not found")
        return session

    @staticmethod
    def _status_response(
        session: TailoringSession,
        draft_review: TailoringDraftReview | None = None,
    ) -> TailoringSessionStatusResponse:
        return TailoringSessionStatusResponse(
            # Historical drafts remain readable/reviewable through the current
            # protocol. V10 adds a separate owner review alongside the frozen
            # submission result.
            protocol_version=session.protocol_version or PROTOCOL_VERSION,
            session_id=session.id,
            application_id=session.application_id,
            source_cv_id=session.cv_id,
            draft_cv_id=session.draft_cv_id,
            cv_id=session.cv_id,
            status=session.status,
            expires_at=session.expires_at,
            created_at=session.created_at,
            exchanged_at=session.exchanged_at,
            submitted_at=session.submitted_at,
            reviewed_at=session.reviewed_at,
            updated_at=session.updated_at,
            attempts=session.attempts,
            result=copy.deepcopy(session.result),
            draft_review=draft_review,
        )

    @staticmethod
    def _submission_payload(session: TailoringSession) -> dict[str, Any] | None:
        if isinstance(session.submission_result, dict):
            return session.submission_result
        return session.result if isinstance(session.result, dict) else None

    @staticmethod
    def _scanner_result_from_submission(payload: Mapping[str, Any] | None) -> ScanResult | None:
        if not payload or not payload.get("scanner_result"):
            return None
        try:
            return ScanResult.model_validate(payload["scanner_result"])
        except (TypeError, ValidationError):
            return None

    @staticmethod
    def _has_historical_submission(session: TailoringSession) -> bool:
        if (
            session.status == TAILORING_SESSION_DRAFT_READY
            or session.submitted_at is not None
            or session.draft_cv_id is not None
        ):
            return True
        payload = TailoringService._submission_payload(session)
        return bool(
            payload
            and (
                payload.get("status") == TAILORING_SESSION_DRAFT_READY
                or payload.get("draft_cv_id") is not None
                or isinstance(payload.get("candidate"), Mapping)
            )
        )

    @staticmethod
    def _persisted_candidate(draft: CV) -> dict[str, Any]:
        candidate = TailoringCandidateCV.model_validate(
            {
                "title": draft.title,
                "description": draft.description,
                "template_id": draft.template_id,
                "sections": draft.sections or [],
                "customizations": draft.customizations or {},
            }
        ).model_dump(mode="json", exclude_none=False)
        return candidate

    async def _current_owner_inputs(
        self,
        session: TailoringSession,
    ) -> tuple[dict[str, Any], UserProfile, dict[str, Any]]:
        """Build live owner render inputs over the session's frozen job context."""

        parts = await self._context_parts(session)
        user_result = await self.db.execute(
            select(User).where(User.id == session.user_id).execution_options(populate_existing=True)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise TailoringConflictError("Tailoring session owner is no longer available")
        profile = await ProfileService(self.db).get_profile(user)
        templates = await self._templates()
        manifests = {
            template.id: manifest
            for template in templates
            if (manifest := _template_manifest(template)) is not None
        }
        parts = dict(parts)
        parts["profile"] = profile
        parts["manifest_by_id"] = manifests
        parts["capabilities"] = renderer_capabilities(HTMLDocumentRenderer.support)
        return parts, profile, manifests

    @staticmethod
    def _owner_render_basis_hash(
        parts: Mapping[str, Any],
        profile: UserProfile,
        candidate: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> str:
        profile_data = profile.model_dump(mode="json", exclude_none=True)
        contact_keys = (
            "name",
            "email",
            "phone",
            "site_text",
            "site_url",
            "email_link",
            "social_links",
            "photo_url",
        )
        return _content_hash(
            {
                "candidate_hash": TailoringService._candidate_hash(candidate),
                "contact": {key: profile_data.get(key) for key in contact_keys},
                "template_id": candidate["template_id"],
                "template_manifest": copy.deepcopy(dict(manifest)),
                "renderer_capabilities": copy.deepcopy(parts["capabilities"]),
                "pdf_renderer_version": PDF_RENDERER_VERSION,
                "scanner_context": parts["scanner_context"].model_dump(mode="json"),
                "target_guard_hash": parts["target_guard_hash"],
            }
        )

    async def _draft_review(
        self,
        session: TailoringSession,
        draft: CV,
        *,
        parts: Mapping[str, Any],
        profile: UserProfile,
        manifests: Mapping[str, Any],
    ) -> TailoringDraftReview:
        candidate = self._persisted_candidate(draft)
        candidate_hash = self._candidate_hash(candidate)
        manifest = manifests.get(draft.template_id)
        if manifest is None:
            return TailoringDraftReview(
                state="needs_reevaluation",
                cv_revision=draft.revision or 1,
                candidate_hash=candidate_hash,
                fit_review_applicability="earlier_version"
                if self._fit_review_from_submission(session) is not None
                else "not_run",
            )
        render_basis_hash = self._owner_render_basis_hash(parts, profile, candidate, manifest)

        record: TailoringEvaluationRecord | None = None
        if session.owner_evaluation_id:
            record = await self.db.get(TailoringEvaluationRecord, session.owner_evaluation_id)
        parsed: tuple[ScanResult, TailoringEvaluation, str] | None = None
        if record is not None and record.session_id == session.id and record.kind == TAILORING_EVALUATION_OWNER_REVIEW:
            parsed = self._record_evaluation_payload(record)
        pdf_is_valid = bool(
            record is not None
            and record.pdf_bytes is not None
            and hashlib.sha256(record.pdf_bytes).hexdigest() == record.pdf_sha256
        )
        review_is_current = bool(
            session.status == TAILORING_SESSION_DRAFT_READY
            and session.owner_review_state == "current"
            and session.owner_cv_revision == (draft.revision or 1)
            and session.owner_candidate_hash == candidate_hash
            and session.owner_render_basis_hash == render_basis_hash
            and record is not None
            and parsed is not None
            and parsed[2] == candidate_hash
            and session.owner_pdf_sha256 == record.pdf_sha256
            and pdf_is_valid
        )

        fit_review = self._fit_review_from_submission(session)
        applicability = "not_run" if fit_review is None else "earlier_version"
        if (
            fit_review is not None
            and review_is_current
            and record is not None
            and fit_review.candidate_hash == candidate_hash
            and fit_review.pdf_sha256 == record.pdf_sha256
        ):
            applicability = "current"
        if not review_is_current or record is None or parsed is None:
            return TailoringDraftReview(
                state="needs_reevaluation",
                cv_revision=draft.revision or 1,
                candidate_hash=candidate_hash,
                render_basis_hash=render_basis_hash,
                fit_review=fit_review,
                fit_review_applicability=applicability,
            )
        scanner_result, evaluation, _ = parsed
        return TailoringDraftReview(
            state="current",
            cv_revision=draft.revision or 1,
            candidate_hash=candidate_hash,
            render_basis_hash=render_basis_hash,
            evaluation_id=record.id,
            evaluation=evaluation,
            scanner_result=scanner_result,
            warnings=list(record.render_warnings or []),
            pdf_sha256=record.pdf_sha256,
            fit_review=fit_review,
            fit_review_applicability=applicability,
        )

    @staticmethod
    def _fit_review_from_submission(session: TailoringSession) -> FitReviewReport | None:
        payload = TailoringService._submission_payload(session)
        if payload is None or payload.get("fit_review") is None:
            return None
        try:
            return _FIT_REVIEW_ADAPTER.validate_python(payload["fit_review"])
        except (TypeError, ValueError, ValidationError):
            return None

    async def _release_session_replacement(self, session: TailoringSession) -> bool:
        quota = QuotaService(self.db)
        released = False
        if session.cv_id is not None:
            released = await quota.release_replacement(
                session.user_id,
                session.application_id,
                source_cv_id=session.cv_id,
                draft_cv_id=session.draft_cv_id,
                retire_draft=False,
            )
        if not released and session.draft_cv_id is not None:
            released = await quota.release_replacement(
                session.user_id,
                session.application_id,
                draft_cv_id=session.draft_cv_id,
                retire_draft=False,
            )
        return released

    async def _reconcile_pending_draft(
        self,
        session: TailoringSession,
        *,
        unavailable: bool = False,
    ) -> bool:
        """Persist a missing or stale submitted draft without rolling it back."""

        now = _utcnow()
        await QuotaService(self.db).ensure_write_transaction()
        async with self.db.begin_nested():
            values: dict[str, Any] = {
                "status": TAILORING_SESSION_STALE,
                "owner_review_state": "unavailable" if unavailable else "needs_reevaluation",
                "updated_at": now,
            }
            if unavailable:
                values.update(
                    owner_cv_revision=None,
                    owner_candidate_hash=None,
                    owner_render_basis_hash=None,
                    owner_evaluation_id=None,
                    owner_pdf_sha256=None,
                )
            result = await self.db.execute(
                update(TailoringSession)
                .where(
                    TailoringSession.id == session.id,
                    TailoringSession.user_id == session.user_id,
                    TailoringSession.status.in_(
                        (TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE, TAILORING_SESSION_EXPIRED)
                    ),
                )
                .values(**values)
            )
            if result.rowcount == 1:
                session.status = TAILORING_SESSION_STALE
                session.owner_review_state = values["owner_review_state"]
                session.updated_at = now
                if unavailable:
                    session.owner_cv_revision = None
                    session.owner_candidate_hash = None
                    session.owner_render_basis_hash = None
                    session.owner_evaluation_id = None
                    session.owner_pdf_sha256 = None
                await self._release_session_replacement(session)
                if unavailable:
                    await self._prune_terminal_preview_data(session.id, now)
                await self.db.flush()
                return True
        return False

    async def reconcile_deleted_draft(self, cv_id: str, user_id: str) -> None:
        """Reconcile pending owner sessions in the CV delete transaction."""

        result = await self.db.execute(
            select(TailoringSession).where(
                TailoringSession.user_id == user_id,
                TailoringSession.draft_cv_id == cv_id,
                TailoringSession.status.in_((TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE)),
            )
        )
        sessions = list(result.scalars().all())
        if not sessions:
            return
        for session in sessions:
            await self._reconcile_pending_draft(session, unavailable=True)

    async def _prune_terminal_preview_data(self, session_id: str, now: datetime) -> None:
        """Expire held leases and lazily drop private PDFs after termination."""

        await self.db.execute(
            update(TailoringPreviewReservation)
            .where(
                TailoringPreviewReservation.session_id == session_id,
                TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
            )
            .values(state=TAILORING_PREVIEW_RESERVATION_EXPIRED, updated_at=now)
        )
        await self.db.execute(
            update(TailoringEvaluationRecord)
            .where(TailoringEvaluationRecord.session_id == session_id)
            .values(pdf_bytes=None)
        )

    async def session_status(self, session_id: str, user_id: str) -> TailoringSessionStatusResponse:
        session = await self._owned_session(session_id, user_id)
        now = _utcnow()
        terminal_status: str | None = None
        if (
            session.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
            and _as_utc(session.expires_at) <= now
        ):
            terminal_status = TAILORING_SESSION_EXPIRED
        elif session.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
            try:
                parts = await self._context_parts(session)
                if session.context_hash and parts["context_hash"] != session.context_hash:
                    terminal_status = TAILORING_SESSION_STALE
            except (TailoringConflictError, TailoringUnavailableError, TailoringStaleError):
                terminal_status = TAILORING_SESSION_STALE
        if terminal_status is not None:
            await QuotaService(self.db).ensure_write_transaction()
            session.status = terminal_status
            session.updated_at = now
            await self.db.flush()
            await self._prune_terminal_preview_data(session.id, now)
        draft_review: TailoringDraftReview | None = None
        if (
            session.protocol_version == PROTOCOL_VERSION
            and session.status in {TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE}
            and session.draft_cv_id
        ):
            draft = await self._owned_cv(session.draft_cv_id, user_id)
            if draft is None:
                await self._reconcile_pending_draft(session, unavailable=True)
                draft_review = TailoringDraftReview(state="unavailable")
            else:
                try:
                    parts, profile, manifests = await self._current_owner_inputs(session)
                    draft_review = await self._draft_review(
                        session,
                        draft,
                        parts=parts,
                        profile=profile,
                        manifests=manifests,
                    )
                except (TailoringStaleError, TailoringConflictError, TailoringUnavailableError):
                    await self._reconcile_pending_draft(session)
                    fit_review = self._fit_review_from_submission(session)
                    draft_review = TailoringDraftReview(
                        state="needs_reevaluation",
                        cv_revision=draft.revision or 1,
                        candidate_hash=self._candidate_hash(self._persisted_candidate(draft)),
                        fit_review=fit_review,
                        fit_review_applicability="earlier_version" if fit_review is not None else "not_run",
                    )
                if draft_review.state != "current" and session.owner_review_state == "current":
                    await QuotaService(self.db).ensure_write_transaction()
                    session.owner_review_state = "needs_reevaluation"
                    session.updated_at = now
                    await self.db.flush()
        return self._status_response(session, draft_review)

    async def latest_session_status(
        self, application_id: str, user_id: str
    ) -> TailoringSessionStatusResponse:
        """Return the newest owner-visible draft session for an application."""

        application = await self._owned_application(application_id, user_id)
        if application is None:
            raise TailoringNotFoundError("Application not found")
        result = await self.db.execute(
            select(TailoringSession)
            .where(
                TailoringSession.application_id == application_id,
                TailoringSession.user_id == user_id,
            )
            .order_by(TailoringSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringSessionNotFoundError("Tailoring session not found")
        return await self.session_status(session.id, user_id)

    async def cancel_session(self, session_id: str, user_id: str) -> TailoringSessionStatusResponse:
        session = await self._owned_session(session_id, user_id)
        if session.status == TAILORING_SESSION_EXPIRED:
            raise TailoringExpiredError("Tailoring session expired")
        if session.status not in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
            raise TailoringConflictError("Tailoring session cannot be cancelled")
        now = _utcnow()
        await QuotaService(self.db).ensure_write_transaction()
        result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.user_id == user_id,
                TailoringSession.status.in_((TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED)),
                TailoringSession.expires_at > _db_utcnow(),
            )
            .values(status=TAILORING_SESSION_CANCELLED, updated_at=now)
        )
        if result.rowcount != 1:
            raise TailoringConflictError("Tailoring session cannot be cancelled")
        now = _utcnow()
        await self._prune_terminal_preview_data(session.id, now)
        await self.db.refresh(session)
        return self._status_response(session)

    async def exchange_code(self, data: TailoringCodeExchange) -> TailoringExchangeResponse:
        result = await self.db.execute(select(TailoringSession).where(TailoringSession.code_hash == hash_token(data.code)))
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring code")
        # The URL is part of the authorization resource identity. Validate it
        # before any status transition can consume this one-time code.
        if session.id != data.session_id:
            raise TailoringConflictError("The supplied link does not match this one-time code", code="invalid_session")
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol; start a new session")
        if session.status != TAILORING_SESSION_CREATED:
            raise TailoringConflictError("Tailoring code has already been exchanged")
        if _as_utc(session.expires_at) <= _utcnow():
            await QuotaService(self.db).ensure_write_transaction()
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            await self._prune_terminal_preview_data(session.id, session.updated_at)
            raise TailoringExpiredError("Tailoring session expired")
        capability = secrets.token_urlsafe(32)
        now = _utcnow()
        session_id = session.id
        protocol_version = session.protocol_version
        expires_at = session.expires_at
        code_hash = session.code_hash
        # Serialize the short compare-and-swap on SQLite while preserving any
        # work already staged by the route's caller.
        await QuotaService(self.db).ensure_write_transaction()
        result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session_id,
                TailoringSession.code_hash == code_hash,
                TailoringSession.status == TAILORING_SESSION_CREATED,
                TailoringSession.expires_at > _db_utcnow(),
            )
            .values(
                capability_hash=hash_token(capability),
                status=TAILORING_SESSION_EXCHANGED,
                exchanged_at=now,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            raise TailoringConflictError("Tailoring code has already been exchanged", code="invalid_session")
        return TailoringExchangeResponse(
            protocol_version=protocol_version,
            session_id=session_id,
            expires_at=expires_at,
            capability=capability,
        )

    async def _session_for_capability(
        self,
        capability: str | None,
        *,
        allow_draft_ready: bool = False,
    ) -> TailoringSession:
        if not capability or len(capability) > 128:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        result = await self.db.execute(
            select(TailoringSession).where(TailoringSession.capability_hash == hash_token(capability.strip()))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        if _as_utc(session.expires_at) <= _utcnow():
            if session.status != TAILORING_SESSION_DRAFT_READY:
                now = _utcnow()
                await QuotaService(self.db).ensure_write_transaction()
                session.status = TAILORING_SESSION_EXPIRED
                session.updated_at = now
                await self.db.flush()
                await self._prune_terminal_preview_data(session.id, now)
            raise TailoringExpiredError("Tailoring session expired")
        if session.status != TAILORING_SESSION_EXCHANGED and not (
            allow_draft_ready and session.status == TAILORING_SESSION_DRAFT_READY
        ):
            raise TailoringConflictError("Tailoring capability is no longer active")
        return session

    async def _mark_session_stale(self, session: TailoringSession) -> None:
        if session.status != TAILORING_SESSION_EXCHANGED:
            return
        now = _utcnow()
        await QuotaService(self.db).ensure_write_transaction()
        result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.status == TAILORING_SESSION_EXCHANGED,
            )
            .values(status=TAILORING_SESSION_STALE, updated_at=now)
        )
        if result.rowcount == 1:
            session.status = TAILORING_SESSION_STALE
            session.updated_at = now
            await self._prune_terminal_preview_data(session.id, now)

    async def _current_context(self, session: TailoringSession) -> dict[str, Any]:
        try:
            parts = await self._context_parts(session)
        except TailoringStaleError as exc:
            await self._mark_session_stale(session)
            raise TailoringStaleError(str(exc), code=exc.code, commit_outcome=True) from exc
        if not session.context_hash:
            session.context_hash = parts["context_hash"]
        if parts["context_hash"] != session.context_hash:
            await self._mark_session_stale(session)
            raise TailoringStaleError(
                "The tailoring context changed; start a new session",
                commit_outcome=True,
            )
        return parts

    async def _agent_evaluations(self, session_id: str) -> list[TailoringEvaluationRecord]:
        result = await self.db.execute(
            select(TailoringEvaluationRecord)
            .where(
                TailoringEvaluationRecord.session_id == session_id,
                TailoringEvaluationRecord.kind == TAILORING_EVALUATION_AGENT_PREVIEW,
            )
            .order_by(TailoringEvaluationRecord.created_at.asc(), TailoringEvaluationRecord.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _evaluation_record_state(record: TailoringEvaluationRecord) -> dict[str, Any]:
        return {
            "evaluation_id": record.id,
            "candidate_hash": record.candidate_hash,
            "scanner_result": record.scanner_result,
            "evaluation": record.evaluation,
        }

    @staticmethod
    def _parse_evaluation_record(
        state: Mapping[str, Any],
    ) -> tuple[ScanResult, TailoringEvaluation, str] | None:
        try:
            scanner = ScanResult.model_validate(state["scanner_result"])
            evaluation = TailoringEvaluation.model_validate(state["evaluation"])
            candidate_hash = str(state["candidate_hash"])
        except (KeyError, TypeError, ValueError, ValidationError):
            return None
        if evaluation.candidate_hash != candidate_hash or scanner.schema_version != "scanner-v1":
            return None
        return scanner, evaluation, candidate_hash

    @staticmethod
    def _record_evaluation_payload(record: TailoringEvaluationRecord) -> tuple[ScanResult, TailoringEvaluation, str] | None:
        try:
            scanner = ScanResult.model_validate(record.scanner_result)
            evaluation = TailoringEvaluation.model_validate(record.evaluation)
        except (TypeError, ValueError, ValidationError):
            return None
        if evaluation.candidate_hash != record.candidate_hash or scanner.schema_version != "scanner-v1":
            return None
        return scanner, evaluation, record.candidate_hash

    async def _evaluate_candidate(
        self,
        session_id: str,
        parts: Mapping[str, Any],
        candidate: Mapping[str, Any],
        pdf: bytes | None,
        *,
        render_warnings: Sequence[str] = (),
        previous_record: Mapping[str, Any] | None = None,
    ) -> tuple[ScanResult, TailoringEvaluation]:
        scanner_result = await self._scan_candidate(parts, candidate, pdf)
        if previous_record is None:
            prior_records = await self._agent_evaluations(session_id)
            previous_record = self._evaluation_record_state(prior_records[-1]) if prior_records else None
        previous = self._parse_evaluation_record(previous_record) if previous_record is not None else None
        evaluation = evaluate_tailoring(
            parts["scanner_context"].requirement_extraction,
            scanner_result,
            self._candidate_hash(candidate),
            source_scan=parts["scanner_context"].source_scan,
            previous_candidate_scan=previous[0] if previous else None,
            previous_candidate_hash=previous[2] if previous else None,
            previous_evaluation=previous[1] if previous else None,
            current_candidate=candidate,
            source_cv=parts["source_cv"],
            library=parts["authoritative_library"],
            render_warnings=render_warnings,
            user_instructions=parts["application"].notes,
        )
        return scanner_result, evaluation

    async def context(self, capability: str | None) -> TailoringContextResponse:
        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        application: Application = parts["application"]
        source_cv: SimpleNamespace | None = parts["source_cv"]
        templates = [
            TailoringTemplate(
                id=template.id,
                name=template.name,
                description=template.description,
                manifest=parts["manifest_by_id"][template.id],
            )
            for template in parts["templates"]
            if template.id in parts["manifest_by_id"]
        ]
        return TailoringContextResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            source_cv_id=source_cv.id if source_cv else None,
            source_cv_revision=parts["source_cv_revision"],
            expires_at=session.expires_at,
            context_hash=parts["context_hash"],
            job=TailoringJob(
                company=application.company,
                role=application.role,
                job_url=application.job_url,
                description=application.job_description,
                user_instructions=application.notes,
            ),
            dossier=_build_dossier(
                parts["profile_data"],
                parts["libraries"],
                _source_cv_snapshot(source_cv),
            ),
            templates=templates,
            selected_template_id=parts["selected_template_id"],
            selected_template_manifest=copy.deepcopy(
                parts["manifest_by_id"][parts["selected_template_id"]]
            ),
            capabilities=parts["capabilities"],
            capabilities_hash=capabilities_hash(parts["capabilities"]),
            scanner_context=parts["scanner_context"],
            evaluation_version=TAILORING_EVALUATION_VERSION,
        )

    @staticmethod
    def _inject_profile_identity(
        sections: list[dict[str, Any]],
        profile: Any,
    ) -> list[dict[str, Any]]:
        profile_data = profile.model_dump(mode="json", exclude_none=True)
        profile_sections = [section for section in sections if section.get("type") == "profile"]
        if len(profile_sections) != 1:
            raise TailoringCandidateError("A candidate must contain exactly one profile section")
        profile_section = profile_sections[0]
        if profile_section.get("enabled") is not True:
            raise TailoringCandidateError("The profile section must remain enabled")
        data = profile_section.get("data")
        if not isinstance(data, dict):
            raise TailoringCandidateError("The profile section must contain object data")
        # Fixed identity and direct contact fields are server-owned. The
        # profile title is the candidate-authored professional headline.
        for key in (
            "name",
            "email",
            "phone",
            "site_text",
            "site_url",
            "email_link",
            "social_links",
            "photo_url",
        ):
            if key in profile_data:
                data[key] = copy.deepcopy(profile_data[key])
            else:
                data.pop(key, None)
        return sections

    @staticmethod
    def _normalize_tailoring_rich_text_ids(raw_sections: Any) -> Any:
        """Fill missing/duplicate rich-text IDs deterministically for retries.

        Ordinary CV writes retain their random-ID behavior. A tailoring
        reservation hashes the normalized complete candidate before preview,
        so the same raw request must normalize identically at reservation,
        render, and retry boundaries. Existing unique IDs remain untouched.
        """

        normalized = copy.deepcopy(raw_sections)
        if not isinstance(normalized, list):
            return normalized

        def stable_id(prefix: str, path: tuple[int | str, ...], value: Mapping[str, Any]) -> str:
            identity = {
                "path": path,
                "value": {key: child for key, child in value.items() if key != "id"},
            }
            seed = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, 'aergia-tailoring-v10:' + seed).hex}"

        for section_index, section in enumerate(normalized):
            if not isinstance(section, dict):
                continue
            fields = rich_text_fields_for_section(str(section.get("type", "")))
            data = section.get("data")
            rows = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
            for row_index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                for field_name in sorted(fields):
                    blocks = row.get(field_name)
                    if not isinstance(blocks, list):
                        continue
                    block_ids: set[str] = set()
                    for block_index, block in enumerate(blocks):
                        if not isinstance(block, dict):
                            continue
                        block_id = block.get("id")
                        if not isinstance(block_id, str) or not block_id.strip() or len(block_id) > 128 or block_id in block_ids:
                            block["id"] = stable_id(
                                "rtb",
                                (section_index, section.get("type", ""), row_index, field_name, block_index),
                                block,
                            )
                            block_id = block["id"]
                        block_ids.add(block_id)

                        items = block.get("items")
                        if not isinstance(items, list):
                            continue
                        item_ids: set[str] = set()
                        for item_index, item in enumerate(items):
                            if not isinstance(item, dict):
                                continue
                            item_id = item.get("id")
                            if not isinstance(item_id, str) or not item_id.strip() or len(item_id) > 128 or item_id in item_ids:
                                item["id"] = stable_id(
                                    "rti",
                                    (section_index, section.get("type", ""), row_index, field_name, block_index, item_index),
                                    item,
                                )
                                item_id = item["id"]
                            item_ids.add(item_id)
        return normalized

    @classmethod
    def _normalize_candidate(
        cls,
        candidate: TailoringCandidateCV,
        parts: Mapping[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        candidate_data = _candidate_dict(candidate)
        template_id = candidate_data.get("template_id")
        if template_id not in parts["manifest_by_id"]:
            raise TailoringCandidateError("Candidate template is not available")
        raw_sections, _ = normalize_rich_text_ids(
            cls._normalize_tailoring_rich_text_ids(candidate_data.get("sections", []))
        )
        if not isinstance(raw_sections, list) or len(raw_sections) > LIMITS["max_sections"]:
            raise TailoringCandidateError("Candidate contains too many sections")
        sections = _sections_as_dicts(raw_sections)
        ids = [section.get("id") for section in sections]
        if any(not isinstance(section_id, str) for section_id in ids) or len(set(ids)) != len(ids):
            raise TailoringCandidateError("Candidate section IDs must be unique")
        for section in sections:
            try:
                validate_section_payload(section)
                SectionInstance.model_validate(section)
            except (CandidateValidationError, ValidationError) as exc:
                raise TailoringCandidateError(str(exc)) from exc
        sections = cls._inject_profile_identity(sections, parts["profile"])
        try:
            customizations = coerce_customizations(candidate_data.get("customizations"))
        except (TypeError, ValueError, ValidationError) as exc:
            raise TailoringCandidateError("Candidate customizations are invalid") from exc
        # CVService adds the template's default zone layout when persisting a
        # draft. Apply the same deterministic default before preview scanning
        # so candidate and persisted CV fingerprints are identical.
        if customizations.layout is None:
            manifest = parts["manifest_by_id"].get(template_id) or {}
            zones = manifest.get("zones") or []
            placement_by_type = manifest.get("placement") or {}
            placement = {
                section["id"]: placement_by_type[section["type"]]
                for section in sections
                if isinstance(section, dict)
                and isinstance(section.get("id"), str)
                and isinstance(section.get("type"), str)
                and isinstance(placement_by_type.get(section["type"]), str)
            }
            if zones:
                customizations = coerce_customizations(
                    {
                        **customizations.model_dump(mode="json", exclude_none=True),
                        "layout": {"zones": zones, "placement": placement},
                    }
                )
        candidate_data["sections"] = sections
        candidate_data["customizations"] = customizations.model_dump(mode="json", exclude_none=True)
        candidate_data.pop("id", None)
        # Re-validate after identity injection and normalization.
        try:
            normalized_candidate = TailoringCandidateCV.model_validate(candidate_data)
        except ValidationError as exc:
            raise TailoringCandidateError("Candidate is invalid after server-owned fields were applied") from exc
        payload_size = len(json.dumps(candidate_data, ensure_ascii=False, separators=(",", ":")))
        if payload_size > 750_000:
            raise TailoringCandidateError("Candidate exceeds the maximum document size")
        return _candidate_dict(normalized_candidate), sections

    @staticmethod
    def _candidate_hash(candidate: Mapping[str, Any]) -> str:
        return _content_hash(candidate)

    async def _scan_candidate(
        self,
        parts: Mapping[str, Any],
        candidate: Mapping[str, Any],
        pdf: bytes | None,
    ) -> ScanResult:
        application: Application = parts["application"]
        return await asyncio.to_thread(
            self.scanner_service.scan_with_extraction,
            application.job_description,
            canonicalize_scanner_cv(candidate),
            parts["scanner_context"].requirement_extraction,
            pdf_bytes=pdf,
            render_manifest=parts["manifest_by_id"][candidate["template_id"]],
        )

    async def _successful_preview_count(self, session_id: str) -> int:
        count = await self.db.scalar(
            select(func.count(TailoringEvaluationRecord.id)).where(
                TailoringEvaluationRecord.session_id == session_id,
                TailoringEvaluationRecord.kind == TAILORING_EVALUATION_AGENT_PREVIEW,
            )
        )
        return int(count or 0)

    @staticmethod
    def _reservation_response(reservation: TailoringPreviewReservation) -> TailoringPreviewReservationResponse:
        return TailoringPreviewReservationResponse(
            reservation_id=reservation.id,
            candidate_hash=reservation.candidate_hash,
            expires_at=_as_utc(reservation.expires_at),
        )

    async def reserve_preview(
        self,
        capability: str | None,
        request: TailoringPreviewReservationRequest,
    ) -> TailoringPreviewReservationResponse:
        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session", code="context_mismatch")
        candidate, _sections = self._normalize_candidate(request.candidate, parts)
        candidate_hash = self._candidate_hash(candidate)
        session_id = session.id
        context_hash = parts["context_hash"]
        session_expiry = _as_utc(session.expires_at)
        request_id = str(request.request_id)
        now = _utcnow()
        lease_expiry = min(now + TAILORING_PREVIEW_LEASE_TTL, session_expiry)
        if lease_expiry <= now:
            raise TailoringExpiredError("Tailoring session expired")

        # Start a short SQLite write transaction if this route has not already
        # staged caller-owned work; never roll back the route's transaction.
        await QuotaService(self.db).ensure_write_transaction()
        reservation = TailoringPreviewReservation(
            session_id=session_id,
            request_id=request_id,
            context_hash=context_hash,
            candidate_hash=candidate_hash,
            expires_at=lease_expiry,
            state=TAILORING_PREVIEW_RESERVATION_ACTIVE,
        )
        try:
            async with self.db.begin_nested():
                self.db.add(reservation)
                await self.db.flush()
                if await self._successful_preview_count(session_id) >= TAILORING_AGENT_PREVIEW_LIMIT:
                    raise _PreviewLimitReached
            return self._reservation_response(reservation)
        except _PreviewLimitReached as exc:
            raise TailoringConflictError(
                "The five-successful-preview limit has been reached",
                code="preview_limit",
            ) from exc
        except IntegrityError as exc:
            existing_result = await self.db.execute(
                select(TailoringPreviewReservation).where(
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.request_id == request_id,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                if existing.candidate_hash != candidate_hash or existing.context_hash != context_hash:
                    raise TailoringConflictError(
                        "This request ID was already used for a different candidate or context",
                        code="request_id_reused",
                    ) from exc
                if existing.state == TAILORING_PREVIEW_RESERVATION_COMPLETED:
                    return self._reservation_response(existing)
                if (
                    existing.state == TAILORING_PREVIEW_RESERVATION_ACTIVE
                    and _as_utc(existing.expires_at) > now
                ):
                    return self._reservation_response(existing)

                reclaimable = existing.state in {
                    TAILORING_PREVIEW_RESERVATION_RELEASED,
                    TAILORING_PREVIEW_RESERVATION_EXPIRED,
                } or (
                    existing.state == TAILORING_PREVIEW_RESERVATION_ACTIVE
                    and _as_utc(existing.expires_at) <= now
                )
                if reclaimable:
                    old_state = existing.state
                    old_expiry = existing.expires_at
                    old_updated_at = existing.updated_at
                    lease_fence = _next_lease_fence(_as_utc(old_updated_at), now)
                    try:
                        await QuotaService(self.db).ensure_write_transaction()
                        async with self.db.begin_nested():
                            reclaimed = await self.db.execute(
                                update(TailoringPreviewReservation)
                                .where(
                                    TailoringPreviewReservation.id == existing.id,
                                    TailoringPreviewReservation.state == old_state,
                                    TailoringPreviewReservation.expires_at == old_expiry,
                                    TailoringPreviewReservation.updated_at == old_updated_at,
                                )
                                .values(
                                    state=TAILORING_PREVIEW_RESERVATION_ACTIVE,
                                    expires_at=lease_expiry,
                                    updated_at=lease_fence,
                                )
                            )
                            if reclaimed.rowcount != 1:
                                raise _FencedPreviewCompletion
                            if await self._successful_preview_count(session_id) >= TAILORING_AGENT_PREVIEW_LIMIT:
                                raise _PreviewLimitReached
                    except _PreviewLimitReached as limit_exc:
                        raise TailoringConflictError(
                            "The five-successful-preview limit has been reached",
                            code="preview_limit",
                        ) from limit_exc
                    except _FencedPreviewCompletion:
                        pass
                    else:
                        await self.db.refresh(existing)
                        return self._reservation_response(existing)

                    refreshed = await self.db.get(TailoringPreviewReservation, existing.id)
                    if refreshed is not None:
                        if refreshed.state == TAILORING_PREVIEW_RESERVATION_COMPLETED:
                            return self._reservation_response(refreshed)
                        if (
                            refreshed.state == TAILORING_PREVIEW_RESERVATION_ACTIVE
                            and _as_utc(refreshed.expires_at) > _utcnow()
                        ):
                            return self._reservation_response(refreshed)

            active_result = await self.db.execute(
                select(TailoringPreviewReservation).where(
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                    TailoringPreviewReservation.expires_at > _db_utcnow(),
                )
            )
            if active_result.scalar_one_or_none() is not None:
                raise TailoringConflictError(
                    "Another preview is in progress; retry this request with the same request ID",
                    code="preview_in_progress",
                ) from exc

            # A different request can take over an expired active lease. The
            # state transition and new reservation share one short savepoint,
            # so at most one contender can replace the expired holder.
            expired_result = await self.db.execute(
                select(TailoringPreviewReservation).where(
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                )
            )
            expired = expired_result.scalar_one_or_none()
            if expired is not None and _as_utc(expired.expires_at) <= now:
                old_expiry = expired.expires_at
                old_updated_at = expired.updated_at
                try:
                    await QuotaService(self.db).ensure_write_transaction()
                    async with self.db.begin_nested():
                        reclaimed = await self.db.execute(
                            update(TailoringPreviewReservation)
                            .where(
                                TailoringPreviewReservation.id == expired.id,
                                TailoringPreviewReservation.session_id == session_id,
                                TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                                TailoringPreviewReservation.expires_at == old_expiry,
                                TailoringPreviewReservation.updated_at == old_updated_at,
                                TailoringPreviewReservation.expires_at <= _db_utcnow(),
                            )
                            .values(
                                state=TAILORING_PREVIEW_RESERVATION_EXPIRED,
                                updated_at=_next_lease_fence(_as_utc(old_updated_at), now),
                            )
                        )
                        if reclaimed.rowcount != 1:
                            raise _FencedPreviewCompletion
                        replacement = TailoringPreviewReservation(
                            session_id=session_id,
                            request_id=request_id,
                            context_hash=context_hash,
                            candidate_hash=candidate_hash,
                            expires_at=lease_expiry,
                            state=TAILORING_PREVIEW_RESERVATION_ACTIVE,
                        )
                        self.db.add(replacement)
                        await self.db.flush()
                        if await self._successful_preview_count(session_id) >= TAILORING_AGENT_PREVIEW_LIMIT:
                            raise _PreviewLimitReached
                    return self._reservation_response(replacement)
                except _PreviewLimitReached as limit_exc:
                    raise TailoringConflictError(
                        "The five-successful-preview limit has been reached",
                        code="preview_limit",
                    ) from limit_exc
                except _FencedPreviewCompletion:
                    active_result = await self.db.execute(
                        select(TailoringPreviewReservation).where(
                            TailoringPreviewReservation.session_id == session_id,
                            TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                            TailoringPreviewReservation.expires_at > _db_utcnow(),
                        )
                    )
                    if active_result.scalar_one_or_none() is not None:
                        raise TailoringConflictError(
                            "Another preview is in progress; retry this request with the same request ID",
                            code="preview_in_progress",
                        ) from exc
            raise

    async def release_preview_reservation(
        self,
        capability: str | None,
        reservation_id: str,
    ) -> TailoringPreviewReservationReleaseResponse:
        session = await self._session_for_capability(capability)
        result = await self.db.execute(
            select(TailoringPreviewReservation).where(TailoringPreviewReservation.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        if reservation is None or reservation.session_id != session.id:
            raise TailoringConflictError("Preview reservation is not available to this session")
        if reservation.state == TAILORING_PREVIEW_RESERVATION_COMPLETED:
            return TailoringPreviewReservationReleaseResponse(reservation_id=reservation.id, state="completed")
        now = _utcnow()
        session_id = session.id
        prior_state = reservation.state
        prior_expiry = reservation.expires_at
        prior_updated_at = reservation.updated_at
        already_released = prior_state in {
            TAILORING_PREVIEW_RESERVATION_RELEASED,
            TAILORING_PREVIEW_RESERVATION_EXPIRED,
        }
        if not already_released:
            await QuotaService(self.db).ensure_write_transaction()
            final_state = (
                TAILORING_PREVIEW_RESERVATION_RELEASED
                if _as_utc(prior_expiry) > now
                else TAILORING_PREVIEW_RESERVATION_EXPIRED
            )
            released = await self.db.execute(
                update(TailoringPreviewReservation)
                .where(
                    TailoringPreviewReservation.id == reservation_id,
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                    TailoringPreviewReservation.expires_at == prior_expiry,
                    TailoringPreviewReservation.updated_at == prior_updated_at,
                )
                .values(state=final_state, updated_at=now)
            )
            if released.rowcount == 1:
                return TailoringPreviewReservationReleaseResponse(
                    reservation_id=reservation_id,
                    state="released" if final_state == TAILORING_PREVIEW_RESERVATION_RELEASED else "already_released",
                )
        latest = await self.db.get(TailoringPreviewReservation, reservation_id)
        if latest is not None and latest.state == TAILORING_PREVIEW_RESERVATION_COMPLETED:
            state = "completed"
        else:
            state = "already_released"
        return TailoringPreviewReservationReleaseResponse(reservation_id=reservation_id, state=state)

    @staticmethod
    def _frozen_candidate_parts(session: TailoringSession) -> dict[str, Any]:
        snapshot = session.context_snapshot
        if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("basis"), Mapping):
            raise TailoringStaleError("The frozen tailoring context is invalid; start a new session")
        basis = snapshot["basis"]
        manifests = {
            item["id"]: copy.deepcopy(item["manifest"])
            for item in basis.get("templates", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str) and isinstance(item.get("manifest"), Mapping)
        }
        try:
            profile = UserProfile.model_validate(basis["profile"])
        except (KeyError, TypeError, ValidationError) as exc:
            raise TailoringStaleError("The frozen tailoring context is invalid; start a new session") from exc
        return {"manifest_by_id": manifests, "profile": profile}

    @staticmethod
    def _preview_response(record: TailoringEvaluationRecord) -> TailoringPreviewResponse:
        if record.pdf_bytes is None or hashlib.sha256(record.pdf_bytes).hexdigest() != record.pdf_sha256:
            raise TailoringConflictError(
                "The saved preview PDF is no longer available for replay",
                code="reservation_conflict",
            )
        try:
            scanner_result = ScanResult.model_validate(record.scanner_result)
            evaluation = TailoringEvaluation.model_validate(record.evaluation)
            candidate = TailoringCandidateCV.model_validate(record.candidate)
        except (TypeError, ValueError, ValidationError) as exc:
            raise TailoringConflictError("The saved preview record is invalid", code="reservation_conflict") from exc
        return TailoringPreviewResponse(
            pdf_base64=base64.b64encode(record.pdf_bytes).decode("ascii"),
            page_count=record.page_count,
            evaluation_id=record.id,
            candidate_hash=record.candidate_hash,
            pdf_sha256=record.pdf_sha256,
            candidate=candidate,
            scanner_result=scanner_result,
            evaluation=evaluation,
            render_warnings=record.render_warnings,
        )

    async def _release_preview_lease(
        self,
        reservation_id: str,
        session_id: str,
        lease_expiry: datetime,
        lease_fence: datetime,
    ) -> None:
        now = _utcnow()
        await QuotaService(self.db).ensure_write_transaction()
        final_state = (
            TAILORING_PREVIEW_RESERVATION_RELEASED
            if _as_utc(lease_expiry) > now
            else TAILORING_PREVIEW_RESERVATION_EXPIRED
        )
        await self.db.execute(
            update(TailoringPreviewReservation)
            .where(
                TailoringPreviewReservation.id == reservation_id,
                TailoringPreviewReservation.session_id == session_id,
                TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                TailoringPreviewReservation.expires_at == lease_expiry,
                TailoringPreviewReservation.updated_at == lease_fence,
            )
            .values(state=final_state, updated_at=now)
        )

    async def candidate_preview(
        self,
        capability: str | None,
        request: TailoringPreviewRequest,
    ) -> TailoringPreviewResponse:
        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        reservation_result = await self.db.execute(
            select(TailoringPreviewReservation).where(
                TailoringPreviewReservation.id == request.reservation_id,
                TailoringPreviewReservation.session_id == session.id,
            )
        )
        reservation = reservation_result.scalar_one_or_none()
        if reservation is None:
            raise TailoringConflictError("Preview reservation is not available to this session")
        if request.context_hash != reservation.context_hash:
            raise TailoringConflictError("This reservation belongs to a different context", code="request_id_reused")

        if reservation.state == TAILORING_PREVIEW_RESERVATION_COMPLETED:
            frozen_parts = self._frozen_candidate_parts(session)
            candidate, _sections = self._normalize_candidate(request.candidate, frozen_parts)
            if self._candidate_hash(candidate) != reservation.candidate_hash:
                raise TailoringConflictError("This reservation belongs to a different candidate", code="request_id_reused")
            record = await self.db.scalar(
                select(TailoringEvaluationRecord).where(
                    TailoringEvaluationRecord.reservation_id == reservation.id,
                    TailoringEvaluationRecord.session_id == session.id,
                )
            )
            if record is None:
                raise TailoringConflictError("The completed preview record is unavailable")
            return self._preview_response(record)

        now = _utcnow()
        if reservation.state != TAILORING_PREVIEW_RESERVATION_ACTIVE:
            raise TailoringConflictError(
                "The preview reservation is no longer active; retry the same request ID to reacquire it",
                code="reservation_expired",
            )
        if _as_utc(reservation.expires_at) <= now:
            reservation_id = reservation.id
            session_id = session.id
            lease_expiry = reservation.expires_at
            lease_fence = reservation.updated_at
            await QuotaService(self.db).ensure_write_transaction()
            await self.db.execute(
                update(TailoringPreviewReservation)
                .where(
                    TailoringPreviewReservation.id == reservation_id,
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                    TailoringPreviewReservation.expires_at == lease_expiry,
                    TailoringPreviewReservation.updated_at == lease_fence,
                    TailoringPreviewReservation.expires_at <= _db_utcnow(),
                )
                .values(state=TAILORING_PREVIEW_RESERVATION_EXPIRED, updated_at=now)
            )
            raise TailoringConflictError(
                "The preview reservation expired; retry the same request ID to reacquire it",
                code="reservation_expired",
                commit_outcome=True,
            )

        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session", code="context_mismatch")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        candidate_hash = self._candidate_hash(candidate)
        if candidate_hash != reservation.candidate_hash:
            raise TailoringConflictError("This reservation belongs to a different candidate", code="request_id_reused")

        session_id = session.id
        reservation_id = reservation.id
        lease_expiry = reservation.expires_at
        lease_fence = reservation.updated_at
        context_hash = parts["context_hash"]
        prior_evaluations = await self._agent_evaluations(session_id)
        previous_record = self._evaluation_record_state(prior_evaluations[-1]) if prior_evaluations else None
        # All values used while rendering are copied from the frozen context.
        # No database writes happen during scanner/Chromium work, so keep the
        # route-owned transaction intact and write the ledger only afterward.
        preview_parts = dict(parts)
        preview_parts["application"] = SimpleNamespace(
            job_description=parts["application"].job_description,
            notes=parts["application"].notes,
        )
        try:
            async with asyncio.timeout(TAILORING_PREVIEW_TIMEOUT_SECONDS):
                pdf = await PDFService(self.db).render_manifest_payload(
                    preview_parts["manifest_by_id"][candidate["template_id"]],
                    sections,
                    candidate["customizations"],
                )
                page_count = pdf_page_count(pdf)
                scanner_result, evaluation = await self._evaluate_candidate(
                    session_id,
                    preview_parts,
                    candidate,
                    pdf,
                    previous_record=previous_record,
                )
        except asyncio.CancelledError:
            try:
                await asyncio.shield(
                    self._release_preview_lease(reservation_id, session_id, lease_expiry, lease_fence)
                )
            finally:
                raise
        except TimeoutError as exc:
            await self._release_preview_lease(reservation_id, session_id, lease_expiry, lease_fence)
            raise TailoringPreviewUnavailableError(
                "Preview timed out; retry with the same request ID and candidate"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - release the failed lease without spending a slot
            await self._release_preview_lease(reservation_id, session_id, lease_expiry, lease_fence)
            if isinstance(exc, TailoringCandidateError):
                exc.commit_outcome = True
                raise
            raise TailoringPreviewUnavailableError(
                "The candidate could not be rendered and scanned; retry with the same request ID"
            ) from exc

        evaluation_id = secrets.token_urlsafe(24)
        pdf_sha256 = hashlib.sha256(pdf).hexdigest()
        record = TailoringEvaluationRecord(
            id=evaluation_id,
            session_id=session_id,
            kind=TAILORING_EVALUATION_AGENT_PREVIEW,
            reservation_id=reservation_id,
            candidate_hash=candidate_hash,
            candidate=candidate,
            scanner_result=scanner_result.model_dump(mode="json"),
            evaluation=evaluation.model_dump(mode="json"),
            render_warnings=evaluation.render_warnings,
            page_count=page_count,
            pdf_sha256=pdf_sha256,
            pdf_bytes=pdf,
        )
        try:
            await QuotaService(self.db).ensure_write_transaction()
            # The live target can change while Chromium or scanning is
            # running. Start the short completion transaction, lock the
            # guarded rows on databases that support it, then revalidate so a
            # superseded target cannot consume a successful-preview slot.
            await self._lock_preview_target_rows(session)
            await self._current_context(session)
            async with self.db.begin_nested():
                self.db.add(record)
                await self.db.flush()
                completed = await self.db.execute(
                    update(TailoringPreviewReservation)
                    .where(
                        TailoringPreviewReservation.id == reservation_id,
                        TailoringPreviewReservation.session_id == session_id,
                        TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                        TailoringPreviewReservation.context_hash == context_hash,
                        TailoringPreviewReservation.candidate_hash == candidate_hash,
                        TailoringPreviewReservation.expires_at == lease_expiry,
                        TailoringPreviewReservation.updated_at == lease_fence,
                        TailoringPreviewReservation.expires_at > _db_utcnow(),
                    )
                    .values(
                        state=TAILORING_PREVIEW_RESERVATION_COMPLETED,
                        evaluation_id=evaluation_id,
                        updated_at=_utcnow(),
                    )
                )
                if completed.rowcount != 1:
                    raise _FencedPreviewCompletion
                counted_attempt = await self.db.execute(
                    update(TailoringSession)
                    .where(
                        TailoringSession.id == session_id,
                        TailoringSession.status == TAILORING_SESSION_EXCHANGED,
                        TailoringSession.expires_at > _db_utcnow(),
                    )
                    .values(
                        attempts=TailoringSession.attempts + 1,
                        updated_at=_utcnow(),
                    )
                )
                if counted_attempt.rowcount != 1:
                    raise _FencedPreviewCompletion
        except (_FencedPreviewCompletion, IntegrityError) as exc:
            saved = await self.db.scalar(
                select(TailoringEvaluationRecord).where(
                    TailoringEvaluationRecord.reservation_id == reservation_id,
                    TailoringEvaluationRecord.session_id == session_id,
                )
            )
            if saved is not None:
                return self._preview_response(saved)
            await self.db.execute(
                update(TailoringPreviewReservation)
                .where(
                    TailoringPreviewReservation.id == reservation_id,
                    TailoringPreviewReservation.session_id == session_id,
                    TailoringPreviewReservation.state == TAILORING_PREVIEW_RESERVATION_ACTIVE,
                    TailoringPreviewReservation.expires_at == lease_expiry,
                    TailoringPreviewReservation.updated_at == lease_fence,
                    TailoringPreviewReservation.expires_at <= _db_utcnow(),
                )
                .values(state=TAILORING_PREVIEW_RESERVATION_EXPIRED, updated_at=_utcnow())
            )
            raise TailoringConflictError(
                "The preview lease expired or was reclaimed before completion; retry the same request ID",
                code="reservation_expired",
                commit_outcome=True,
            ) from exc
        return self._preview_response(record)

    async def submit(
        self,
        capability: str | None,
        request: TailoringSubmitRequest,
    ) -> TailoringSubmitResponse:
        session = await self._session_for_capability(capability, allow_draft_ready=True)
        submit_request_digest = _content_hash(request.model_dump(mode="json"))
        if session.status == TAILORING_SESSION_DRAFT_READY:
            saved = self._submission_payload(session)
            if saved is None or saved.get("submit_request_digest") != submit_request_digest:
                raise TailoringConflictError("Tailoring session already has a different draft submission")
            return TailoringSubmitResponse.model_validate(
                {
                    "protocol_version": saved["protocol_version"],
                    "session_id": saved["session_id"],
                    "application_id": saved["application_id"],
                    "status": saved["status"],
                    "source_cv_id": saved.get("source_cv_id"),
                    "draft_cv_id": saved["draft_cv_id"],
                    "evaluation_id": saved["evaluation_id"],
                    "candidate_hash": saved["candidate_hash"],
                    "candidate": saved["candidate"],
                    "scanner_result": saved["scanner_result"],
                    "evaluation": saved["tailoring_evaluation"],
                    "render_warnings": saved["render_warnings"],
                    "review_notes": saved["review_notes"],
                    "fit_review": saved.get("fit_review"),
                }
            )
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        candidate_hash = self._candidate_hash(candidate)
        if request.candidate_hash != candidate_hash:
            raise TailoringStaleError("The candidate changed after preview; render the current candidate before submitting")
        history = await self._agent_evaluations(session.id)
        reviewed_index = next(
            (index for index, record in enumerate(history) if record.id == request.evaluation_id),
            None,
        )
        if reviewed_index is None:
            raise TailoringStaleError(
                "The selected evaluation is unavailable in this session; preview the candidate again",
                code="evaluation_mismatch",
            )
        selected_record = history[reviewed_index]
        reservation = await self.db.get(TailoringPreviewReservation, selected_record.reservation_id)
        if reservation is None or reservation.context_hash != request.context_hash:
            raise TailoringStaleError(
                "The selected evaluation belongs to a different tailoring context",
                code="evaluation_mismatch",
            )
        if selected_record.candidate_hash != candidate_hash:
            raise TailoringStaleError(
                "The selected evaluation belongs to a different candidate",
                code="evaluation_mismatch",
            )
        reviewed_value = self._record_evaluation_payload(selected_record)
        if reviewed_value is None:
            raise TailoringStaleError("The preview evaluation is invalid; render the candidate again")
        reviewed_scanner, reviewed_evaluation, reviewed_candidate_hash = reviewed_value
        if reviewed_evaluation.candidate_hash != candidate_hash:
            raise TailoringStaleError("The selected evaluation is bound to a different candidate")
        if selected_record.pdf_bytes is None or hashlib.sha256(selected_record.pdf_bytes).hexdigest() != selected_record.pdf_sha256:
            raise TailoringStaleError(
                "The selected preview PDF is unavailable; preview the candidate again",
                code="evaluation_mismatch",
            )
        try:
            fit_review = validate_fit_review_binding(
                request.fit_review,
                selected_evaluation_id=selected_record.id,
                selected_candidate_hash=selected_record.candidate_hash,
                selected_pdf_sha256=selected_record.pdf_sha256,
            )
        except FitReviewBindingError as exc:
            raise TailoringStaleError(str(exc), code=exc.code) from exc

        application: Application = parts["application"]
        application_id = application.id
        source_cv_id = session.cv_id
        scanner_payload = reviewed_scanner.model_dump(mode="json")
        evaluation_payload = reviewed_evaluation.model_dump(mode="json")
        fit_payload = fit_review.model_dump(mode="json") if fit_review is not None else None
        create_data = CVCreate(
            title=candidate["title"],
            description=candidate.get("description"),
            template_id=candidate["template_id"],
            sections=sections,
            customizations=candidate["customizations"],
            extra_metadata={
                "tailoring_mode": "complete_candidate",
                "tailoring_session_id": session.id,
                "source_cv_id": source_cv_id,
                "candidate_hash": candidate_hash,
                "evaluation_id": selected_record.id,
                "scanner_result": scanner_payload,
                "review_notes": request.review_notes,
                "tailoring_evaluation": evaluation_payload,
                "fit_review": fit_payload,
            },
        )
        result_payload = {
            "protocol_version": session.protocol_version,
            "session_id": session.id,
            "application_id": application_id,
            "status": TAILORING_SESSION_DRAFT_READY,
            "source_cv_id": source_cv_id,
            "evaluation_id": selected_record.id,
            "candidate_hash": candidate_hash,
            "candidate": candidate,
            "scanner_result": scanner_payload,
            "tailoring_evaluation": evaluation_payload,
            "render_warnings": list(selected_record.render_warnings or []),
            "review_notes": request.review_notes,
            "fit_review": fit_payload,
            "pdf_sha256": selected_record.pdf_sha256,
            "context_hash": request.context_hash,
            "submit_request_digest": submit_request_digest,
        }

        await QuotaService(self.db).ensure_write_transaction()
        new_cv: CV | None = None
        seeded_owner_record: TailoringEvaluationRecord | None = None
        seeded_render_basis_hash: str | None = None
        stale_target = False
        now = _utcnow()
        try:
            async with self.db.begin_nested():
                await self._lock_preview_target_rows(session)
                try:
                    final_parts = await self._context_parts(session)
                    if (
                        final_parts["context_hash"] != request.context_hash
                        or final_parts["target_guard_hash"] != session.target_guard_hash
                    ):
                        raise TailoringStaleError("The application or source CV changed during submission")
                except TailoringStaleError:
                    stale_update = await self.db.execute(
                        update(TailoringSession)
                        .where(
                            TailoringSession.id == session.id,
                            TailoringSession.status == TAILORING_SESSION_EXCHANGED,
                            TailoringSession.expires_at > _db_utcnow(),
                        )
                        .values(
                            status=TAILORING_SESSION_STALE,
                            capability_hash=None,
                            updated_at=now,
                        )
                    )
                    if stale_update.rowcount != 1:
                        raise TailoringConflictError("Tailoring session changed during submission")
                    session.status = TAILORING_SESSION_STALE
                    session.capability_hash = None
                    session.updated_at = now
                    await self._prune_terminal_preview_data(session.id, now)
                    stale_target = True

                if not stale_target:
                    other_result = await self.db.execute(
                        select(TailoringSession).where(
                            TailoringSession.application_id == application_id,
                            TailoringSession.user_id == session.user_id,
                            TailoringSession.id != session.id,
                            TailoringSession.status.in_(
                                (
                                    TAILORING_SESSION_DRAFT_READY,
                                    TAILORING_SESSION_STALE,
                                    TAILORING_SESSION_EXPIRED,
                                )
                            ),
                        )
                    )
                    for other_session in other_result.scalars().all():
                        other_draft = await self._owned_cv(other_session.draft_cv_id, session.user_id)
                        if other_draft is not None and other_draft.application_id == application_id:
                            raise TailoringConflictError(
                                "Discard the existing tailoring draft before submitting another",
                                code="session_in_progress",
                            )
                        await self._reconcile_pending_draft(other_session, unavailable=True)
                    new_cv = await CVService(self.db).create_replacement_draft(
                        session.user_id,
                        create_data,
                        application_id=application_id,
                        source_cv_id=source_cv_id,
                    )
                    result_payload["draft_cv_id"] = new_cv.id

                # A submitted preview can serve as the initial owner review
                # only when the persisted candidate and every live render
                # input still match the frozen preview basis. Copying its
                # immutable ledger keeps the exact selected PDF digest.
                try:
                    if stale_target:
                        raise TailoringStaleError("The application or source CV changed during submission")
                    owner_parts, owner_profile, owner_manifests = await self._current_owner_inputs(session)
                    owner_candidate, _ = self._normalize_candidate(
                        TailoringCandidateCV.model_validate(candidate),
                        owner_parts,
                    )
                    frozen_manifest = parts["manifest_by_id"].get(candidate["template_id"])
                    owner_manifest = owner_manifests.get(candidate["template_id"])
                    if (
                        frozen_manifest is not None
                        and owner_manifest is not None
                        and self._candidate_hash(owner_candidate) == candidate_hash
                    ):
                        frozen_basis_hash = self._owner_render_basis_hash(
                            parts,
                            parts["profile"],
                            candidate,
                            frozen_manifest,
                        )
                        current_basis_hash = self._owner_render_basis_hash(
                            owner_parts,
                            owner_profile,
                            owner_candidate,
                            owner_manifest,
                        )
                        persisted_hash = self._candidate_hash(self._persisted_candidate(new_cv))
                        if frozen_basis_hash == current_basis_hash and persisted_hash == candidate_hash:
                            seeded_render_basis_hash = current_basis_hash
                            seeded_owner_record = TailoringEvaluationRecord(
                                id=str(uuid.uuid4()),
                                session_id=session.id,
                                kind=TAILORING_EVALUATION_OWNER_REVIEW,
                                reservation_id=None,
                                candidate_hash=candidate_hash,
                                candidate=copy.deepcopy(candidate),
                                scanner_result=scanner_payload,
                                evaluation=evaluation_payload,
                                render_warnings=list(selected_record.render_warnings or []),
                                page_count=selected_record.page_count,
                                pdf_sha256=selected_record.pdf_sha256,
                                pdf_bytes=selected_record.pdf_bytes,
                            )
                            self.db.add(seeded_owner_record)
                except (TailoringCandidateError, TailoringConflictError, TailoringStaleError, ValidationError):
                    seeded_owner_record = None
                    seeded_render_basis_hash = None

                if not stale_target:
                    update_result = await self.db.execute(
                        update(TailoringSession)
                        .where(
                            TailoringSession.id == session.id,
                            TailoringSession.status == TAILORING_SESSION_EXCHANGED,
                            TailoringSession.expires_at > _db_utcnow(),
                            TailoringSession.draft_cv_id.is_(None),
                        )
                        .values(
                            status=TAILORING_SESSION_DRAFT_READY,
                            draft_cv_id=new_cv.id,
                            submitted_at=now,
                            result=result_payload,
                            submission_result=result_payload,
                            owner_review_state="current" if seeded_owner_record is not None else "needs_reevaluation",
                            owner_cv_revision=new_cv.revision or 1,
                            owner_candidate_hash=candidate_hash,
                            owner_render_basis_hash=seeded_render_basis_hash,
                            owner_evaluation_id=seeded_owner_record.id if seeded_owner_record is not None else None,
                            owner_pdf_sha256=selected_record.pdf_sha256 if seeded_owner_record is not None else None,
                            updated_at=now,
                        )
                    )
                    if update_result.rowcount != 1:
                        raise TailoringConflictError("Tailoring session already has a draft")
                    await self.db.execute(
                        update(TailoringEvaluationRecord)
                        .where(
                            TailoringEvaluationRecord.session_id == session.id,
                            TailoringEvaluationRecord.kind == TAILORING_EVALUATION_AGENT_PREVIEW,
                            TailoringEvaluationRecord.id != selected_record.id,
                        )
                        .values(pdf_bytes=None)
                    )
                    if seeded_owner_record is not None:
                        await self.db.flush()
        except ReplacementAlreadyPendingError as exc:
            raise TailoringConflictError(str(exc), code="quota") from exc

        if stale_target:
            raise TailoringConflictError(
                "The application or source CV changed; start a new tailoring session",
                code="stale_target",
                commit_outcome=True,
            )

        assert new_cv is not None
        session.status = TAILORING_SESSION_DRAFT_READY
        session.draft_cv_id = new_cv.id
        session.submitted_at = now
        session.result = result_payload
        session.submission_result = result_payload
        session.owner_review_state = "current" if seeded_owner_record is not None else "needs_reevaluation"
        session.owner_cv_revision = new_cv.revision or 1
        session.owner_candidate_hash = candidate_hash
        session.owner_render_basis_hash = seeded_render_basis_hash
        session.owner_evaluation_id = seeded_owner_record.id if seeded_owner_record is not None else None
        session.owner_pdf_sha256 = selected_record.pdf_sha256 if seeded_owner_record is not None else None
        session.updated_at = now
        return TailoringSubmitResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=application_id,
            status=TAILORING_SESSION_DRAFT_READY,
            source_cv_id=source_cv_id,
            draft_cv_id=new_cv.id,
            evaluation_id=selected_record.id,
            candidate_hash=candidate_hash,
            candidate=TailoringCandidateCV.model_validate(candidate),
            scanner_result=reviewed_scanner,
            evaluation=reviewed_evaluation,
            render_warnings=list(selected_record.render_warnings or []),
            review_notes=request.review_notes,
            fit_review=fit_review,
        )

    async def _lock_owner_rows(self, session: TailoringSession, draft_id: str, template_id: str) -> None:
        """Take final short write locks after owner rendering has finished."""

        await self.db.execute(
            select(TailoringSession.id)
            .where(TailoringSession.id == session.id, TailoringSession.user_id == session.user_id)
            .with_for_update()
        )
        await self.db.execute(
            select(Application.id)
            .where(Application.id == session.application_id, Application.user_id == session.user_id)
            .with_for_update()
        )
        if session.cv_id is not None:
            await self.db.execute(
                select(CV.id)
                .where(CV.id == session.cv_id, CV.user_id == session.user_id)
                .with_for_update()
            )
        await self.db.execute(
            select(CV.id)
            .where(CV.id == draft_id, CV.user_id == session.user_id)
            .with_for_update()
        )
        await self.db.execute(
            select(User.id).where(User.id == session.user_id).with_for_update()
        )
        await self.db.execute(
            select(Template.id).where(Template.id == template_id).with_for_update()
        )

    async def reevaluate_draft(
        self,
        session_id: str,
        user_id: str,
        request: TailoringReevaluateRequest,
    ) -> TailoringReevaluateResponse:
        session = await self._owned_session(session_id, user_id)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("Historical tailoring drafts cannot be reevaluated")
        if session.status not in {TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE} or not session.draft_cv_id:
            raise TailoringConflictError("Tailoring draft is not available for reevaluation", code="draft_unavailable")
        draft = await self._owned_cv(session.draft_cv_id, user_id)
        if draft is None or draft.application_id != session.application_id:
            await self._reconcile_pending_draft(session, unavailable=True)
            raise TailoringConflictError(
                "Tailoring draft is no longer available",
                code="draft_unavailable",
                commit_outcome=True,
            )
        if session.status == TAILORING_SESSION_STALE:
            raise TailoringConflictError(
                "The application or source CV changed; discard this draft and start a new session",
                code="stale_target",
                commit_outcome=True,
            )
        if request.expected_cv_revision != (draft.revision or 1):
            raise TailoringConflictError(
                "The CV changed after it was loaded; refresh it before reevaluating",
                code="edited_draft",
            )

        try:
            parts, profile, manifests = await self._current_owner_inputs(session)
        except TailoringStaleError as exc:
            await self._reconcile_pending_draft(session)
            raise TailoringConflictError(
                "The application or source CV changed; discard this draft and start a new session",
                code="stale_target",
                commit_outcome=True,
            ) from exc
        manifest = manifests.get(draft.template_id)
        if manifest is None:
            raise TailoringConflictError(
                "The draft template is no longer available; choose a current template and save again",
                code="review_not_current",
            )

        original_revision = draft.revision or 1
        original_candidate = self._persisted_candidate(draft)
        original_candidate_hash = self._candidate_hash(original_candidate)
        try:
            candidate, sections = self._normalize_candidate(
                TailoringCandidateCV.model_validate(original_candidate),
                parts,
            )
        except (TailoringCandidateError, ValidationError) as exc:
            raise TailoringConflictError("The saved tailoring draft is invalid; edit and save it again") from exc
        candidate_hash = self._candidate_hash(candidate)
        render_basis_hash = self._owner_render_basis_hash(parts, profile, candidate, manifest)

        # Rendering, PDF scanning, and comparison all happen before the
        # conditional write transaction. Owner reevaluation never consumes
        # an agent preview reservation.
        pdf = await PDFService(self.db).render_manifest_payload(
            manifest,
            sections,
            candidate["customizations"],
        )
        previous_record: Mapping[str, Any] | None = None
        owner_history_result = await self.db.execute(
            select(TailoringEvaluationRecord)
            .where(
                TailoringEvaluationRecord.session_id == session.id,
                TailoringEvaluationRecord.kind == TAILORING_EVALUATION_OWNER_REVIEW,
            )
            .order_by(TailoringEvaluationRecord.created_at.desc(), TailoringEvaluationRecord.id.desc())
            .limit(1)
        )
        previous_owner = owner_history_result.scalar_one_or_none()
        if previous_owner is not None:
            previous_record = self._evaluation_record_state(previous_owner)
        else:
            submission = self._submission_payload(session) or {}
            selected_id = submission.get("evaluation_id")
            selected = await self.db.get(TailoringEvaluationRecord, selected_id) if isinstance(selected_id, str) else None
            if selected is not None and selected.kind == TAILORING_EVALUATION_AGENT_PREVIEW:
                previous_record = self._evaluation_record_state(selected)
        scanner_result, evaluation = await self._evaluate_candidate(
            session.id,
            parts,
            candidate,
            pdf,
            previous_record=previous_record,
        )
        pdf_sha256 = hashlib.sha256(pdf).hexdigest()
        page_count = pdf_page_count(pdf)

        quota = QuotaService(self.db)
        await quota.ensure_write_transaction()
        stale_target = False
        conflict: TailoringConflictError | None = None
        now = _utcnow()
        owner_record = TailoringEvaluationRecord(
            id=str(uuid.uuid4()),
            session_id=session.id,
            kind=TAILORING_EVALUATION_OWNER_REVIEW,
            reservation_id=None,
            candidate_hash=candidate_hash,
            candidate=copy.deepcopy(candidate),
            scanner_result=scanner_result.model_dump(mode="json"),
            evaluation=evaluation.model_dump(mode="json"),
            render_warnings=list(evaluation.render_warnings),
            page_count=page_count,
            pdf_sha256=pdf_sha256,
            pdf_bytes=pdf,
        )
        updated_revision: int | None = None
        async with self.db.begin_nested():
            await self._lock_owner_rows(session, draft.id, draft.template_id)
            current_session = await self.db.scalar(
                select(TailoringSession)
                .where(TailoringSession.id == session.id, TailoringSession.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            current_draft = await self._owned_cv(draft.id, user_id)
            if (
                current_session is None
                or current_session.status != TAILORING_SESSION_DRAFT_READY
                or current_session.draft_cv_id != draft.id
                or current_draft is None
                or current_draft.application_id != session.application_id
            ):
                conflict = TailoringConflictError(
                    "The tailoring draft changed while it was being reevaluated",
                    code="draft_unavailable",
                )
            elif (current_draft.revision or 1) != original_revision or self._candidate_hash(
                self._persisted_candidate(current_draft)
            ) != original_candidate_hash:
                conflict = TailoringConflictError(
                    "The CV changed while it was being reevaluated; refresh it and try again",
                    code="edited_draft",
                )
            else:
                try:
                    final_parts, final_profile, final_manifests = await self._current_owner_inputs(current_session)
                    final_manifest = final_manifests.get(current_draft.template_id)
                    final_candidate, final_sections = self._normalize_candidate(
                        TailoringCandidateCV.model_validate(self._persisted_candidate(current_draft)),
                        final_parts,
                    )
                    final_basis_hash = (
                        self._owner_render_basis_hash(final_parts, final_profile, final_candidate, final_manifest)
                        if final_manifest is not None
                        else None
                    )
                except TailoringStaleError:
                    await self._reconcile_pending_draft(current_session)
                    stale_target = True
                    final_candidate = None
                    final_sections = None
                    final_manifest = None
                    final_basis_hash = None
                    current_session = None
                except (TailoringCandidateError, ValidationError, TailoringConflictError):
                    conflict = TailoringConflictError(
                        "The draft render basis changed while it was being reevaluated; refresh and try again",
                        code="review_not_current",
                    )
                    final_candidate = None
                    final_sections = None
                    final_manifest = None
                    final_basis_hash = None

                if not stale_target and conflict is None:
                    if (
                        final_manifest is None
                        or final_candidate is None
                        or self._candidate_hash(final_candidate) != candidate_hash
                        or final_basis_hash != render_basis_hash
                    ):
                        conflict = TailoringConflictError(
                            "The draft render basis changed while it was being reevaluated; refresh and try again",
                            code="review_not_current",
                        )
                    else:
                        changed_at_commit = (
                            _content_hash(_candidate_content_for_comparison(self._persisted_candidate(current_draft)))
                            != _content_hash(_candidate_content_for_comparison(candidate))
                        )
                        cv_update = (
                            update(CV)
                            .where(
                                CV.id == current_draft.id,
                                CV.user_id == user_id,
                                CV.is_active.is_(True),
                                CV.application_id == session.application_id,
                                CV.revision == original_revision,
                            )
                            .values(
                                title=candidate["title"],
                                description=candidate.get("description"),
                                template_id=candidate["template_id"],
                                sections=final_sections,
                                customizations=candidate["customizations"],
                                revision=CV.revision + 1 if changed_at_commit else CV.revision,
                                updated_at=now if changed_at_commit else CV.updated_at,
                            )
                            .returning(CV.revision)
                        )
                        cv_update_result = await self.db.execute(cv_update)
                        updated_revision = cv_update_result.scalar_one_or_none()
                        if updated_revision is None:
                            conflict = TailoringConflictError(
                                "The CV changed while it was being reevaluated; refresh it and try again",
                                code="edited_draft",
                            )
                        else:
                            self.db.add(owner_record)
                            current_session.owner_review_state = "current"
                            current_session.owner_cv_revision = int(updated_revision)
                            current_session.owner_candidate_hash = candidate_hash
                            current_session.owner_render_basis_hash = render_basis_hash
                            current_session.owner_evaluation_id = owner_record.id
                            current_session.owner_pdf_sha256 = pdf_sha256
                            current_session.updated_at = now
                            current_draft.title = candidate["title"]
                            current_draft.description = candidate.get("description")
                            current_draft.template_id = candidate["template_id"]
                            current_draft.sections = final_sections
                            current_draft.customizations = candidate["customizations"]
                            current_draft.revision = int(updated_revision)
                            if changed_at_commit:
                                current_draft.updated_at = now
                            await self.db.flush()

        if stale_target:
            raise TailoringConflictError(
                "The application or source CV changed; discard this draft and start a new session",
                code="stale_target",
                commit_outcome=True,
            )
        if conflict is not None:
            raise conflict
        assert updated_revision is not None
        review = TailoringDraftReview(
            state="current",
            cv_revision=int(updated_revision),
            candidate_hash=candidate_hash,
            render_basis_hash=render_basis_hash,
            evaluation_id=owner_record.id,
            evaluation=evaluation,
            scanner_result=scanner_result,
            warnings=list(evaluation.render_warnings),
            pdf_sha256=pdf_sha256,
            fit_review=self._fit_review_from_submission(session),
            fit_review_applicability="current"
            if (
                (fit := self._fit_review_from_submission(session)) is not None
                and fit.candidate_hash == candidate_hash
                and fit.pdf_sha256 == pdf_sha256
            )
            else "earlier_version"
            if self._fit_review_from_submission(session) is not None
            else "not_run",
        )
        return TailoringReevaluateResponse(
            session_id=session.id,
            application_id=session.application_id,
            draft_cv_id=draft.id,
            draft_review=review,
            pdf_base64=base64.b64encode(pdf).decode("ascii"),
            page_count=page_count,
        )

    async def draft_context(self, cv_id: str, user_id: str) -> TailoringDraftContextResponse:
        session_result = await self.db.execute(
            select(TailoringSession).where(
                TailoringSession.user_id == user_id,
                TailoringSession.draft_cv_id == cv_id,
                TailoringSession.status.in_((TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE)),
            )
        )
        session = session_result.scalar_one_or_none()
        if session is None or session.protocol_version != PROTOCOL_VERSION:
            raise TailoringSessionNotFoundError("Tailoring draft context not found")
        draft = await self._owned_cv(cv_id, user_id)
        if draft is None or draft.application_id != session.application_id:
            await self._reconcile_pending_draft(session, unavailable=True)
            raise TailoringSessionNotFoundError("Tailoring draft context not found")
        status_response = await self.session_status(session.id, user_id)
        application = await self._owned_application(session.application_id, user_id)
        if application is None:
            raise TailoringSessionNotFoundError("Tailoring draft context not found")
        snapshot = session.context_snapshot if isinstance(session.context_snapshot, Mapping) else {}
        try:
            scanner = TailoringScannerContext.model_validate(snapshot.get("scanner"))
        except ValidationError as exc:
            raise TailoringConflictError("Tailoring scanner context is unavailable") from exc
        return TailoringDraftContextResponse(
            session_id=session.id,
            application_id=session.application_id,
            draft_cv_id=cv_id,
            draft_review=status_response.draft_review or TailoringDraftReview(state="unavailable"),
            job=TailoringJob(
                company=application.company,
                role=application.role,
                job_url=application.job_url,
                description=application.job_description,
                user_instructions=application.notes,
            ),
            scanner_context=TailoringDraftScannerContext(
                versions=scanner.versions,
                requirement_extraction=scanner.requirement_extraction,
            ),
        )

    async def accept_draft(
        self,
        session_id: str,
        user_id: str,
        request: TailoringAcceptRequest | None = None,
    ) -> TailoringReviewResponse:
        session = await self._owned_session(session_id, user_id)
        if session.protocol_version == PROTOCOL_VERSION:
            return await self._accept_v10_draft(session, user_id, request)
        if session.status != TAILORING_SESSION_DRAFT_READY or not session.draft_cv_id:
            raise TailoringConflictError("Tailoring draft is not ready for acceptance")
        application = await self._owned_application(session.application_id, user_id)
        draft = await self._owned_cv(session.draft_cv_id, user_id)
        if application is None or draft is None or draft.application_id != application.id:
            raise TailoringConflictError("Tailoring draft is no longer available")
        stored_result = (session.result or {}).get("scanner_result") if isinstance(session.result, dict) else None
        try:
            scanner_result = ScanResult.model_validate(stored_result)
        except (ValidationError, TypeError) as exc:
            raise TailoringConflictError("The tailoring draft has no valid scanner result") from exc
        stored_candidate = (session.result or {}).get("candidate") if isinstance(session.result, dict) else None
        stored_candidate_hash = (session.result or {}).get("candidate_hash") if isinstance(session.result, dict) else None
        if not isinstance(stored_candidate, Mapping) or not isinstance(stored_candidate_hash, str):
            raise TailoringConflictError("The tailoring draft has no valid candidate binding")
        if self._candidate_hash(stored_candidate) != stored_candidate_hash:
            raise TailoringConflictError("The tailoring draft candidate binding is invalid")
        persisted_candidate = {
            "title": draft.title,
            "description": draft.description,
            "template_id": draft.template_id,
            "sections": draft.sections or [],
            "customizations": draft.customizations or {},
        }
        if _content_hash(_candidate_content_for_comparison(stored_candidate)) != _content_hash(
            _candidate_content_for_comparison(persisted_candidate)
        ):
            raise TailoringConflictError("The tailoring draft changed after submission; review it again")
        freshness = scanner_result_freshness(
            scanner_result.model_dump(mode="json"),
            application.job_description,
            draft,
            extractor_version=configured_extractor_version(),
        )
        if not freshness["current"]:
            session.status = TAILORING_SESSION_STALE
            session.reviewed_at = _utcnow()
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringConflictError("The tailoring draft scanner result is stale; review it again")
        # Compare-and-swap protects a CV selected after the agent began.
        source_condition = Application.cv_id.is_(None) if session.cv_id is None else Application.cv_id == session.cv_id
        now = _utcnow()
        result = await self.db.execute(
            update(Application)
            .where(Application.id == application.id, Application.user_id == user_id, source_condition)
            .values(
                cv_id=draft.id,
                scanner_result=scanner_result.model_dump(mode="json"),
                scanner_rescan_required=False,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            session.status = TAILORING_SESSION_STALE
            session.reviewed_at = now
            session.updated_at = now
            await self.db.flush()
            raise TailoringConflictError("The application changed; review this draft against the current CV")
        # Retire only the application-owned CV this accepted draft replaces.
        # Keep history references intact and release its quota through normal
        # soft deletion, in the same transaction as the current-CV switch.
        previous_cv = await self._owned_cv(session.cv_id, user_id)
        if previous_cv is not None and previous_cv.id != draft.id and previous_cv.application_id == application.id:
            linked_application = await self.db.scalar(
                select(Application.id).where(Application.cv_id == previous_cv.id).limit(1)
            )
            # Historical data can share a CV across applications. A remaining
            # current-CV reference takes precedence over revision cleanup.
            if linked_application is None:
                await CVService(self.db).delete_cv(previous_cv.id, user_id)
        session.status = TAILORING_SESSION_ACCEPTED
        if isinstance(session.result, dict):
            session.result = {**session.result, "scanner_result": scanner_result.model_dump(mode="json")}
        session.reviewed_at = now
        session.updated_at = now
        await self.db.flush()
        return TailoringReviewResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=application.id,
            status="accepted",
            source_cv_id=session.cv_id,
            draft_cv_id=draft.id,
            cv_id=draft.id,
            scanner_result=scanner_result,
        )

    async def _accept_v10_draft(
        self,
        session: TailoringSession,
        user_id: str,
        request: TailoringAcceptRequest | None,
    ) -> TailoringReviewResponse:
        if session.status != TAILORING_SESSION_DRAFT_READY or not session.draft_cv_id:
            raise TailoringConflictError("Tailoring draft is not ready for acceptance")
        if request is None:
            raise TailoringCandidateError("Protocol v10 acceptance requires the current CV revision and candidate hash")
        draft_id = session.draft_cv_id
        draft = await self._owned_cv(draft_id, user_id)
        if draft is None or draft.application_id != session.application_id:
            await self._reconcile_pending_draft(session, unavailable=True)
            raise TailoringConflictError(
                "Tailoring draft is no longer available",
                code="draft_unavailable",
                commit_outcome=True,
            )
        try:
            parts, profile, manifests = await self._current_owner_inputs(session)
        except TailoringStaleError as exc:
            await self._reconcile_pending_draft(session)
            raise TailoringConflictError(
                "The application or source CV changed; discard this draft and start a new session",
                code="stale_target",
                commit_outcome=True,
            ) from exc
        review = await self._draft_review(
            session,
            draft,
            parts=parts,
            profile=profile,
            manifests=manifests,
        )
        if (
            request.expected_cv_revision != review.cv_revision
            or request.candidate_hash != review.candidate_hash
            or request.expected_cv_revision != (draft.revision or 1)
        ):
            raise TailoringConflictError(
                "The saved draft changed after review; reevaluate it before accepting",
                code="edited_draft",
            )
        if review.state != "current" or review.evaluation_id is None:
            raise TailoringConflictError(
                "Reevaluate the saved draft before accepting it",
                code="review_not_current",
            )

        application_id = session.application_id
        source_cv_id = session.cv_id
        await QuotaService(self.db).ensure_write_transaction()
        stale_target = False
        result_scanner: ScanResult | None = None
        now = _utcnow()
        async with self.db.begin_nested():
            await self._lock_owner_rows(session, draft_id, draft.template_id)
            current_session = await self.db.scalar(
                select(TailoringSession)
                .where(TailoringSession.id == session.id, TailoringSession.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            current_draft = await self._owned_cv(draft_id, user_id)
            current_application = await self._owned_application(application_id, user_id)
            if (
                current_session is None
                or current_session.status != TAILORING_SESSION_DRAFT_READY
                or current_session.draft_cv_id != draft_id
                or current_draft is None
                or current_draft.application_id != application_id
                or current_application is None
            ):
                raise TailoringConflictError("The tailoring draft changed before acceptance", code="draft_unavailable")
            if (
                (current_draft.revision or 1) != request.expected_cv_revision
                or self._candidate_hash(self._persisted_candidate(current_draft)) != request.candidate_hash
            ):
                raise TailoringConflictError(
                    "The saved draft changed after review; reevaluate it before accepting",
                    code="edited_draft",
                )
            try:
                final_parts, final_profile, final_manifests = await self._current_owner_inputs(current_session)
            except TailoringStaleError:
                await self._reconcile_pending_draft(current_session)
                stale_target = True
                final_parts = {}
                final_profile = None
                final_manifests = {}
            if not stale_target:
                final_review = await self._draft_review(
                    current_session,
                    current_draft,
                    parts=final_parts,
                    profile=final_profile,
                    manifests=final_manifests,
                )
                if (
                    final_review.state != "current"
                    or final_review.cv_revision != request.expected_cv_revision
                    or final_review.candidate_hash != request.candidate_hash
                    or final_review.render_basis_hash != current_session.owner_render_basis_hash
                    or final_review.evaluation_id != current_session.owner_evaluation_id
                ):
                    raise TailoringConflictError(
                        "The render or contact basis changed after review; reevaluate the draft before accepting",
                        code="review_not_current",
                    )
                owner_record = await self.db.get(TailoringEvaluationRecord, current_session.owner_evaluation_id)
                parsed_owner = self._record_evaluation_payload(owner_record) if owner_record is not None else None
                if owner_record is None or parsed_owner is None or owner_record.pdf_bytes is None:
                    raise TailoringConflictError("The current owner review is unavailable", code="review_not_current")
                result_scanner = parsed_owner[0]
                quota = QuotaService(self.db)

                if not current_draft.quota_counted:
                    if source_cv_id is None:
                        raise TailoringConflictError("The replacement source changed", code="source_changed")
                    try:
                        await quota.transfer_replacement(
                            user_id,
                            application_id,
                            source_cv_id,
                            draft_id,
                        )
                    except ReplacementReservationConflictError as exc:
                        raise TailoringConflictError(str(exc), code="source_changed") from exc
                    scanner_update = await self.db.execute(
                        update(Application)
                        .where(
                            Application.id == application_id,
                            Application.user_id == user_id,
                            Application.cv_id == draft_id,
                        )
                        .values(
                            scanner_result=result_scanner.model_dump(mode="json"),
                            scanner_rescan_required=False,
                            updated_at=now,
                        )
                    )
                    if scanner_update.rowcount != 1:
                        raise TailoringConflictError("The application changed during acceptance", code="source_changed")
                else:
                    source_condition = (
                        Application.cv_id.is_(None)
                        if source_cv_id is None
                        else Application.cv_id == source_cv_id
                    )
                    bind_result = await self.db.execute(
                        update(Application)
                        .where(
                            Application.id == application_id,
                            Application.user_id == user_id,
                            source_condition,
                        )
                        .values(
                            cv_id=draft_id,
                            scanner_result=result_scanner.model_dump(mode="json"),
                            scanner_rescan_required=False,
                            updated_at=now,
                        )
                    )
                    if bind_result.rowcount != 1:
                        await self._reconcile_pending_draft(current_session)
                        stale_target = True
                    elif source_cv_id is not None and source_cv_id != draft_id:
                        old_source = await self._owned_cv(source_cv_id, user_id)
                        if old_source is not None:
                            shared_link = await self.db.scalar(
                                select(Application.id)
                                .where(Application.cv_id == source_cv_id, Application.id != application_id)
                                .limit(1)
                            )
                            if shared_link is None:
                                try:
                                    await CVService(self.db).delete_cv(source_cv_id, user_id)
                                except CVLinkedToApplicationError as exc:
                                    raise TailoringConflictError(
                                        "The source CV became shared before acceptance",
                                        code="source_changed",
                                    ) from exc

                if not stale_target:
                    status_update = await self.db.execute(
                        update(TailoringSession)
                        .where(
                            TailoringSession.id == session.id,
                            TailoringSession.user_id == user_id,
                            TailoringSession.status == TAILORING_SESSION_DRAFT_READY,
                            TailoringSession.draft_cv_id == draft_id,
                        )
                        .values(
                            status=TAILORING_SESSION_ACCEPTED,
                            reviewed_at=now,
                            updated_at=now,
                        )
                    )
                    if status_update.rowcount != 1:
                        raise TailoringConflictError("The tailoring draft was reviewed concurrently")
                    current_session.status = TAILORING_SESSION_ACCEPTED
                    current_session.reviewed_at = now
                    current_session.updated_at = now
                    await self._prune_terminal_preview_data(session.id, now)
                    await self.db.flush()

        if stale_target:
            raise TailoringConflictError(
                "The application or source CV changed; discard this draft and start a new session",
                code="stale_target",
                commit_outcome=True,
            )
        session.status = TAILORING_SESSION_ACCEPTED
        session.reviewed_at = now
        session.updated_at = now
        return TailoringReviewResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=application_id,
            status="accepted",
            source_cv_id=source_cv_id,
            draft_cv_id=draft_id,
            cv_id=draft_id,
            scanner_result=result_scanner,
        )

    async def reject_draft(self, session_id: str, user_id: str) -> TailoringReviewResponse:
        session = await self._owned_session(session_id, user_id)
        if session.status == TAILORING_SESSION_ACCEPTED:
            raise TailoringConflictError("An accepted tailoring draft cannot be discarded")
        if session.status == TAILORING_SESSION_REJECTED:
            result = self._submission_payload(session) or {}
            return TailoringReviewResponse(
                protocol_version=session.protocol_version,
                session_id=session.id,
                application_id=session.application_id,
                status="rejected",
                source_cv_id=session.cv_id,
                draft_cv_id=session.draft_cv_id,
                cv_id=None,
                scanner_result=self._scanner_result_from_submission(result),
            )
        historical = session.protocol_version != PROTOCOL_VERSION
        allowed_statuses = {TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE}
        if historical:
            allowed_statuses.add(TAILORING_SESSION_EXPIRED)
        if session.status not in allowed_statuses:
            if (
                not historical
                and not session.draft_cv_id
                and session.status in {TAILORING_SESSION_EXPIRED, TAILORING_SESSION_FAILED}
            ):
                return TailoringReviewResponse(
                    protocol_version=session.protocol_version,
                    session_id=session.id,
                    application_id=session.application_id,
                    status="rejected",
                    source_cv_id=session.cv_id,
                    draft_cv_id=None,
                    cv_id=None,
                )
            raise TailoringConflictError("Tailoring draft is not ready for rejection")
        if historical and not self._has_historical_submission(session):
            raise TailoringConflictError("Tailoring draft is not ready for rejection")

        draft_id = session.draft_cv_id
        now = _utcnow()
        await QuotaService(self.db).ensure_write_transaction()
        async with self.db.begin_nested():
            await self.db.execute(
                select(TailoringSession.id)
                .where(TailoringSession.id == session.id, TailoringSession.user_id == user_id)
                .with_for_update()
            )
            current_session = await self.db.scalar(
                select(TailoringSession)
                .where(TailoringSession.id == session.id, TailoringSession.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            if current_session is None:
                raise TailoringSessionNotFoundError("Tailoring session not found")
            if current_session.status == TAILORING_SESSION_ACCEPTED:
                raise TailoringConflictError("An accepted tailoring draft cannot be discarded")
            if current_session.status == TAILORING_SESSION_REJECTED:
                pass
            else:
                current_historical = current_session.protocol_version != PROTOCOL_VERSION
                current_allowed_statuses = {TAILORING_SESSION_DRAFT_READY, TAILORING_SESSION_STALE}
                if current_historical:
                    current_allowed_statuses.add(TAILORING_SESSION_EXPIRED)
                    if not self._has_historical_submission(current_session):
                        raise TailoringConflictError("Tailoring draft is not ready for rejection")
                if current_session.status not in current_allowed_statuses:
                    raise TailoringConflictError("Tailoring draft is not ready for rejection")
                draft_id = current_session.draft_cv_id
                current_draft = await self._owned_cv(current_session.draft_cv_id, user_id)
                if current_draft is not None:
                    try:
                        await CVService(self.db).delete_cv(current_draft.id, user_id)
                    except CVLinkedToApplicationError as exc:
                        raise TailoringConflictError(
                            "The draft is linked to an application and cannot be discarded",
                            code="draft_unavailable",
                        ) from exc
                status_update = await self.db.execute(
                    update(TailoringSession)
                    .where(
                        TailoringSession.id == current_session.id,
                        TailoringSession.status.in_(current_allowed_statuses),
                    )
                    .values(status=TAILORING_SESSION_REJECTED, reviewed_at=now, updated_at=now)
                )
                if status_update.rowcount != 1:
                    raise TailoringConflictError("The tailoring draft was reviewed concurrently")
                current_session.status = TAILORING_SESSION_REJECTED
                current_session.reviewed_at = now
                current_session.updated_at = now
                if not current_historical:
                    await self._release_session_replacement(current_session)
                await self._prune_terminal_preview_data(current_session.id, now)
                await self.db.flush()
                session.status = TAILORING_SESSION_REJECTED
                session.reviewed_at = now
                session.updated_at = now

        result = self._submission_payload(session) or {}
        return TailoringReviewResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=session.application_id,
            status="rejected",
            source_cv_id=session.cv_id,
            draft_cv_id=draft_id,
            cv_id=None,
            scanner_result=self._scanner_result_from_submission(result),
        )


__all__ = [
    "PROTOCOL_VERSION",
    "TAILORING_SESSION_ACCEPTED",
    "TAILORING_SESSION_CANCELLED",
    "TAILORING_SESSION_CREATED",
    "TAILORING_SESSION_DRAFT_READY",
    "TAILORING_SESSION_EXCHANGED",
    "TAILORING_SESSION_EXPIRED",
    "TAILORING_SESSION_FAILED",
    "TAILORING_SESSION_REJECTED",
    "TAILORING_SESSION_STALE",
    "TailoringCandidateError",
    "TailoringConflictError",
    "TailoringExpiredError",
    "TailoringNotFoundError",
    "TailoringService",
    "TailoringSessionNotFoundError",
    "TailoringStaleError",
    "TailoringUnauthorizedError",
    "TailoringUnavailableError",
    "build_tailoring_prompt",
    "cv_snapshot_hash",
    "fresh_tailoring_sections",
    "library_entry_content_hash",
    "profile_snapshot_hash",
]
