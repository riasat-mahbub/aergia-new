"""Local-agent tailoring sessions and server-side patch application."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_token
from app.models.application import Application
from app.models.cv import CV
from app.models.library import Library, LibraryEntry
from app.models.tailoring_session import TailoringSession
from app.models.user import User
from app.schema.models import SectionInstance
from app.schemas.application import JobRequirement, RequirementRelevanceResult
from app.schemas.tailoring import (
    AddLibraryEntryChange,
    PROTOCOL_VERSION,
    RemoveBulletChange,
    RemoveEntryChange,
    ReorderBulletsChange,
    ReorderEntriesChange,
    ReportGapChange,
    ReplaceDescriptionChange,
    ReplaceRichTextChange,
    RewriteRichTextChange,
    TailoringCodeExchange,
    TailoringEvidencePacket,
    TailoringEvidenceRef,
    TailoringExchangeResponse,
    TailoringJob,
    TailoringLibraryEntry,
    TailoringPatch,
    TailoringProvenance,
    TailoringReportedGap,
    TailoringSessionCreateResponse,
    TailoringSessionStatusResponse,
    TailoringSubmitResponse,
)
from app.services.profile import ProfileService
from app.services.relevance import REQUIREMENT_ALGORITHM_VERSION, evaluate_requirement_relevance
from app.services.rich_text import normalize_rich_text_ids
from app.services.tailoring_facts import TailoringFactError, validate_tailoring_facts
from app.services.tailoring_policy import (
    LIBRARY_KIND_TO_SECTION_TYPE,
    TailoringPolicyError,
    entry_by_id,
    section_by_id,
    protected_fields,
    validate_document_delta,
    validate_rich_text_target,
)

TAILORING_SESSION_TTL = timedelta(minutes=15)
TAILORING_SESSION_CREATED = "created"
TAILORING_SESSION_EXCHANGED = "exchanged"
TAILORING_SESSION_SUBMITTED = "submitted"
TAILORING_SESSION_APPLIED = "applied"
TAILORING_SESSION_CANCELLED = "cancelled"
TAILORING_SESSION_STALE = "stale"
TAILORING_SESSION_EXPIRED = "expired"

TAILORING_SUPPORTED_OPERATIONS = (
    "replace_description",
    "replace_rich_text",
    "rewrite_rich_text",
    "remove_bullet",
    "reorder_bullets",
    "remove_entry",
    "reorder_entries",
    "add_library_entry",
    "report_gap",
)


def build_tailoring_prompt(session_url: str, code: str) -> str:
    """Build the only user-facing handoff from Aergia to a coding agent.

    The URL identifies the public session context. The one-time code is kept
    as a separate line so the skill can submit it in a request body rather
    than putting the secret in a URL query string.
    """

    return (
        "Use the Aergia tailoring skill for this session:\n\n"
        f"{session_url}\n\n"
        f"One-time session code: {code}\n\n"
        "If the aergia-tailor skill is missing or incompatible, tell me and "
        "ask for approval before installing or updating it from the official "
        "Aergia source. Do not install code automatically."
    )


class TailoringNotFoundError(LookupError):
    """The authenticated owner cannot access the requested tailoring target."""


class TailoringSessionNotFoundError(LookupError):
    """The authenticated owner cannot access the requested session."""


class TailoringUnauthorizedError(PermissionError):
    """A code or scoped capability is invalid."""


class TailoringExpiredError(PermissionError):
    """A tailoring session has passed its expiry time."""


class TailoringStaleError(RuntimeError):
    """The CV, requirements, or evidence source changed after exchange."""


class TailoringConflictError(RuntimeError):
    """The tailoring session cannot perform the requested one-time action."""


class TailoringUnavailableError(ValueError):
    """The application is not ready for the Phase 1 tailoring flow."""


class StoredRequirementsUnavailableError(ValueError):
    """The application has no valid persisted requirement snapshot."""


class TailoringPatchError(ValueError):
    """The patch is valid JSON but cannot be applied to the target CV."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _db_utcnow() -> datetime:
    """Return UTC without tzinfo for SQLite DateTime bind parameters.

    SQLite stores SQLAlchemy ``DateTime(timezone=True)`` values as naive text.
    Loaded values are normalized with ``_as_utc`` below, but predicates sent to
    SQLite must use the same naive representation or Python/driver versions
    can raise when comparing aware and naive datetimes.
    """

    return _utcnow().replace(tzinfo=None)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive datetime values for comparisons."""

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _content_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cv_snapshot_hash(cv: CV) -> str:
    """Hash the authoritative CV state relevant to a tailoring patch.

    User-editable ``extra_metadata`` is intentionally excluded; it is not a
    provenance store and does not change the rendered CV document.
    """

    return _content_hash(
        {
            "title": cv.title,
            "description": cv.description,
            "template_id": cv.template_id,
            "customizations": cv.customizations or {},
            "sections": cv.sections or [],
            "is_active": bool(cv.is_active),
        }
    )


def requirements_snapshot_hash(requirements: list[JobRequirement]) -> str:
    return _content_hash([requirement.model_dump(mode="json") for requirement in requirements])


def profile_snapshot_hash(profile: Mapping[str, Any]) -> str:
    """Hash only the profile snapshot that is exposed to the local agent."""

    return _content_hash(dict(profile))


def protected_facts_for_cv(
    sections: Any,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a narrow, explicit fact manifest for local validation.

    This is an evidence manifest, not a second editable CV representation. It
    intentionally omits prose fields so the agent can distinguish immutable
    identity facts from fields it may rewrite.
    """

    section_list = _sections_from_payload(sections)
    facts: dict[str, Any] = {
        "profile": {
            key: copy.deepcopy(profile[key])
            for key in protected_fields("profile")
            if key in profile
        },
        "entries": [],
    }
    for section in section_list:
        section_type = str(section.get("type", ""))
        allowed = protected_fields(section_type)
        if not allowed or "*" in allowed:
            continue
        data = section.get("data")
        rows = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_id = row.get("id")
            if not isinstance(row_id, str):
                continue
            facts["entries"].append(
                {
                    "section_id": section.get("id"),
                    "entry_id": row_id,
                    "section_type": section_type,
                    "fields": {
                        key: copy.deepcopy(row[key])
                        for key in allowed
                        if key in row
                    },
                }
            )
    return facts


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


def _sections_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        sections = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("sections"), list):
        sections = payload["sections"]
    else:
        raise TailoringPatchError("CV sections must be a list")
    if not all(isinstance(section, dict) for section in sections):
        raise TailoringPatchError("CV sections contain an invalid entry")
    return sections


def _stored_requirements(application: Application) -> list[JobRequirement]:
    """Read requirement models from persisted relevance JSON only.

    This deliberately has no extraction fallback. A tailoring submission must
    score against the same requirement snapshot that was stored for the
    application rather than invoking the server extractor again.
    """

    relevance = application.relevance if isinstance(application.relevance, dict) else {}
    raw_matches = relevance.get("requirements")
    if not isinstance(raw_matches, list):
        raise StoredRequirementsUnavailableError(
            "Stored application requirements are unavailable; recompute the application first"
        )

    requirements: list[JobRequirement] = []
    for raw_match in raw_matches:
        if not isinstance(raw_match, Mapping):
            raise StoredRequirementsUnavailableError("Stored application requirements are invalid")
        raw_requirement = raw_match.get("requirement", raw_match)
        if not isinstance(raw_requirement, Mapping):
            raise StoredRequirementsUnavailableError("Stored application requirements are invalid")
        try:
            requirements.append(JobRequirement.model_validate(raw_requirement))
        except ValidationError as exc:
            raise StoredRequirementsUnavailableError("Stored application requirements are invalid") from exc
    return requirements


def _normalize_requirement_label(value: str) -> str:
    """Normalize agent labels for the backwards-compatible text fallback."""

    return re.sub(r"[^a-z0-9+#]+", " ", value.casefold()).strip()


class TailoringService:
    """Own the scoped capability flow and atomic patch transaction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _owned_application(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _owned_cv(self, cv_id: str, user_id: str) -> CV | None:
        result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
        )
        return result.scalar_one_or_none()

    async def _target_for_session(self, session: TailoringSession) -> tuple[Application, CV]:
        application = await self._owned_application(session.application_id, session.user_id)
        cv = await self._owned_cv(session.cv_id, session.user_id)
        if application is None or cv is None or application.cv_id != session.cv_id:
            raise TailoringConflictError("Tailoring target is no longer available")
        return application, cv

    async def _library_entries(self, user_id: str) -> list[LibraryEntry]:
        result = await self.db.execute(
            select(LibraryEntry)
            .join(Library, LibraryEntry.library_id == Library.id)
            .where(Library.user_id == user_id)
            .order_by(LibraryEntry.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_session(
        self,
        application_id: str,
        user_id: str,
        session_url_base: str | None = None,
    ) -> tuple[TailoringSessionCreateResponse, TailoringSession]:
        application = await self._owned_application(application_id, user_id)
        if application is None:
            raise TailoringNotFoundError("Application not found")
        if not application.cv_id:
            raise TailoringUnavailableError("Generate and link a CV before starting local tailoring")

        cv = await self._owned_cv(application.cv_id, user_id)
        if cv is None:
            raise TailoringUnavailableError("The linked CV is not available for local tailoring")
        user = await self.db.get(User, user_id)
        if user is None:
            raise TailoringNotFoundError("User not found")
        profile = await ProfileService(self.db).get_profile(user)
        profile_payload = profile.model_dump(mode="json", exclude_none=True, exclude={"photo_url"})
        requirements = _stored_requirements(application)

        # Legacy CVs may contain rich-text blocks without stable IDs. Make the
        # canonicalization part of session creation so the evidence hash and
        # the first patch target the same persisted document.
        normalized_sections, normalized = normalize_rich_text_ids(cv.sections or [])
        now = _utcnow()
        if normalized:
            cv.sections = normalized_sections
            cv.revision = (cv.revision or 1) + 1
            cv.updated_at = now

        library_entries = await self._library_entries(user_id)
        library_snapshot = {
            entry.id: library_entry_content_hash(entry)
            for entry in library_entries
        }

        code = secrets.token_urlsafe(32)
        session = TailoringSession(
            user_id=user_id,
            application_id=application.id,
            cv_id=cv.id,
            code_hash=hash_token(code),
            status=TAILORING_SESSION_CREATED,
            expires_at=now + TAILORING_SESSION_TTL,
            base_cv_revision=cv.revision or 1,
            base_cv_hash=cv_snapshot_hash(cv),
            base_requirements_hash=requirements_snapshot_hash(requirements),
            base_profile_hash=profile_snapshot_hash(profile_payload),
            library_snapshot=library_snapshot,
        )
        self.db.add(session)
        await self.db.flush()
        session_url = f"{session_url_base.rstrip('/') if session_url_base else ''}/agent/tailor/{session.id}"
        response = TailoringSessionCreateResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            code=code,
            session_url=session_url,
            prompt=build_tailoring_prompt(session_url, code),
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
    def _session_is_terminal(session: TailoringSession) -> bool:
        return session.status in {
            TAILORING_SESSION_APPLIED,
            TAILORING_SESSION_CANCELLED,
            TAILORING_SESSION_STALE,
            TAILORING_SESSION_EXPIRED,
        }

    async def session_status(
        self, session_id: str, user_id: str
    ) -> TailoringSessionStatusResponse:
        session = await self._owned_session(session_id, user_id)
        now = _utcnow()
        if _as_utc(session.expires_at) <= now and not self._session_is_terminal(session):
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = now
            await self.db.flush()
        elif session.status in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
            # Status polling is also a safe place to surface a changed source
            # snapshot. The capability endpoints still enforce the same check
            # immediately before returning evidence or applying a patch.
            try:
                application, cv = await self._target_for_session(session)
                requirements = _stored_requirements(application)
                library_entries = await self._library_entries(session.user_id)
                await self._assert_snapshot_is_current(session, application, cv, requirements, library_entries)
            except (TailoringStaleError, TailoringConflictError, StoredRequirementsUnavailableError):
                session.status = TAILORING_SESSION_STALE
                session.updated_at = now
                await self.db.flush()
        return TailoringSessionStatusResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=session.application_id,
            cv_id=session.cv_id,
            status=session.status,
            expires_at=session.expires_at,
            created_at=session.created_at,
            exchanged_at=session.exchanged_at,
            submitted_at=session.submitted_at,
            updated_at=session.updated_at,
            attempts=session.attempts,
            reported_gaps=[TailoringReportedGap.model_validate(gap) for gap in (session.reported_gaps or [])],
            result=copy.deepcopy(session.result),
        )

    async def cancel_session(self, session_id: str, user_id: str) -> TailoringSessionStatusResponse:
        session = await self._owned_session(session_id, user_id)
        now = _utcnow()
        db_now = _db_utcnow()
        if _as_utc(session.expires_at) <= now and not self._session_is_terminal(session):
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = now
            await self.db.flush()
        if session.status == TAILORING_SESSION_EXPIRED:
            raise TailoringExpiredError("Tailoring session expired")
        if session.status not in {TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED}:
            raise TailoringConflictError("Tailoring session cannot be cancelled")

        cancel_result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.user_id == user_id,
                TailoringSession.status.in_((TAILORING_SESSION_CREATED, TAILORING_SESSION_EXCHANGED)),
                TailoringSession.expires_at > db_now,
            )
            .values(status=TAILORING_SESSION_CANCELLED, updated_at=now)
        )
        if cancel_result.rowcount != 1:
            raise TailoringConflictError("Tailoring session cannot be cancelled")
        await self.db.refresh(session)
        return await self.session_status(session_id, user_id)

    async def exchange_code(self, data: TailoringCodeExchange) -> TailoringExchangeResponse:
        code_hash = hash_token(data.code)
        result = await self.db.execute(
            select(TailoringSession).where(TailoringSession.code_hash == code_hash)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring code")
        if _as_utc(session.expires_at) <= _utcnow():
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringExpiredError("Tailoring session expired")
        if session.status != TAILORING_SESSION_CREATED:
            raise TailoringConflictError("Tailoring code has already been exchanged")

        capability = secrets.token_urlsafe(32)
        capability_hash = hash_token(capability)
        now = _utcnow()
        db_now = _db_utcnow()
        exchange_result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.status == TAILORING_SESSION_CREATED,
                TailoringSession.expires_at > db_now,
            )
            .values(
                capability_hash=capability_hash,
                status=TAILORING_SESSION_EXCHANGED,
                exchanged_at=now,
                updated_at=now,
            )
        )
        if exchange_result.rowcount != 1:
            raise TailoringConflictError("Tailoring code has already been exchanged")
        await self.db.refresh(session)
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
            select(TailoringSession).where(
                TailoringSession.capability_hash == hash_token(capability.strip())
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        if _as_utc(session.expires_at) <= _utcnow():
            session.status = TAILORING_SESSION_EXPIRED
            session.updated_at = _utcnow()
            await self.db.flush()
            raise TailoringExpiredError("Tailoring session expired")
        if session.status == TAILORING_SESSION_SUBMITTED:
            raise TailoringConflictError("Tailoring session has already been submitted")
        if session.status != TAILORING_SESSION_EXCHANGED:
            raise TailoringUnauthorizedError("Invalid tailoring capability")
        return session

    async def _assert_snapshot_is_current(
        self,
        session: TailoringSession,
        application: Application,
        cv: CV,
        requirements: list[JobRequirement],
        library_entries: list[LibraryEntry],
    ) -> None:
        if (
            not session.base_cv_revision
            or not session.base_cv_hash
            or not session.base_requirements_hash
            or not session.base_profile_hash
        ):
            raise TailoringStaleError("Tailoring session predates the current patch protocol; start a new session")
        if cv.revision != session.base_cv_revision or cv_snapshot_hash(cv) != session.base_cv_hash:
            raise TailoringStaleError("The linked CV changed; start a new tailoring session")
        if requirements_snapshot_hash(requirements) != session.base_requirements_hash:
            raise TailoringStaleError("The application requirements changed; start a new tailoring session")

        user = await self.db.get(User, session.user_id)
        if user is None:
            raise TailoringConflictError("Tailoring session owner is no longer available")
        profile = await ProfileService(self.db).get_profile(user)
        profile_payload = profile.model_dump(mode="json", exclude_none=True, exclude={"photo_url"})
        if profile_snapshot_hash(profile_payload) != session.base_profile_hash:
            raise TailoringStaleError("The profile changed; start a new tailoring session")

        current_library_snapshot = {
            entry.id: library_entry_content_hash(entry)
            for entry in library_entries
        }
        if current_library_snapshot != (session.library_snapshot or {}):
            raise TailoringStaleError("The Library changed; start a new tailoring session")

        if application.cv_id != cv.id:
            raise TailoringConflictError("Tailoring target is no longer available")

    async def evidence(self, capability: str | None) -> TailoringEvidencePacket:
        session = await self._session_for_capability(capability)
        application, cv = await self._target_for_session(session)
        requirements = _stored_requirements(application)
        library_entries = await self._library_entries(session.user_id)
        await self._assert_snapshot_is_current(session, application, cv, requirements, library_entries)
        user = await self.db.get(User, session.user_id)
        if user is None:
            raise TailoringUnauthorizedError("Invalid tailoring session owner")
        profile = await ProfileService(self.db).get_profile(user)

        library = [
            TailoringLibraryEntry(
                id=entry.id,
                kind=entry.kind,
                content_hash=library_entry_content_hash(entry),
                payload=copy.deepcopy(entry.payload or []),
            )
            for entry in library_entries
        ]

        return TailoringEvidencePacket(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            expires_at=session.expires_at,
            base_revision=session.base_cv_revision or 1,
            base_hash=session.base_cv_hash or "0" * 64,
            requirements_hash=session.base_requirements_hash or "0" * 64,
            profile_hash=session.base_profile_hash or "0" * 64,
            supported_operations=list(TAILORING_SUPPORTED_OPERATIONS),
            job=TailoringJob(
                company=application.company,
                role=application.role,
                job_url=application.job_url,
                description=application.job_description,
            ),
            cv={
                "id": cv.id,
                "title": cv.title,
                "sections": copy.deepcopy(cv.sections or []),
            },
            profile=profile.model_dump(mode="json", exclude_none=True, exclude={"photo_url"}),
            protected_facts=protected_facts_for_cv(
                cv.sections or [],
                profile.model_dump(mode="json", exclude_none=True, exclude={"photo_url"}),
            ),
            library=library,
            requirements=[requirement.model_dump(mode="json") for requirement in requirements],
        )

    @staticmethod
    def _validate_sections(sections: list[dict[str, Any]]) -> None:
        try:
            for section in sections:
                SectionInstance.model_validate(section)
        except ValidationError as exc:
            raise TailoringPatchError("Updated CV sections are invalid") from exc

    @staticmethod
    def _attach_tailoring_feedback(
        relevance: RequirementRelevanceResult,
        changes: list[Any],
    ) -> None:
        """Attach local-agent gap explanations to their stored requirements.

        New agents should send ``requirement_id``. Older agents only sent a
        requirement label, so an exact or bounded normalized-text fallback is
        retained for compatibility. An ID never falls back to text matching;
        this keeps a malformed or stale ID from attaching feedback to the
        wrong requirement.
        """

        for change in changes:
            if not isinstance(change, ReportGapChange):
                continue
            normalized_label = _normalize_requirement_label(change.requirement)
            for match in relevance.requirements:
                requirement = match.requirement
                if change.requirement_id:
                    matches = requirement.id == change.requirement_id
                else:
                    candidates = {
                        _normalize_requirement_label(candidate)
                        for candidate in (
                            requirement.text,
                            requirement.normalized,
                            requirement.canonical or "",
                        )
                        if candidate
                    }
                    matches = any(
                        normalized_label == candidate
                        or (len(normalized_label) >= 3 and normalized_label in candidate)
                        or (len(candidate) >= 3 and candidate in normalized_label)
                        for candidate in candidates
                    )
                if matches and change.reason not in match.tailoring_feedback:
                    match.tailoring_feedback.append(change.reason)

    @staticmethod
    def _validate_requirement_feedback_targets(
        requirements: list[JobRequirement],
        changes: list[Any],
    ) -> None:
        """Reject IDs that are not part of this session's stored snapshot."""

        requirement_ids = {requirement.id for requirement in requirements}
        for change in changes:
            if (
                isinstance(change, ReportGapChange)
                and change.requirement_id
                and change.requirement_id not in requirement_ids
            ):
                raise TailoringPatchError(f"Unknown requirement ID: {change.requirement_id}")

    @classmethod
    def _apply_patch(
        cls,
        raw_sections: Any,
        patch: TailoringPatch,
        library_rows: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
    ) -> tuple[Any, list[str], list[TailoringReportedGap]]:
        normalized_source, _ = normalize_rich_text_ids(raw_sections)
        updated_sections = copy.deepcopy(normalized_source)
        before_sections = copy.deepcopy(_sections_from_payload(normalized_source))
        sections = _sections_from_payload(updated_sections)
        applied_operations: list[str] = []
        gaps: list[TailoringReportedGap] = []
        replaced_targets: set[tuple[str, str]] = set()
        library_rows = library_rows or {}

        try:
            for change in patch.changes:
                if isinstance(change, ReplaceDescriptionChange):
                    target_key = (change.section_id, change.entry_id)
                    if target_key in replaced_targets:
                        raise TailoringPatchError("A description target may only be replaced once")
                    replaced_targets.add(target_key)
                    cls._replace_description(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, ReplaceRichTextChange):
                    cls._replace_rich_text_string(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, RewriteRichTextChange):
                    cls._rewrite_rich_text(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, RemoveBulletChange):
                    cls._remove_bullet(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, ReorderBulletsChange):
                    cls._reorder_bullets(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, RemoveEntryChange):
                    cls._remove_entry(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, ReorderEntriesChange):
                    cls._reorder_entries(sections, change)
                    applied_operations.append(change.operation)
                elif isinstance(change, AddLibraryEntryChange):
                    cls._add_library_entry(sections, change, library_rows)
                    applied_operations.append(change.operation)
                elif isinstance(change, ReportGapChange):
                    gaps.append(TailoringReportedGap(requirement=change.requirement, reason=change.reason))
                    applied_operations.append(change.operation)
                else:  # pragma: no cover - the discriminated schema closes this set
                    raise TailoringPatchError("Unsupported tailoring operation")
        except TailoringPolicyError as exc:
            raise TailoringPatchError(str(exc)) from exc

        cls._validate_sections(sections)
        try:
            validate_document_delta(before_sections, sections, list(patch.changes))
        except TailoringPolicyError as exc:
            raise TailoringPatchError(str(exc)) from exc
        return updated_sections, applied_operations, gaps

    @staticmethod
    def _replace_description(
        sections: list[dict[str, Any]], change: ReplaceDescriptionChange
    ) -> None:
        section = section_by_id(sections, change.section_id)
        entry = validate_rich_text_target(section, "description", change.entry_id)
        if "description" not in entry:
            raise TailoringPatchError("Description target has no description field")
        if not isinstance(entry["description"], str):
            raise TailoringPatchError(
                "replace_description only supports plain-string descriptions; use rewrite_rich_text"
            )
        entry["description"] = change.value

    @staticmethod
    def _replace_rich_text_string(
        sections: list[dict[str, Any]], change: ReplaceRichTextChange
    ) -> None:
        section = section_by_id(sections, change.section_id)
        entry = validate_rich_text_target(section, change.field, change.entry_id)
        if change.field not in entry:
            raise TailoringPatchError(f"{change.field.title()} target has no {change.field} field")
        if not isinstance(entry[change.field], str):
            raise TailoringPatchError(
                "replace_rich_text only supports plain-string fields; use rewrite_rich_text for rich blocks"
            )
        entry[change.field] = change.value

    @staticmethod
    def _rewrite_rich_text(
        sections: list[dict[str, Any]], change: RewriteRichTextChange
    ) -> None:
        section = section_by_id(sections, change.section_id)
        entry = validate_rich_text_target(section, change.field, change.entry_id)
        block_ids = [block.id for block in change.value]
        if len(set(block_ids)) != len(block_ids):
            raise TailoringPatchError("Rich-text block IDs must be unique")
        for block in change.value:
            item_ids = [item.id for item in block.items]
            if len(set(item_ids)) != len(item_ids):
                raise TailoringPatchError("Rich-text item IDs must be unique within a block")
        entry[change.field] = [block.model_dump(mode="json", exclude_none=True) for block in change.value]

    @staticmethod
    def _rich_text_blocks(
        sections: list[dict[str, Any]], section_id: str, entry_id: str | None, field: str
    ) -> list[dict[str, Any]]:
        section = section_by_id(sections, section_id)
        entry = validate_rich_text_target(section, field, entry_id)
        value = entry.get(field)
        if not isinstance(value, list) or not all(isinstance(block, dict) for block in value):
            raise TailoringPatchError("Bullet operation requires canonical rich-text blocks")
        return value

    @classmethod
    def _remove_bullet(cls, sections: list[dict[str, Any]], change: RemoveBulletChange) -> None:
        blocks = cls._rich_text_blocks(sections, change.section_id, change.entry_id, change.field)
        matches = [block for block in blocks if block.get("id") == change.block_id]
        if not matches:
            raise TailoringPatchError("Bullet block not found")
        if len(matches) > 1:
            raise TailoringPatchError("Bullet block is ambiguous")
        if matches[0].get("type") != "bullet_list":
            raise TailoringPatchError("remove_bullet requires a bullet-list block")
        items = matches[0].get("items")
        if not isinstance(items, list):
            raise TailoringPatchError("Bullet block items are invalid")
        original_length = len(items)
        if not all(isinstance(item, dict) for item in items):
            raise TailoringPatchError("Bullet block items are invalid")
        matches[0]["items"] = [item for item in items if item.get("id") != change.item_id]
        if len(matches[0]["items"]) == original_length:
            raise TailoringPatchError("Bullet item not found")
        if not matches[0]["items"]:
            blocks.remove(matches[0])

    @classmethod
    def _reorder_bullets(cls, sections: list[dict[str, Any]], change: ReorderBulletsChange) -> None:
        blocks = cls._rich_text_blocks(sections, change.section_id, change.entry_id, change.field)
        matches = [block for block in blocks if block.get("id") == change.block_id]
        if not matches:
            raise TailoringPatchError("Bullet block not found")
        if len(matches) > 1:
            raise TailoringPatchError("Bullet block is ambiguous")
        if matches[0].get("type") != "bullet_list":
            raise TailoringPatchError("reorder_bullets requires a bullet-list block")
        items = matches[0].get("items")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise TailoringPatchError("Bullet block items are invalid")
        existing_ids = [item.get("id") for item in items]
        if len(set(existing_ids)) != len(existing_ids) or set(existing_ids) != set(change.item_ids):
            raise TailoringPatchError("reorder_bullets must contain every existing item exactly once")
        by_id = {item["id"]: item for item in items}
        matches[0]["items"] = [by_id[item_id] for item_id in change.item_ids]

    @staticmethod
    def _remove_entry(sections: list[dict[str, Any]], change: RemoveEntryChange) -> None:
        section = section_by_id(sections, change.section_id)
        data = section.get("data")
        if not isinstance(data, list):
            raise TailoringPatchError("Entry removal requires an entry-based section")
        original_length = len(data)
        data[:] = [entry for entry in data if not (isinstance(entry, dict) and entry.get("id") == change.entry_id)]
        if len(data) == original_length:
            raise TailoringPatchError("Entry target not found")

    @staticmethod
    def _reorder_entries(sections: list[dict[str, Any]], change: ReorderEntriesChange) -> None:
        section = section_by_id(sections, change.section_id)
        data = section.get("data")
        if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
            raise TailoringPatchError("Entry reordering requires an entry-based section")
        existing_ids = [entry.get("id") for entry in data]
        if len(set(existing_ids)) != len(existing_ids) or set(existing_ids) != set(change.entry_ids):
            raise TailoringPatchError("reorder_entries must contain every existing entry exactly once")
        by_id = {entry["id"]: entry for entry in data}
        data[:] = [by_id[entry_id] for entry_id in change.entry_ids]

    @staticmethod
    def _add_library_entry(
        sections: list[dict[str, Any]],
        change: AddLibraryEntryChange,
        library_rows: Mapping[tuple[str, str], Mapping[str, Any]],
    ) -> None:
        source = library_rows.get((change.library_entry_id, change.source_row_id))
        if source is None:
            raise TailoringPatchError("Library source row is not available in the evidence snapshot")
        section = section_by_id(sections, change.section_id)
        expected_type = LIBRARY_KIND_TO_SECTION_TYPE.get(str(source.get("kind", "")))
        if expected_type is None or section.get("type") != expected_type:
            raise TailoringPatchError("Library source kind does not match the target section")
        data = section.get("data")
        if not isinstance(data, list):
            raise TailoringPatchError("Library insertion requires an entry-based section")
        source_row = source.get("row")
        if not isinstance(source_row, dict):
            raise TailoringPatchError("Library source row is invalid")
        new_entry = copy.deepcopy(source_row)
        new_entry["id"] = f"tailoring_{secrets.token_hex(16)}"
        normalized, _ = normalize_rich_text_ids(
            [{"id": "source", "type": expected_type, "title": "source", "data": [new_entry]}]
        )
        normalized_row = normalized[0]["data"][0]
        data.append(normalized_row)

    async def _library_rows_for_patch(
        self, patch: TailoringPatch, library_entries: list[LibraryEntry]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        requested = {
            (change.library_entry_id, change.source_row_id)
            for change in patch.changes
            if isinstance(change, AddLibraryEntryChange)
        }
        if not requested:
            return {}

        entries_by_id = {entry.id: entry for entry in library_entries}
        resolved: dict[tuple[str, str], dict[str, Any]] = {}
        for library_entry_id, source_row_id in requested:
            entry = entries_by_id.get(library_entry_id)
            if entry is None:
                raise TailoringPatchError("Library source entry is not available in the evidence snapshot")
            row = next(
                (
                    candidate
                    for candidate in (entry.payload or [])
                    if isinstance(candidate, dict) and candidate.get("id") == source_row_id
                ),
                None,
            )
            if row is None:
                raise TailoringPatchError("Library source row is not available in the evidence snapshot")
            resolved[(library_entry_id, source_row_id)] = {
                "kind": entry.kind,
                "row": copy.deepcopy(row),
            }
        return resolved

    @staticmethod
    def _read_source_field(source: Mapping[str, Any], field_path: str) -> Any:
        value: Any = source
        for component in field_path.split("."):
            if not isinstance(value, Mapping) or component not in value:
                return None
            value = value[component]
        return value

    @classmethod
    def _validate_evidence_refs(
        cls,
        session: TailoringSession,
        sections: list[dict[str, Any]],
        changes: list[Any],
        library_entries: list[LibraryEntry],
    ) -> None:
        """Validate every declared source against the exchanged snapshot."""

        library_by_id = {entry.id: entry for entry in library_entries}
        snapshot = session.library_snapshot or {}
        for change in changes:
            evidence = getattr(change, "evidence", None) or []
            if not evidence:
                continue
            for reference in evidence:
                if not isinstance(reference, TailoringEvidenceRef):
                    raise TailoringPatchError("Evidence reference is invalid")
                if reference.source == "cv":
                    try:
                        section = section_by_id(sections, reference.section_id or "")
                        source = entry_by_id(section, reference.entry_id)
                    except TailoringPolicyError as exc:
                        raise TailoringPatchError(str(exc)) from exc
                    if cls._read_source_field(source, reference.field_path) is None:
                        raise TailoringPatchError("CV evidence field does not exist")
                    continue

                library_entry = library_by_id.get(reference.library_entry_id or "")
                if library_entry is None:
                    raise TailoringPatchError("Library evidence entry is unavailable")
                current_hash = library_entry_content_hash(library_entry)
                if snapshot.get(library_entry.id) != reference.source_hash or current_hash != reference.source_hash:
                    raise TailoringStaleError("A Library evidence source changed; start a new tailoring session")
                source_row = next(
                    (
                        candidate
                        for candidate in (library_entry.payload or [])
                        if isinstance(candidate, dict) and candidate.get("id") == reference.source_row_id
                    ),
                    None,
                )
                if source_row is None or cls._read_source_field(source_row, reference.field_path) is None:
                    raise TailoringPatchError("Library evidence field does not exist")

            if isinstance(change, AddLibraryEntryChange):
                if not any(
                    reference.source == "library"
                    and reference.library_entry_id == change.library_entry_id
                    and reference.source_row_id == change.source_row_id
                    for reference in evidence
                ):
                    raise TailoringPatchError("Library insertion must cite its source row")

    @staticmethod
    def _provenance_for_patch(patch: TailoringPatch) -> list[TailoringProvenance]:
        return [
            TailoringProvenance(
                operation=change.operation,
                section_id=getattr(change, "section_id", None),
                entry_id=getattr(change, "entry_id", None),
                field=getattr(change, "field", None),
                evidence=list(getattr(change, "evidence", None) or []),
            )
            for change in patch.changes
        ]

    async def submit(
        self, capability: str | None, patch: TailoringPatch
    ) -> TailoringSubmitResponse:
        session = await self._session_for_capability(capability)
        application, cv = await self._target_for_session(session)
        requirements = _stored_requirements(application)
        library_entries = await self._library_entries(session.user_id)
        await self._assert_snapshot_is_current(session, application, cv, requirements, library_entries)
        if patch.base_revision != session.base_cv_revision or patch.base_hash != session.base_cv_hash:
            raise TailoringStaleError("The patch was created from a different CV snapshot; start a new session")

        source_sections, _ = normalize_rich_text_ids(cv.sections or [])
        source_section_list = _sections_from_payload(source_sections)
        self._validate_evidence_refs(session, source_section_list, list(patch.changes), library_entries)
        self._validate_requirement_feedback_targets(requirements, list(patch.changes))
        library_rows = await self._library_rows_for_patch(patch, library_entries)

        before_relevance = copy.deepcopy(application.relevance or {})
        updated_sections, applied_operations, gaps = self._apply_patch(source_sections, patch, library_rows)
        try:
            validate_tailoring_facts(
                source_section_list,
                _sections_from_payload(updated_sections),
                list(patch.changes),
                library_entries,
            )
        except TailoringFactError as exc:
            raise TailoringPatchError(str(exc)) from exc
        relevance = evaluate_requirement_relevance(requirements, updated_sections)
        self._attach_tailoring_feedback(relevance, list(patch.changes))

        now = _utcnow()
        db_now = _db_utcnow()
        submit_result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.status == TAILORING_SESSION_EXCHANGED,
                TailoringSession.expires_at > db_now,
            )
            .values(
                status=TAILORING_SESSION_SUBMITTED,
                submitted_at=now,
                attempts=TailoringSession.attempts + 1,
                updated_at=now,
            )
        )
        if submit_result.rowcount != 1:
            raise TailoringConflictError("Tailoring session has already been submitted")
        await self.db.refresh(session)

        cv_update = await self.db.execute(
            update(CV)
            .where(CV.id == cv.id, CV.revision == session.base_cv_revision)
            .values(
                sections=updated_sections,
                revision=CV.revision + 1,
                updated_at=now,
            )
        )
        if cv_update.rowcount != 1:
            raise TailoringStaleError("The linked CV changed while the patch was being applied")
        cv.sections = updated_sections
        cv.revision = (session.base_cv_revision or 1) + 1
        cv.updated_at = now

        application.relevance = relevance.model_dump(mode="json")
        application.extracted_keywords = []
        application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
        application.updated_at = now
        session.reported_gaps = [gap.model_dump(mode="json") for gap in gaps]
        provenance = self._provenance_for_patch(patch)
        session.provenance = [record.model_dump(mode="json") for record in provenance]
        response = TailoringSubmitResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            base_revision=session.base_cv_revision or 1,
            new_revision=(session.base_cv_revision or 1) + 1,
            applied_operations=applied_operations,
            gaps=gaps,
            provenance=provenance,
            before_relevance=before_relevance,
            relevance=relevance.model_dump(mode="json"),
        )
        session.status = TAILORING_SESSION_APPLIED
        session.result = response.model_dump(mode="json")
        session.updated_at = now
        await self.db.flush()
        return response


__all__ = [
    "TAILORING_SESSION_CREATED",
    "TAILORING_SESSION_EXCHANGED",
    "TAILORING_SESSION_EXPIRED",
    "TAILORING_SESSION_APPLIED",
    "TAILORING_SESSION_CANCELLED",
    "TAILORING_SESSION_STALE",
    "TAILORING_SESSION_SUBMITTED",
    "TailoringSessionNotFoundError",
    "StoredRequirementsUnavailableError",
    "TailoringConflictError",
    "TailoringExpiredError",
    "TailoringNotFoundError",
    "TailoringPatchError",
    "TailoringStaleError",
    "TailoringService",
    "TailoringUnauthorizedError",
    "TailoringUnavailableError",
    "build_tailoring_prompt",
]
