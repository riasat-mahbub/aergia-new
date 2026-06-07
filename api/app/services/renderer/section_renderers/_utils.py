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



def format_date_range(start: str, end: str | None, current: bool) -> str:
    """Format a date range for display.

    Mirrors the TypeScript `formatDateRange` helper used by the preview
    renderers in web/src/lib/sections/DateField.tsx.

    - Empty start → ""
    - Empty end + current=false → just "start"
    - Empty end + current=true → "start – Present"
    - Both set → "start – end"
    - current=True takes precedence over any end value
    """
    if not start:
        return ""
    if current:
        return f"{start} – Present"
    if not end:
        return start
    return f"{start} – {end}"
