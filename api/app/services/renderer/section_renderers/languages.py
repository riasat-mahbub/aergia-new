"""Languages section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both.
"""

from ._utils import esc

def render_languages(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    subsection_gap = css_vars.get("--subsection-gap", "4px")
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span class="f-language">{esc(e.get("language", ""))}</span>'
        f'<span class="f-proficiency">{esc(e.get("proficiency", ""))}</span>'
        f'</div>'
        for e in data
    )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">{items}</div>'
