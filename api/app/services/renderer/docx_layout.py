"""Small native layout helpers for the editable Word renderer.

These helpers own Word-specific paragraph properties. They intentionally do
not resolve document styles; the caller passes colors and effective font/page
measurements from the resolved render model.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Callable, Sequence

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from app.document_schema.models import FieldBlock

_PPR_AFTER_SHADING = tuple(
    f"w:{name}"
    for name in (
        "tabs",
        "suppressAutoHyphens",
        "kinsoku",
        "wordWrap",
        "overflowPunct",
        "topLinePunct",
        "autoSpaceDE",
        "autoSpaceDN",
        "bidi",
        "adjustRightInd",
        "snapToGrid",
        "spacing",
        "ind",
        "contextualSpacing",
        "mirrorIndents",
        "suppressOverlap",
        "jc",
        "textDirection",
        "textAlignment",
        "textboxTightWrap",
        "outlineLvl",
        "divId",
        "cnfStyle",
        "rPr",
        "sectPr",
        "pPrChange",
    )
)

_PPR_AFTER_BORDER = ("w:shd", *_PPR_AFTER_SHADING)
_PBDR_AFTER_BOTTOM = ("w:right", "w:between", "w:bar")
_ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def _insert_schema_ordered(parent, element, successors: tuple[str, ...]) -> None:
    """Insert an XML child before the first existing schema successor."""

    successor_tags = {qn(tag) for tag in successors}
    successor = next((child for child in parent if child.tag in successor_tags), None)
    if successor is None:
        parent.append(element)
    else:
        successor.addprevious(element)


def _rgb_hex(color: RGBColor | str | None) -> str | None:
    """Serialize a pre-resolved Word color as six hexadecimal digits."""

    if isinstance(color, RGBColor):
        return "".join(f"{component:02X}" for component in color)
    if not isinstance(color, str):
        return None
    digits = color.removeprefix("#")
    if len(digits) not in {3, 6} or any(char not in "0123456789abcdefABCDEF" for char in digits):
        return None
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    return digits.upper()


def set_paragraph_alignment(paragraph, alignment: str | None) -> None:
    """Set a native Word alignment when the resolved token is supported."""

    value = _ALIGNMENT.get(alignment or "")
    if value is not None:
        paragraph.alignment = value


def set_paragraph_shading(paragraph, color: RGBColor | str | None) -> None:
    """Apply a paragraph-wide fill using an ordered ``w:shd`` property."""

    fill = _rgb_hex(color)
    if fill is None:
        return

    properties = paragraph._p.get_or_add_pPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        _insert_schema_ordered(properties, shading, _PPR_AFTER_SHADING)
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)


def set_paragraph_bottom_border(
    paragraph,
    color: RGBColor | str | None,
    *,
    size_eighth_points: int = 6,
    space_points: int = 2,
) -> None:
    """Apply or update a thin bottom paragraph border.

    Existing paragraph borders on other edges are preserved. ``size`` is in
    eighth-points as required by WordprocessingML.
    """

    rgb = _rgb_hex(color)
    if rgb is None:
        return

    properties = paragraph._p.get_or_add_pPr()
    border = properties.find(qn("w:pBdr"))
    if border is None:
        border = OxmlElement("w:pBdr")
        _insert_schema_ordered(properties, border, _PPR_AFTER_BORDER)

    bottom = border.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        _insert_schema_ordered(border, bottom, _PBDR_AFTER_BOTTOM)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(max(1, int(size_eighth_points))))
    bottom.set(qn("w:space"), str(max(0, int(space_points))))
    bottom.set(qn("w:color"), rgb)


def set_right_aligned_tab_stop(paragraph, usable_width_pt: float) -> None:
    """Place or update a right-aligned tab at the paragraph's usable edge."""

    if not math.isfinite(usable_width_pt) or usable_width_pt <= 0:
        return

    tab_stops = paragraph.paragraph_format.tab_stops
    for tab_stop in tab_stops:
        if abs(tab_stop.position.pt - usable_width_pt) < 0.01:
            tab_stop.alignment = WD_TAB_ALIGNMENT.RIGHT
            return
    tab_stops.add_tab_stop(Pt(usable_width_pt), WD_TAB_ALIGNMENT.RIGHT)


def _char_em_width(char: str, *, monospace: bool) -> float:
    """Return a conservative approximate advance width in ems."""

    if unicodedata.east_asian_width(char) in {"F", "W"}:
        return 1.0
    if monospace:
        return 0.64
    if char.isspace():
        return 0.37
    if char in "ilI|!.,:;'`":
        return 0.38
    if char in "MW@%&":
        return 0.88
    if char.isdigit():
        return 0.59
    if char.isupper():
        return 0.68
    if char.isalpha():
        return 0.59
    return 0.58


def _text_width_pt(
    text: str,
    font_size_pt: float,
    *,
    monospace: bool,
    bold: bool = False,
    italic: bool = False,
) -> float:
    """Estimate width without depending on fonts installed on this machine."""

    em_width = sum(_char_em_width(char, monospace=monospace) for char in text)
    emphasis_factor = (1.06 if bold else 1.0) * (1.03 if italic else 1.0)
    # A little headroom makes an under-estimate less likely across Word fonts.
    return em_width * font_size_pt * emphasis_factor * 1.08


def _field_width_pt(
    field: FieldBlock,
    base_font_size_pt: float,
    *,
    monospace: bool,
    font_size_resolver: Callable[[str | None], float | None] | None,
) -> float:
    width = 0.0
    default_bold = field.group == "header" and field.key not in {"date", "link"}
    for run in field.runs:
        style = run.style
        resolved_size = (
            font_size_resolver(style.font_size)
            if style is not None and style.font_size and font_size_resolver is not None
            else None
        )
        font_size = resolved_size or base_font_size_pt
        bold = default_bold
        italic = False
        if style is not None:
            if "bold" in style.model_fields_set:
                bold = style.bold
            else:
                bold = bold or style.bold
            italic = style.italic
        width += _text_width_pt(
            run.text,
            font_size,
            monospace=monospace,
            bold=bold,
            italic=italic,
        )
    return width


def row_can_use_right_aligned_tab(
    fields: Sequence[FieldBlock],
    usable_width_pt: float,
    *,
    base_font_size_pt: float = 11.0,
    font_family: str | None = None,
    font_size_resolver: Callable[[str | None], float | None] | None = None,
) -> bool:
    """Return whether a grouped row safely fits a right-aligned tab layout.

    A row is tabbed only when one simple right field is last in source order.
    Rich block content, multiple right fields, embedded line breaks, and rows
    whose approximate text widths compete for the usable line width use the
    stacked paragraph fallback. Styled runs and hyperlinks remain eligible;
    the caller should render them through its normal run path after the tab.
    """

    if not math.isfinite(usable_width_pt) or usable_width_pt <= 0 or len(fields) < 2:
        return False

    right_fields = [index for index, field in enumerate(fields) if field.align == "right"]
    if len(right_fields) != 1 or right_fields[0] != len(fields) - 1:
        return False
    if any(field.blocks or field.rich_text for field in fields):
        return False
    if any(
        any(char in run.text for char in "\r\n\t")
        for field in fields
        for run in field.runs
    ):
        return False

    right_field = fields[-1]
    left_fields = fields[:-1]
    if not any(run.text for field in left_fields for run in field.runs):
        return False

    font_size = max(1.0, base_font_size_pt)
    family = (font_family or "").lower()
    monospace = any(marker in family for marker in ("mono", "consolas", "courier"))
    left_width = sum(
        _field_width_pt(
            field,
            font_size,
            monospace=monospace,
            font_size_resolver=font_size_resolver,
        )
        for field in left_fields
    )
    # The fields in a row share a group, so use the same separator as the
    # renderer's existing text-only grouping for any additional left fields.
    if len(left_fields) > 1:
        separator = "  ·  " if left_fields[0].group == "contact" else (
            "  |  " if left_fields[0].group in {"header", "secondary"} else "  ·  "
        )
        left_width += (len(left_fields) - 1) * _text_width_pt(
            separator,
            font_size,
            monospace=monospace,
        )

    right_width = _field_width_pt(
        right_field,
        font_size,
        monospace=monospace,
        font_size_resolver=font_size_resolver,
    )
    min_gap = max(14.0, font_size * 1.5)
    return (
        left_width <= usable_width_pt * 0.70
        and right_width <= usable_width_pt * 0.40
        and left_width + right_width + min_gap <= usable_width_pt
    )


__all__ = [
    "row_can_use_right_aligned_tab",
    "set_paragraph_alignment",
    "set_paragraph_bottom_border",
    "set_paragraph_shading",
    "set_right_aligned_tab_stop",
]
