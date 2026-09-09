"""Compatibility exports for HTML token mappings.

The manifest exposes a closed design vocabulary (see
:data:`app.document_schema.models.WidthToken`, :data:`SpacingToken`,
:data:`FontToken`). The token name is renderer-independent; this
module is where each token meets a renderer-specific value. The HTML target's
actual values live in :mod:`app.services.renderer.html_values` so token
conversion and HTML safety rules have one home.

The names remain available here for compatibility. A future DOCX renderer
would ship its own target profile (e.g. ``narrow`` -> a column width in
twips). The manifest stays renderer-independent; only the renderer-side
mapping changes.
"""

from typing import Literal

from app.services.renderer.html_values import (
    FONT_TOKEN_VALUES,
    PADDING_TOKEN_VALUES,
    SPACING_TOKEN_VALUES,
    WIDTH_TOKEN_VALUES,
)

WidthToken = Literal["narrow", "half", "full", "auto"]

PaddingToken = Literal["none", "tight", "comfortable", "loose", "spacious"]

SpacingToken = Literal["none", "compact", "comfortable", "minimal"]

FontToken = Literal["sans-serif", "serif", "mono", "display"]


__all__ = [
    "FONT_TOKEN_VALUES",
    "FontToken",
    "PADDING_TOKEN_VALUES",
    "PaddingToken",
    "SPACING_TOKEN_VALUES",
    "SpacingToken",
    "WIDTH_TOKEN_VALUES",
    "WidthToken",
]
