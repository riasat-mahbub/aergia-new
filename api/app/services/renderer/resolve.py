"""Compatibility facade for the typed renderer resolution core.

The implementation lives in :mod:`app.services.renderer.resolution`, where
section cascading, zone placement, and render-model assembly are separate
stages. This module keeps the existing public ``resolve`` import stable and
retains the wire-input validation boundary.
"""

from __future__ import annotations

from app.document_schema.models import Customizations, Document, RenderModel, TemplateManifest
from app.services.renderer.base import DocumentRenderer
from app.services.renderer.html_values import (
    LINK_STYLES,
    PLAIN_LINK_STYLES,
    PRINT_STYLES,
    resolve_color_ref,
)

from .resolution import resolve_validated
from .resolution.context import prepare_context
from .resolution.errors import ManifestVersionError


def resolve_color(value: str) -> str:
    """Resolve an HTML palette reference or return a literal CSS color."""

    return resolve_color_ref(value)


def resolve(
    document: Document,
    renderer: DocumentRenderer,
    manifest: TemplateManifest | dict | None = None,
    customizations: Customizations | dict | None = None,
) -> RenderModel:
    """Resolve a document through the typed renderer resolution core."""

    context = prepare_context(renderer.support, manifest, customizations)
    return resolve_validated(document, context)


__all__ = [
    "LINK_STYLES",
    "PLAIN_LINK_STYLES",
    "PRINT_STYLES",
    "ManifestVersionError",
    "resolve",
]
