"""Languages section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both.
"""

from ._utils import esc


def render_languages(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'font-size:0.875rem;">'
        f'<span>{esc(e.get("language", ""))}</span>'
        f'<span style="font-size:0.75rem;">{esc(e.get("proficiency", ""))}</span>'
        f'</div>'
        for e in data
    )
    return f'<div style="display:flex;flex-direction:column;gap:4px;">{items}</div>'
