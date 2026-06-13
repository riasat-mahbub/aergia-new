"""Profile section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. The h2 name keeps no inline color (template --heading applies
via inheritance) and the contact separator stays a subtle divider color.
"""

from ._utils import esc, esc_attr, normalize_url_scheme

SECTION_LABELS = {
    "profile": "Profile",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "languages": "Languages",
    "certifications": "Certifications",
}


def render_profile(data: dict, context: dict | None = None) -> str:
    ctx = context or {}
    parts = []
    if data.get("photo_url"):
        parts.append(
            f'<img src="{data["photo_url"]}" alt="" '
            f'style="width:80px;height:80px;border-radius:9999px;object-fit:cover;'
            f'margin-bottom:12px;border:2px solid var(--accent, transparent);" />'
        )
    parts.append(
        f'<h2 class="f-name" style="margin:0;">'
        f'{esc(data.get("name")) or "Your Name"}</h2>'
    )
    parts.append(
        f'<p class="f-title" style="margin:0;">'
        f'{esc(data.get("title", ""))}</p>'
    )
    contact_items = []
    if data.get("email"):
        if data.get("email_link", True) is not False:
            contact_items.append(
                f'<a href="mailto:{esc_attr(data["email"])}" class="f-contact">'
                f'{esc(data["email"])}</a>'
            )
        else:
            contact_items.append(f'<span>{esc(data["email"])}</span>')
    if data.get("phone"):
        contact_items.append(f'<span>{esc(data["phone"])}</span>')
    if data.get("location"):
        contact_items.append(f'<span>{esc(data["location"])}</span>')
    if data.get("site_url"):
        site_text = data.get("site_text") or data["site_url"]
        # Normalize so Chromium emits a /Link annotation in PDF export —
        # a bare "rmahbub.com" would render visible text but no click target.
        site_href = esc_attr(normalize_url_scheme(data["site_url"]))
        contact_items.append(
            f'<a href="{site_href}" class="f-contact" '
            f'target="_blank" rel="noopener noreferrer">'
            f'{esc(site_text)}</a>'
        )
    if contact_items:
        sep = '<span style="margin:0 6px;color:var(--divider, #d1d5db)">·</span>'
        inner = sep.join(contact_items)
        parts.append(f'<div class="f-contact" style="margin-top:8px;">{inner}</div>')
    if data.get("summary"):
        parts.append(
            f'<p class="f-summary" style="margin-top:12px;margin-bottom:0;">'
            f'{esc(data["summary"])}</p>'
        )
    # Profile text is centered by default; an explicit per-section text_align
    # override (carried on the panel wrapper via context.instance_style) wins.
    text_align = "center"
    if (ctx.get("instance_style") or {}).get("text_align"):
        text_align = ""
    wrapper_attr = f' style="text-align:{text_align}"' if text_align else ""
    return f'<div class="profile-section"{wrapper_attr}>{"".join(parts)}</div>'
