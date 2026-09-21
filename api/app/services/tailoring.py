"""Whole-document local-agent tailoring and review lifecycle.

Protocol v4 intentionally has one write primitive: a complete CV candidate.
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
from collections.abc import Mapping
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
    TailoringLibraryEntry,
    TailoringPreviewRequest,
    TailoringPreviewResponse,
    TailoringRenderArtifact,
    TailoringReviewResponse,
    TailoringSection,
    TailoringSessionCreateResponse,
    TailoringSessionStatusResponse,
    TailoringScannerContext,
    TailoringSubmitRequest,
    TailoringSubmitResponse,
    TailoringTemplate,
    TailoringCodeExchange,
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


def build_tailoring_prompt(session_url: str, code: str, skill_url: str) -> str:
    return (
        "Use the Aergia tailoring skill for this session:\n\n"
        f"{session_url}\n\n"
        f"One-time session code: {code}\n\n"
        "The skill will give your coding agent the job, profile, Library, "
        "optional previous CV, templates, and effective styles. Compose one "
        "complete candidate, render and critique it, revise until it passes "
        "the bounded review or reaches its fallback limit, then submit it "
        "for my review. "
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
    }


def _template_manifest(template: Template) -> dict[str, Any] | None:
    if not isinstance(template.manifest, dict):
        return None
    try:
        return TemplateManifest.model_validate(template.manifest).model_dump(mode="json")
    except ValidationError:
        return None


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
        }

    async def _context_parts(
        self,
        session: TailoringSession,
        *,
        initialize: bool = False,
    ) -> dict[str, Any]:
        resources = await self._context_resources(session)
        if not session.context_snapshot:
            if not initialize:
                raise TailoringStaleError("This tailoring session predates protocol v4; start a new session")
            scanner_context = await self._freeze_scanner_context(resources)
            basis = self._context_basis(resources, scanner_context)
            session.context_snapshot = {
                "schema_version": "tailoring-v4",
                "scanner": scanner_context.model_dump(mode="json"),
                "basis": basis,
            }
        else:
            try:
                snapshot = session.context_snapshot
                scanner_context = TailoringScannerContext.model_validate(snapshot["scanner"])
                frozen_basis = snapshot["basis"]
            except (KeyError, TypeError, ValidationError) as exc:
                raise TailoringStaleError("The tailoring scanner context is invalid; start a new session") from exc
            current_basis = self._context_basis(resources, scanner_context)
            if _content_hash(current_basis) != _content_hash(frozen_basis):
                raise TailoringStaleError("The tailoring context changed; start a new session")

        context_snapshot = session.context_snapshot
        scanner_context = TailoringScannerContext.model_validate(context_snapshot["scanner"])
        basis = self._context_basis(resources, scanner_context)
        return {
            **resources,
            "scanner_context": scanner_context,
            "requirements": scanner_context.requirement_extraction.requirements,
            "context_hash": _content_hash(basis),
        }

    async def create_session(
        self,
        application_id: str,
        user_id: str,
        session_url_base: str | None = None,
    ) -> tuple[TailoringSessionCreateResponse, TailoringSession]:
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
            protocol_version=PROTOCOL_VERSION,
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
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            source_cv_id=source_cv_id,
            cv_id=source_cv_id,
            code=code,
            session_url=session_url,
            skill_url=skill_url,
            prompt=build_tailoring_prompt(session_url, code, skill_url),
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
            protocol_version=PROTOCOL_VERSION,
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
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            expires_at=session.expires_at,
            capability=capability,
        )

    async def _session_for_capability(self, capability: str | None) -> TailoringSession:
        if not capability or len(capability) > 128:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        result = await self.db.execute(
            select(TailoringSession).where(TailoringSession.capability_hash == hash_token(capability.strip()))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        if session.status != TAILORING_SESSION_EXCHANGED:
            raise TailoringConflictError("Tailoring capability is no longer active")
        if _as_utc(session.expires_at) <= _utcnow():
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringExpiredError("Tailoring session expired")
        return session

    async def _current_context(self, session: TailoringSession) -> dict[str, Any]:
        parts = await self._context_parts(session)
        if not session.context_hash:
            session.context_hash = parts["context_hash"]
        if parts["context_hash"] != session.context_hash:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        return parts

    async def context(self, capability: str | None) -> TailoringContextResponse:
        session = await self._session_for_capability(capability)
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
        library = [
            TailoringLibraryEntry(
                id=entry.id,
                kind=entry.kind,
                content_hash=library_entry_content_hash(entry),
                payload=copy.deepcopy(entry.payload or []),
            )
            for entry in parts["libraries"]
        ]
        return TailoringContextResponse(
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
            ),
            profile=copy.deepcopy(parts["profile_data"]),
            previous_cv=previous,
            library=library,
            scanner=parts["scanner_context"],
            requirements=[requirement.model_dump(mode="json") for requirement in parts["requirements"]],
            templates=templates,
            selected_template_id=parts["selected_template_id"],
            selected_template_manifest=copy.deepcopy(
                parts["manifest_by_id"][parts["selected_template_id"]]
            ),
            capabilities=parts["capabilities"],
            capabilities_hash=capabilities_hash(parts["capabilities"]),
            effective_appearance=parts["effective"],
            rendered_source=TailoringRenderArtifact(endpoint="/api/v1/tailoring/source-preview") if source_cv else None,
        )

    async def source_preview(self, capability: str | None) -> TailoringPreviewResponse:
        session = await self._session_for_capability(capability)
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
        return TailoringPreviewResponse(
            pdf_base64=base64.b64encode(pdf).decode("ascii"),
            page_count=pdf_page_count(pdf),
            candidate_hash=cv_snapshot_hash(source_cv) or _content_hash({}),
            scanner_result=source_scan,
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
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        pdf = await PDFService(self.db).render_payload(
            candidate["template_id"],
            sections,
            candidate["customizations"],
        )
        page_count = pdf_page_count(pdf)
        scanner_result = await self._scan_candidate(parts, candidate, pdf)
        return TailoringPreviewResponse(
            pdf_base64=base64.b64encode(pdf).decode("ascii"),
            page_count=page_count,
            candidate_hash=self._candidate_hash(candidate),
            scanner_result=scanner_result,
        )

    async def submit(
        self,
        capability: str | None,
        request: TailoringSubmitRequest,
    ) -> TailoringSubmitResponse:
        session = await self._session_for_capability(capability)
        parts = await self._current_context(session)
        if request.context_hash != parts["context_hash"]:
            raise TailoringStaleError("The tailoring context changed; start a new session")
        candidate, sections = self._normalize_candidate(request.candidate, parts)
        if request.expected_candidate_hash is not None and request.expected_candidate_hash != self._candidate_hash(candidate):
            raise TailoringStaleError("The candidate changed after preview; render the current candidate before submitting")
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
        scanner_result = await self._scan_candidate(parts, candidate, pdf)
        source_cv_id = source_cv.id if source_cv else None
        candidate_hash = self._candidate_hash(candidate)
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
                    "review_notes": request.review_notes,
                },
            ),
            application_id=application_id,
        )
        await self.db.refresh(session)
        now = _utcnow()
        result_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "session_id": session.id,
            "application_id": application_id,
            "status": TAILORING_SESSION_DRAFT_READY,
            "source_cv_id": source_cv_id,
            "draft_cv_id": new_cv.id,
            "candidate_hash": candidate_hash,
            "candidate": candidate,
            "scanner_result": scanner_result.model_dump(mode="json"),
            "review_notes": request.review_notes,
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
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application_id,
            status=TAILORING_SESSION_DRAFT_READY,
            source_cv_id=source_cv_id,
            draft_cv_id=new_cv.id,
            candidate_hash=candidate_hash,
            candidate=TailoringCandidateCV.model_validate(candidate),
            scanner_result=scanner_result,
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
        parts = await self._current_context(session)
        stored_result = (session.result or {}).get("scanner_result") if isinstance(session.result, dict) else None
        try:
            scanner_result = ScanResult.model_validate(stored_result)
        except (ValidationError, TypeError) as exc:
            raise TailoringConflictError("The tailoring draft has no valid scanner result") from exc
        freshness = scanner_result_freshness(
            scanner_result.model_dump(mode="json"),
            application.job_description,
            draft,
            extractor_version=configured_extractor_version(),
        )
        if not freshness["current"] or scanner_result.requirement_extraction != parts["scanner_context"].requirement_extraction:
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
        session.status = TAILORING_SESSION_ACCEPTED
        if isinstance(session.result, dict):
            session.result = {**session.result, "scanner_result": scanner_result.model_dump(mode="json")}
        session.reviewed_at = now
        session.updated_at = now
        await self.db.flush()
        return TailoringReviewResponse(
            protocol_version=PROTOCOL_VERSION,
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
            protocol_version=PROTOCOL_VERSION,
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
