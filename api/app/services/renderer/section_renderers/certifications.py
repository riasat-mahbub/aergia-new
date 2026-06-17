"""Certifications section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. The credential link keeps the template accent color for
affordance.
"""

from ._utils import esc, esc_attr, format_single_date, normalize_url_scheme


def render_certifications(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    instance_style = (context or {}).get("instance_style") or {}
    subsection_gap = instance_style.get("subsection_gap") or css_vars.get("--subsection-gap", "8px")
    date_style = (context or {}).get("instance_style", {}).get("date_style")
    items = []
    for i, entry in enumerate(data):
        issuer = esc(entry.get("issuer", ""))
        formatted_date = format_single_date(entry.get("date", ""), date_style)
        cred_link = (
            f'<a href="{esc_attr(normalize_url_scheme(entry["credential_url"]))}" '
            f'class="f-url">Credential</a>'
            if entry.get("credential_url")
            else ""
        )
        date_paragraph = (
            f'<p class="f-date" style="margin:2px 0 0;font-size:0.75rem;opacity:0.75;">{esc(formatted_date)}</p>'
            if formatted_date
            else ""
        )
        items.append(
            f'''<div>
  <h3 class="f-name" style="margin:0;">{esc(entry.get("name", ""))}</h3>
  <p class="f-meta" style="margin:0;">{issuer}</p>
  {date_paragraph}
  {cred_link}
</div>'''
        )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">' + "".join(items) + "</div>"
