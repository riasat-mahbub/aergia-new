import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.cv import CV
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

    async def create_cv(self, user_id: str, data: CVCreate) -> CV:
        cv = CV(
            user_id=user_id,
            title=data.title,
            description=data.description,
            template_id=data.template_id,
            sections=data.sections,
            customizations=data.customizations,
            metadata=data.metadata,
        )
        self.db.add(cv)
        await self.db.flush()
        return cv

    async def update_cv(self, cv_id: str, user_id: str, data: CVUpdate) -> CV | None:
        cv = await self.get_cv(cv_id, user_id)
        if not cv:
            return None

        update_data = data.model_dump(exclude_unset=True)
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
            metadata=original.metadata,
        )
        self.db.add(new_cv)
        await self.db.flush()
        return new_cv
