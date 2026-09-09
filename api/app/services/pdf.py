"""PDF export service — drives the new AST → HTML → PDF pipeline."""

from __future__ import annotations

import pypdfium2 as pdfium
from sqlalchemy.ext.asyncio import AsyncSession

from app.document_schema.models import TemplateManifest
from app.services.cv import CVService
from app.services.renderer.pipeline import (
    prepare_render_source,
    render_html_pdf,
    render_source_html,
)


class PDFUnavailableError(RuntimeError):
    """Raised when the external Chromium runtime cannot render a PDF."""


class PDFService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_service = CVService(db)

    async def render_payload(
        self,
        template_id: str,
        sections: list[dict],
        customizations: dict,
    ) -> bytes:
        template_data = await self.cv_service.get_template_data(template_id)
        if not template_data:
            raise ValueError("Template not found")
        manifest_dict = template_data.get("manifest")
        if not manifest_dict:
            raise ValueError("Template has no manifest")

        manifest = TemplateManifest.model_validate(manifest_dict)
        source = prepare_render_source(sections, manifest, customizations)
        html = render_source_html(source)
        try:
            return await render_html_pdf(html)
        except Exception as exc:
            raise PDFUnavailableError("PDF rendering is unavailable") from exc

    async def export_pdf(self, cv_id: str, user_id: str) -> bytes:
        cv = await self.cv_service.get_cv(cv_id, user_id)
        if not cv:
            raise ValueError("CV not found")
        return await self.render_payload(cv.template_id, cv.sections, cv.customizations)


def pdf_page_count(pdf_bytes: bytes) -> int:
    document = pdfium.PdfDocument(pdf_bytes)
    try:
        return len(document)
    finally:
        document.close()


__all__ = ["PDFService", "PDFUnavailableError", "pdf_page_count"]
