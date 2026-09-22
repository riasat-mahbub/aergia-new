"""Application lifecycle, legacy relevance refresh, and scanner execution."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationStatusHistory
from app.models.cv import CV
from app.scanner.service import ScannerService
from app.http_schemas.application import (
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services.cv import CVService
from app.services.pdf import PDFService, pdf_page_count
from app.services.relevance import (
    REQUIREMENT_ALGORITHM_VERSION,
    evaluate_requirement_relevance,
    extract_requirements,
    not_evaluated_relevance,
)
from app.services.quality import evaluate_cv_quality
from app.services.quotas import QuotaResource, QuotaService

APPLICATION_NOT_FOUND = "Application not found"
logger = logging.getLogger(__name__)


class ApplicationCVLinkError(ValueError):
    """Raised when a CV cannot be linked to an application."""


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_service = CVService(db)
        self.pdf_service = PDFService(db)
        self.scanner_service = ScannerService()

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
            .options(selectinload(Application.status_history), selectinload(Application.cv))
            .where(Application.id == application_id, Application.user_id == user_id)
        )
        application = result.scalar_one_or_none()
        if application is not None and application.applied_at is not None and application.applied_at.tzinfo is None:
            application.applied_at = application.applied_at.replace(tzinfo=timezone.utc)
        return application

    async def create_application(self, user_id: str, data: ApplicationCreate) -> Application:
        # Extraction is part of application creation. A model failure must
        # abort the request rather than creating a row with an empty result.
        requirements = extract_requirements(data.role, data.job_description)
        application = Application(
            user_id=user_id,
            company=data.company,
            role=data.role,
            job_url=data.job_url.strip() if data.job_url and data.job_url.strip() else None,
            job_description=data.job_description,
            notes=data.notes,
            status=ApplicationStatus.DRAFT.value,
            next_follow_up_at=data.next_follow_up_at,
            algorithm_version=REQUIREMENT_ALGORITHM_VERSION,
            status_history=[],
        )
        application.relevance = not_evaluated_relevance(requirements).model_dump(mode="json")
        await QuotaService(self.db).reserve(user_id, QuotaResource.APPLICATION)
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
        cv_changed = "cv_id" in update_data and update_data["cv_id"] != application.cv_id
        job_description_changed = (
            "job_description" in update_data
            and update_data["job_description"] is not None
            and update_data["job_description"] != application.job_description
        )
        for field in ("company", "role", "job_description"):
            if field in update_data and update_data[field] is not None:
                setattr(application, field, update_data[field])
                job_changed = True
        if cv_changed:
            new_cv_id = update_data["cv_id"]
            next_cv = None
            if new_cv_id is not None:
                next_cv = await self.cv_service.get_cv(new_cv_id, user_id)
                if next_cv is None:
                    raise ApplicationCVLinkError("CV not found")
                if next_cv.application_id not in {None, application.id}:
                    raise ApplicationCVLinkError("CV is already associated with another application")
                linked_elsewhere = await self.db.execute(
                    select(Application.id).where(
                        Application.cv_id == new_cv_id,
                        Application.id != application.id,
                    ).limit(1)
                )
                if linked_elsewhere.scalar_one_or_none() is not None:
                    raise ApplicationCVLinkError("CV is already linked to another application")

            previous_cv = await self.cv_service.get_cv(application.cv_id, user_id) if application.cv_id else None
            if previous_cv is not None and previous_cv.application_id == application.id:
                previous_cv.application_id = None
            application.cv_id = new_cv_id
            application.cv = next_cv
            if next_cv is not None:
                next_cv.application_id = application.id
            application.scanner_rescan_required = (
                application.scanner_result is not None or application.scanner_rescan_required
            )
            application.scanner_result = None
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
        if job_description_changed:
            # Keep the previous scanner result from being mistaken for an
            # evaluation of the newly edited posting.
            application.scanner_rescan_required = (
                application.scanner_result is not None or application.scanner_rescan_required
            )
            application.scanner_result = None
        await self.db.flush()

        if job_changed or cv_changed:
            await self._recompute(application, user_id)
        return application

    async def delete_application(self, application_id: str, user_id: str) -> bool:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return False
        # SQLite foreign-key enforcement is disabled on the app's connections;
        # explicitly detach owned CVs so deletion cannot leave dangling links.
        await self.db.execute(
            update(CV)
            .where(CV.application_id == application.id, CV.user_id == user_id)
            .values(application_id=None)
        )
        await self.db.delete(application)
        await self.db.flush()
        await QuotaService(self.db).release(user_id, QuotaResource.APPLICATION)
        return True

    async def recompute_relevance(self, application_id: str, user_id: str) -> Application | None:
        application = await self.get_application(application_id, user_id)
        if application is None:
            return None
        await self._recompute(application, user_id)
        return application

    async def scan_application(self, application_id: str, user_id: str) -> Application | None:
        """Run the new scanner against an application's linked CV."""

        application = await self.get_application(application_id, user_id)
        if application is None:
            return None
        if not application.cv_id:
            raise ValueError("Application has no linked CV")
        cv = await self.cv_service.get_cv(application.cv_id, user_id)
        if cv is None:
            raise ValueError("Application's linked CV is unavailable")
        pdf_bytes: bytes | None = None
        render_manifest = None
        template_data = await self.cv_service.get_template_data(cv.template_id)
        if template_data:
            render_manifest = template_data.get("manifest")
        try:
            pdf_bytes = await self.pdf_service.render_payload(
                cv.template_id,
                cv.sections or [],
                cv.customizations or {},
            )
        except Exception as exc:  # noqa: BLE001 - other scanner branches remain useful without a PDF
            logger.info("scanner_pdf_render_unavailable", extra={"exception_type": type(exc).__name__})
        result = await asyncio.to_thread(
            self.scanner_service.scan,
            application.job_description,
            cv,
            pdf_bytes=pdf_bytes,
            render_manifest=render_manifest,
        )
        application.scanner_result = result.model_dump(mode="json")
        application.scanner_rescan_required = False
        application.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return application

    async def _recompute(self, application: Application, user_id: str) -> None:
        requirements = extract_requirements(application.role, application.job_description)
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
    "APPLICATION_NOT_FOUND",
    "ApplicationCVLinkError",
    "ApplicationService",
]
