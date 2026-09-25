"""Persistent-index whole-document tailoring and review lifecycle.

Protocol v8 intentionally has one write primitive: a complete CV candidate.
The candidate is rendered and stored as an ordinary, unlinked CV draft.  The
browser owner later accepts or rejects it; the scoped capability can neither
change application linkage nor perform that review action.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import secrets
import asyncio
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_token
from app.document_schema.capabilities import LIMITS, capabilities_hash, renderer_capabilities
from app.document_schema.models import SectionInstance, TemplateManifest
from app.http_schemas.cv import CVCreate
from app.http_schemas.tailoring import (
    PROTOCOL_VERSION,
    TailoringCandidateCV,
    TailoringContextResponse,
    TailoringCV,
    TailoringExchangeResponse,
    TailoringJob,
    TailoringPreviewRequest,
    TailoringPreviewResponse,
    TailoringRenderArtifact,
    TailoringReviewResponse,
    TailoringSection,
    TailoringSessionCreateResponse,
    TailoringSessionStatusResponse,
    TailoringScannerContext,
    TailoringEvidenceContextResponse,
    TailoringEvidenceSourcesResponse,
    TailoringEvidenceSubmission,
    TailoringEvidenceVersions,
    TailoringSubmitRequest,
    TailoringSubmitResponse,
    TailoringSourcePreviewResponse,
    TailoringTemplate,
    TailoringCodeExchange,
)
from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringEvaluation,
)
from app.models.application import Application
from app.models.cv import CV
from app.models.library import Library, LibraryEntry
from app.models.tailoring_session import TailoringSession
from app.models.template import Template
from app.models.user import User
from app.scanner.freshness import configured_extractor_version, scanner_result_freshness
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import ScanResult
from app.scanner.service import ScannerService, canonicalize_scanner_cv, scanner_versions_for_extraction
from app.services.cv import CVService, coerce_customizations
from app.services.pdf import PDFService, pdf_page_count
from app.services.profile import ProfileService
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.pipeline import prepare_render_source, resolve_source
from app.services.rich_text import normalize_rich_text_ids
from app.services.tailoring_validation import CandidateValidationError, validate_section_payload
from app.services.tailoring_evaluation import evaluate_tailoring
from app.services.candidate_evidence import (
    CANDIDATE_EVIDENCE_EXTRACTOR_VERSION,
    CANDIDATE_EVIDENCE_PROMPT_VERSION,
    CANDIDATE_EVIDENCE_PROPOSITION_MODEL,
    CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION,
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    CandidateEvidenceSource,
    build_candidate_evidence,
    composer_projection,
)
from app.services.candidate_index import (
    CandidateIndexService,
    MAX_REFRESH_CHARACTERS,
    MAX_REFRESH_SOURCES,
)
from app.services.tailoring_opportunities import map_tailoring_opportunities


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _db_utcnow() -> datetime:
    """Bind a naive UTC value for SQLite's timezone-aware DateTime columns."""

    return _utcnow().replace(tzinfo=None)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


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


def requirements_snapshot_hash(requirements: Any) -> str:
    """Hash frozen scanner requirements or a complete extraction snapshot."""

    if isinstance(requirements, RequirementExtraction):
        payload = requirements.model_dump(mode="json")
    elif hasattr(requirements, "model_dump"):
        payload = requirements.model_dump(mode="json")
    else:
        payload = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in requirements
        ]
    return _content_hash(payload)


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
        "Use the Aergia persistent-index tailoring skill for this session:\n\n"
        f"{session_url}\n\n"
        f"One-time session code: {code}\n\n"
        "The skill checks and refreshes stale candidate-index sources in an isolated job-blind worker, "
        "then gives the writer a bounded set of current Library narratives with the job, linked CV, "
        "requirements, and renderer capabilities. Re-author one complete truthful CV, verify it, "
        "render and review each candidate. Fix any known serious issue, make another truthful revision "
        "when it is worthwhile, or select the strongest reviewed candidate for my review. "
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


class TailoringExpiredError(PermissionError):
    """A tailoring session has passed its expiry time."""


class TailoringStaleError(RuntimeError):
    """The exchanged context is no longer the current context."""


class TailoringConflictError(RuntimeError):
    """The session cannot perform the requested one-time action."""


class TailoringUnavailableError(ValueError):
    """The application is not ready for tailoring."""


class TailoringCandidateError(ValueError):
    """A complete candidate is structurally or mechanically invalid."""


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


def _job_terms(requirements: Sequence[Any]) -> list[str]:
    terms: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            concept = value.get("concept")
            if isinstance(concept, Mapping):
                name = concept.get("name")
                if isinstance(name, str) and name.strip():
                    terms.add(name.strip())
            for child in value.values():
                visit(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for child in value:
                visit(child)

    for requirement in requirements:
        payload = requirement.model_dump(mode="python") if hasattr(requirement, "model_dump") else requirement
        visit(payload)
    return sorted(terms, key=str.casefold)[:500]


class TailoringService:
    """Own context exchange, complete-candidate persistence, and review."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scanner_service = ScannerService()

    async def _owned_application(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _owned_cv(self, cv_id: str | None, user_id: str) -> CV | None:
        if not cv_id:
            return None
        result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
        )
        return result.scalar_one_or_none()

    async def _library_entries(self, user_id: str) -> list[LibraryEntry]:
        result = await self.db.execute(
            select(LibraryEntry)
            .join(Library, LibraryEntry.library_id == Library.id)
            .where(Library.user_id == user_id)
            .order_by(LibraryEntry.created_at.asc())
        )
        return list(result.scalars().all())

    async def _templates(self) -> list[Template]:
        result = await self.db.execute(select(Template).order_by(Template.created_at.asc(), Template.id.asc()))
        return list(result.scalars().all())

    async def _context_resources(self, session: TailoringSession) -> dict[str, Any]:
        application = await self._owned_application(session.application_id, session.user_id)
        if application is None:
            raise TailoringConflictError("Tailoring application is no longer available")
        source_cv = await self._owned_cv(session.cv_id, session.user_id)
        if session.cv_id and source_cv is None:
            raise TailoringConflictError("The source CV is no longer available")
        user = await self.db.get(User, session.user_id)
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
        effective: dict[str, Any] = {}
        if source_cv is not None:
            try:
                source = prepare_render_source(
                    source_cv.sections or [],
                    manifest_by_id.get(source_cv.template_id),
                    source_cv.customizations or {},
                )
                resolved = resolve_source(source, HTMLDocumentRenderer())
                effective = {
                    "template_id": source_cv.template_id,
                    "body_font": resolved.body_font,
                    "heading_font": resolved.heading_font,
                    "css_vars": resolved.css_vars,
                    "sections": {
                        section_id: section.model_dump(mode="json", exclude_none=True)
                        for section_id, section in resolved.sections.items()
                    },
                }
            except (ValidationError, ValueError, KeyError):
                effective = {"template_id": source_cv.template_id, "unavailable": True}
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
            "effective": effective,
        }

    async def _render_cv_pdf(self, cv: CV) -> bytes | None:
        try:
            return await PDFService(self.db).render_payload(
                cv.template_id,
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
        if existing is not None:
            freshness = scanner_result_freshness(
                existing,
                application.job_description,
                source_cv,
                extractor_version=configured_extractor_version(),
            )
            if freshness["current"]:
                try:
                    source_scan = ScanResult.model_validate(existing)
                except ValidationError:
                    source_scan = None

        if source_scan is None:
            pdf_bytes = await self._render_cv_pdf(source_cv)
            source_scan = await asyncio.to_thread(
                self.scanner_service.scan,
                application.job_description,
                source_cv,
                pdf_bytes=pdf_bytes,
            )
            application.scanner_result = source_scan.model_dump(mode="json")
            application.scanner_rescan_required = False
            application.updated_at = _utcnow()
            await self.db.flush()

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
        manifest_by_id: dict[str, dict[str, Any]] = resources["manifest_by_id"]
        capabilities: dict[str, Any] = resources["capabilities"]
        return {
            "application": _application_context_snapshot(application),
            "profile": resources["profile_data"],
            "source_cv": cv_snapshot_hash(source_cv),
            "library": {entry.id: library_entry_content_hash(entry) for entry in libraries},
            "scanner": scanner_context.model_dump(mode="json"),
            "templates": manifest_by_id,
            "capabilities": capabilities_hash(capabilities),
            "evaluation_version": TAILORING_EVALUATION_VERSION,
        }

    async def _context_parts(
        self,
        session: TailoringSession,
        *,
        initialize: bool = False,
    ) -> dict[str, Any]:
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringStaleError("This tailoring session uses an older protocol; start a new session")
        resources = await self._context_resources(session)
        index_service = CandidateIndexService(self.db)
        indexed_sources = await index_service.ensure_current(session.user_id)
        fresh_sources, semantic_results, source_counts = await index_service.fresh_semantic_results(session.user_id)
        if not session.context_snapshot:
            if not initialize:
                raise TailoringStaleError("This tailoring session predates protocol v8; start a new session")
            scanner_context = await self._freeze_scanner_context(resources)
            basis = self._context_basis(resources, scanner_context)
            session.context_snapshot = {
                "schema_version": f"tailoring-v{session.protocol_version}",
                "protocol_version": session.protocol_version,
                "evaluation_version": TAILORING_EVALUATION_VERSION,
                "scanner": scanner_context.model_dump(mode="json"),
                "basis": basis,
            }
        else:
            try:
                snapshot = session.context_snapshot
                if snapshot.get("protocol_version") != session.protocol_version:
                    raise TailoringStaleError("The tailoring session protocol is no longer supported")
                if snapshot.get("evaluation_version") != TAILORING_EVALUATION_VERSION:
                    raise TailoringStaleError("The tailoring evaluation contract changed; start a new session")
                scanner_context = TailoringScannerContext.model_validate(snapshot["scanner"])
                frozen_basis = snapshot["basis"]
            except (KeyError, TypeError, ValidationError) as exc:
                raise TailoringStaleError("The tailoring scanner context is invalid; start a new session") from exc
            current_versions = scanner_versions_for_extraction(scanner_context.requirement_extraction)
            configured_version = configured_extractor_version()
            if configured_version and configured_version != scanner_context.versions.extractor_version:
                raise TailoringStaleError("The scanner contract changed; start a new tailoring session")
            if current_versions != scanner_context.versions:
                raise TailoringStaleError("The scanner contract changed; start a new tailoring session")
            current_basis = self._context_basis(resources, scanner_context)
            if _content_hash(current_basis) != _content_hash(frozen_basis):
                current_without_library = {key: value for key, value in current_basis.items() if key != "library"}
                frozen_without_library = {key: value for key, value in frozen_basis.items() if key != "library"}
                if _content_hash(current_without_library) != _content_hash(frozen_without_library):
                    raise TailoringStaleError("The tailoring context changed; start a new session")
                # Candidate Library material is live-indexed. If a source was
                # edited while its old fingerprint was being refreshed, use
                # the current source version and leave the old result stale.
                snapshot = copy.deepcopy(session.context_snapshot)
                snapshot["basis"] = current_basis
                session.context_snapshot = snapshot
                session.context_hash = _content_hash(current_basis)
                await self.db.flush()

        context_snapshot = session.context_snapshot
        scanner_context = TailoringScannerContext.model_validate(context_snapshot["scanner"])
        basis = self._context_basis(resources, scanner_context)
        application: Application = resources["application"]
        retrieval_query = " ".join((
            application.job_description,
            *_job_terms(scanner_context.requirement_extraction.requirements),
        ))[:60_000]
        retrieved_index_sources = await index_service.search_sources(
            session.user_id,
            retrieval_query,
            max_sources=500,
        )
        return {
            **resources,
            # The context hash freezes these rows for the session. Pass a
            # serialized copy into the pure evaluator rather than exposing
            # database/ORM access to tailoring_evaluation.py.
            "authoritative_library": [
                {
                    "id": entry.id,
                    "kind": entry.kind,
                    "payload": copy.deepcopy(entry.payload or []),
                    "_row_ids": list(entry.row_ids or []),
                }
                for entry in resources["libraries"]
            ],
            "candidate_index_sources": [
                CandidateEvidenceSource(
                    source_id=source.source_id,
                    entry_id=source.library_entry_id,
                    row_id=source.row_id,
                    kind=source.kind,
                    identity=source.identity or {},
                    structured_facts=source.structured_facts or {},
                    source_field=source.field_path,
                    source_hash=source.source_fingerprint,
                    raw_value=source.narrative,
                    text=source.narrative,
                    canonical_skills=list(source.canonical_skills or []),
                )
                for source in retrieved_index_sources
                if source.field_path != "$row"
            ],
            "candidate_index_rows": [
                {
                    "source_id": source.source_id,
                    "kind": source.kind,
                    "identity": source.identity or {},
                    "structured_facts": source.structured_facts or {},
                    "canonical_skills": list(source.canonical_skills or []),
                    "normalized_text": source.normalized_text,
                }
                for source in retrieved_index_sources
                if source.field_path == "$row"
            ],
            "fresh_candidate_sources": fresh_sources,
            "fresh_candidate_semantics": semantic_results,
            "candidate_source_counts": source_counts,
            "candidate_index_summary": {
                "schema_version": "candidate-index-v1",
                "canonical_skills": sorted({skill for item in indexed_sources for skill in (item.canonical_skills or [])}),
                "source_count": len([item for item in indexed_sources if item.field_path != "$row"]),
                "row_count": sum(source.field_path == "$row" for source in indexed_sources),
                "semantic_source_counts": {key.lower(): value for key, value in source_counts.items()},
                "cache_state": (
                    "warm" if source_counts["STALE"] == 0 and source_counts["MISSING"] == 0
                    else "mixed" if source_counts["STALE"] and source_counts["MISSING"]
                    else "stale" if source_counts["STALE"]
                    else "missing"
                ),
            },
            "scanner_context": scanner_context,
            "requirements": scanner_context.requirement_extraction.requirements,
            "context_hash": _content_hash(basis),
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
                    (TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED, TAILORING_SESSION_DRAFT_READY)
                ),
            )
        )
        now = _utcnow()
        expired_sessions: list[TailoringSession] = []
        for existing in existing_result.scalars().all():
            if (
                existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
                and existing.protocol_version != PROTOCOL_VERSION
            ):
                existing.status = TAILORING_SESSION_STALE
                existing.capability_hash = None
                existing.updated_at = now
                expired_sessions.append(existing)
                continue
            if (
                existing.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
                and _as_utc(existing.expires_at) <= now
            ):
                existing.status = TAILORING_SESSION_EXPIRED
                existing.capability_hash = None
                existing.updated_at = now
                expired_sessions.append(existing)
                continue
            raise TailoringConflictError(
                "Finish or cancel the existing tailoring session before starting another"
            )
        if expired_sessions:
            await self.db.flush()
        # Validate the owner, profile, and template availability before
        # issuing a capability. A source CV is intentionally optional.
        user = await self.db.get(User, user_id)
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
        self.db.add(session)
        await self.db.flush()
        # Context construction also checks for a renderable template.
        parts = await self._context_parts(session, initialize=True)
        session.context_hash = parts["context_hash"]
        await self.db.flush()
        public_origin = session_url_base.rstrip("/") if session_url_base else ""
        session_url = f"{public_origin}/agent/tailor/{session.id}"
        skill_url = f"{public_origin}/api/v1/tailoring/skill.zip"
        source_cv_id = application.cv_id
        response = TailoringSessionCreateResponse(
            protocol_version=protocol_version,
            session_id=session.id,
            application_id=application.id,
            source_cv_id=source_cv_id,
            cv_id=source_cv_id,
            code=code,
            session_url=session_url,
            skill_url=skill_url,
            prompt=build_tailoring_prompt(session_url, code, skill_url, protocol_version),
            expires_at=session.expires_at,
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
    def _status_response(session: TailoringSession) -> TailoringSessionStatusResponse:
        return TailoringSessionStatusResponse(
            # Historical v4-v7 drafts remain readable/reviewable. New sessions
            # use the v8 contract through review.
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
        )

    async def session_status(self, session_id: str, user_id: str) -> TailoringSessionStatusResponse:
        session = await self._owned_session(session_id, user_id)
        now = _utcnow()
        if (
            session.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}
            and _as_utc(session.expires_at) <= now
        ):
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = now
            await self.db.flush()
        elif session.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
            try:
                parts = await self._context_parts(session)
                if session.context_hash and parts["context_hash"] != session.context_hash:
                    session.status = TAILORING_SESSION_STALE
                    session.updated_at = now
                    await self.db.flush()
            except (TailoringConflictError, TailoringUnavailableError, TailoringStaleError):
                session.status = TAILORING_SESSION_STALE
                session.updated_at = now
                await self.db.flush()
        return self._status_response(session)

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
        await self.db.refresh(session)
        return self._status_response(session)

    async def exchange_code(self, data: TailoringCodeExchange) -> TailoringExchangeResponse:
        result = await self.db.execute(select(TailoringSession).where(TailoringSession.code_hash == hash_token(data.code)))
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring code")
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol; start a new session")
        if session.status != TAILORING_SESSION_CREATED:
            raise TailoringConflictError("Tailoring code has already been exchanged")
        if _as_utc(session.expires_at) <= _utcnow():
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringExpiredError("Tailoring session expired")
        capability = secrets.token_urlsafe(32)
        now = _utcnow()
        result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
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
            raise TailoringConflictError("Tailoring code has already been exchanged")
        return TailoringExchangeResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            expires_at=session.expires_at,
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
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringExpiredError("Tailoring session expired")
        if session.status != TAILORING_SESSION_EXCHANGED and not (
            allow_draft_ready and session.status == TAILORING_SESSION_DRAFT_READY
        ):
            raise TailoringConflictError("Tailoring capability is no longer active")
        return session

    async def _current_context(self, session: TailoringSession) -> dict[str, Any]:
        parts = await self._context_parts(session)
        if not session.context_hash:
            session.context_hash = parts["context_hash"]
        if parts["context_hash"] != session.context_hash:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        return parts

    @classmethod
    def _evaluation_history(cls, session: TailoringSession) -> list[dict[str, Any]]:
        snapshot = session.context_snapshot
        if not isinstance(snapshot, dict):
            return []
        history = snapshot.get("evaluation_history")
        if not isinstance(history, list):
            return []
        return [item for item in history if isinstance(item, dict)]

    @classmethod
    def _parsed_previous_evaluation(
        cls,
        session: TailoringSession,
    ) -> tuple[ScanResult, TailoringEvaluation, str] | None:
        history = cls._evaluation_history(session)
        if not history:
            return None
        return cls._parse_evaluation_record(history[-1])

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

    @classmethod
    def _record_evaluation(
        cls,
        session: TailoringSession,
        evaluation_id: str,
        context_hash: str,
        scanner_result: ScanResult,
        evaluation: TailoringEvaluation,
    ) -> None:
        snapshot = copy.deepcopy(session.context_snapshot or {})
        record = {
            "evaluation_id": evaluation_id,
            "context_hash": context_hash,
            "candidate_hash": evaluation.candidate_hash,
            "scanner_result": scanner_result.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
        }
        history = snapshot.get("evaluation_history")
        prior_history = history if isinstance(history, list) else []
        snapshot["evaluation_history"] = [*prior_history, record]
        snapshot["evaluation_state"] = record
        session.context_snapshot = snapshot

    async def _evaluate_candidate(
        self,
        session: TailoringSession,
        parts: Mapping[str, Any],
        candidate: Mapping[str, Any],
        pdf: bytes | None,
        *,
        render_warnings: Sequence[str] = (),
        reviewed_record: tuple[int, tuple[ScanResult, TailoringEvaluation, str] | None] | None = None,
    ) -> tuple[ScanResult, TailoringEvaluation]:
        scanner_result = await self._scan_candidate(parts, candidate, pdf)
        history = self._evaluation_history(session)
        previous = self._parsed_previous_evaluation(session)
        if reviewed_record is not None:
            reviewed_index, _reviewed_value = reviewed_record
            previous = self._parse_evaluation_record(history[reviewed_index - 1]) if reviewed_index > 0 else None
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
        source_cv: CV | None = parts["source_cv"]
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
        previous = None
        if source_cv is not None:
            previous = TailoringCV.model_validate(
                {
                    "id": source_cv.id,
                    "title": source_cv.title,
                    "description": source_cv.description,
                    "template_id": source_cv.template_id,
                    "sections": source_cv.sections or [],
                    "customizations": source_cv.customizations or {},
                }
            )
        linked_cv = previous
        opportunities, rich_sources = map_tailoring_opportunities(
            parts["scanner_context"].requirement_extraction,
            parts["scanner_context"].source_scan,
            linked_cv,
            parts["candidate_index_sources"],
        )
        retrieved_ids = {source["source_id"] for source in rich_sources}
        semantic_by_id = {
            item["source_id"]: item
            for item in parts["fresh_candidate_semantics"]
            if isinstance(item, Mapping)
            and isinstance(item.get("source_id"), str)
            and item["source_id"] in retrieved_ids
        }
        extraction = build_candidate_evidence(
            parts["authoritative_library"],
            list(semantic_by_id.values()),
            require_complete=False,
            source_ids=retrieved_ids,
        )
        projection = composer_projection(extraction)
        for source in rich_sources:
            source["source_fingerprint"] = source.pop("content_hash", "")
            semantic = semantic_by_id.get(source["source_id"], {})
            source["semantic_claims"] = copy.deepcopy(semantic.get("claims", []))
        focus_terms = {
            str(term).casefold()
            for term in _job_terms(parts["requirements"])
            if isinstance(term, str) and len(term.strip()) >= 3
        }
        focus_terms.update(
            word
            for word in re.findall(r"[a-z][a-z0-9.+#-]{2,}", application.job_description.casefold())[:300]
        )
        ranked_facts: list[tuple[int, dict[str, Any]]] = []
        for row in parts["candidate_index_rows"]:
            indexed_text = str(row["normalized_text"])
            score = sum(
                1
                for term in focus_terms
                if re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", indexed_text)
            )
            if score:
                ranked_facts.append((score, row))
        ranked_facts.sort(key=lambda item: (-item[0], str(item[1]["source_id"])))
        deterministic_facts: list[dict[str, Any]] = []
        facts_characters = 0
        for _score, row in ranked_facts:
            fact = {key: row[key] for key in ("source_id", "kind", "identity", "structured_facts", "canonical_skills")}
            cost = len(json.dumps(fact, ensure_ascii=False, default=str))
            if facts_characters + cost > 12_000 or len(deterministic_facts) >= 40:
                continue
            deterministic_facts.append(fact)
            facts_characters += cost
        candidate_index = {
            **parts["candidate_index_summary"],
            "relevant_structured_facts": deterministic_facts,
        }
        response = TailoringContextResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            source_cv_id=source_cv.id if source_cv else None,
            expires_at=session.expires_at,
            context_hash=parts["context_hash"],
            job=TailoringJob(
                company=application.company,
                role=application.role,
                job_url=application.job_url,
                description=application.job_description,
                user_instructions=application.notes,
            ),
            profile=copy.deepcopy(parts["profile_data"]),
            previous_cv=previous,
            scanner=parts["scanner_context"],
            requirements=[requirement.model_dump(mode="json") for requirement in parts["requirements"]],
            templates=templates,
            selected_template_id=parts["selected_template_id"],
            selected_template_manifest=copy.deepcopy(
                parts["manifest_by_id"][parts["selected_template_id"]]
            ),
            capabilities=parts["capabilities"],
            capabilities_hash=capabilities_hash(parts["capabilities"]),
            candidate_index=candidate_index,
            candidate_evidence=projection.model_dump(mode="json"),
            linked_cv_scan=parts["scanner_context"].source_scan,
            opportunities=opportunities,
            retrieved_sources=rich_sources,
            writer_context_characters=0,
            effective_appearance=parts["effective"],
            rendered_source=TailoringRenderArtifact(endpoint="/api/v1/tailoring/source-preview") if source_cv else None,
            evaluation_version=TAILORING_EVALUATION_VERSION,
        )
        writer_context_characters = len(json.dumps(
            response.model_dump(mode="json", exclude={"writer_context_characters"}),
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ))
        return response.model_copy(update={"writer_context_characters": writer_context_characters})

    async def candidate_index_refresh_context(self, capability: str | None) -> TailoringEvidenceSourcesResponse:
        """Return a bounded, job-blind batch of only stale/missing sources."""

        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("Candidate index refresh requires protocol v8")
        stale, counts = await CandidateIndexService(self.db).refresh_batch_sources(
            session.user_id,
            max_sources=MAX_REFRESH_SOURCES,
            max_characters=MAX_REFRESH_CHARACTERS,
        )
        stale_count = counts["STALE"]
        missing_count = counts["MISSING"]
        if stale_count == 0 and missing_count == 0:
            cache_state = "warm"
        elif stale_count and missing_count:
            cache_state = "mixed"
        elif stale_count:
            cache_state = "stale"
        else:
            cache_state = "missing"
        return TailoringEvidenceSourcesResponse(
            session_id=session.id,
            expires_at=session.expires_at,
            cache_state=cache_state,
            source_counts={key.lower(): value for key, value in counts.items()},
            semantic_contract=TailoringEvidenceVersions(
                proposition_extractor="isolated-job-blind-worker",
                proposition_model=CANDIDATE_EVIDENCE_PROPOSITION_MODEL,
                proposition_model_revision=CANDIDATE_EVIDENCE_PROPOSITION_MODEL_REVISION,
                prompt_version=CANDIDATE_EVIDENCE_PROMPT_VERSION,
                schema_version=CANDIDATE_EVIDENCE_SCHEMA_VERSION,
                extractor_version=CANDIDATE_EVIDENCE_EXTRACTOR_VERSION,
            ),
            sources=[
                {
                    "source_id": source.source_id,
                    "source_fingerprint": source.source_fingerprint,
                    "kind": source.kind,
                    "identity": source.identity or {},
                    "structured_facts": source.structured_facts or {},
                    "narrative": source.narrative,
                }
                for source in stale
            ],
        )

    async def evidence_context(
        self,
        capability: str | None,
        request: TailoringEvidenceSubmission,
    ) -> TailoringEvidenceContextResponse:
        """Validate each worker result independently and persist current source versions."""

        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("Candidate index refresh requires protocol v8")
        started = time.perf_counter()
        outcome = await CandidateIndexService(self.db).persist_refresh_results(
            session.user_id,
            request.source_results,
        )
        duration_ms = round((time.perf_counter() - started) * 1000)
        snapshot = copy.deepcopy(session.context_snapshot or {})
        metrics = snapshot.get("runtime_metrics")
        metrics = metrics if isinstance(metrics, dict) else {}
        metrics.update({
            "candidate_semantic_refresh_duration_ms": duration_ms,
            "candidate_semantic_batches_processed": int(metrics.get("candidate_semantic_batches_processed", 0)) + 1,
            "candidate_semantic_refresh_sources_accepted": len(outcome["accepted_source_ids"]),
            "candidate_semantic_refresh_sources_rejected": len(outcome["rejected_source_ids"]),
            "candidate_cue_calls": 0,
        })
        snapshot["runtime_metrics"] = metrics
        session.context_snapshot = snapshot
        await self.db.flush()
        return TailoringEvidenceContextResponse(
            session_id=session.id,
            expires_at=session.expires_at,
            accepted_source_ids=outcome["accepted_source_ids"],
            rejected_source_ids=outcome["rejected_source_ids"],
            source_counts={key.lower(): value for key, value in outcome["source_counts"].items()},
        )

    async def source_preview(self, capability: str | None) -> TailoringSourcePreviewResponse:
        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        source_cv: CV | None = parts["source_cv"]
        if source_cv is None:
            raise TailoringCandidateError("This session has no source CV preview")
        pdf = await PDFService(self.db).render_payload(
            source_cv.template_id,
            source_cv.sections or [],
            source_cv.customizations or {},
        )
        source_scan = parts["scanner_context"].source_scan
        if source_scan is None:
            raise TailoringCandidateError("This session has no source scanner analysis")
        source_hash = cv_snapshot_hash(source_cv) or _content_hash({})
        source_evaluation = evaluate_tailoring(
            parts["scanner_context"].requirement_extraction,
            source_scan,
            source_hash,
            source_scan=source_scan,
            current_candidate=source_cv,
            source_cv=source_cv,
            library=parts["authoritative_library"],
            user_instructions=parts["application"].notes,
        )
        return TailoringSourcePreviewResponse(
            pdf_base64=base64.b64encode(pdf).decode("ascii"),
            page_count=pdf_page_count(pdf),
            candidate_hash=source_hash,
            scanner_result=source_scan,
            evaluation=source_evaluation,
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
        # Identity and direct contact fields are server-owned. Location is
        # intentionally candidate-editable so the agent can tailor its
        # disclosure without changing the saved user profile.
        for key in (
            "name",
            "title",
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
        raw_sections, _ = normalize_rich_text_ids(candidate_data.get("sections", []))
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
        )

    async def candidate_preview(
        self,
        capability: str | None,
        request: TailoringPreviewRequest,
    ) -> TailoringPreviewResponse:
        session = await self._session_for_capability(capability)
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        if len(self._evaluation_history(session)) >= 5:
            raise TailoringConflictError("The five-candidate-preview resource limit has been reached")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        pdf = await PDFService(self.db).render_payload(
            candidate["template_id"],
            sections,
            candidate["customizations"],
        )
        page_count = pdf_page_count(pdf)
        scanner_result, evaluation = await self._evaluate_candidate(
            session,
            parts,
            candidate,
            pdf,
        )
        evaluation_id = secrets.token_urlsafe(24)
        self._record_evaluation(
            session,
            evaluation_id,
            parts["context_hash"],
            scanner_result,
            evaluation,
        )
        await self.db.flush()
        return TailoringPreviewResponse(
            pdf_base64=base64.b64encode(pdf).decode("ascii"),
            page_count=page_count,
            evaluation_id=evaluation_id,
            candidate_hash=self._candidate_hash(candidate),
            scanner_result=scanner_result,
            evaluation=evaluation,
        )

    async def submit(
        self,
        capability: str | None,
        request: TailoringSubmitRequest,
    ) -> TailoringSubmitResponse:
        session = await self._session_for_capability(capability, allow_draft_ready=True)
        submit_request_digest = _content_hash(request.model_dump(mode="json"))
        if session.status == TAILORING_SESSION_DRAFT_READY:
            saved = session.result if isinstance(session.result, dict) else None
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
                    "editorial_review": saved["editorial_review"],
                    "render_warnings": saved["render_warnings"],
                    "review_notes": saved["review_notes"],
                }
            )
        if session.protocol_version != PROTOCOL_VERSION:
            raise TailoringConflictError("This tailoring session uses an unsupported protocol")
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        candidate_hash = self._candidate_hash(candidate)
        if request.expected_candidate_hash != candidate_hash:
            raise TailoringStaleError("The candidate changed after preview; render the current candidate before submitting")
        history = self._evaluation_history(session)
        reviewed_record = next(
            (
                (index, self._parse_evaluation_record(record))
                for index, record in enumerate(history)
                if record.get("evaluation_id") == request.evaluation_id
            ),
            None,
        )
        if reviewed_record is None or reviewed_record[1] is None:
            raise TailoringStaleError("The selected evaluation is unavailable in this session; preview the candidate again")
        reviewed_state = history[reviewed_record[0]]
        if reviewed_state.get("context_hash") != request.context_hash:
            raise TailoringStaleError("The selected evaluation belongs to a different tailoring context")
        if reviewed_state.get("candidate_hash") != candidate_hash:
            raise TailoringStaleError("The selected evaluation belongs to a different candidate")
        try:
            reviewed_evaluation = TailoringEvaluation.model_validate(reviewed_state.get("evaluation"))
        except (ValidationError, TypeError) as exc:
            raise TailoringStaleError("The preview evaluation is invalid; render the candidate again") from exc
        if request.editorial_review.evaluation_id != request.evaluation_id:
            raise TailoringStaleError("The editorial review belongs to a different evaluation")
        if request.editorial_review.candidate_hash != candidate_hash:
            raise TailoringStaleError("The editorial review belongs to a different candidate")
        if reviewed_evaluation.candidate_hash != candidate_hash:
            raise TailoringStaleError("The selected evaluation is bound to a different candidate")
        application: Application = parts["application"]
        source_cv: CV | None = parts["source_cv"]
        # Quota reservation starts a SQLite write transaction by rolling back
        # the read transaction used to build the context. Capture scalar IDs
        # before that rollback expires the loaded ORM objects.
        application_id = application.id
        # Render before persistence: the saved document and the preview use
        # exactly the same pipeline and malformed templates cannot become
        # drafts.
        pdf = await PDFService(self.db).render_payload(
            candidate["template_id"],
            sections,
            candidate["customizations"],
        )
        scanner_result, evaluation = await self._evaluate_candidate(
            session,
            parts,
            candidate,
            pdf,
            reviewed_record=reviewed_record,
        )
        source_cv_id = source_cv.id if source_cv else None
        # The service reserves a quota slot and creates an application-owned
        # candidate. It does not change application.cv_id until owner review.
        new_cv = await CVService(self.db).create_cv(
            session.user_id,
            CVCreate(
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
                    "evaluation_id": request.evaluation_id,
                    "scanner_result": scanner_result.model_dump(mode="json"),
                    "review_notes": request.review_notes,
                    "editorial_review": request.editorial_review.model_dump(mode="json"),
                    "tailoring_evaluation": evaluation.model_dump(mode="json"),
                },
            ),
            application_id=application_id,
        )
        await self.db.refresh(session)
        now = _utcnow()
        result_payload = {
            "protocol_version": session.protocol_version,
            "session_id": session.id,
            "application_id": application_id,
            "status": TAILORING_SESSION_DRAFT_READY,
            "source_cv_id": source_cv_id,
            "draft_cv_id": new_cv.id,
            "evaluation_id": request.evaluation_id,
            "candidate_hash": candidate_hash,
            "candidate": candidate,
            "scanner_result": scanner_result.model_dump(mode="json"),
            "tailoring_evaluation": evaluation.model_dump(mode="json"),
            "editorial_review": request.editorial_review.model_dump(mode="json"),
            "render_warnings": evaluation.render_warnings,
            "review_notes": request.review_notes,
            "runtime_metrics": request.runtime_metrics.model_dump(mode="json"),
            "context_hash": request.context_hash,
            "submit_request_digest": submit_request_digest,
        }
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
                attempts=TailoringSession.attempts + 1,
                result=result_payload,
                updated_at=now,
            )
        )
        if update_result.rowcount != 1:
            # This is only reachable under a concurrent submit. The enclosing
            # transaction rolls back the just-created CV and quota reservation.
            raise TailoringConflictError("Tailoring session already has a draft")
        return TailoringSubmitResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=application_id,
            status=TAILORING_SESSION_DRAFT_READY,
            source_cv_id=source_cv_id,
            draft_cv_id=new_cv.id,
            evaluation_id=request.evaluation_id,
            candidate_hash=candidate_hash,
            candidate=TailoringCandidateCV.model_validate(candidate),
            scanner_result=scanner_result,
            evaluation=evaluation,
            editorial_review=request.editorial_review,
            render_warnings=evaluation.render_warnings,
            review_notes=request.review_notes,
        )

    async def accept_draft(self, session_id: str, user_id: str) -> TailoringReviewResponse:
        session = await self._owned_session(session_id, user_id)
        if session.status != TAILORING_SESSION_DRAFT_READY or not session.draft_cv_id:
            raise TailoringConflictError("Tailoring draft is not ready for acceptance")
        application = await self._owned_application(session.application_id, user_id)
        draft = await self._owned_cv(session.draft_cv_id, user_id)
        if application is None or draft is None or draft.application_id != application.id:
            raise TailoringConflictError("Tailoring draft is no longer available")
        parts: dict[str, Any] | None
        if session.protocol_version == PROTOCOL_VERSION:
            try:
                parts = await self._current_context(session)
            except TailoringStaleError as exc:
                now = _utcnow()
                session.status = TAILORING_SESSION_STALE
                session.reviewed_at = now
                session.updated_at = now
                await self.db.flush()
                raise TailoringConflictError("The tailoring context changed; start a new session") from exc
        else:
            # Historical v4 drafts remain owner-reviewable, but an exchanged
            # v4 session cannot resume under the v5 context contract.
            parts = None
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
        if parts is not None and (
            scanner_result.requirement_extraction != parts["scanner_context"].requirement_extraction
            or scanner_result.versions != parts["scanner_context"].versions
        ):
            now = _utcnow()
            session.status = TAILORING_SESSION_STALE
            session.reviewed_at = now
            session.updated_at = now
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

    async def reject_draft(self, session_id: str, user_id: str) -> TailoringReviewResponse:
        session = await self._owned_session(session_id, user_id)
        if session.status != TAILORING_SESSION_DRAFT_READY or not session.draft_cv_id:
            raise TailoringConflictError("Tailoring draft is not ready for rejection")
        draft_id = session.draft_cv_id
        application = await self._owned_application(session.application_id, user_id)
        if application is None:
            raise TailoringConflictError("Tailoring application is no longer available")
        # The draft is unlinked by construction, so normal CV deletion safely
        # marks it inactive and releases the reserved CV quota.
        deleted = await CVService(self.db).delete_cv(draft_id, user_id)
        if not deleted:
            raise TailoringConflictError("Tailoring draft is no longer available")
        now = _utcnow()
        session.status = TAILORING_SESSION_REJECTED
        session.reviewed_at = now
        session.updated_at = now
        await self.db.flush()
        return TailoringReviewResponse(
            protocol_version=session.protocol_version,
            session_id=session.id,
            application_id=application.id,
            status="rejected",
            source_cv_id=session.cv_id,
            draft_cv_id=draft_id,
            cv_id=None,
            scanner_result=ScanResult.model_validate((session.result or {}).get("scanner_result"))
            if isinstance(session.result, dict) and session.result.get("scanner_result")
            else None,
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
    "requirements_snapshot_hash",
]
