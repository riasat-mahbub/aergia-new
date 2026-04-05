"""HTML preview renderer service — generates preview HTML matching frontend templates."""

from typing import Any
import json

SECTION_LABELS = {
    "profile": "Profile",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "languages": "Languages",
    "certifications": "Certifications",
}


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


def render_experience(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        end = "Present" if entry.get("current") else (entry.get("end_date") or "")
        loc = f', {entry["location"]}' if entry.get("location") else ""
        items.append(
            f"""<div style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;">{entry.get("position", "")}</h3>
      <p style="font-size:0.875rem;color:#6b7280;">{entry.get("company", "")}{loc}</p>
    </div>
    <p style="font-size:0.75rem;color:#9ca3af;">{entry.get("start_date", "")} &ndash; {end}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;color:#374151;">{entry["description"]}</p>' if entry.get("description") else ""}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:16px;">' + "".join(items) + "</div>"


def render_education(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        end = "Present" if entry.get("current") else (entry.get("end_date") or "")
        gpa = f' | GPA: {entry["gpa"]}' if entry.get("gpa") else ""
        items.append(
            f"""<div>
  <h3 style="font-weight:600;">{entry.get("degree", "")}</h3>
  <p style="font-size:0.875rem;color:#6b7280;">{entry.get("institution", "")}</p>
  <p style="font-size:0.75rem;color:#9ca3af;">{entry.get("start_date", "")} &ndash; {end}{gpa}</p>
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"


def render_skills(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for group in data:
        skill_items = "".join(
            f'<span style="display:inline-block;background:#f3f4f6;padding:2px 8px;border-radius:4px;font-size:0.75rem;color:#374151;">{item}</span>'
            for item in group.get("items", [])
        )
        items.append(
            f"""<div>
  <h3 style="font-size:0.875rem;font-weight:600;">{group.get("category", "")}</h3>
  <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">{skill_items}</div>
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"


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


def render_languages(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.875rem;"><span>{e.get("language", "")}</span><span style="font-size:0.75rem;color:#9ca3af;">{e.get("proficiency", "")}</span></div>'
        for e in data
    )
    return f'<div style="display:flex;flex-direction:column;gap:4px;">{items}</div>'


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


SECTION_RENDERERS = {
    "profile": render_profile,
    "experience": render_experience,
    "education": render_education,
    "skills": render_skills,
    "projects": render_projects,
    "languages": render_languages,
    "certifications": render_certifications,
}


def render_section_preview(section_type: str, data: Any) -> str:
    renderer = SECTION_RENDERERS.get(section_type)
    if not renderer:
        return ""
    return renderer(data)


def render_instance_panel(instance: dict) -> str:
    if not instance.get("enabled", True):
        return ""
    section_type = instance.get("type", "")
    label = instance.get("title", SECTION_LABELS.get(section_type, section_type))
    section_data = instance.get("data")
    content = render_section_preview(section_type, section_data)
    if not content:
        content = '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'

    per_style = instance.get("style") or {}
    wrapper_extra = ""
    heading_extra = ""
    if per_style.get("font"):
        wrapper_extra += f"font-family:{per_style['font']};"
    if per_style.get("color"):
        wrapper_extra += f"color:{per_style['color']};"
        heading_extra += f"color:{per_style['color']};"
    if per_style.get("weight"):
        heading_extra += f"font-weight:{per_style['weight']};"

    base_wrapper = "margin-bottom:24px"
    wrapper_style = f"{base_wrapper};{wrapper_extra}" if wrapper_extra else base_wrapper
    base_heading = "margin-bottom:8px;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#1f2937"
    heading_style = f"{base_heading};{heading_extra}" if heading_extra else base_heading

    return f"""<div style="{wrapper_style}">
  <h2 style="{heading_style}">{label}</h2>
  {content}
</div>"""


PRINT_STYLES = """
  @page { size: A4; margin: 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def render_modern(instances: list[dict], customizations: dict) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    accent = colors.get("accent", "#2563eb")
    bg_sidebar = colors.get("bg_sidebar", "#f8fafc")
    body_font = fonts.get("body", "Inter, system-ui, sans-serif")
    heading_font = fonts.get("heading", "Inter, system-ui, sans-serif")
    section_gap = spacing.get("section_gap", "24px")

    sidebar = "".join(render_instance_panel(i) for i in instances if i.get("type") == "profile")
    main = "".join(render_instance_panel(i) for i in instances if i.get("type") != "profile")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="display:flex;min-height:297mm;">
  <div style="width:30%;padding:24px;background-color:{bg_sidebar};">
    {sidebar}
  </div>
  <div style="width:70%;padding:24px;">
    <div style="margin-bottom:24px;height:4px;width:64px;background-color:{accent};"></div>
    <div style="display:flex;flex-direction:column;gap:{section_gap};">{main}</div>
  </div>
</div>
</body></html>"""


def render_classic(instances: list[dict], customizations: dict) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    header_color = colors.get("header", "#000000")
    divider_color = colors.get("divider", "#d1d5db")
    body_font = fonts.get("body", "Georgia, Crimson, serif")
    heading_font = fonts.get("heading", "Georgia, Crimson, serif")
    section_gap = spacing.get("section_gap", "20px")

    panels = []
    for i, instance in enumerate(instances):
        panel = render_instance_panel(instance)
        if panel:
            panels.append(f'<div style="margin-bottom:{section_gap};">{panel}</div>')
            if i < len(instances) - 1:
                panels.append(f'<hr style="border-color:{divider_color};margin:16px 0;" />')

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; color:{header_color}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="padding:32px;">{"".join(panels)}</div>
</body></html>"""


def render_minimal(instances: list[dict], customizations: dict) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    text_color = colors.get("text", "#374151")
    heading_color = colors.get("heading", "#111827")
    body_font = fonts.get("body", "system-ui, sans-serif")
    heading_font = fonts.get("heading", "system-ui, sans-serif")
    section_gap = spacing.get("section_gap", "16px")

    panels = "".join(
        f'<div style="margin-bottom:{section_gap};">{render_instance_panel(instance)}</div>'
        for instance in instances
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; color:{text_color}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; color:{heading_color}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="padding:32px;">{panels}</div>
</body></html>"""


TEMPLATE_RENDERERS = {
    "generic-modern": render_modern,
    "generic-classic": render_classic,
    "generic-minimal": render_minimal,
}


def render_user_template(instances: list[dict], customizations: dict, template_content: str) -> str:
    """Inject CV data into user template HTML."""
    data_script = f"""<script>
window.__CV_DATA__ = {json.dumps({"instances": instances})};
</script>"""
    return data_script + "\n" + template_content


def render_preview(instances: list[dict], customizations: dict, template_id: str, template_content: str = None) -> str:
    if template_id.startswith("user_") and template_content:
        return render_user_template(instances, customizations, template_content)
    renderer = TEMPLATE_RENDERERS.get(template_id, render_modern)
    return renderer(instances, customizations)
