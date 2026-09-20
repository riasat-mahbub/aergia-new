"""HTML renderer values and safety boundaries.

The document schema carries renderer-neutral tokens and references. This
module is the HTML target's value profile: it translates those tokens into
CSS values and validates values before they enter generated markup.

Keeping these values together gives the HTML renderer and resolver one
readable source of truth without making the schema aware of CSS.
"""

from __future__ import annotations

import re

from app.document_schema.models import is_color_ref
from app.services.renderer.palette import DEFAULT_PALETTE, resolve_palette_ref


# Width tokens: ``narrow`` ≈ 30%, ``half`` ≈ 50%, ``full`` ≈ 100%.
WIDTH_TOKEN_VALUES: dict[str, str] = {
    "narrow": "30%",
    "half": "50%",
    "full": "100%",
    "auto": "auto",
}

# Padding tokens: renderer-defined CSS values.
PADDING_TOKEN_VALUES: dict[str, str] = {
    "none": "0",
    "tight": "12px",
    "comfortable": "24px",
    "loose": "32px",
    "spacious": "32px",
}

# Spacing design tokens: ``layout_defaults.spacing`` maps to section and
# subsection CSS values emitted by the HTML renderer.
SPACING_TOKEN_VALUES: dict[str, tuple[str, str]] = {
    "none": ("0px", "0px"),
    "compact": ("20px", "0px"),
    "comfortable": ("24px", "16px"),
    "minimal": ("16px", "0px"),
}

# Font tokens: renderer-defined CSS stacks.
FONT_TOKEN_VALUES: dict[str, str] = {
    "sans-serif": "Inter, system-ui, sans-serif",
    "serif": "Georgia, Crimson, serif",
    "mono": "ui-monospace, SFMono-Regular, Menlo, monospace",
    "display": "Inter, system-ui, sans-serif",
}

FONT_SIZE_VALUES: dict[str, str] = {
    "xs": "0.75rem",
    "small": "0.875rem",
    "normal": "1rem",
    "large": "1.125rem",
    "xl": "1.25rem",
}

SPACING_VALUES: dict[str, str] = {
    "none": "0",
    "tight": "4px",
    "snug": "8px",
    "balanced": "12px",
    "roomy": "16px",
    "comfortable": "24px",
    "loose": "32px",
    "spacious": "40px",
    "compact": "20px",
    "minimal": "0px",
}

SAFE_SPACING_VALUES = frozenset({
    "0", "0px", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "40px",
    "var(--spacing-section, 16px)", "var(--spacing-section, 24px)",
    "var(--spacing-subsection, 0px)", "var(--spacing-subsection, 16px)",
})

SAFE_FONT_FAMILY_VALUES = frozenset({
    "Inter", "Georgia", "Crimson", "system-ui", "sans-serif", "serif",
    "Inter, system-ui, sans-serif", "Georgia, Crimson, serif",
    "system-ui, sans-serif",
    "ui-monospace, SFMono-Regular, Menlo, monospace",
})

LINK_STYLES = "  a { color: var(--accent, #2563eb); text-decoration: underline; }\n"
PLAIN_LINK_STYLES = "  a { color: inherit; text-decoration: none; }\n"

PRINT_STYLES = """
  @page { size: A4; margin: 24px 0 0 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""

_PX_VALUE = re.compile(r"(?:0|[1-9][0-9]?)px")
_HEX_VALUE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?")


def resolve_color_ref(value: str) -> str:
    """Resolve an HTML color reference to a concrete color value."""

    return resolve_palette_ref(value, DEFAULT_PALETTE)


def safe_color(value: object) -> str:
    """Return a safe concrete HTML color or an empty string."""

    if not is_color_ref(value):
        return ""
    resolved = resolve_color_ref(str(value))
    return resolved if _HEX_VALUE.fullmatch(resolved) else ""


def safe_spacing(value: object) -> str:
    """Return a known spacing value suitable for an HTML style."""

    if not isinstance(value, str):
        return ""
    if value in SPACING_VALUES:
        return SPACING_VALUES[value]
    if value in SAFE_SPACING_VALUES:
        return value
    if _PX_VALUE.fullmatch(value):
        return value
    return ""


def safe_font_family(value: object) -> str:
    """Return a known font stack suitable for an HTML style."""

    if not isinstance(value, str):
        return ""
    if value == "mono":
        return FONT_TOKEN_VALUES["mono"]
    if value == "display":
        return FONT_TOKEN_VALUES["display"]
    return value if value in SAFE_FONT_FAMILY_VALUES else ""


__all__ = [
    "FONT_SIZE_VALUES",
    "FONT_TOKEN_VALUES",
    "LINK_STYLES",
    "PADDING_TOKEN_VALUES",
    "PLAIN_LINK_STYLES",
    "PRINT_STYLES",
    "SAFE_FONT_FAMILY_VALUES",
    "SAFE_SPACING_VALUES",
    "SPACING_TOKEN_VALUES",
    "SPACING_VALUES",
    "WIDTH_TOKEN_VALUES",
    "resolve_color_ref",
    "safe_color",
    "safe_font_family",
    "safe_spacing",
]
