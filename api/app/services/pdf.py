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
        manifest = template_data.get("manifest") if template_data else None
        if not manifest:
            raise ValueError("Template has no manifest")

        # Merge CV-level customizations.layout into the manifest so the rendered
        # PDF mirrors the live preview (new zones, per-zone styles, etc.).
        customizations = cv.customizations or {}
        cv_layout = (customizations.get("layout") if isinstance(customizations, dict) else None)
        if isinstance(cv_layout, dict) and cv_layout.get("zones"):
            manifest = {
                **manifest,
                "layout_config": cv_layout,
                "zones": cv_layout.get("zones", manifest.get("zones", [])),
            }

        pdf_bytes = await render_pdf(
            manifest=manifest,
            cv_data={"instances": instances},
            customizations=customizations,
        )

        return pdf_bytes
