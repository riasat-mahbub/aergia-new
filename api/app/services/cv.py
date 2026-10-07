from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.application import Application
from app.models.cv import CV
from app.models.template import Template
from app.models.tailoring_replacement_reservation import (
    TAILORING_REPLACEMENT_PENDING,
    TailoringReplacementReservation,
)
from app.document_schema.models import Customizations
from app.http_schemas.cv import CVCreate, CVUpdate
from app.services.relevance import (
    REQUIREMENT_ALGORITHM_VERSION,
    evaluate_requirement_relevance,
    extract_requirements,
)
from app.services.quotas import (
    QuotaResource,
    QuotaService,
    ReplacementSourceNotEligibleError,
)
from app.services.rich_text import normalize_rich_text_ids


def _without_none(value):
    if isinstance(value, dict):
        return {key: _without_none(child) for key, child in value.items() if child is not None}
    if isinstance(value, list):
        return [_without_none(child) for child in value]
    return value


def _canonical_update_value(key: str, value):
    if key == "customizations":
        return coerce_customizations(value).model_dump(exclude_none=True)
    if key == "sections":
        sections, _ = normalize_rich_text_ids(value)
        return _without_none(sections)
    return value


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
            select(CV)
            .where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
            .execution_options(populate_existing=True)
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
        sections, customizations = await self._prepare_cv(data)

        if application_id is not None:
            await self._require_owned_application(application_id, user_id)

        await QuotaService(self.db).reserve(user_id, QuotaResource.CV)
        return await self._persist_cv(
            user_id,
            data,
            sections=sections,
            customizations=customizations,
            application_id=application_id,
            quota_counted=True,
        )

    async def create_replacement_draft(
        self,
        user_id: str,
        data: CVCreate,
        *,
        application_id: str,
        source_cv_id: str | None,
    ) -> CV:
        """Create an uncounted draft when the source qualifies for replacement.

        A missing or ineligible source falls back to ordinary counted creation,
        so a no-source session or an application with a free normal slot follows
        the same quota rule as standalone CV creation. Existing pending
        reservations remain conflicts and cannot consume a second slot.
        """

        if source_cv_id is None:
            return await self.create_cv(user_id, data, application_id=application_id)

        sections, customizations = await self._prepare_cv(data)
        quota = QuotaService(self.db)
        try:
            # The CV and reservation form one savepoint unit. A failed flush
            # cannot leave an allowance row without its draft.
            await quota.ensure_write_transaction()
            async with self.db.begin_nested():
                reservation = await quota.reserve_replacement(
                    user_id,
                    application_id,
                    source_cv_id,
                )
                cv = await self._persist_cv(
                    user_id,
                    data,
                    sections=sections,
                    customizations=customizations,
                    application_id=application_id,
                    quota_counted=False,
                )
                reservation.draft_cv_id = cv.id
                await self.db.flush()
            return cv
        except ReplacementSourceNotEligibleError:
            return await self.create_cv(user_id, data, application_id=application_id)

    async def _prepare_cv(self, data: CVCreate) -> tuple[list, dict]:
        raw_sections = data.sections if isinstance(data.sections, list) else []
        sections = [
            s.model_dump(mode="json", exclude_none=True) if hasattr(s, "model_dump") else s
            for s in raw_sections
        ]
        sections, _ = normalize_rich_text_ids(sections)
        customizations = coerce_customizations(data.customizations).model_dump(exclude_none=True)

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

        return sections, customizations

    async def _require_owned_application(self, application_id: str, user_id: str) -> None:
        owned_application = await self.db.execute(
            update(Application)
            .where(
                Application.id == application_id,
                Application.user_id == user_id,
            )
            .values(updated_at=Application.updated_at)
        )
        if owned_application.rowcount != 1:
            raise LookupError("Application not found")

    async def _persist_cv(
        self,
        user_id: str,
        data: CVCreate,
        *,
        sections: list,
        customizations: dict,
        application_id: str | None,
        quota_counted: bool,
    ) -> CV:
        cv = CV(
            user_id=user_id,
            application_id=application_id,
            title=data.title,
            description=data.description,
            template_id=data.template_id,
            sections=sections,
            customizations=customizations,
            extra_metadata=data.extra_metadata,
            quota_counted=quota_counted,
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
        meaningful_fields = {"title", "description", "template_id", "customizations", "sections"}
        scanner_fields = {"template_id", "customizations", "sections"}
        changed_fields = set()
        for key, value in update_data.items():
            current_value = getattr(cv, key)
            if key in meaningful_fields:
                unchanged = _canonical_update_value(key, current_value) == _canonical_update_value(key, value)
            else:
                unchanged = current_value == value
            if not unchanged:
                changed_fields.add(key)
                setattr(cv, key, value)
        if changed_fields & meaningful_fields:
            cv.revision = (cv.revision or 1) + 1
        if changed_fields:
            cv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        if changed_fields & scanner_fields:
            await self._refresh_linked_application_relevance(cv)
        return cv

    async def _refresh_linked_application_relevance(self, cv: CV) -> None:
        """Keep score state in sync for direct CV API edits without rebuilding content."""
        result = await self.db.execute(
            select(Application).where(Application.cv_id == cv.id, Application.user_id == cv.user_id)
        )
        applications = result.scalars().all()
        for application in applications:
            # The persisted scan describes the previous CV revision.
            application.scanner_rescan_required = (
                application.scanner_result is not None or application.scanner_rescan_required
            )
            application.scanner_result = None
            requirements = extract_requirements(application.role, application.job_description)
            relevance = evaluate_requirement_relevance(requirements, cv.sections or [])
            application.relevance = relevance.model_dump(mode="json")
            application.extracted_keywords = []
            application.algorithm_version = REQUIREMENT_ALGORITHM_VERSION
            application.updated_at = datetime.now(timezone.utc)
        if applications:
            await self.db.flush()

    async def delete_cv(self, cv_id: str, user_id: str) -> bool:
        quota = QuotaService(self.db)
        # SQLite's legacy transaction mode does not protect the following
        # reads until a write starts. Acquire the short write transaction
        # before refreshing the CV and its app links so a concurrent manual
        # link cannot slip between the conflict check and retirement.
        await quota.ensure_write_transaction()
        async with self.db.begin_nested():
            cv = await self.db.scalar(
                select(CV)
                .where(CV.id == cv_id, CV.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            if cv is None or not cv.is_active:
                return False

            # Serialize with the normal link flow on the target CV row. The
            # conditional final update below also repeats both the app-link
            # exclusion and the observed application_id.
            cv_lock = await self.db.execute(
                update(CV)
                .where(CV.id == cv_id, CV.user_id == user_id, CV.is_active.is_(True))
                .values(updated_at=CV.updated_at)
            )
            if cv_lock.rowcount != 1:
                return False
            cv = await self.db.scalar(
                select(CV)
                .where(CV.id == cv_id, CV.user_id == user_id)
                .execution_options(populate_existing=True)
            )
            if cv is None or not cv.is_active:
                return False

            linked = await self.db.scalar(
                select(Application.id)
                .where(Application.user_id == user_id, Application.cv_id == cv_id)
                .limit(1)
            )
            if linked is not None:
                raise CVLinkedToApplicationError("CV is linked to an application")

            observed_application = (
                CV.application_id.is_(None)
                if cv.application_id is None
                else CV.application_id == cv.application_id
            )
            result = await self.db.execute(
                update(CV)
                .where(
                    CV.id == cv_id,
                    CV.user_id == user_id,
                    CV.is_active.is_(True),
                    observed_application,
                    ~select(Application.id)
                    .where(Application.user_id == user_id, Application.cv_id == cv_id)
                    .exists(),
                )
                .values(is_active=False, updated_at=datetime.now(timezone.utc))
                .returning(CV.quota_counted)
            )
            quota_counted = result.scalar_one_or_none()
            if quota_counted is None:
                linked = await self.db.scalar(
                    select(Application.id)
                    .where(Application.user_id == user_id, Application.cv_id == cv_id)
                    .limit(1)
                )
                if linked is not None:
                    raise CVLinkedToApplicationError("CV is linked to an application")
                return False

            # Retire associated pending allowances only after the CV CAS has
            # succeeded. If a concurrent link/delete wins, none of these
            # reservation writes have happened and no allowance can be left
            # partially released.
            pending_draft_application = await self.db.scalar(
                select(TailoringReplacementReservation.application_id)
                .join(
                    Application,
                    Application.id == TailoringReplacementReservation.application_id,
                )
                .where(
                    TailoringReplacementReservation.draft_cv_id == cv.id,
                    TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                    Application.user_id == user_id,
                )
                .limit(1)
            )
            if pending_draft_application is not None:
                await quota.release_replacement(
                    user_id,
                    pending_draft_application,
                    draft_cv_id=cv.id,
                    retire_draft=False,
                )

            pending_source_applications = await self.db.execute(
                select(TailoringReplacementReservation.application_id)
                .join(
                    Application,
                    Application.id == TailoringReplacementReservation.application_id,
                )
                .where(
                    TailoringReplacementReservation.source_cv_id == cv.id,
                    TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                    Application.user_id == user_id,
                )
            )
            for application_id in pending_source_applications.scalars().all():
                await quota.release_replacement(
                    user_id,
                    application_id,
                    source_cv_id=cv.id,
                    retire_draft=True,
                )
            if quota_counted:
                await quota.release(user_id, QuotaResource.CV)
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
