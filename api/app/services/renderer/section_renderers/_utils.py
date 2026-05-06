"""Shared utilities for section renderers."""
import html


def esc(text: object) -> str:
    """Escape text for safe insertion into HTML (between tags, not inside attributes)."""
    if text is None:
        return ""
    return html.escape(str(text))
