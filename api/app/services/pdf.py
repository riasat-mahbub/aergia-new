"""PDF export service — drives the new AST → HTML → PDF pipeline."""

from __future__ import annotations

from types import SimpleNamespace

import pypdfium2 as pdfium
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.models import TemplateManifest
from app.services.cv import CVService, coerce_customizations
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.services.renderer._pdf_runtime import html_to_pdf


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
        customizations_model = coerce_customizations(customizations)
        payload = SimpleNamespace(sections=sections, customizations=customizations)
        document = build_document(payload, manifest)
        renderer = HTMLDocumentRenderer()
        model = resolve(document, renderer, manifest, customizations_model)
        html = renderer.render(model)
        try:
            return await html_to_pdf(html)
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
