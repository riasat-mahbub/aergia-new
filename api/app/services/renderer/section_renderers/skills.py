"""Skills section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. Skill chips are subtle grey-on-grey to keep the focus on
the category and the per-section text color.
"""

from ._utils import esc


def render_skills(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    items = []
    for group in data:
        skill_items = "".join(
            f'<span style="display:inline-block;background:#f3f4f6;padding:2px 8px;border-radius:4px;'
            f'font-size:0.75rem;">{esc(item)}</span>'
            for item in group.get("items", [])
        )
        items.append(
            f'''<div>
  <h3 style="font-size:0.875rem;font-weight:600;margin:0;">{esc(group.get("category", ""))}</h3>
  <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">{skill_items}</div>
</div>'''
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"
