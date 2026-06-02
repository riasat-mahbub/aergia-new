"""Shared utilities for section renderers."""
import html


def esc(text: object) -> str:
    """Escape text for safe insertion into HTML (between tags, not inside attributes)."""
    if text is None:
        return ""
    return html.escape(str(text))


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
