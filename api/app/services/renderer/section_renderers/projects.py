"""Projects section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. Hyperlinks keep the template accent color for affordance.
"""

from ._utils import esc, esc_attr, format_date_range, normalize_url_scheme


def render_projects(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    instance_style = (context or {}).get("instance_style") or {}
    subsection_gap = instance_style.get("subsection_gap") or css_vars.get("--subsection-gap", "16px")
    date_style = (context or {}).get("instance_style", {}).get("date_style")
    items = []
    for i, entry in enumerate(data):
        tech_items = ""
        if entry.get("tech_stack"):
            tech_items = '<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">' + "".join(
                f'<span class="f-tech" style="display:inline-block;background:#eff6ff;padding:2px 6px;border-radius:4px;color:#1d4ed8;">{esc(t)}</span>'
                for t in entry["tech_stack"]
            ) + "</div>"
        url = entry.get("url") or ""
        link_text = entry.get("link_text") or url
        # Normalize so Chromium emits a /Link annotation in the exported PDF —
        # a bare domain like "example.com" would render visible text but the
        # printed PDF would carry no clickable /Link annotation.
        url_href = esc_attr(normalize_url_scheme(url))
        url_link = (
            f'<a href="{url_href}" class="f-url" target="_blank" rel="noopener noreferrer" '
            f'style="flex-shrink:0;white-space:nowrap;">{esc(link_text)}'
            f'<span aria-hidden="true"> \u2197</span></a>'
            if url else ""
        )
        date_range = format_date_range(
            entry.get("start_date", ""),
            entry.get("end_date"),
            False,
            date_style,
        )
        items.append(
            f'''<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
    <div>
      <h3 class="f-name" style="margin:0;">{esc(entry.get("name", ""))}</h3>
      {f'<p class="f-description" style="margin-top:4px;margin-bottom:0;">{esc(entry["description"])}</p>' if entry.get("description") else ""}
      {tech_items}
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px;flex-shrink:0;">
      {url_link}
      <p class="f-date" style="margin:0;font-size:0.75rem;opacity:0.75;white-space:nowrap;">{esc(date_range)}</p>
    </div>
  </div>
</div>'''
        )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">' + "".join(items) + "</div>"
