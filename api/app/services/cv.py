from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv import CV


class CVService:
    def __init__(self, db: AsyncSession):
        self.db = db
