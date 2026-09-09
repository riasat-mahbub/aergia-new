"""Renderer package — the new AST-driven pipeline.

Public API:

- :func:`build_document` — wire ``SectionInstance`` list → :class:`Document`.
- :func:`resolve` — :class:`Document` + manifest + customizations + support → :class:`RenderModel`.
- :class:`HTMLDocumentRenderer` — :class:`RenderModel` → HTML5.
- :func:`prepare_render_source` / :func:`render_source_html` /
  :func:`render_source_pdf` — the canonical composed pipeline.
- :class:`HTMLDocumentRenderer.support` — class-level capability declaration.
- :class:`RendererSupport` / :class:`SupportLevel` — capability primitives.
"""

from __future__ import annotations

from app.services.renderer.base import DocumentRenderer
from app.services.renderer.builders import build_document, build_document_from_sections
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.pipeline import (
    RenderSource,
    build_source_document,
    prepare_render_source,
    render_html_pdf,
    render_source_html,
    render_source_pdf,
    resolve_source,
)
from app.services.renderer.resolve import resolve
from app.services.renderer.support import RendererSupport, SupportLevel

__all__ = [
    "DocumentRenderer",
    "HTMLDocumentRenderer",
    "RendererSupport",
    "SupportLevel",
    "build_document",
    "build_document_from_sections",
    "RenderSource",
    "build_source_document",
    "prepare_render_source",
    "render_html_pdf",
    "render_source_html",
    "render_source_pdf",
    "resolve",
    "resolve_source",
]
