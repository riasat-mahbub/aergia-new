"""Projects section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. Hyperlinks keep the template accent color for affordance.
"""

from ._utils import esc, format_date_range


def render_projects(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    items = []
    for entry in data:
        tech_items = ""
        if entry.get("tech_stack"):
            tech_items = '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + "".join(
                f'<span style="display:inline-block;background:#eff6ff;padding:2px 6px;border-radius:4px;'
                f'font-size:0.75rem;color:#1d4ed8;">{esc(t)}</span>'
                for t in entry["tech_stack"]
            ) + "</div>"
        url = entry.get("url") or ""
        link_text = entry.get("link_text") or url
        url_link = (
            f'<a href="{esc(url)}" style="font-size:0.75rem;color:var(--accent, #2563eb);">'
            f'{esc(link_text)}</a>' if url else ""
        )
        date_range = format_date_range(
            entry.get("start_date", ""),
            entry.get("end_date"),
            False,
        )
        items.append(
            f'''<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;margin:0;">{esc(entry.get("name", ""))}</h3>
      {url_link}
    </div>
    <p style="font-size:0.75rem;margin:0;">{esc(date_range)}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;margin-bottom:0;">{esc(entry["description"])}</p>' if entry.get("description") else ""}
  {tech_items}
</div>'''
        )
    return '<div style="display:flex;flex-direction:column;gap:16px;">' + "".join(items) + "</div>"
