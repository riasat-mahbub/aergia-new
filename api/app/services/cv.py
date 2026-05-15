from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.cv import CV
from app.models.template import Template
from app.schemas.cv import CVCreate, CVUpdate


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cvs(self, user_id: str) -> list[CV]:
        result = await self.db.execute(
            select(CV).where(CV.user_id == user_id, CV.is_active).order_by(CV.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_cv(self, cv_id: str, user_id: str) -> CV | None:
        result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.is_active)
        )
        return result.scalar_one_or_none()

    async def get_template_data(self, template_id: str) -> dict | None:
        """Get template manifest and default customizations."""
        template = await self.db.get(Template, template_id)
        if not template:
            return None
        return {
            "default_customizations": template.default_customizations,
            "manifest": template.manifest,
        }

    async def create_cv(self, user_id: str, data: CVCreate) -> CV:
        raw_sections = data.sections if isinstance(data.sections, list) else []
        sections = [s.model_dump() if hasattr(s, "model_dump") else s for s in raw_sections]
        customizations = data.customizations or {}

        # Inherit layout from template when CV doesn't have one yet
        if not customizations.get("layout") and data.template_id:
            template = await self.db.get(Template, data.template_id)
            lc = template.manifest.get("layout_config") if template and template.manifest else None
            if lc:
                placement = lc.get("placement", {}) or {}
                if placement and not any(k.startswith("sec_") for k in placement):
                    customizations["layout"] = {
                        **lc,
                        "placement": {
                            inst["id"]: placement[inst["type"]]
                            for inst in sections
                            if isinstance(inst, dict) and inst.get("type") in placement
                        },
                    }

        cv = CV(
            user_id=user_id,
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
        # Convert ValidatedSectionInstance objects to plain dicts for DB storage
        if "sections" in update_data and isinstance(update_data["sections"], list):
            update_data["sections"] = [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in update_data["sections"]
            ]
        for key, value in update_data.items():
            setattr(cv, key, value)
        cv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return cv

    async def delete_cv(self, cv_id: str, user_id: str) -> bool:
        cv = await self.get_cv(cv_id, user_id)
        if not cv:
            return False
        cv.is_active = False
        cv.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def copy_cv(self, cv_id: str, user_id: str) -> CV | None:
        original = await self.get_cv(cv_id, user_id)
        if not original:
            return None

        new_cv = CV(
            user_id=user_id,
            title=f"{original.title} (Copy)",
            description=original.description,
            template_id=original.template_id,
            sections=original.sections,
            customizations=original.customizations,
            extra_metadata=original.extra_metadata,
        )
        self.db.add(new_cv)
        await self.db.flush()
        return new_cv
