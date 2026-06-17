"""Shared utilities for section renderers."""
import html
import re


_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def normalize_url_scheme(value: object) -> str:
    """Ensure ``value`` carries an absolute URL scheme.

    Chromium's print pipeline silently drops ``<a href>`` annotations when the
    href is missing a scheme (e.g. ``rmahbub.com`` is treated as a relative
    path against ``about:blank`` and never becomes a clickable ``/Link`` in
    the exported PDF). Always emit a scheme so the link survives both
    rendering and PDF export.

    - Empty / None / whitespace-only strings return unchanged so the caller
      can still treat them as "no link".
    - Strings that already start with a scheme (``http://``, ``https://``,
      ``mailto:``, ``tel:``, etc.) pass through unchanged.
    - Otherwise ``https://`` is prepended.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if _URL_SCHEME_RE.match(s):
        return s
    return f"https://{s}"


def esc(text: object) -> str:
    """Escape text for safe insertion into HTML (between tags, not inside attributes)."""
    if text is None:
        return ""
    return html.escape(str(text))


def esc_attr(text: object) -> str:
    """Escape text for safe insertion into a double-quoted HTML attribute value."""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)



SHORT_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# Canonical list of date-format presets. The dropdown in the per-section
# Customize panel is exactly this list — no separate format + separator UI.
# Each preset encodes its own `range_sep` so backend and frontend cannot drift.
DATE_STYLE_OPTIONS: list[tuple[str, str, str]] = [
    ("YYYY-MM", "YYYY-MM (default)", " \u2013 "),  # " – " (space + en-dash + space)
    ("YYYY/MM", "YYYY/MM", "/"),
    ("MM/YYYY", "MM/YYYY", "/"),
    ("MM-YYYY", "MM-YYYY", "-"),
    ("MM.YYYY", "MM.YYYY", "."),
    ("YYYY.MM", "YYYY.MM", "."),
    ("Mon YYYY", "Mon YYYY (e.g. Mar 2021)", " \u2013 "),
    ("Month YYYY", "Month YYYY (e.g. March 2021)", " \u2013 "),
    ("YYYY", "YYYY", " \u2013 "),
    ("Mon-YYYY", "Mon-YYYY (e.g. Mar-2021)", "-"),
]


def format_single_date(value: str | None, style: dict | None = None) -> str:
    """Format a single "YYYY-MM" date string for display using the given style.

    Mirrors the TypeScript `formatSingleDate` helper in
    web/src/lib/sections/DateField.tsx. ``style`` is a dict with keys
    ``"key"`` and ``"range_sep"`` (the same shape ``DATE_STYLE_OPTIONS``
    encodes).

    - Empty input → ""
    - Unparseable input (legacy year-only "2020", out-of-range months) → raw value
    - Unset/empty style → raw value
    - Otherwise switches on style["key"]
    """
    if not value:
        return ""
    if not style or not style.get("key"):
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
    key = style["key"]
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
    style: dict | None = None,
) -> str:
    """Format a date range for display.

    Mirrors the TypeScript `formatDateRange` helper used by the preview
    renderers in web/src/lib/sections/DateField.tsx.

    - Empty start → ""
    - Empty end + current=false → just "start"
    - Empty end + current=true → "start – Present"
    - Both set → "start – end"
    - current=True takes precedence over any end value
    - When `style` is set, each bound is first reformatted via
      format_single_date and the range is joined with `style["range_sep"]`.
      The default behavior (no style) is unchanged.
    """
    if not start:
        return ""
    if current:
        return f"{format_single_date(start, style)} – Present"
    if not end:
        return format_single_date(start, style)
    a = format_single_date(start, style)
    b = format_single_date(end, style)
    sep = style["range_sep"] if style and style.get("range_sep") else " – "
    return f"{a}{sep}{b}"
