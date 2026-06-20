"""Renderer package — the new AST-driven pipeline.

Public API:

- :func:`build_document` — wire ``SectionInstance`` list → :class:`Document`.
- :func:`resolve` — :class:`Document` + manifest + customizations + support → :class:`RenderModel`.
- :class:`HTMLDocumentRenderer` — :class:`RenderModel` → HTML5.
- :class:`HTMLDocumentRenderer.support` — class-level capability declaration.
- :class:`RendererSupport` / :class:`SupportLevel` — capability primitives.
"""

from __future__ import annotations

from app.services.renderer.base import DocumentRenderer
from app.services.renderer.builders import build_document
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.resolve import resolve
from app.services.renderer.support import RendererSupport, SupportLevel

__all__ = [
    "DocumentRenderer",
    "HTMLDocumentRenderer",
    "RendererSupport",
    "SupportLevel",
    "build_document",
    "resolve",
]
