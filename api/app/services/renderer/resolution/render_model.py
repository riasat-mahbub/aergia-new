"""Assemble CSS variables and the final resolved render model."""

from __future__ import annotations

from app.document_schema.models import RenderModel, ResolvedZone, Section, TemplateManifest
from app.services.renderer.html_values import (
    FONT_TOKEN_VALUES as FONT_TOKENS,
    FONT_SIZE_VALUES as FONT_SIZES,
    LINK_STYLES,
    LINE_HEIGHT_TOKEN_VALUES as LINE_HEIGHTS,
    PLAIN_LINK_STYLES,
    PRINT_STYLES,
    SPACING_TOKEN_VALUES as _SPACING_TOKENS,
    SPACING_VALUES,
    resolve_color_ref,
)

from .context import ResolutionContext


def _build_css_vars(context: ResolutionContext) -> dict[str, str]:
    customizations = context.customizations
    manifest = context.manifest

    spacing_override = customizations.spacing is not None
    spacing = customizations.spacing
    if spacing is None and manifest is not None:
        spacing = manifest.layout_defaults.spacing

    vars_: dict[str, str] = {}
    section_gap, subsection_gap = _SPACING_TOKENS.get(
        spacing or "none",
        _SPACING_TOKENS["none"],
    )
    vars_["--spacing-section"] = section_gap
    vars_["--spacing-subsection"] = subsection_gap

    # Legacy manifests inherit entry and field rhythm from their layout
    # preset's subsection value. New template-specific gaps replace that
    # fallback only when the CV has not selected its own spacing preset.
    entry_gap = subsection_gap
    field_gap = subsection_gap
    if not spacing_override and manifest is not None:
        if manifest.layout_defaults.entry_gap is not None:
            entry_gap = SPACING_VALUES[manifest.layout_defaults.entry_gap]
        if manifest.layout_defaults.field_gap is not None:
            field_gap = SPACING_VALUES[manifest.layout_defaults.field_gap]
    vars_["--spacing-entry"] = entry_gap
    vars_["--spacing-field"] = field_gap

    if manifest is not None:
        body_font_size = manifest.global_styles.body_font_size
        if body_font_size is not None:
            vars_["--body-size"] = FONT_SIZES[body_font_size]
        body_line_height = manifest.global_styles.body_line_height
        if body_line_height is not None:
            vars_["--body-line-height"] = LINE_HEIGHTS[body_line_height]

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
        vars_["--accent"] = resolve_color_ref(accent)

    return vars_


def build_render_model(
    sections: dict[str, Section],
    zones: list[ResolvedZone],
    context: ResolutionContext,
) -> RenderModel:
    """Build the renderer-facing model from resolved sections and zones."""

    manifest: TemplateManifest | None = context.manifest
    css_vars = _build_css_vars(context)
    body_font = (
        css_vars.get("--body-font")
        or (manifest.global_styles.body_font if manifest else None)
        or "system-ui, sans-serif"
    )
    heading_font = (
        css_vars.get("--heading-font")
        or (manifest.global_styles.heading_font if manifest else None)
        or body_font
    )
    link_styles = (
        LINK_STYLES
        if context.customizations.flags.get("default_link_style", False)
        else PLAIN_LINK_STYLES
    )
    return RenderModel(
        zones=zones,
        css_vars=css_vars,
        body_font=body_font,
        heading_font=heading_font,
        link_styles=link_styles,
        print_styles=PRINT_STYLES,
        sections=sections,
    )


__all__ = ["build_render_model"]
