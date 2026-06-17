"""Abstract base for document renderers.

A renderer consumes a fully resolved :class:`RenderModel` and produces a
target format. The HTML renderer emits HTML5; the PDF renderer emits raw
PDF bytes; a future DOCX renderer would emit a DOCX document.

Renderers declare their capabilities via a class-level ``support``
attribute (:class:`RendererSupport`). The customize panel reads it; the
resolver drops ``NONE`` features; ``BEST_EFFORT`` features are passed
through with a marker comment in the output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schema.models import RenderModel

from .support import RendererSupport


class DocumentRenderer(ABC):
    """Base class for all renderers."""

    support: RendererSupport

    @abstractmethod
    def render(self, model: RenderModel) -> str:
        """Render the model to a target format's string representation.

        HTML renderers return HTML text. PDF renderers may return either a
        string or bytes — see :meth:`render_bytes` for the byte-friendly
        form."""


__all__ = ["DocumentRenderer"]
