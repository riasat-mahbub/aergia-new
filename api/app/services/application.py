"""Application tracker lifecycle and keyword-tailored CV generation."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.schemas.cv import CVCreate
from app.services.cv import CVService
from app.services.library import LibraryService
from app.services.pdf import PDFService, pdf_page_count
from app.services.profile import ProfileService
from app.services.relevance import (
    ALGORITHM_VERSION,
    KEYWORD_EXTRACTION_ERROR,
    MAX_FIT_PASSES,
    KeywordExtractionError,
    calculate_relevance,
    extract_keywords,
    flatten_library_fields,
    flatten_profile_fields,
    select_relevant_library_rows,
)

APPLICATION_NOT_FOUND = "Application not found"
APPLICATION_ALREADY_GENERATED = "Application already has a generated CV"
PROFILE_REQUIRED = "Complete your Library Profile before generating a CV"
GENERATION_FAILED = "CV generation failed. Please retry."

_SECTION_ORDER: tuple[tuple[str, str, str], ...] = (
    ("profile", "Profile", "profile"),
    ("education", "Education", "education"),
    ("skills", "Skills", "skill"),
    ("experience", "Experience", "experience"),
    ("certifications", "Certifications", "certification"),
    ("projects", "Projects", "project"),
    ("research", "Research", "research"),
)
_REVERSE_FIT_PRIORITY = {
    "research": 0,
    "projects": 1,
    "certifications": 2,
    "experience": 3,
    "skills": 4,
    "education": 5,
}


class ApplicationGenerationConflictError(ValueError):
    """Raised when generation would replace an already-linked CV."""


class ProfileRequiredError(ValueError):
    """Raised when the singleton profile has no usable name."""


@dataclass(frozen=True)
class GeneratedApplication:
    application: Application
    cv_id: str | None


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_service = CVService(db)
        self.pdf_service = PDFService(db)
        self.library_service = LibraryService(db)
        self.profile_service = ProfileService(db)

    async def list_applications(self, user_id: str) -> list[Application]:
        result = await self.db.execute(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_application(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        application = result.scalar_one_or_none()
        if application is not None and application.applied_at is not None and application.applied_at.tzinfo is None:
            application.applied_at = application.applied_at.replace(tzinfo=timezone.utc)
        return application

    async def create_application(self, user_id: str, data: ApplicationCreate) -> Application:
        application = Application(
            user_id=user_id,
            company=data.company,
            role=data.role,
            job_url=data.job_url.strip() if data.job_url and data.job_url.strip() else None,
            job_description=data.job_description,
            notes=data.notes,
            status=ApplicationStatus.DRAFT.value,
            generation_status="pending",
            algorithm_version=ALGORITHM_VERSION,
        )
        self.db.add(application)
        await self.db.flush()
        return application

    async def update_application(
        self, application_id: str, user_id: str, data: ApplicationUpdate
    ) -> Application | None:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        job_changed = False
        for field in ("company", "role", "job_description"):
            if field in update_data and update_data[field] is not None:
                setattr(application, field, update_data[field])
                job_changed = True
        if "job_url" in update_data:
            value = update_data["job_url"]
            application.job_url = value.strip() if value and value.strip() else None
        if "notes" in update_data:
            application.notes = update_data["notes"]
        if "applied_at" in update_data:
            application.applied_at = update_data["applied_at"]
        if "status" in update_data and update_data["status"] is not None:
            next_status = update_data["status"].value
            application.status = next_status
            if next_status == ApplicationStatus.APPLIED.value and application.applied_at is None:
                application.applied_at = datetime.now(timezone.utc)
        application.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        if job_changed and application.cv_id is not None:
            await self._recompute(application, user_id)
        return application

    async def delete_application(self, application_id: str, user_id: str) -> bool:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return False
        await self.db.delete(application)
        await self.db.flush()
        return True

    async def recompute_relevance(self, application_id: str, user_id: str) -> Application | None:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return None
        await self._recompute(application, user_id)
        return application

    async def _recompute(self, application: Application, user_id: str) -> None:
        library_entries = await self.library_service.list_entries(user_id)
        keywords = extract_keywords(application.role, application.job_description, library_entries)
        cv = await self.cv_service.get_cv(application.cv_id, user_id) if application.cv_id else None
        if cv is None:
            relevance = calculate_relevance(keywords, [])
        else:
            relevance = calculate_relevance(keywords, cv.sections or [])
        application.extracted_keywords = [keyword.model_dump() for keyword in keywords]
        application.relevance = relevance.model_dump(mode="json")
        application.algorithm_version = ALGORITHM_VERSION
        application.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def generate_cv(self, application_id: str, user: User) -> GeneratedApplication:
        application = await self.get_application(application_id, user.id)
        if application is None:
            raise LookupError(APPLICATION_NOT_FOUND)
        if application.cv_id is not None or application.generation_status == "ready":
            raise ApplicationGenerationConflictError(APPLICATION_ALREADY_GENERATED)
        if application.generation_status not in {"pending", "failed"}:
            raise ApplicationGenerationConflictError(APPLICATION_ALREADY_GENERATED)

        profile = await self.profile_service.get_profile(user)
        if not profile.name or not profile.name.strip():
            raise ProfileRequiredError(PROFILE_REQUIRED)

        library_entries = await self.library_service.list_entries(user.id)
        try:
            keywords = extract_keywords(application.role, application.job_description, library_entries)
        except KeywordExtractionError:
            raise ValueError(KEYWORD_EXTRACTION_ERROR) from None

        application.generation_status = "pending"
        application.generation_error = None
        await self.db.flush()

        try:
            selected = select_relevant_library_rows(keywords, library_entries)
            sections, selected_after_fit, fits_one_page = await self._fit_sections(
                profile.model_dump(exclude_none=True), selected
            )
            selected_sources = [
                {
                    "library_entry_id": row.library_entry_id,
                    "source_row_id": row.source_row_id,
                }
                for row in selected_after_fit
            ]
            extra_metadata = {
                "application_id": application.id,
                "generated_by": ALGORITHM_VERSION,
                "selected_sources": selected_sources,
                "extracted_keywords": [keyword.model_dump() for keyword in keywords],
            }
            cv = await self.cv_service.create_cv(
                user.id,
                CVCreate(
                    title=f"{application.company} — {application.role}",
                    description=f"Tailored for {application.role} at {application.company}",
                    template_id="generic-minimal",
                    sections=sections,
                    customizations={"spacing": "minimal"},
                    extra_metadata=extra_metadata,
                ),
            )
            relevance_fields = flatten_profile_fields(profile)
            relevance_fields.extend(
                flatten_library_fields(
                    [
                        {
                            "id": row.library_entry_id,
                            "kind": row.kind,
                            "payload": [row.payload],
                        }
                        for row in selected_after_fit
                    ]
                )
            )
            relevance = calculate_relevance(keywords, fields=relevance_fields)
            application.cv_id = cv.id
            application.generation_status = "ready"
            application.generation_error = None
            application.extracted_keywords = [keyword.model_dump() for keyword in keywords]
            application.relevance = relevance.model_dump(mode="json")
            application.algorithm_version = ALGORITHM_VERSION
            application.fits_one_page = fits_one_page
            application.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return GeneratedApplication(application=application, cv_id=cv.id)
        except Exception:
            application.generation_status = "failed"
            application.generation_error = GENERATION_FAILED
            application.cv_id = None
            application.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return GeneratedApplication(application=application, cv_id=None)

    async def _fit_sections(
        self,
        profile_data: dict[str, Any],
        selected_rows: list,
    ) -> tuple[list[dict], list, bool]:
        sections, generated_ids = self._materialize_sections(profile_data, selected_rows)
        fit_rows = list(selected_rows)
        for attempt in range(MAX_FIT_PASSES):
            pdf_bytes = await self.pdf_service.render_payload(
                "generic-minimal", sections, {"spacing": "minimal"}
            )
            if pdf_page_count(pdf_bytes) == 1:
                return sections, fit_rows, True
            if not fit_rows or attempt == MAX_FIT_PASSES - 1:
                break
            remove_index = min(
                range(len(fit_rows)),
                key=lambda index: (
                    fit_rows[index].normalized_score,
                    _REVERSE_FIT_PRIORITY.get(fit_rows[index].section_type, 99),
                    -fit_rows[index].order,
                ),
            )
            row_to_remove = fit_rows.pop(remove_index)
            self._remove_materialized_row(
                sections,
                row_to_remove.section_type,
                generated_ids.pop(id(row_to_remove), None),
            )
        return sections, fit_rows, False

    @staticmethod
    def _materialize_sections(
        profile_data: dict[str, Any],
        selected_rows: list,
    ) -> tuple[list[dict], dict[int, str]]:
        sections: list[dict] = [
            {
                "id": str(uuid.uuid4()),
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": copy.deepcopy(profile_data),
                "style": None,
            }
        ]
        generated_ids: dict[int, str] = {}
        grouped: dict[str, list] = {kind: [] for _, _, kind in _SECTION_ORDER if kind != "profile"}
        for row in selected_rows:
            grouped.setdefault(row.kind, []).append(row)
        for section_type, title, kind in _SECTION_ORDER[1:]:
            rows = grouped.get(kind) or []
            if not rows:
                continue
            data: list[dict] = []
            for row in rows:
                payload = copy.deepcopy(row.payload)
                payload_id = str(uuid.uuid4())
                payload["id"] = payload_id
                generated_ids[id(row)] = payload_id
                data.append(payload)
            sections.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": section_type,
                    "title": title,
                    "enabled": True,
                    "data": data,
                    "style": None,
                }
            )
        return sections, generated_ids

    @staticmethod
    def _remove_materialized_row(
        sections: list[dict],
        section_type: str,
        generated_id: str | None,
    ) -> None:
        section = next((section for section in sections if section["type"] == section_type), None)
        if section is None or not isinstance(section.get("data"), list) or generated_id is None:
            return
        section["data"][:] = [
            payload for payload in section["data"] if payload.get("id") != generated_id
        ]
        if not section["data"]:
            sections.remove(section)


__all__ = [
    "APPLICATION_ALREADY_GENERATED",
    "APPLICATION_NOT_FOUND",
    "GENERATION_FAILED",
    "GeneratedApplication",
    "ApplicationGenerationConflictError",
    "ApplicationService",
    "ProfileRequiredError",
]
