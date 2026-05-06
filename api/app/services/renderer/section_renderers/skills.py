"""Skills section renderer."""

from ._utils import esc


def render_skills(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for group in data:
        skill_items = "".join(
            f'<span style="display:inline-block;background:#f3f4f6;padding:2px 8px;border-radius:4px;font-size:0.75rem;color:#374151;">{esc(item)}</span>'
            for item in group.get("items", [])
        )
        items.append(
            f"""<div>
  <h3 style="font-size:0.875rem;font-weight:600;">{esc(group.get("category", ""))}</h3>
  <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">{skill_items}</div>
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"
