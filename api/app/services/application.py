"""Application tracker lifecycle and requirement-tailored CV generation."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationStatusHistory
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
    JobRequirement,
)
from app.schemas.cv import CVCreate
from app.services.cv import CVService
from app.services.library import LibraryService
from app.services.pdf import PDFService, pdf_page_count
from app.services.profile import ProfileService
from app.services.relevance import (
    KEYWORD_EXTRACTION_ERROR,
    MAX_FIT_PASSES,
    REQUIREMENT_ALGORITHM_VERSION,
    KeywordExtractionError,
    evaluate_requirement_relevance,
    extract_requirements,
    not_evaluated_relevance,
    score_requirement_skill_items,
    score_skill_items,
    select_requirement_library_rows,
)
from app.services.quality import evaluate_cv_quality

APPLICATION_NOT_FOUND = "Application not found"
APPLICATION_ALREADY_GENERATED = "Application already has a generated CV"
PROFILE_REQUIRED = "Complete your Library Profile before generating a CV"
GENERATION_FAILED = "CV generation failed. Please retry."

_SECTION_ORDER: tuple[tuple[str, str, str], ...] = (
    ("profile", "Profile", "profile"),
    ("education", "Education", "education"),
    ("skills", "Skills", "skill"),
    ("experience", "Experience", "experience"),
    ("languages", "Languages", "language"),
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
    "languages": 5,
    "education": 6,
}


@dataclass(frozen=True)
class _SkillFitCandidate:
    row_index: int
    item_index: int
    score: float
    row_order: int


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
            select(Application).options(selectinload(Application.status_history))
            .where(Application.user_id == user_id)
            .order_by(Application.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_application(self, application_id: str, user_id: str) -> Application | None:
        result = await self.db.execute(
            select(Application)
            .options(selectinload(Application.status_history))
            .where(Application.id == application_id, Application.user_id == user_id)
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
            next_follow_up_at=data.next_follow_up_at,
            generation_status="pending",
            algorithm_version=REQUIREMENT_ALGORITHM_VERSION,
            status_history=[],
        )
        try:
            requirements = extract_requirements(data.role, data.job_description)
            application.relevance = not_evaluated_relevance(requirements).model_dump(mode="json")
        except KeywordExtractionError:
            # Keep creation permissive; generation will return the actionable
            # extraction error if a future parser cannot find requirements.
            application.relevance = {}
        self.db.add(application)
        await self.db.flush()
        history = ApplicationStatusHistory(
            application_id=application.id,
            from_status=None,
            to_status=application.status,
            changed_at=application.created_at or datetime.now(timezone.utc),
        )
        application.status_history.append(history)
        self.db.add(history)
        await self.db.flush()
        return application

    async def update_application(
        self, application_id: str, user_id: str, data: ApplicationUpdate
    ) -> Application | None:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        previous_status = application.status
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
        if "next_follow_up_at" in update_data:
            application.next_follow_up_at = update_data["next_follow_up_at"]
        if "applied_at" in update_data:
            application.applied_at = update_data["applied_at"]
        if "status" in update_data and update_data["status"] is not None:
            next_status = update_data["status"].value
            application.status = next_status
            if next_status == ApplicationStatus.APPLIED.value and application.applied_at is None:
                application.applied_at = datetime.now(timezone.utc)
            if next_status != previous_status:
                history = ApplicationStatusHistory(
                    application_id=application.id,
                    from_status=previous_status,
                    to_status=next_status,
                    changed_at=datetime.now(timezone.utc),
                )
                application.status_history.append(history)
                self.db.add(history)
        application.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        if job_changed:
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
        try:
            requirements = extract_requirements(application.role, application.job_description)
        except KeywordExtractionError:
            application.relevance = {}
            application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
            application.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return
        cv = await self.cv_service.get_cv(application.cv_id, user_id) if application.cv_id else None
        if cv is None:
            relevance = not_evaluated_relevance(requirements)
            application.quality = {}
        else:
            relevance = evaluate_requirement_relevance(requirements, cv.sections or [])
            application.quality = (
                await self._quality_for_cv(cv)
            ).model_dump(mode="json")
        application.relevance = relevance.model_dump(mode="json")
        application.extracted_keywords = []
        application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
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
            requirements = extract_requirements(application.role, application.job_description)
        except KeywordExtractionError:
            raise ValueError(KEYWORD_EXTRACTION_ERROR) from None

        application.generation_status = "pending"
        application.generation_error = None
        await self.db.flush()

        try:
            selected = select_requirement_library_rows(requirements, library_entries)
            sections, selected_after_fit, fits_one_page, page_count = await self._fit_sections(
                profile.model_dump(exclude_none=True), selected, requirements
            )
            selected_sources = [
                {
                    "library_entry_id": row.library_entry_id,
                    "source_row_id": row.source_row_id,
                    "covered_requirements": list(row.covered_requirement_ids),
                }
                for row in selected_after_fit
            ]
            extra_metadata = {
                "application_id": application.id,
                "generated_by": REQUIREMENT_ALGORITHM_VERSION,
                "selected_sources": selected_sources,
                "extracted_requirements": [requirement.model_dump() for requirement in requirements],
            }
            cv = await self.cv_service.create_cv(
                user.id,
                CVCreate(
                    title=f"{application.company} — {application.role}",
                    description=f"Tailored for {application.role} at {application.company}",
                    template_id="generic-minimal",
                    sections=sections,
                    customizations={"spacing": "none"},
                    extra_metadata=extra_metadata,
                ),
            )
            # Score the materialized snapshot, not the Library rows used to
            # create it. Manual Builder edits therefore affect the score while
            # Library edits never rewrite an existing generated CV.
            relevance = evaluate_requirement_relevance(
                requirements,
                sections,
                profile=profile,
            )
            application.cv_id = cv.id
            application.generation_status = "ready"
            application.generation_error = None
            application.extracted_keywords = []
            application.relevance = relevance.model_dump(mode="json")
            application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
            application.fits_one_page = fits_one_page
            application.quality = evaluate_cv_quality(
                sections,
                page_count=page_count,
            ).model_dump(mode="json")
            application.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return GeneratedApplication(application=application, cv_id=cv.id)
        except Exception:
            application.generation_status = "failed"
            application.generation_error = GENERATION_FAILED
            application.cv_id = None
            application.quality = {}
            application.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return GeneratedApplication(application=application, cv_id=None)

    async def _fit_sections(
        self,
        profile_data: dict[str, Any],
        selected_rows: list,
        keywords: list,
    ) -> tuple[list[dict], list, bool, int | None]:
        sections, generated_ids = self._materialize_sections(profile_data, selected_rows)
        fit_rows = list(selected_rows)
        last_page_count: int | None = None
        for attempt in range(MAX_FIT_PASSES):
            pdf_bytes = await self.pdf_service.render_payload(
                "generic-minimal", sections, {"spacing": "none"}
            )
            last_page_count = pdf_page_count(pdf_bytes)
            if last_page_count == 1:
                return sections, fit_rows, True, last_page_count
            skill_candidates = self._skill_fit_candidates(keywords, fit_rows)
            if skill_candidates:
                candidate = min(
                    skill_candidates,
                    key=lambda item: (item.score, item.row_order, item.item_index),
                )
                row = fit_rows[candidate.row_index]
                generated_id = generated_ids.get(id(row))
                if generated_id is not None:
                    self._remove_materialized_skill_item(
                        sections,
                        generated_id,
                        candidate.item_index,
                    )
                trimmed_payload = copy.deepcopy(row.payload)
                items = list(trimmed_payload.get("items") or [])
                if 0 <= candidate.item_index < len(items):
                    del items[candidate.item_index]
                    trimmed_payload["items"] = items
                    trimmed_row = replace(row, payload=trimmed_payload)
                    fit_rows[candidate.row_index] = trimmed_row
                    if generated_id is not None:
                        generated_ids[id(trimmed_row)] = generated_id
                continue
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
        return sections, fit_rows, False, last_page_count

    @staticmethod
    def _skill_fit_candidates(keywords: list, fit_rows: list) -> list[_SkillFitCandidate]:
        candidates: list[_SkillFitCandidate] = []
        for row_index, row in enumerate(fit_rows):
            items = row.payload.get("items") if row.kind == "skill" else None
            # Removing the final item is equivalent to removing the group and
            # should be handled by the existing row-level policy instead.
            if not isinstance(items, list) or len(items) <= 1:
                continue
            if keywords and isinstance(keywords[0], JobRequirement):
                scored_items = score_requirement_skill_items(keywords, row)
            else:
                scored_items = score_skill_items(keywords, row)
            for item in scored_items:
                candidates.append(
                    _SkillFitCandidate(
                        row_index=row_index,
                        item_index=item.item_index,
                        score=item.score,
                        row_order=item.order,
                    )
                )
        return candidates

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

    @staticmethod
    def _remove_materialized_skill_item(
        sections: list[dict],
        generated_id: str,
        item_index: int,
    ) -> None:
        section = next((section for section in sections if section["type"] == "skills"), None)
        if section is None or not isinstance(section.get("data"), list):
            return
        payload = next((payload for payload in section["data"] if payload.get("id") == generated_id), None)
        if payload is None:
            return
        items = list(payload.get("items") or [])
        if 0 <= item_index < len(items):
            del items[item_index]
            payload["items"] = items

    async def _quality_for_cv(self, cv) -> Any:
        """Run static checks and, when possible, reuse the canonical PDF path."""
        page_count: int | None = None
        try:
            pdf_bytes = await self.pdf_service.render_payload(
                cv.template_id,
                cv.sections,
                cv.customizations,
            )
            page_count = pdf_page_count(pdf_bytes)
        except Exception:  # noqa: BLE001 - static quality remains useful if PDF is unavailable
            pass
        return evaluate_cv_quality(cv.sections, page_count=page_count)


__all__ = [
    "APPLICATION_ALREADY_GENERATED",
    "APPLICATION_NOT_FOUND",
    "GENERATION_FAILED",
    "GeneratedApplication",
    "ApplicationGenerationConflictError",
    "ApplicationService",
    "ProfileRequiredError",
]
