"""Certifications section renderer."""

def render_certifications(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        issuer_date = entry.get("issuer", "")
        if entry.get("date"):
            issuer_date += f' · {entry["date"]}'
        cred_link = (
            f'<a href="{entry["credential_url"]}" style="font-size:0.75rem;color:#2563eb;">Credential</a>'
            if entry.get("credential_url")
            else ""
        )
        items.append(
            f"""<div>
  <h3 style="font-size:0.875rem;font-weight:600;">{entry.get("name", "")}</h3>
  <p style="font-size:0.75rem;color:#6b7280;">{issuer_date}</p>
  {cred_link}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:8px;">' + "".join(items) + "</div>"