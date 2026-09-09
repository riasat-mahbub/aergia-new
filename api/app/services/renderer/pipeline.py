"""Canonical document rendering pipeline.

This module is the application-facing facade for the fixed renderer path:

    wire sections -> AST -> resolved model -> HTML -> Chromium PDF

The individual stages remain independently testable. The facade gives HTTP
routes and services one place to compose them and one place to normalize
wire input, without moving policy or layout decisions into an orchestrator.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.document_schema.models import (
    Customizations,
    Document,
    RenderModel,
    SectionInstance,
    TemplateManifest,
)
from app.services.renderer._pdf_runtime import html_to_pdf
from app.services.renderer.base import DocumentRenderer
from app.services.renderer.builders import build_document_from_sections
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.resolve import resolve


@dataclass(frozen=True)
class RenderSource:
    """Validated inputs shared by every output of the render pipeline."""

    sections: tuple[SectionInstance, ...]
    manifest: TemplateManifest | None
    customizations: Customizations


def _validate_sections(
    sections: Iterable[SectionInstance | dict],
) -> tuple[SectionInstance, ...]:
    """Validate section dicts while retaining legacy non-dict skipping."""

    validated: list[SectionInstance] = []
    for section in sections:
        if isinstance(section, SectionInstance):
            validated.append(section)
        elif isinstance(section, dict):
            validated.append(SectionInstance.model_validate(section))
    return tuple(validated)


def _coerce_manifest(
    manifest: TemplateManifest | dict | None,
) -> TemplateManifest | None:
    """Convert an optional manifest to the typed schema boundary."""

    if manifest is None or isinstance(manifest, TemplateManifest):
        return manifest
    return TemplateManifest.model_validate(manifest)


def _coerce_customizations(
    customizations: Customizations | dict | None,
) -> Customizations:
    """Convert absent or wire customizations to the canonical model."""

    if isinstance(customizations, Customizations):
        return customizations
    return Customizations.model_validate(customizations or {})


def prepare_render_source(
    sections: Iterable[SectionInstance | dict],
    manifest: TemplateManifest | dict | None = None,
    customizations: Customizations | dict | None = None,
) -> RenderSource:
    """Validate wire inputs once before building any render output.

    Non-dict section values are ignored to preserve the existing builder's
    handling of malformed legacy rows. Dicts are validated as
    :class:`SectionInstance` values and therefore still fail loudly when
    their shape is invalid.
    """

    return RenderSource(
        sections=_validate_sections(sections),
        manifest=_coerce_manifest(manifest),
        customizations=_coerce_customizations(customizations),
    )


def build_source_document(source: RenderSource) -> Document:
    """Build the AST for a prepared render source."""

    return build_document_from_sections(source.sections, source.manifest)


def resolve_source(
    source: RenderSource,
    renderer: DocumentRenderer | None = None,
) -> RenderModel:
    """Resolve a prepared source for the selected renderer."""

    target = renderer or HTMLDocumentRenderer()
    document = build_source_document(source)
    return resolve(document, target, source.manifest, source.customizations)


def render_source_html(
    source: RenderSource,
    renderer: DocumentRenderer | None = None,
) -> str:
    """Render a prepared source to target HTML."""

    target = renderer or HTMLDocumentRenderer()
    return target.render(resolve_source(source, target))


async def render_source_pdf(
    source: RenderSource,
    renderer: DocumentRenderer | None = None,
) -> bytes:
    """Render a prepared source through HTML and the shared PDF runtime."""

    return await render_html_pdf(render_source_html(source, renderer))


async def render_html_pdf(html: str) -> bytes:
    """Send already-rendered HTML through the shared PDF runtime."""

    return await html_to_pdf(html)


__all__ = [
    "RenderSource",
    "build_source_document",
    "prepare_render_source",
    "render_source_html",
    "render_source_pdf",
    "render_html_pdf",
    "resolve_source",
]
