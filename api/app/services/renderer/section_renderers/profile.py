"""Profile section renderer."""

from ..section_renderers import SECTION_LABELS


def render_profile(data: dict) -> str:
    parts = []
    if data.get("photo_url"):
        parts.append(
            f'<img src="{data["photo_url"]}" alt="" style="width:80px;height:80px;border-radius:9999px;object-fit:cover;margin-bottom:12px;" />'
        )
    parts.append(f'<h2 style="font-size:1.25rem;font-weight:700;">{data.get("name") or "Your Name"}</h2>')
    parts.append(f'<p style="font-size:0.875rem;color:#6b7280;">{data.get("title", "")}</p>')
    contact = []
    if data.get("email"):
        contact.append(f"<p>{data['email']}</p>")
    if data.get("phone"):
        contact.append(f"<p>{data['phone']}</p>")
    if data.get("location"):
        contact.append(f"<p>{data['location']}</p>")
    if contact:
        parts.append(f'<div style="margin-top:8px;font-size:0.75rem;color:#9ca3af;">{"".join(contact)}</div>')
    if data.get("summary"):
        parts.append(f'<p style="margin-top:12px;font-size:0.875rem;color:#374151;">{data["summary"]}</p>')
    return "".join(parts)