"""Profile section renderer."""

from ._utils import esc

SECTION_LABELS = {
    "profile": "Profile",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "languages": "Languages",
    "certifications": "Certifications",
}


def _font_style(context: dict, kind: str) -> str:
    """Return an inline `font-family:...;` style when context provides a font override."""
    css_vars = context.get("css_vars") or {}
    key = "--heading-font" if kind == "heading" else "--body-font"
    font = context.get(f"{kind}_font") or css_vars.get(key)
    if not font:
        return ""
    return f"font-family:{font};"


def render_profile(data: dict, context: dict | None = None) -> str:
    ctx = context or {}
    css_vars = ctx.get("css_vars") or {}
    heading_font_style = _font_style(ctx, "heading")
    body_font_style = _font_style(ctx, "body")
    name_size = css_vars.get("--profile-name-size", "1.5rem")
    parts = []
    if data.get("photo_url"):
        parts.append(
            f'<img src="{data["photo_url"]}" alt="" '
            f'style="width:80px;height:80px;border-radius:9999px;object-fit:cover;'
            f'margin-bottom:12px;border:2px solid var(--accent, transparent);" />'
        )
    parts.append(
        f'<h2 style="font-size:{name_size};font-weight:700;'
        f'color:var(--heading, #111827);{heading_font_style}">'
        f'{esc(data.get("name")) or "Your Name"}</h2>'
    )
    parts.append(
        f'<p style="font-size:0.875rem;color:var(--accent, #2563eb);{body_font_style}">'
        f'{esc(data.get("title", ""))}</p>'
    )
    contact_items = []
    if data.get("email"):
        contact_items.append(f'<span>{esc(data["email"])}</span>')
    if data.get("phone"):
        contact_items.append(f'<span>{esc(data["phone"])}</span>')
    if data.get("location"):
        contact_items.append(f'<span>{esc(data["location"])}</span>')
    if contact_items:
        sep = '<span style="margin:0 6px;color:var(--divider, #d1d5db)">·</span>'
        inner = sep.join(contact_items)
        parts.append(
            f'<div style="margin-top:8px;font-size:0.75rem;'
            f'color:var(--text, #6b7280);{body_font_style}">{inner}</div>'
        )
    if data.get("summary"):
        parts.append(
            f'<p style="margin-top:12px;font-size:0.875rem;'
            f'color:var(--text, #374151);{body_font_style}">'
            f'{esc(data["summary"])}</p>'
        )
    return "".join(parts)
