import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.cv import CV
from app.models.template import Template
from app.schemas.cv import CVCreate, CVUpdate


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cvs(self, user_id: str) -> list[CV]:
        result = await self.db.execute(
            select(CV).where(CV.user_id == user_id, CV.is_active == True).order_by(CV.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_cv(self, cv_id: str, user_id: str) -> CV | None:
        result = await self.db.execute(
            select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_template_data(self, template_id: str) -> dict | None:
        """Get full template data for user templates (layout_template, layout_config, default_customizations)."""
        if not template_id.startswith("user_"):
            return None
        template = await self.db.get(Template, template_id)
        if not template:
            return None
        return {
            "layout_template": template.layout_template,
            "layout_config": template.layout_config,
            "default_customizations": template.default_customizations,
        }

    async def create_cv(self, user_id: str, data: CVCreate) -> CV:
        cv = CV(
            user_id=user_id,
            title=data.title,
            description=data.description,
            template_id=data.template_id,
            sections=data.sections,
            customizations=data.customizations,
            extra_metadata=data.extra_metadata,
        )
        self.db.add(cv)
        await self.db.flush()
        return cv

    async def _load_template_content(self, template_id: str) -> str | None:
        if not template_id.startswith("user_"):
            return None
        template = await self.db.get(Template, template_id)
        return template.layout_template if template else None

    async def update_cv(self, cv_id: str, user_id: str, data: CVUpdate) -> CV | None:
        cv = await self.get_cv(cv_id, user_id)
        if not cv:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cv, key, value)
        if "template_id" in update_data and update_data["template_id"].startswith("user_"):
            content = await self._load_template_content(update_data["template_id"])
            cv.template_content = content
        elif not cv.template_content and cv.template_id.startswith("user_") and "template_id" not in update_data:
            content = await self._load_template_content(cv.template_id)
            if content:
                cv.template_content = content
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
            template_content=original.template_content,
        )
        self.db.add(new_cv)
        await self.db.flush()
        return new_cv
