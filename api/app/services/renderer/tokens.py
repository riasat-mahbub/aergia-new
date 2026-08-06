"""Token-to-renderer-value mapping tables.

The manifest exposes a closed design vocabulary (see
:data:`app.schema.models.WidthToken`, :data:`SpacingToken`,
:data:`FontToken`). The token name is renderer-independent; this
module is where each token meets a renderer-specific value.

The HTML renderer ships the mappings below. A future DOCX renderer
would ship its own ``tokens_docx.py`` and register a parallel mapping
(e.g. ``narrow`` -> a column width in twips). The manifest stays
renderer-independent; only the renderer-side mapping changes.
"""

from typing import Literal

# Width tokens: ``narrow`` ≈ 30%, ``half`` ≈ 50%, ``full`` ≈ 100%.
WidthToken = Literal["narrow", "half", "full", "auto"]
WIDTH_TOKEN_VALUES: dict[str, str] = {
    "narrow": "30%",
    "half": "50%",
    "full": "100%",
    "auto": "auto",
}

# Padding tokens: renderer-defined CSS values.
PaddingToken = Literal["none", "tight", "comfortable", "loose", "spacious"]
PADDING_TOKEN_VALUES: dict[str, str] = {
    "none": "0",
    "tight": "12px",
    "comfortable": "24px",
    "loose": "32px",
    "spacious": "32px",
}

# Spacing design tokens (CSS variables the renderer emits). The
# ``layout_defaults.spacing`` enum maps to these pairs; the renderer
# is the only place these values live.
SpacingToken = Literal["compact", "comfortable", "minimal"]
SPACING_TOKEN_VALUES: dict[str, tuple[str, str]] = {
    # layout_defaults.spacing -> (--spacing-section, --spacing-subsection)
    "compact": ("20px", "12px"),
    "comfortable": ("24px", "16px"),
    "minimal": ("16px", "8px"),
}

# Font tokens: renderer-defined font stacks.
FontToken = Literal["sans-serif", "serif", "mono", "display"]
FONT_TOKEN_VALUES: dict[str, str] = {
    "sans-serif": "Inter, system-ui, sans-serif",
    "serif": "Georgia, Crimson, serif",
    "mono": "ui-monospace, SFMono-Regular, Menlo, monospace",
    "display": "Inter, system-ui, sans-serif",
}


def resolve_width(token: str) -> str:
    return WIDTH_TOKEN_VALUES.get(token, token)


def resolve_padding(token: str) -> str:
    return PADDING_TOKEN_VALUES.get(token, token)


def resolve_font(token: str) -> str:
    return FONT_TOKEN_VALUES.get(token, token)


def resolve_spacing_pair(token: str) -> tuple[str, str]:
    return SPACING_TOKEN_VALUES.get(token, SPACING_TOKEN_VALUES["comfortable"])
