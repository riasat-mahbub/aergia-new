"""Projects section renderer."""


def render_projects(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        tech_items = ""
        if entry.get("tech_stack"):
            tech_items = '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + "".join(
                f'<span style="display:inline-block;background:#eff6ff;padding:2px 6px;border-radius:4px;font-size:0.75rem;color:#1d4ed8;">{t}</span>'
                for t in entry["tech_stack"]
            ) + "</div>"
        url_link = f'<a href="{entry["url"]}" style="font-size:0.75rem;color:#2563eb;">{entry["url"]}</a>' if entry.get("url") else ""
        items.append(
            f"""<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;">{entry.get("name", "")}</h3>
      {url_link}
    </div>
    <p style="font-size:0.75rem;color:#9ca3af;">{entry.get("start_date", "")} &ndash; {entry.get("end_date") or "Present"}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;color:#374151;">{entry["description"]}</p>' if entry.get("description") else ""}
  {tech_items}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"