"""Pydantic AST models for the HTML-first renderer pipeline.

The new pipeline is a typed document model. Every wire shape that travels
over HTTP, persists in the DB, or is consumed by the renderer is defined
here. The legacy IR-based pipeline (raw ``dict``s, dataclasses) is replaced
in one cutover.

Three orthogonal axes for styling:

- :class:`TextStyle` — inline per-field appearance (bold, italic, color,
  font-size, link).
- :class:`SubsectionStyle` — block-level appearance per section/entry
  (``text_align``, spacing, ``background_color``).
- :class:`LayoutHints` — page flow and structural intent (``break_before``,
  ``keep_together``, ``orphans``/``widows``, ``font_family``, ``date_style``).

:data:`SectionPolicy` is document semantics, not HTML-oriented. A future
DOCX renderer would implement the same policy with DOCX constructs.

Manifest version 2 supersedes the legacy v1 schema (``layout_config`` /
``globalStyleSchema``). Old manifests are no longer valid.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------


class DateStyle(BaseModel):
    """Per-section date display format.

    Mirrors the TypeScript ``DateStyle`` in ``web/src/generated/schema.ts``
    and the ``DATE_STYLE_OPTIONS`` presets in
    ``app/services/renderer/builders/_utils.py``. The ``key`` selects the
    format; ``range_sep`` is the separator between the start and end bound.
    """
    key: str = Field(default="YYYY-MM", alias="key")
    range_sep: str = Field(default=" \u2013 ", alias="rangeSep")

    model_config = {"extra": "ignore", "populate_by_name": True}


# ---------------------------------------------------------------------------
# Three-axis style model
# ---------------------------------------------------------------------------


class TextStyle(BaseModel):
    """Inline per-field appearance. Applied to a single ``TextRun``."""

    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    color: str | None = None
    link: str | None = None
    font_size: Literal["xs", "small", "normal", "large", "xl"] | None = None


class SubsectionStyle(BaseModel):
    """Block-level appearance per section/entry.

    ``section_color`` is the legacy ``SectionStyle.color`` cascade target —
    the per-section accent color used by the heading and other wrappers.
    """

    text_align: Literal["left", "right", "center", "justify"] | None = None
    spacing_before: str | None = None
    spacing_after: str | None = None
    background_color: str | None = None
    section_color: str | None = None


class LayoutHints(BaseModel):
    """Page flow and structural intent. The renderer emits these as CSS.

    ``orphans``/``widows`` map to the CSS ``orphans``/``widows`` properties
    on the section wrapper; Chromium honours them on ``@page`` flow but is
    best-effort elsewhere. ``keep_together`` maps to ``break-inside: avoid``.
    """

    font_family: str | None = None
    date_style: DateStyle | None = None
    break_before: bool = False
    keep_together: bool = True
    heading_keeps_with_first: bool = True
    orphans: int = 2
    widows: int = 2


class SectionPolicy(BaseModel):
    """Document semantics for a section. The renderer implements these
    with HTML constructs; a future DOCX renderer would do the same with
    DOCX constructs. Policy stays semantic — renderers pick the markup."""

    show_title: bool = True
    skill_variant: Literal["block", "inline"] | None = None


# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


class TextRun(BaseModel):
    """A single run of styled text inside a field."""

    text: str
    style: TextStyle | None = None


class FieldBlock(BaseModel):
    """A named field (e.g. ``"company"``, ``"title"``) containing one or more
    text runs. The renderer emits a ``<div class="f-{key}">`` wrapper."""

    key: str
    runs: list[TextRun]


class Entry(BaseModel):
    """One entry inside a section (a job, a school, a skill group, ...)."""

    id: str
    fields: list[FieldBlock]


class Section(BaseModel):
    """One section of the document. Carries the three-axis style."""

    id: str
    type: str  # profile, experience, education, ...
    title: str
    enabled: bool = True
    entries: list[Entry]
    policy: SectionPolicy | None = None
    subsection: SubsectionStyle | None = None
    layout: LayoutHints | None = None


class Document(BaseModel):
    """The full document AST."""

    sections: list[Section]


# ---------------------------------------------------------------------------
# Wire carriers — the JSON shape that travels over HTTP / persists in DB
# ---------------------------------------------------------------------------


class SectionInstanceStyle(BaseModel):
    """Three-axis style carried on a wire ``SectionInstance``.

    The legacy ``SectionStyle`` keys (``font``, ``color``, ``weight``,
    ``text_align``, ``show_title``, ``layout``, ``field_styles``,
    ``date_style``, ``subsection_gap``, ``row_gap``) are accepted on
    inbound payloads during normalisation. The builder applies them as
    legacy-style overlays before producing the resolved three-axis shape;
    the resolver cascades over the three axes. Extra keys are ignored by
    the renderer.
    """

    model_config = {"extra": "ignore"}

    text: dict[str, TextStyle] = Field(default_factory=dict)  # field_key -> TextStyle
    subsection: SubsectionStyle | None = None
    layout: LayoutHints | None = None
    policy: SectionPolicy | None = None

class SectionInstance(BaseModel):
    """The wire representation of a section in a CV.

    ``data`` is either a ``dict`` (for ``profile``) or a ``list[dict]`` (for
    the entry-based sections). The builder dispatches by ``type`` and
    constructs the AST accordingly.

    ``legacy_style`` is accepted on inbound payloads for backwards
    compatibility with rows stored before the cutover; the builder
    normalises it into the three-axis shape and drops the legacy field.
    It will be deleted once every legacy row has been re-saved.
    """

    id: str
    type: str
    title: str
    enabled: bool = True
    data: list | dict = Field(default_factory=dict)
    style: SectionInstanceStyle | None = None
    legacy_style: dict | None = None


class CVRow(BaseModel):
    """One rendered row of zones (the layout row, not the data row).

    Rows no longer exist in the new zone-only data model — every zone
    collapses to content height. This type remains as a structural marker
    for layout rows that a future renderer might re-introduce."""

    zones: list[str]  # zone IDs in render order


# ---------------------------------------------------------------------------
# Template manifest (version 2)
# ---------------------------------------------------------------------------


class LayoutDefaults(BaseModel):
    """Layout-wide defaults. Spacing maps to design tokens."""

    spacing: Literal["compact", "comfortable", "minimal"] = "comfortable"


class PolicyOverrides(BaseModel):
    """Per-type policy overrides layered over the default ``SECTION_POLICIES``."""

    by_type: dict[str, SectionPolicy] = Field(default_factory=dict)


class ZoneStyle(BaseModel):
    """Explicit CSS-level style on a zone.

    Stored with a hyphen-cased alias for ``background-color`` because
    manifests are authored by humans and the CSS convention is hyphens."""

    width: str | None = None
    background_color: str | None = Field(None, alias="background-color")
    padding: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}


class Zone(BaseModel):
    """One zone in the template layout."""

    id: str
    label: str | None = None
    styles: ZoneStyle = Field(default_factory=ZoneStyle)


class TemplateManifest(BaseModel):
    """Template manifest schema (version 2).

    Supersedes the legacy v1 schema (``layout_config`` / ``globalStyleSchema``).
    Every seed manifest is v2; user-uploaded manifests must match.
    """

    manifest_version: Literal[2] = 2
    name: str
    description: str | None = None
    zones: list[Zone] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)  # section_type -> zone_id
    layout_defaults: LayoutDefaults = Field(default_factory=LayoutDefaults)
    policy_overrides: PolicyOverrides = Field(default_factory=PolicyOverrides)
    global_styles: dict[str, str] = Field(default_factory=dict)  # accent_color, body_font, ...


# ---------------------------------------------------------------------------
# Resolved output — the renderer consumes this
# ---------------------------------------------------------------------------


class ResolvedZone(BaseModel):
    """One zone with its fully resolved CSS and ordered section IDs."""

    id: str
    styles: dict[str, str]  # fully resolved CSS (background-color, padding, ...)
    section_ids: list[str]  # ordered


class RenderModel(BaseModel):
    """The fully resolved document the renderer consumes.

    No defaults remain; every value the renderer might read is present.
    The renderer is the source of CSS knowledge — this model only carries
    values, not stylesheets."""

    zones: list[ResolvedZone]
    css_vars: dict[str, str]  # --spacing-section, --body-font, ...
    body_font: str
    heading_font: str
    link_styles: str
    print_styles: str
    sections: dict[str, Section]  # id -> Section (resolved)


class Customizations(BaseModel):
    """User-level overrides on the cascade (canonical v2 shape).

    Phase 2 cut over from the legacy ``{colors, fonts, spacing, flags}``
    shape: those top-level keys are now rejected at the boundary via
    ``_reject_legacy`` below. Stored legacy rows are migrated on read
    by ``app.services.legacy_customizations``; this model only accepts
    the canonical v2 fields, so any panel or wizard that writes the
    legacy shape fails loudly instead of silently dropping values.
    """

    accent_color: str | None = None
    body_font: str | None = None
    heading_font: str | None = None
    default_text_align: Literal["left", "right", "center", "justify"] | None = None
    spacing: Literal["compact", "comfortable", "minimal"] | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    per_section: dict[str, SectionInstanceStyle] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy(cls, data):
        if not isinstance(data, dict):
            return data
        legacy = {"colors", "fonts"} & set(data.keys())
        if legacy:
            raise ValueError(
                f"Legacy customizations shape rejected ({sorted(legacy)}). "
                f"Use accent_color / body_font / heading_font instead."
            )
        return data


class TemplateListItem(BaseModel):
    """List-page representation of a template (no manifest payload)."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    preview_image_url: str | None
    is_user_template: bool = False

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        data = super().model_validate(obj, *args, **kwargs)
        data.is_user_template = not getattr(obj, "is_system", False)
        return data


class TemplateDetail(BaseModel):
    """Detail-page representation of a template."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    preview_image_url: str | None
    default_customizations: dict | None
    manifest: dict | None = None
    assets: dict | None = None
    generated_html_url: str | None = None
    is_user_template: bool = False

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        data = super().model_validate(obj, *args, **kwargs)
        data.is_user_template = not getattr(obj, "is_system", False)
        return data


class UserTemplateCreate(BaseModel):
    """Create-a-template request body."""

    name: str
    description: str | None = None
    default_customizations: dict | None = None
