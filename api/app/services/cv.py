from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application import Application
from app.models.cv import CV
from app.models.template import Template
from app.document_schema.models import Customizations
from app.http_schemas.cv import CVCreate, CVUpdate
from app.services.relevance import (
    REQUIREMENT_ALGORITHM_VERSION,
    evaluate_requirement_relevance,
    extract_requirements,
)
from app.services.quotas import QuotaResource, QuotaService
from app.services.rich_text import normalize_rich_text_ids

def coerce_customizations(raw: dict | Customizations | None) -> Customizations:
    """Validate customizations at the service boundary.

    Persisted rows are migrated before the application starts using them, so
    this function deliberately accepts only the canonical model shape.
    """
    if isinstance(raw, Customizations):
        return raw
    return Customizations.model_validate(raw or {})


class CVLinkedToApplicationError(ValueError):
    """Raised when a visible application still references this CV."""


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cvs(self, user_id: str) -> list[CV]:
        result = await self.db.execute(
            select(CV).where(CV.user_id == user_id, CV.is_active).order_by(CV.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_cv_summaries(self, user_id: str) -> list[tuple[CV, Application | None]]:
        """Return the user's CVs with their owning application, if any.

        The relationship is deliberately queried by both owners and the CV's
        relational ``application_id``. CV metadata is user-editable JSON and
        must not be used as provenance.
        """
        cvs = await self.list_cvs(user_id)
        if not cvs:
            return []

        cv_ids = [cv.id for cv in cvs]
        result = await self.db.execute(
            select(CV.id, Application)
            .join(Application, Application.id == CV.application_id)
            .where(
                CV.id.in_(cv_ids),
                CV.user_id == user_id,
                Application.user_id == user_id,
            )
        )
        application_by_cv = {cv_id: application for cv_id, application in result.all()}

        return [(cv, application_by_cv.get(cv.id)) for cv in cvs]

    async def get_cv(self, cv_id: str, user_id: str) -> CV | None:
        result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
        )
        return result.scalar_one_or_none()

    async def get_template_data(self, template_id: str) -> dict | None:
        """Get the canonical template manifest."""
        template = await self.db.get(Template, template_id)
        if not template:
            return None
        return {"manifest": template.manifest}

    async def create_cv(
        self,
        user_id: str,
        data: CVCreate,
        *,
        application_id: str | None = None,
    ) -> CV:
        raw_sections = data.sections if isinstance(data.sections, list) else []
        sections = [
            s.model_dump(mode="json", exclude_none=True) if hasattr(s, "model_dump") else s
            for s in raw_sections
        ]
        sections, _ = normalize_rich_text_ids(sections)
        customizations = coerce_customizations(data.customizations).model_dump(exclude_none=True)

        if application_id is not None:
            owned_application = await self.db.execute(
                select(Application.id).where(
                    Application.id == application_id,
                    Application.user_id == user_id,
                )
            )
            if owned_application.scalar_one_or_none() is None:
                raise LookupError("Application not found")

        await QuotaService(self.db).reserve(user_id, QuotaResource.CV)

        # A new CV inherits the template's zone layout so the editor opens
        # with zones and every section is assignable. Template placement is
        # type-keyed; persisted per-CV placement is instance-keyed.
        if not customizations.get("layout"):
            template_data = await self.get_template_data(data.template_id)
            manifest = (template_data or {}).get("manifest") or {}
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
                customizations["layout"] = {"zones": zones, "placement": placement}

        cv = CV(
            user_id=user_id,
            application_id=application_id,
            title=data.title,
            description=data.description,
            template_id=data.template_id,
            sections=sections,
            customizations=customizations,
            extra_metadata=data.extra_metadata,
        )
        self.db.add(cv)
        await self.db.flush()
        return cv

    async def update_cv(self, cv_id: str, user_id: str, data: CVUpdate) -> CV | None:
        cv = await self.get_cv(cv_id, user_id)
        if not cv:
            return None

        update_data = data.model_dump(exclude_unset=True)
        # Convert validated section instances to plain dicts and canonicalize
        # legacy rich-text blocks before storing them. This keeps stable IDs
        # durable across normal editor saves as well as tailoring writes.
        if "sections" in update_data:
            if isinstance(update_data["sections"], list):
                update_data["sections"] = [
                    s.model_dump(mode="json", exclude_none=True) if hasattr(s, "model_dump") else s
                    for s in update_data["sections"]
                ]
            update_data["sections"], _ = normalize_rich_text_ids(update_data["sections"])
        if "customizations" in update_data:
            update_data["customizations"] = coerce_customizations(update_data["customizations"]).model_dump(
                exclude_none=True,
            )
        for key, value in update_data.items():
            setattr(cv, key, value)
        cv.revision = (cv.revision or 1) + 1
        cv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self._refresh_linked_application_relevance(cv)
        return cv

    async def _refresh_linked_application_relevance(self, cv: CV) -> None:
        """Keep score state in sync for direct CV API edits without rebuilding content."""
        result = await self.db.execute(
            select(Application).where(Application.cv_id == cv.id, Application.user_id == cv.user_id)
        )
        applications = result.scalars().all()
        for application in applications:
            requirements = extract_requirements(application.role, application.job_description)
            relevance = evaluate_requirement_relevance(requirements, cv.sections or [])
            application.relevance = relevance.model_dump(mode="json")
            application.extracted_keywords = []
            application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
            application.updated_at = datetime.now(timezone.utc)
        if applications:
            await self.db.flush()

    async def delete_cv(self, cv_id: str, user_id: str) -> bool:
        cv = await self.get_cv(cv_id, user_id)
        if not cv:
            return False
        linked = await self.db.execute(
            select(Application.id)
            .where(Application.user_id == user_id, Application.cv_id == cv_id)
            .limit(1)
        )
        if linked.scalar_one_or_none() is not None:
            raise CVLinkedToApplicationError("CV is linked to an application")
        cv.is_active = False
        cv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await QuotaService(self.db).release(user_id, QuotaResource.CV)
        return True

    async def copy_cv(self, cv_id: str, user_id: str) -> CV | None:
        original = await self.get_cv(cv_id, user_id)
        if not original:
            return None

        copied_metadata = dict(original.extra_metadata or {})
        for key in (
            "application_id",
            "generated_by",
            "selected_sources",
            "extracted_keywords",
            "extracted_requirements",
            "fit_removed",
        ):
            copied_metadata.pop(key, None)

        title = f"{original.title} (Copy)"
        description = original.description
        template_id = original.template_id
        sections, _ = normalize_rich_text_ids(original.sections)
        customizations = coerce_customizations(original.customizations).model_dump(exclude_none=True)
        await QuotaService(self.db).reserve(user_id, QuotaResource.CV)
        new_cv = CV(
            user_id=user_id,
            title=title,
            description=description,
            template_id=template_id,
            sections=sections,
            customizations=customizations,
            extra_metadata=copied_metadata,
        )
        self.db.add(new_cv)
        await self.db.flush()
        return new_cv
