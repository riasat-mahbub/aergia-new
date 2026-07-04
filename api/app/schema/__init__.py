"""Pydantic AST schema for the HTML-first renderer pipeline.

The new pipeline:

    AST (this module)  ->  Resolver  ->  RenderModel  ->  HTMLDocumentRenderer  ->  HTML5  ->  Chromium  ->  PDF

This package is the single source of truth for the document model. The
TypeScript types in ``web/src/generated/schema.ts`` are derived from these
models via ``api/scripts/codegen_schema.py``.

Three orthogonal axes for styling (ADR-three-axis-style-model):

- :class:`TextStyle` — inline per-field appearance.
- :class:`SubsectionStyle` — block-level appearance per section/entry.
- :class:`LayoutHints` — page flow and structural intent.

:data:`DateStyle` (the format preset for dates) is reused from the legacy
``app.schemas.sections`` module during cutover; it now lives next to the
rest of the AST.
"""

from .models import (
    CVRow,
    Customizations,
    Document,
    DateStyle,
    Entry,
    FieldBlock,
    LayoutDefaults,
    LayoutHints,
    PolicyOverrides,
    RenderModel,
    ResolvedZone,
    Section,
    SectionInstance,
    SectionInstanceStyle,
    SectionPolicy,
    SubsectionStyle,
    TemplateDetail,
    TemplateListItem,
    TemplateManifest,
    TextRun,
    TextStyle,
    Zone,
    ZoneStyle,
)

__all__ = [
    "CVRow",
    "Customizations",
    "Document",
    "DateStyle",
    "Entry",
    "FieldBlock",
    "LayoutDefaults",
    "LayoutHints",
    "PolicyOverrides",
    "RenderModel",
    "ResolvedZone",
    "Section",
    "SectionInstance",
    "SectionInstanceStyle",
    "SectionPolicy",
    "SubsectionStyle",
    "TemplateDetail",
    "TemplateListItem",
    "TemplateManifest",
    "TextRun",
    "TextStyle",
    "Zone",
    "ZoneStyle",
]
