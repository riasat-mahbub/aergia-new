"""Typed core for document resolution."""

from __future__ import annotations

from app.document_schema.models import Document, RenderModel

from .context import ResolutionContext
from .render_model import build_render_model
from .sections import resolve_sections
from .zones import resolve_zones


def resolve_validated(
    document: Document,
    context: ResolutionContext,
) -> RenderModel:
    """Resolve typed inputs without repeating compatibility-boundary coercion."""

    resolved_sections = resolve_sections(document.sections, context)
    zones = resolve_zones(tuple(resolved_sections.values()), context)
    return build_render_model(resolved_sections, zones, context)


__all__ = ["ResolutionContext", "resolve_validated"]
