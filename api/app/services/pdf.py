from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cv import CVService
from app.services.renderer import render_preview
from playwright.async_api import async_playwright


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

        html = render_preview(
            instances=instances,
            customizations=cv.customizations or {},
            template_id=cv.template_id,
            layout_template=template_data.get("layout_template") if template_data else None,
            layout_config=template_data.get("layout_config") if template_data else None,
            default_customizations=template_data.get("default_customizations") if template_data else None,
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            await browser.close()

        return pdf_bytes
