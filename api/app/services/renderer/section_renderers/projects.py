"""Projects section renderer."""

from ._utils import esc


def _font_style(context: dict, kind: str) -> str:
    css_vars = context.get("css_vars") or {}
    key = "--heading-font" if kind == "heading" else "--body-font"
    font = context.get(f"{kind}_font") or css_vars.get(key)
    if not font:
        return ""
    return f"font-family:{font};"


def render_projects(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:var(--text, #9ca3af);font-style:italic;">No data</p>'
    ctx = context or {}
    heading_font_style = _font_style(ctx, "heading")
    body_font_style = _font_style(ctx, "body")
    items = []
    for entry in data:
        tech_items = ""
        if entry.get("tech_stack"):
            tech_items = '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + "".join(
                f'<span style="display:inline-block;background:#eff6ff;padding:2px 6px;border-radius:4px;'
                f'font-size:0.75rem;color:#1d4ed8;{body_font_style}">{esc(t)}</span>'
                for t in entry["tech_stack"]
            ) + "</div>"
        url_link = (
            f'<a href="{entry["url"]}" style="font-size:0.75rem;color:var(--accent, #2563eb);">'
            f'{esc(entry["url"])}</a>' if entry.get("url") else ""
        )
        items.append(
            f"""<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;color:var(--heading, #111827);{heading_font_style}">{esc(entry.get("name", ""))}</h3>
      {url_link}
    </div>
    <p style="font-size:0.75rem;color:var(--text, #9ca3af);{body_font_style}">{esc(entry.get("start_date", ""))} &ndash; {esc(entry.get("end_date") or "Present")}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;color:var(--text, #374151);{body_font_style}">{esc(entry["description"])}</p>' if entry.get("description") else ""}
  {tech_items}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:16px;">' + "".join(items) + "</div>"
