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
SpacingToken = Literal["none", "compact", "comfortable", "minimal"]
SPACING_TOKEN_VALUES: dict[str, tuple[str, str]] = {
    # layout_defaults.spacing -> (--spacing-section, --spacing-subsection)
    "none": ("0px", "0px"),
    "compact": ("20px", "0px"),
    "comfortable": ("24px", "16px"),
    # minimal: section gap stays at 16px (visible separation between
    # section blocks), but the per-field gap inside entries is 0 — the
    # user explicitly asked for tightest possible. Adjacent lines are
    # still distinguishable via font-size, color, and grid structure
    # (the right column's date+link are right-justified on separate
    # rows, not stacked on the same baseline).
    "minimal": ("16px", "0px"),
}

# Font tokens: renderer-defined font stacks.
FontToken = Literal["sans-serif", "serif", "mono", "display"]
FONT_TOKEN_VALUES: dict[str, str] = {
    "sans-serif": "Inter, system-ui, sans-serif",
    "serif": "Georgia, Crimson, serif",
    "mono": "ui-monospace, SFMono-Regular, Menlo, monospace",
    "display": "Inter, system-ui, sans-serif",
}
