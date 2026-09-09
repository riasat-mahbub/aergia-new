"""Pydantic AST schema for the HTML-first renderer pipeline.

The new pipeline:

    AST (this module)  ->  Resolver  ->  RenderModel  ->  HTMLDocumentRenderer  ->  HTML5  ->  Chromium  ->  PDF

This package is the single source of truth for the document model. The
TypeScript types in ``web/src/generated/schema.ts`` are derived from these
models via ``api/scripts/codegen_schema.py``.

Four orthogonal axes for styling:

- :class:`TextStyle` — inline per-field appearance.
- :class:`SubsectionStyle` — block-level appearance per section/entry.
- :class:`LayoutHints` — page flow and structural intent.
- :class:`SectionTypography` — section-local heading and body typography.

:data:`DateStyle` is the format preset for dates and lives next to the rest of
the AST.
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
    SectionTypography,
    SubsectionStyle,
    TemplateDetail,
    TemplateListItem,
    TemplateManifest,
    TextRun,
    TextStyle,
    TypographyRole,
    Zone,
    ZoneStyle,
)
from .capabilities import capabilities_hash, renderer_capabilities

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
    "SectionTypography",
    "SubsectionStyle",
    "TemplateDetail",
    "TemplateListItem",
    "TemplateManifest",
    "TextRun",
    "TextStyle",
    "TypographyRole",
    "Zone",
    "ZoneStyle",
    "capabilities_hash",
    "renderer_capabilities",
]
