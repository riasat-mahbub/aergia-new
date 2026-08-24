"""Shared utilities for AST builders.

Date formatters, URL-scheme normalisation, and the rich-text field block
converter. The date helpers are pure (no AST knowledge — they only
transform strings — so they live alongside the builders rather than
inside the renderer.

The :data:`DATE_STYLE_OPTIONS` list is the canonical preset table shared
with the frontend; each preset encodes its own ``range_sep`` so backend
and frontend cannot drift.
"""

from __future__ import annotations

from app.core.safe_url import normalize_url
from app.schema.models import DateStyle, FieldBlock, RichTextBlock, TextRun


def normalize_url_scheme(value: object) -> str:
    """Ensure ``value`` carries an absolute URL scheme.

    Chromium's print pipeline silently drops ``<a href>`` annotations when
    the href is missing a scheme (e.g. ``rmahbub.com`` is treated as a
    relative path against ``about:blank`` and never becomes a clickable
    ``/Link`` in the exported PDF). Always emit a scheme so the link
    survives both rendering and PDF export.

    - Empty / None / whitespace-only strings return ``""``.
    - Strings that already start with a scheme pass through unchanged.
    - Otherwise ``https://`` is prepended.
    """

    return normalize_url(value)



SHORT_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# Canonical list of date-format presets. Mirrors the dropdown in
# ``web/src/components/sections/DateField.tsx``.
DATE_STYLE_OPTIONS: list[tuple[str, str, str]] = [
    ("YYYY-MM", "YYYY-MM", " \u2013 "),
    ("YYYY/MM", "YYYY/MM", "/"),
    ("MM/YYYY", "MM/YYYY", "/"),
    ("MM-YYYY", "MM-YYYY", "-"),
    ("MM.YYYY", "MM.YYYY", "."),
    ("YYYY.MM", "YYYY.MM", "."),
    ("Mon YYYY", "Mon YYYY (e.g. Mar 2021)", " \u2013 "),
    ("Month YYYY", "Month YYYY (default; e.g. March 2021)", " \u2013 "),
    ("YYYY", "YYYY", " \u2013 "),
    ("Mon-YYYY", "Mon-YYYY (e.g. Mar-2021)", "-"),
]


def _style_dict(style: DateStyle | dict | None) -> dict | None:
    """Coerce a ``DateStyle`` or ``dict`` to a plain ``dict`` for the
    legacy formatter signature."""

    if style is None:
        return None
    if isinstance(style, dict):
        return style
    return style.model_dump()


def format_single_date(value: str | None, style: DateStyle | dict | None = None) -> str:
    """Format a single ``YYYY-MM`` date string for display using ``style``."""

    if not value:
        return ""
    style_dict = _style_dict(style)
    if not style_dict or not style_dict.get("key"):
        return value
    raw = str(value)
    parts = raw.split("-")
    if len(parts) != 2:
        return raw
    year_str, month_str = parts
    if not year_str or not month_str:
        return raw
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        return raw
    if month < 1 or month > 12:
        return raw
    yy = str(year)
    mm = f"{month:02d}"
    key = style_dict["key"]
    if key == "YYYY-MM":
        return f"{yy}-{mm}"
    if key == "YYYY/MM":
        return f"{yy}/{mm}"
    if key == "MM/YYYY":
        return f"{mm}/{yy}"
    if key == "MM-YYYY":
        return f"{mm}-{yy}"
    if key == "MM.YYYY":
        return f"{mm}.{yy}"
    if key == "YYYY.MM":
        return f"{yy}.{mm}"
    if key == "Mon YYYY":
        return f"{SHORT_MONTH_NAMES[month - 1]} {yy}"
    if key == "Month YYYY":
        return f"{MONTH_NAMES[month - 1]} {yy}"
    if key == "YYYY":
        return yy
    if key == "Mon-YYYY":
        return f"{SHORT_MONTH_NAMES[month - 1]}-{yy}"
    return raw


def format_date_range(
    start: str,
    end: str | None,
    current: bool,
    style: DateStyle | dict | None = None,
) -> str:
    """Format a date range for display."""

    if not start:
        return ""
    if current:
        return f"{format_single_date(start, style)} – Present"
    if not end:
        return format_single_date(start, style)
    a = format_single_date(start, style)
    b = format_single_date(end, style)
    style_dict = _style_dict(style)
    sep = style_dict["range_sep"] if style_dict and style_dict.get("range_sep") else " – "
    return f"{a}{sep}{b}"


def rich_text_to_field_block(
    key: str,
    value: list | str | None,
    *,
    group: str = "body",
) -> FieldBlock | None:
    """Convert a rich-text value (``RichTextBlock[]`` or legacy string) to a
    :class:`FieldBlock`.

    Returns ``None`` when the value is empty or absent.  For legacy plain
    strings the result is a single unstyled ``TextRun`` inside a paragraph
    block.  For ``RichTextBlock[]`` the ``blocks`` field is populated and
    ``runs`` carries flat text for backward compat — the renderer checks
    ``blocks`` first when present.
    """
    if value is None:
        return None

    # Legacy plain string
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return FieldBlock(
            key=key,
            runs=[TextRun(text=text)],
            group=group,
            blocks=[RichTextBlock(type="paragraph", items=[{"text": text}])],
            rich_text=True,
        )

    # RichTextBlock[] — validate and filter empty blocks
    if not isinstance(value, list):
        return None

    blocks: list[RichTextBlock] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        block = RichTextBlock.model_validate(raw)
        if block.items:
            blocks.append(block)

    if not blocks:
        return None

    # Build runs for backward compat (flat list of all text items)
    runs: list[TextRun] = []
    for block in blocks:
        for item in block.items:
            runs.append(TextRun(text=item.text, style=item.style))

    return FieldBlock(
        key=key,
        runs=runs,
        group=group,
        blocks=blocks,
        rich_text=True,
    )
