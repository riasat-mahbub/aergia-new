"""Local-agent tailoring session lifecycle and Phase 1 patch application."""

from __future__ import annotations

import copy
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
from app.schemas.application import JobRequirement
from app.schemas.tailoring import (
    PROTOCOL_VERSION,
    ReportGapChange,
    ReplaceDescriptionChange,
    TailoringCodeExchange,
    TailoringEvidencePacket,
    TailoringExchangeResponse,
    TailoringJob,
    TailoringLibraryEntry,
    TailoringPatch,
    TailoringReportedGap,
    TailoringSessionCreateResponse,
    TailoringSubmitResponse,
)
from app.services.profile import ProfileService
from app.services.relevance import REQUIREMENT_ALGORITHM_VERSION, evaluate_requirement_relevance

TAILORING_SESSION_TTL = timedelta(minutes=15)
TAILORING_SESSION_CREATED = "created"
TAILORING_SESSION_EXCHANGED = "exchanged"
TAILORING_SESSION_SUBMITTED = "submitted"
TAILORING_SESSION_EXPIRED = "expired"


class TailoringNotFoundError(LookupError):
    """The authenticated owner cannot access the requested tailoring target."""


class TailoringUnauthorizedError(PermissionError):
    """A code or scoped capability is invalid."""


class TailoringExpiredError(PermissionError):
    """A tailoring session has passed its expiry time."""


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


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive datetime values for comparisons."""

    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


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


class TailoringService:
    """Own the scoped capability flow and atomic Phase 1 patch transaction."""

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

    async def create_session(
        self, application_id: str, user_id: str
    ) -> tuple[TailoringSessionCreateResponse, TailoringSession]:
        application = await self._owned_application(application_id, user_id)
        if application is None:
            raise TailoringNotFoundError("Application not found")
        if not application.cv_id:
            raise TailoringUnavailableError("Generate and link a CV before starting local tailoring")

        cv = await self._owned_cv(application.cv_id, user_id)
        if cv is None:
            raise TailoringUnavailableError("The linked CV is not available for local tailoring")
        _stored_requirements(application)

        code = secrets.token_urlsafe(32)
        now = _utcnow()
        session = TailoringSession(
            user_id=user_id,
            application_id=application.id,
            cv_id=cv.id,
            code_hash=hash_token(code),
            status=TAILORING_SESSION_CREATED,
            expires_at=now + TAILORING_SESSION_TTL,
        )
        self.db.add(session)
        await self.db.flush()
        response = TailoringSessionCreateResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            code=code,
            expires_at=session.expires_at,
        )
        return response, session

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
        exchange_result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.status == TAILORING_SESSION_CREATED,
                TailoringSession.expires_at > now,
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

    async def evidence(self, capability: str | None) -> TailoringEvidencePacket:
        session = await self._session_for_capability(capability)
        application, cv = await self._target_for_session(session)
        requirements = _stored_requirements(application)
        user = await self.db.get(User, session.user_id)
        if user is None:
            raise TailoringUnauthorizedError("Invalid tailoring session owner")
        profile = await ProfileService(self.db).get_profile(user)

        library_result = await self.db.execute(
            select(LibraryEntry)
            .join(Library, LibraryEntry.library_id == Library.id)
            .where(Library.user_id == session.user_id)
            .order_by(LibraryEntry.created_at.asc())
        )
        library = [
            TailoringLibraryEntry(
                id=entry.id,
                kind=entry.kind,
                payload=copy.deepcopy(entry.payload or []),
            )
            for entry in library_result.scalars().all()
        ]

        return TailoringEvidencePacket(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            expires_at=session.expires_at,
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

    @classmethod
    def _apply_patch(
        cls, raw_sections: Any, patch: TailoringPatch
    ) -> tuple[Any, list[str], list[TailoringReportedGap]]:
        updated_sections = copy.deepcopy(raw_sections)
        sections = _sections_from_payload(updated_sections)
        applied_operations: list[str] = []
        gaps: list[TailoringReportedGap] = []
        replaced_targets: set[tuple[str, str]] = set()

        for change in patch.changes:
            if isinstance(change, ReplaceDescriptionChange):
                target_key = (change.section_id, change.entry_id)
                if target_key in replaced_targets:
                    raise TailoringPatchError("A description target may only be replaced once")
                replaced_targets.add(target_key)
                cls._replace_description(sections, change)
                applied_operations.append(change.operation)
            elif isinstance(change, ReportGapChange):
                gaps.append(TailoringReportedGap(requirement=change.requirement, reason=change.reason))
                applied_operations.append(change.operation)
            else:  # pragma: no cover - the discriminated schema closes this set
                raise TailoringPatchError("Unsupported tailoring operation")

        cls._validate_sections(sections)
        return updated_sections, applied_operations, gaps

    @staticmethod
    def _replace_description(
        sections: list[dict[str, Any]], change: ReplaceDescriptionChange
    ) -> None:
        matching_sections = [section for section in sections if section.get("id") == change.section_id]
        if not matching_sections:
            raise TailoringPatchError("Description target section not found")
        if len(matching_sections) > 1:
            raise TailoringPatchError("Description target section is ambiguous")

        data = matching_sections[0].get("data")
        if not isinstance(data, list):
            raise TailoringPatchError("Description target section is not entry-based")
        matching_entries = [
            entry for entry in data
            if isinstance(entry, dict) and entry.get("id") == change.entry_id
        ]
        if not matching_entries:
            raise TailoringPatchError("Description target entry not found")
        if len(matching_entries) > 1:
            raise TailoringPatchError("Description target entry is ambiguous")

        entry = matching_entries[0]
        if "description" not in entry:
            raise TailoringPatchError("Description target has no description field")
        if not isinstance(entry["description"], str):
            raise TailoringPatchError(
                "Phase 1 replace_description only supports plain-string descriptions"
            )
        entry["description"] = change.value

    async def submit(
        self, capability: str | None, patch: TailoringPatch
    ) -> TailoringSubmitResponse:
        session = await self._session_for_capability(capability)
        application, cv = await self._target_for_session(session)
        requirements = _stored_requirements(application)

        updated_sections, applied_operations, gaps = self._apply_patch(cv.sections, patch)
        relevance = evaluate_requirement_relevance(requirements, updated_sections)

        if updated_sections != cv.sections:
            cv.sections = updated_sections
            cv.updated_at = _utcnow()
        now = _utcnow()
        submit_result = await self.db.execute(
            update(TailoringSession)
            .where(
                TailoringSession.id == session.id,
                TailoringSession.status == TAILORING_SESSION_EXCHANGED,
                TailoringSession.expires_at > now,
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

        application.relevance = relevance.model_dump(mode="json")
        application.extracted_keywords = []
        application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
        application.updated_at = now
        session.reported_gaps = [gap.model_dump(mode="json") for gap in gaps]
        await self.db.flush()

        return TailoringSubmitResponse(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            application_id=application.id,
            cv_id=cv.id,
            applied_operations=applied_operations,
            gaps=gaps,
            relevance=relevance.model_dump(mode="json"),
        )


__all__ = [
    "TAILORING_SESSION_CREATED",
    "TAILORING_SESSION_EXCHANGED",
    "TAILORING_SESSION_EXPIRED",
    "TAILORING_SESSION_SUBMITTED",
    "StoredRequirementsUnavailableError",
    "TailoringConflictError",
    "TailoringExpiredError",
    "TailoringNotFoundError",
    "TailoringPatchError",
    "TailoringService",
    "TailoringUnauthorizedError",
    "TailoringUnavailableError",
]
