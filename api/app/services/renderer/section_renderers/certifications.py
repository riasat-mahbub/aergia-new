"""Certifications section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. The credential link keeps the template accent color for
affordance.
"""

from ._utils import esc


def render_certifications(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    items = []
    for entry in data:
        issuer_date = esc(entry.get("issuer", ""))
        if entry.get("date"):
            issuer_date += f' · {esc(entry["date"])}'
        cred_link = (
            f'<a href="{entry["credential_url"]}" style="font-size:0.75rem;color:var(--accent, #2563eb);">Credential</a>'
            if entry.get("credential_url")
            else ""
        )
        items.append(
            f'''<div>
  <h3 style="font-size:0.875rem;font-weight:600;margin:0;">{esc(entry.get("name", ""))}</h3>
  <p style="font-size:0.75rem;margin:0;">{issuer_date}</p>
  {cred_link}
</div>'''
        )
    return '<div style="display:flex;flex-direction:column;gap:8px;">' + "".join(items) + "</div>"
