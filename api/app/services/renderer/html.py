"""Public HTML renderer facade.

``HTMLDocumentRenderer`` consumes a fully resolved :class:`RenderModel` and
delegates document assembly to focused HTML modules.  This module keeps the
stable ``app.services.renderer.html`` import path and the renderer capability
declaration; markup, layout, and static assets live in their own modules.
"""

from __future__ import annotations

from app.document_schema.models import RenderModel
from app.services.renderer.html_renderer.html_document import _render_document
from app.services.renderer.support import RendererSupport
from app.services.renderer.base import DocumentRenderer


class HTMLDocumentRenderer(DocumentRenderer):
    """Render a :class:`RenderModel` to a complete HTML5 document."""

    support = RendererSupport()

    def render(self, model: RenderModel) -> str:
        return _render_document(model, self.support)

    def render_bytes(self, model: RenderModel) -> bytes:
        return self.render(model).encode("utf-8")


__all__ = ["HTMLDocumentRenderer"]
