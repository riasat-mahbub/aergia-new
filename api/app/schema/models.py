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

The manifest exposes a **closed design vocabulary** (the constrained tokens
in :data:`WidthToken`, :data:`SpacingToken`, :data:`FontToken`, etc.).
The manifest never carries raw CSS strings; the resolver maps each token
to the renderer's native value. A future DOCX renderer reads the same
tokens and produces DOCX equivalents.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Design tokens — the constrained vocabulary the manifest exposes
# ---------------------------------------------------------------------------


# A zone's width. ``narrow`` ≈ 30%, ``half`` ≈ 50%, ``full`` ≈ 100%.
# ``auto`` lets the renderer fall back to its content-driven default.
WidthToken = Literal["narrow", "half", "full", "auto"]

# Spacing and padding presets. The resolver maps these to design-token
# CSS variables (``--spacing-section`` etc.). The values are renderer-
# defined; the schema only carries the names.
SpacingToken = Literal["none", "tight", "comfortable", "loose", "spacious"]

# Font families exposed to template authors. Each renderer maps a token
# to its native font stack (CSS, DOCX font reference, etc.).
FontToken = Literal["sans-serif", "serif", "mono", "display"]

# Font size class. The resolver maps each to a concrete CSS length.
FontSizeToken = Literal["xs", "small", "normal", "large", "xl"]

# Text alignment. Mirrors CSS ``text-align`` values and DOCX alignment.
AlignmentToken = Literal["left", "right", "center", "justify"]

# A color reference is either a hex literal (``#RRGGBB``) or a named
# palette slot (``palette.<name>``). Renderers define their own
# palettes; the schema carries the reference, not the color value.
_HEX_LITERAL = re.compile(r"^#[0-9a-fA-F]{6}$")
_PALETTE_REF = re.compile(r"^palette\.[a-z][a-z0-9_-]*$")


def is_color_ref(value: object) -> bool:
    """Type guard for ``ColorRef``. Used by Pydantic field validators."""
    if not isinstance(value, str):
        return False
    return bool(_HEX_LITERAL.match(value)) or bool(_PALETTE_REF.match(value))


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
    font_size: FontSizeToken | None = None


class RichTextItem(BaseModel):
    """A single inline run of styled text inside a rich-text block."""

    text: str
    style: TextStyle | None = None


class RichTextBlock(BaseModel):
    """One block of rich text: a paragraph or a list.

    Descriptions and summary fields use ``list[RichTextBlock]`` for rich
    text content.  Each block is either a paragraph (inline-styled runs)
    or a list (one item per entry in ``items``).
    """

    type: Literal["paragraph", "bullet_list", "numbered_list"] = "paragraph"
    items: list[RichTextItem] = Field(default_factory=list)


class SubsectionStyle(BaseModel):
    """Block-level appearance per section/entry.

    ``section_color`` is the legacy ``SectionStyle.color`` cascade target —
    the per-section accent color used by the heading and other wrappers.
    """

    text_align: AlignmentToken | None = None
    spacing_before: str | None = None
    spacing_after: str | None = None
    background_color: str | None = None
    section_color: str | None = None


class LayoutHints(BaseModel):
    """Page flow and structural intent. The renderer emits these as CSS.

    ``orphans``/``widows`` map to the CSS ``orphans``/``widows`` properties
    on the section wrapper; Chromium honours them on ``@page`` flow but is
    best-effort elsewhere. ``keep_together`` maps to ``break-inside: avoid``
    applied per entry (each ``<div class="entry">`` is the unit that must
    not split across pages), so an overflowing entry moves to the next
    page on its own instead of dragging the whole section with it. Entries
    larger than a page split anyway — Chromium's ``break-inside: avoid``
    is best-effort.
    """

    font_family: str | None = None
    date_style: DateStyle | None = None
    break_before: bool = False
    keep_together: bool = True
    heading_keeps_with_first: bool = True
    orphans: int = 2
    widows: int = 2
    # Field keys whose FieldBlocks render as inline chip pills (e.g. project
    # ``tech`` items, skill ``tag`` items). ``None`` = no chips. The renderer
    # is renderer-key-agnostic: it reads only this list.
    chip_keys: list[str] | None = None

class SectionPolicy(BaseModel):
    """Document semantics for a section. The renderer implements these
    with HTML constructs; a future DOCX renderer would do the same with
    DOCX constructs. Policy stays semantic — renderers pick the markup."""

    show_title: bool = True
    heading_divider: bool = False
    skill_variant: Literal["block", "inline"] | None = None
    entry_layout: Literal["stack", "two-column"] = "stack"
# ---------------------------------------------------------------------------
# AST nodes
# ---------------------------------------------------------------------------


class TextRun(BaseModel):
    """A single run of styled text inside a field."""

    text: str
    style: TextStyle | None = None


class FieldBlock(BaseModel):
    """A named field (e.g. ``"company"``, ``"title"``) containing one or more
    text runs. The renderer emits a ``<div class="f-{key}">`` wrapper.

    ``group`` names the semantic row the field belongs to (``"header"``,
    ``"contact"``, ``"social"``, ``"body"``, ...); consecutive same-group
    fields render inline in one row. ``icon`` names a social icon for the
    field; the renderer draws it from its icon table when known. ``align``
    names a right-rail field — the first right-aligned field in a row is
    pushed to the row's right edge via margin-left:auto."""

    key: str
    runs: list[TextRun]
    group: str | None = None
    align: Literal["right"] | None = None
    icon: str | None = None
    blocks: list[RichTextBlock] | None = None
    rich_text: bool = False


class Entry(BaseModel):
    """One entry inside a section (a job, a school, a skill group, ...)."""

    id: str
    fields: list[FieldBlock]


class Section(BaseModel):
    """One section of the document. Carries the three-axis style."""

    id: str
    type: str
    title: str
    enabled: bool = True
    entries: list[Entry] = Field(default_factory=list)
    fields: list[FieldBlock] = Field(default_factory=list)
    layout: LayoutHints | None = None
    subsection: SubsectionStyle | None = None
    policy: SectionPolicy | None = None

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
    """

    id: str
    type: str
    title: str
    enabled: bool = True
    data: list | dict = Field(default_factory=dict)
    style: SectionInstanceStyle | None = None


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


class GlobalStyles(BaseModel):
    """Template-level style tokens.

    Closed vocabulary: ``accent_color`` is a color ref (a hex literal or
    a ``palette.<name>`` reference); ``body_font`` and ``heading_font``
    are :data:`FontToken` enums. The schema rejects unknown keys, so a
    manifest cannot smuggle in arbitrary CSS.
    """

    model_config = {"extra": "forbid"}

    accent_color: str | None = None
    body_font: FontToken | None = None
    heading_font: FontToken | None = None

    @model_validator(mode="after")
    def _check_color_ref(self):
        if self.accent_color is not None and not is_color_ref(self.accent_color):
            raise ValueError(
                f"GlobalStyles.accent_color must be a hex literal (#RRGGBB) "
                f"or a palette reference (palette.<name>); got {self.accent_color!r}"
            )
        return self


class ZoneStyle(BaseModel):
    """Constrained style for a zone.

    The manifest exposes a closed vocabulary: ``width`` is a
    :data:`WidthToken`, ``background`` is a color ref (a hex literal or
    a palette reference), and ``padding`` is a :data:`SpacingToken`.
    The manifest never carries raw CSS strings; the resolver maps each
    token to the renderer's native value.

    The schema is closed (``extra="forbid"``) so a manifest cannot smuggle
    in raw CSS like ``display: flex`` or ``position: absolute``. The
    renderer's vocabulary is the only vocabulary.
    """

    width: WidthToken | None = None
    background: str | None = None
    padding: SpacingToken | None = None

    model_config = {"extra": "forbid", "populate_by_name": True}

    @model_validator(mode="after")
    def _check_color_ref(self):
        if self.background is not None and not is_color_ref(self.background):
            raise ValueError(
                f"ZoneStyle.background must be a hex literal (#RRGGBB) "
                f"or a palette reference (palette.<name>); got {self.background!r}"
            )
        return self


class Zone(BaseModel):
    """One zone in the template layout."""

    id: str
    label: str | None = None
    styles: ZoneStyle = Field(default_factory=ZoneStyle)


class CVLayout(BaseModel):
    """Per-CV zone layout written by the editor's layout authoring.

    Carries the same shape as the manifest's zones/placement but is a per-CV
    override: the resolver renders these zones when present, falling back to
    the template manifest. ``placement`` is keyed by section instance id
    (the editor's convention); the resolver also accepts section-type keys
    (the manifest convention)."""

    zones: list[Zone] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)


class TemplateManifest(BaseModel):
    """Template manifest schema (version 2).

    Supersedes the legacy v1 schema (``layout_config`` / ``globalStyleSchema``).
    Every seed manifest is v2; user-uploaded manifests must match.

    The manifest is a closed declarative document. ``global_styles`` is a
    typed :class:`GlobalStyles` with a fixed key set: ``accent_color``
    (a color ref), ``body_font`` and ``heading_font`` (a
    :data:`FontToken`). The schema rejects unknown keys so a manifest
    cannot smuggle in arbitrary CSS.
    """

    manifest_version: Literal[2] = 2
    name: str
    description: str | None = None
    zones: list[Zone] = Field(default_factory=list)
    placement: dict[str, str] = Field(default_factory=dict)  # section_type -> zone_id
    layout_defaults: LayoutDefaults = Field(default_factory=LayoutDefaults)
    policy_overrides: PolicyOverrides = Field(default_factory=PolicyOverrides)
    global_styles: GlobalStyles = Field(default_factory=GlobalStyles)


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

    The four canonical fields are written by the per-CV customizations
    editor. ``accent_color`` is a color ref (hex literal or palette
    reference). The legacy ``{colors, fonts, spacing, flags}`` top-level
    keys are rejected at the boundary via ``_reject_legacy`` below.
    """

    accent_color: str | None = None
    body_font: FontToken | None = None
    heading_font: FontToken | None = None
    default_text_align: AlignmentToken | None = None
    spacing: Literal["compact", "comfortable", "minimal"] | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    per_section: dict[str, SectionInstanceStyle] = Field(default_factory=dict)
    layout: CVLayout | None = None

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

    @model_validator(mode="after")
    def _check_accent_color_ref(self):
        if self.accent_color is not None and not is_color_ref(self.accent_color):
            raise ValueError(
                f"Customizations.accent_color must be a hex literal (#RRGGBB) "
                f"or a palette reference (palette.<name>); got {self.accent_color!r}"
            )
        return self


class TemplateListItem(BaseModel):
    """List-page representation of a template (no manifest payload)."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    preview_image_url: str | None


class TemplateDetail(BaseModel):
    """Detail-page representation of a template.

    The manifest is the only template payload. The legacy
    ``default_customizations`` and ``layout_config`` keys are no longer
    persisted; renderers and the editor consume the manifest directly.
    """

    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    manifest: dict | None = None


# ---------------------------------------------------------------------------
# Library — AST types for reusable content entries
# ---------------------------------------------------------------------------

"""Library AST types.
``LibraryEntryKindStr`` enumerates the kinds a Library entry can take.
The set is closed: only entry-based section types are eligible. The CV's
``profile`` and ``summary`` sections have dict-shaped ``data`` and stay
authored directly in the CV — promote-to-library skips them.

``LibraryEntryPayload`` mirrors ``SectionInstance.data`` for entry-based
sections (a list of dicts). The model uses ``extra="ignore"`` so older
Library rows remain readable if ``SectionInstance.data`` gains new
optional fields in the future.
"""

LibraryEntryKindStr = Literal["experience", "education", "skill", "project", "certification", "language"]


class LibraryEntryPayload(BaseModel):
    """Payload of a Library entry — a list of ``SectionInstance.data`` rows."""

    model_config = {"extra": "ignore"}

    entries: list[dict] = Field(default_factory=list)
