"""Saved-CV DOCX export service."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cv import CVService
from app.services.renderer.pipeline import prepare_render_source, render_source_docx


class DOCXCVNotFoundError(LookupError):
    """The requested CV is missing, inactive, or not owned by the user."""


class DOCXManifestLookupError(RuntimeError):
    """The current template manifest could not be loaded for export."""


class DOCXGenerationError(RuntimeError):
    """The saved CV could not be rendered as a Word document."""


class DOCXService:
    def __init__(self, db: AsyncSession):
        self.cv_service = CVService(db)

    async def export_docx(self, cv_id: str, user_id: str) -> bytes:
        """Render the current saved state of an active, owned CV."""

        cv = await self.cv_service.get_cv(cv_id, user_id)
        if cv is None:
            raise DOCXCVNotFoundError("CV not found")

        try:
            template_data = await self.cv_service.get_template_data(cv.template_id)
        except Exception as exc:  # noqa: BLE001
            raise DOCXManifestLookupError("Template manifest lookup failed") from exc

        manifest = template_data.get("manifest") if isinstance(template_data, dict) else None
        if not manifest:
            raise DOCXManifestLookupError("Template manifest is unavailable")

        try:
            source = prepare_render_source(cv.sections, manifest, cv.customizations)
            return await asyncio.to_thread(render_source_docx, source)
        except Exception as exc:  # noqa: BLE001
            raise DOCXGenerationError("DOCX generation failed") from exc


__all__ = [
    "DOCXCVNotFoundError",
    "DOCXGenerationError",
    "DOCXManifestLookupError",
    "DOCXService",
]
