"""PDF export service — drives the new AST → HTML → PDF pipeline."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cv import CVService, coerce_customizations
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.services.renderer._pdf_runtime import html_to_pdf
from app.schema.models import TemplateManifest


class PDFService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cv_service = CVService(db)

    async def export_pdf(self, cv_id: str, user_id: str) -> bytes:
        cv = await self.cv_service.get_cv(cv_id, user_id)
        if not cv:
            raise ValueError("CV not found")

        template_data = await self.cv_service.get_template_data(cv.template_id)
        if not template_data:
            raise ValueError("Template not found")
        manifest_dict = template_data.get("manifest")
        if not manifest_dict:
            raise ValueError("Template has no manifest")

        # Build the AST straight from the wire shape on the CV row.
        document = build_document(cv, None)

        # Resolve the manifest. v1 manifests are rejected.
        manifest = TemplateManifest.model_validate(manifest_dict)
        customizations = coerce_customizations(cv.customizations)

        model = resolve(document, manifest, customizations, HTMLDocumentRenderer.support)
        html = HTMLDocumentRenderer().render(model)
        return await html_to_pdf(html)


__all__ = ["PDFService"]
