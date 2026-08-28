"""Resolver — Document + manifest + customizations + renderer capabilities → RenderModel.

The Resolver is the only place where three layers of style meet:

1. **Per-instance style overrides** (``customizations.per_section[id]``)
   overlay onto the section's already-built three-axis style.
2. **Template defaults** paint template-wide values onto each section
   when the section didn't declare them.
3. **User customizations** paint shared values onto every section only
   when neither the template nor the section declared them.

Then it:

4. Computes CSS variables (``--spacing-section``, ``--body-font``, …)
   from the resolved values.
5. Resolves zones via ``manifest.placement[type]``.
6. Reads :class:`RendererSupport` to **drop** features the renderer
   declared as ``NONE``. ``BEST_EFFORT`` features pass through (the
   renderer emits a ``<!-- best-effort: … -->`` comment).

The Resolver is pure: no I/O, no DB, no Pydantic over DB rows. It receives
already-validated models and returns a fully resolved :class:`RenderModel`.
"""

from __future__ import annotations

from app.schema.models import (
    Customizations,
    Document,
    LayoutHints,
    RenderModel,
    ResolvedZone,
    Section,
    SectionInstanceStyle,
    SubsectionStyle,
    TemplateManifest,
    Zone,
)
from app.services.renderer.base import DocumentRenderer
from app.services.renderer.palette import DEFAULT_PALETTE, resolve_palette_ref
from app.services.renderer.support import RendererSupport, SupportLevel
from app.services.renderer.tokens import (
    FONT_TOKEN_VALUES as FONT_TOKENS,
    PADDING_TOKEN_VALUES as PADDING_TOKENS,
    SPACING_TOKEN_VALUES as _SPACING_TOKENS,
    WIDTH_TOKEN_VALUES as WIDTH_TOKENS,
)
LINK_STYLES = "  a { color: var(--accent, #2563eb); text-decoration: underline; }\n"
PLAIN_LINK_STYLES = "  a { color: inherit; text-decoration: none; }\n"

_MANIFEST_VERSION_KEY = "manifest_version"
PRINT_STYLES = """
  @page { size: A4; margin: 24px 0 0 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def resolve_color(value: str) -> str:
    """Resolve a color ref to a concrete color value.

    A hex literal is returned as-is. A palette reference is resolved
    against :data:`DEFAULT_PALETTE`; unknown palette names fall back to
    the literal string (the renderer will fail loudly downstream).
    """
    return resolve_palette_ref(value, DEFAULT_PALETTE)


class ManifestVersionError(ValueError):
    """Raised when the manifest is not v2."""


def _default_date_style() -> dict:
    """The professional default date style used when no override is set."""

    return {"key": "Month YYYY", "range_sep": " – "}


def _overlay_subsection(base: SubsectionStyle | None, override: SubsectionStyle | None) -> SubsectionStyle:
    if override is None:
        return base or SubsectionStyle()
    base_dict = (base.model_dump(exclude_none=True) if base else {})
    over_dict = override.model_dump(exclude_none=True)
    return SubsectionStyle.model_validate({**base_dict, **over_dict})


def _overlay_layout(base: LayoutHints | None, override: LayoutHints | None) -> LayoutHints:
    if override is None:
        return base or LayoutHints()
    base_dict = (base.model_dump(exclude_none=True) if base else {})
    over_dict = override.model_dump(exclude_none=True)
    return LayoutHints.model_validate({**base_dict, **over_dict})


def _overlay_policy(base, override):
    if override is None:
        return base
    if base is None:
        return override
    base_dict = base.model_dump(exclude_none=True)
    over_dict = override.model_dump(exclude_none=True)
    return type(base).model_validate({**base_dict, **over_dict})


def _apply_section_overlay(section: Section, override: SectionInstanceStyle) -> Section:
    """Merge a per-instance user override onto a section's three-axis style."""

    new_subsection = _overlay_subsection(section.subsection, override.subsection)
    new_layout = _overlay_layout(section.layout, override.layout)
    new_policy = _overlay_policy(section.policy, override.policy)
    section = section.model_copy(update={
        "subsection": new_subsection,
        "layout": new_layout,
        "policy": new_policy,
    })
    # Per-field text styles ride in the override's `text` dict and must land
    # on the runs, mirroring the per-instance path in build_document.
    if override.text:
        from app.services.renderer.builders import apply_field_text_styles

        section = apply_field_text_styles(section, override.text)
    return section


def _apply_template_defaults(section: Section, manifest: TemplateManifest | None) -> Section:
    """Paint template defaults onto each section where the section didn't
    declare a value."""

    if manifest is None:
        return section

    layout_dict = section.layout.model_dump(exclude_none=True) if section.layout else {}
    sub_dict = section.subsection.model_dump(exclude_none=True) if section.subsection else {}

    body_font = manifest.global_styles.body_font
    if body_font and not layout_dict.get("font_family"):
        layout_dict["font_family"] = FONT_TOKENS.get(body_font, body_font)

    accent = manifest.global_styles.accent_color
    if accent and not sub_dict.get("section_color"):
        sub_dict["section_color"] = resolve_color(accent)

    if not layout_dict.get("date_style"):
        layout_dict["date_style"] = _default_date_style()

    new_layout = LayoutHints.model_validate(layout_dict) if layout_dict else section.layout
    new_subsection = SubsectionStyle.model_validate(sub_dict) if sub_dict else section.subsection
    return section.model_copy(update={"subsection": new_subsection, "layout": new_layout})


def _apply_user_customizations(section: Section, customizations: Customizations) -> Section:
    """Paint user customizations onto each section where the template
    didn't declare a value."""

    layout_dict = section.layout.model_dump(exclude_none=True) if section.layout else {}
    sub_dict = section.subsection.model_dump(exclude_none=True) if section.subsection else {}

    if customizations.body_font:
        layout_dict["font_family"] = FONT_TOKENS.get(customizations.body_font, customizations.body_font)
    if customizations.accent_color:
        sub_dict["section_color"] = resolve_color(customizations.accent_color)
    if customizations.default_text_align and not sub_dict.get("text_align"):
        sub_dict["text_align"] = customizations.default_text_align

    new_layout = LayoutHints.model_validate(layout_dict) if layout_dict else section.layout
    new_subsection = SubsectionStyle.model_validate(sub_dict) if sub_dict else section.subsection
    return section.model_copy(update={"subsection": new_subsection, "layout": new_layout})


def _build_css_vars(customizations: Customizations, manifest: TemplateManifest | None) -> dict[str, str]:
    spacing = customizations.spacing
    if spacing is None and manifest is not None:
        spacing = manifest.layout_defaults.spacing

    vars_: dict[str, str] = {}
    section_gap, subsection_gap = _SPACING_TOKENS.get(spacing or "none", _SPACING_TOKENS["none"])
    vars_["--spacing-section"] = section_gap
    vars_["--spacing-subsection"] = subsection_gap

    body_font = customizations.body_font
    if body_font is None and manifest is not None:
        body_font = manifest.global_styles.body_font
    if body_font:
        vars_["--body-font"] = FONT_TOKENS.get(body_font, body_font)

    heading_font = customizations.heading_font
    if heading_font is None and manifest is not None:
        heading_font = manifest.global_styles.heading_font
    if heading_font:
        vars_["--heading-font"] = FONT_TOKENS.get(heading_font, heading_font)
    elif body_font:
        vars_["--heading-font"] = FONT_TOKENS.get(body_font, body_font)

    accent = customizations.accent_color
    if accent is None and manifest is not None:
        accent = manifest.global_styles.accent_color
    if accent:
        vars_["--accent"] = resolve_color(accent)

    return vars_


def _resolve_zone_styles(zone: Zone) -> dict[str, str]:
    """Map a manifest zone's token-based styles to concrete CSS values.

    This is the only place raw CSS values are produced from the manifest's
    token vocabulary. A future DOCX renderer would provide its own
    mapping; the manifest stays renderer-independent.
    """
    css: dict[str, str] = {}
    if zone.styles.width is not None:
        css["width"] = WIDTH_TOKENS.get(zone.styles.width, zone.styles.width)
    if zone.styles.background is not None:
        css["background-color"] = resolve_color(zone.styles.background)
    if zone.styles.padding is not None:
        css["padding"] = PADDING_TOKENS.get(zone.styles.padding, zone.styles.padding)
    return css


def _resolve_zones(
    document: Document,
    manifest: TemplateManifest | None,
    customizations: Customizations | None = None,
) -> list[ResolvedZone]:
    """Resolve the document's zone layout.

    Per-CV ``customizations.layout`` (the editor's zone authoring) wins over
    the template manifest's zones; the manifest is the fallback; a single
    ``main`` zone is the last resort so rendering never fails on layout.
    """
    layout = customizations.layout if customizations is not None else None
    zones = layout.zones if layout is not None and layout.zones else (manifest.zones if manifest else [])
    if not zones:
        return [ResolvedZone(
            id="main",
            styles={},
            section_ids=[s.id for s in document.sections],
        )]

    placement = (
        layout.placement
        if layout is not None and layout.placement
        else (manifest.placement if manifest else {})
    )
    fallback_zone = zones[0].id

    groups: dict[str, list[str]] = {zone.id: [] for zone in zones}
    for section in document.sections:
        # The editor keys placement by section instance id; manifests key it
        # by section type. Honor both, then fall back to the first zone.
        zone_id = placement.get(section.id) or placement.get(section.type, fallback_zone)
        if zone_id is None:
            raise ManifestVersionError(
                f"No zone defined for section type '{section.type}' and no fallback zone available"
            )
        groups.setdefault(zone_id, []).append(section.id)

    return [
        ResolvedZone(id=zone.id, styles=_resolve_zone_styles(zone), section_ids=groups.get(zone.id, []))
        for zone in zones
    ]


def _drop_none_features(model: RenderModel, support: RendererSupport) -> RenderModel:
    """Drop features the renderer declared as ``NONE``.

    Only fields with a per-section resolver mapping are gated here:
    ``break_before``, ``keep_together``, ``heading_keeps_with_first``.
    ``keep_together`` is rendered per entry (each ``<div class="entry">``
    carries ``break-inside: avoid``); an unsupported renderer drops the
    flag so entries are free to split across pages. The no-op markers
    ``keep_with_next``, ``feature_section_underline``, and
    ``feature_anchor_styling`` have no per-section resolver mapping
    today; the renderer ignores them regardless of support level. The
    panel hides their controls on NONE but the resolver does not act.
    """
    none_fields = [
        f for f in ("break_before", "keep_together", "heading_keeps_with_first")
        if getattr(support, f) is SupportLevel.NONE
    ]
    if not none_fields:
        return model

    def _strip(section: Section) -> Section:
        if section.layout is None:
            return section
        layout = section.layout
        updates: dict[str, object] = {}
        for f in none_fields:
            if getattr(layout, f):
                updates[f] = False
        if not updates:
            return section
        return section.model_copy(update={"layout": layout.model_copy(update=updates)})

    new_sections = {sid: _strip(s) for sid, s in model.sections.items()}
    return model.model_copy(update={"sections": new_sections})



def _check_manifest(manifest: TemplateManifest | dict | None) -> TemplateManifest | None:
    if manifest is None:
        return None
    if isinstance(manifest, TemplateManifest):
        return manifest
    if isinstance(manifest, dict):
        version = manifest.get(_MANIFEST_VERSION_KEY)
        if version != 2:
            raise ManifestVersionError(
                f"Template manifest version {version!r} is not supported; expected 2."
            )
        return TemplateManifest.model_validate(manifest)
    raise ManifestVersionError("Template manifest must be a dict or TemplateManifest.")

def resolve(
    document: Document,
    renderer: DocumentRenderer,
    manifest: TemplateManifest | dict | None = None,
    customizations: Customizations | dict | None = None,
) -> RenderModel:
    """Resolve a :class:`Document` into a fully resolved :class:`RenderModel`."""

    support = renderer.support

    manifest_model = _check_manifest(manifest)

    if customizations is None:
        customizations_model = Customizations()
    elif isinstance(customizations, Customizations):
        customizations_model = customizations
    else:
        customizations_model = Customizations.model_validate(customizations)

    from app.services.renderer.policy import resolve_policy

    resolved_sections: dict[str, Section] = {}
    for section in document.sections:
        # 0. Default the policy when the section didn't declare one.
        if section.policy is None:
            section = section.model_copy(update={"policy": resolve_policy(section.type, manifest_model)})
        # 1. Per-instance override.
        override = customizations_model.per_section.get(section.id)
        if override is not None:
            section = _apply_section_overlay(section, override)
        # 2. Template defaults.
        section = _apply_template_defaults(section, manifest_model)
        # 3. User customizations.
        section = _apply_user_customizations(section, customizations_model)
        # 4. Renderer capability gating.
        if support.feature_skills_inline is SupportLevel.NONE and section.type == "skills":
            if section.policy is not None and section.policy.skill_variant is not None:
                section = section.model_copy(update={
                    "policy": section.policy.model_copy(update={"skill_variant": "block"}),
                })

        resolved_sections[section.id] = section

    css_vars = _build_css_vars(customizations_model, manifest_model)
    body_font = (
        css_vars.get("--body-font")
        or (manifest_model.global_styles.body_font if manifest_model else None)
        or "system-ui, sans-serif"
    )
    heading_font = (
        css_vars.get("--heading-font")
        or (manifest_model.global_styles.heading_font if manifest_model else None)
        or body_font
    )
    link_styles = (
        LINK_STYLES
        if customizations_model.flags.get("default_link_style", False)
        else PLAIN_LINK_STYLES
    )

    zones = _resolve_zones(
        Document(sections=list(resolved_sections.values())),
        manifest_model,
        customizations_model,
    )

    model = RenderModel(
        zones=zones,
        css_vars=css_vars,
        body_font=body_font,
        heading_font=heading_font,
        link_styles=link_styles,
        print_styles=PRINT_STYLES,
        sections=resolved_sections,
    )
    return _drop_none_features(model, support)


__all__ = [
    "LINK_STYLES",
    "PLAIN_LINK_STYLES",
    "PRINT_STYLES",
    "ManifestVersionError",
    "resolve",
]
