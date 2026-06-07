"""Skills section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. Skill chips are subtle grey-on-grey to keep the focus on
the category and the per-section text color.
"""

from ._utils import esc


def render_skills(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    subsection_gap = css_vars.get("--subsection-gap", "12px")
    items = []
    for group in data:
        skill_items = "".join(
            f'<span class="f-tag" style="display:inline-block;background:#f3f4f6;padding:2px 8px;border-radius:4px;'
            f'">{esc(item)}</span>'
            for item in group.get("items", [])
        )
        items.append(
            f'''<div>
  <h3 class="f-category" style="margin:0;">{esc(group.get("category", ""))}</h3>
  <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">{skill_items}</div>
</div>'''
        )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">' + "".join(items) + "</div>"
