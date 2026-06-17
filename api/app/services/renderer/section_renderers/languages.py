"""Languages section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both.
"""

from ._utils import esc

def render_languages(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    instance_style = (context or {}).get("instance_style") or {}
    subsection_gap = instance_style.get("subsection_gap") or css_vars.get("--subsection-gap", "4px")
    items = "".join(
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        + '"><span class="f-language">' + esc(e.get("language", "")) + '</span>'
        + '<span class="f-proficiency">' + esc(e.get("proficiency", "")) + '</span>'
        + '</div>'
        for i, e in enumerate(data)
    )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">{items}</div>'
