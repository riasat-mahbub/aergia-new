"""CSS variable substitution and customization merging."""

from typing import Any


def merge_customizations(defaults: dict, overrides: dict) -> dict:
    """Deep merge overrides on top of defaults."""
    merged = {}
    for key in defaults:
        if key in overrides:
            if isinstance(defaults[key], dict) and isinstance(overrides[key], dict):
                merged[key] = {**defaults[key], **overrides[key]}
            else:
                merged[key] = overrides[key]
        else:
            merged[key] = defaults[key]
    for key in overrides:
        if key not in merged:
            merged[key] = overrides[key]
    return merged


def build_css_vars(customizations: dict) -> dict[str, str]:
    """Build CSS variable map from customizations."""
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})

    css_var_map = {
        "--accent": colors.get("accent"),
        "--bg-sidebar": colors.get("bg_sidebar"),
        "--header": colors.get("header"),
        "--divider": colors.get("divider"),
        "--text": colors.get("text"),
        "--heading": colors.get("heading"),
        "--body-font": fonts.get("body"),
        "--heading-font": fonts.get("heading"),
        "--section-gap": spacing.get("section_gap"),
    }

    return {k: v for k, v in css_var_map.items() if v is not None}


def substitute_css_vars(html: str, customizations: dict) -> str:
    """Replace CSS custom property placeholders with actual values."""
    css_vars = build_css_vars(customizations)
    result = html
    for placeholder, value in css_vars.items():
        result = result.replace(f"var({placeholder})", value)
    return result