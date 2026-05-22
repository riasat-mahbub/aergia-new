"""Certifications section renderer."""

from ._utils import esc


def _font_style(context: dict, kind: str) -> str:
    css_vars = context.get("css_vars") or {}
    key = "--heading-font" if kind == "heading" else "--body-font"
    font = context.get(f"{kind}_font") or css_vars.get(key)
    if not font:
        return ""
    return f"font-family:{font};"


def render_certifications(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:var(--text, #9ca3af);font-style:italic;">No data</p>'
    ctx = context or {}
    heading_font_style = _font_style(ctx, "heading")
    body_font_style = _font_style(ctx, "body")
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
            f"""<div>
  <h3 style="font-size:0.875rem;font-weight:600;color:var(--heading, #111827);{heading_font_style}">{esc(entry.get("name", ""))}</h3>
  <p style="font-size:0.75rem;color:var(--text, #6b7280);{body_font_style}">{issuer_date}</p>
  {cred_link}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:8px;">' + "".join(items) + "</div>"
