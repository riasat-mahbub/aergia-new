from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cv import CVService
from app.services.renderer import render_pdf


class PDFService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_service = CVService(db)

    async def export_pdf(self, cv_id: str, user_id: str) -> bytes:
        cv = await self.cv_service.get_cv(cv_id, user_id)
        if not cv:
            raise ValueError("CV not found")

        instances = cv.sections or []
        if isinstance(instances, dict):
            instances = []

        template_data = await self.cv_service.get_template_data(cv.template_id)

        # Get manifest should have manifest from template
        manifest = template_data.get("manifest") if template_data else None
        if not manifest:
            raise ValueError("Template has no manifest")

        pdf_bytes = await render_pdf(
            manifest=manifest,
            cv_data={"instances": instances},
            customizations=cv.customizations or {},
        )

        return pdf_bytes