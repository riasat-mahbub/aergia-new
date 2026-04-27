"""HTML preview renderer service — generates preview HTML matching frontend templates."""

from typing import Any

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


def _build_zone_styles(zone: dict) -> str:
    styles = zone.get("styles", {})
    if not styles:
        return ""
    return "".join(f"{k}:{v};" for k, v in styles.items())


def _extract_zone_placeholders(template: str) -> set[str]:
    """Extract all {{zone_id}} placeholders from a template string."""
    import re
    matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', template)
    return set(matches)


def _group_instances_by_zone(instances: list[dict], layout_config: dict | None, layout_template: str | None = None) -> dict[str, list[dict]]:
    """Group section instances by their target zone based on layout_config.placement.

    When no placement config is provided, infer defaults from the template:
    - Scan template for zone placeholders and assign sections accordingly
    - Fallback: put everything in "main"
    """
    if not layout_config or "placement" not in layout_config:
        # Smart default: scan template for known zone placeholders
        if layout_template:
            zone_placeholders = _extract_zone_placeholders(layout_template)
            if "main" not in zone_placeholders and zone_placeholders:
                # Template has zones but no "main" — assign first zone to all
                target_zone = next(iter(zone_placeholders))
                groups: dict[str, list[dict]] = {}
                for instance in instances:
                    if not instance.get("enabled", True):
                        continue
                    if target_zone not in groups:
                        groups[target_zone] = []
                    groups[target_zone].append(instance)
                return groups

        # Fallback: everything goes to "main"
        return {"main": [i for i in instances if i.get("enabled", True)]}

    placement = layout_config["placement"]
    groups: dict[str, list[dict]] = {}

    for instance in instances:
        if not instance.get("enabled", True):
            continue
        section_type = instance.get("type", "")
        zone_id = placement.get(section_type, "main")
        if zone_id not in groups:
            groups[zone_id] = []
        groups[zone_id].append(instance)

    return groups


def _render_zones(instances: list[dict], layout_config: dict | None) -> str:
    """Render all zones with their grouped section instances.

    Zones are grouped by their `row` value (default 0). Each row becomes
    a flex container with zones laid out horizontally. Rows stack vertically.
    """
    if not layout_config or "zones" not in layout_config:
        # Fallback: single main zone
        panels = []
        for instance in instances:
            panel = render_instance_panel(instance)
            if panel:
                panels.append(f'<div style="margin-bottom:24px;">{panel}</div>')
        return "".join(panels)

    zones = layout_config["zones"]
    groups = _group_instances_by_zone(instances, layout_config)

    # Group zones by row (default row 0)
    from collections import defaultdict
    rows: dict[int, list[dict]] = defaultdict(list)
    for zone in zones:
        row_num = zone.get("row", 0)
        rows[row_num].append(zone)

    rendered_rows = []
    row_heights = layout_config.get("rowHeights", {})
    for row_num in sorted(rows.keys()):
        row_zones = rows[row_num]
        rendered_zones = []
        for zone in row_zones:
            zone_id = zone.get("id", "")
            zone_instances = groups.get(zone_id, [])
            panels = "".join(
                f'<div style="margin-bottom:var(--section-gap, 24px);">{render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            zone_styles = _build_zone_styles(zone)
            rendered_zones.append(f'<div style="{zone_styles}">{panels}</div>')

        # Apply row height if configured, otherwise equal distribution via flex
        row_height_spec = row_heights.get(str(row_num))
        if row_height_spec:
            flex_val = f"{int(row_height_spec.replace('%', ''))} 0 0%"
        else:
            flex_val = "1 0 auto"
        rendered_rows.append(f'<div style="display:flex;flex:{flex_val};">{"".join(rendered_zones)}</div>')

    return "".join(rendered_rows)


def render_modern(instances: list[dict], customizations: dict, layout_config: dict | None = None) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    accent = colors.get("accent", "#2563eb")
    bg_sidebar = colors.get("bg_sidebar", "#f8fafc")
    body_font = fonts.get("body", "Inter, system-ui, sans-serif")
    heading_font = fonts.get("heading", "Inter, system-ui, sans-serif")

    # Use zone-based rendering if layout_config is provided
    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        sidebar = "".join(render_instance_panel(i) for i in instances if i.get("type") == "profile")
        main = "".join(render_instance_panel(i) for i in instances if i.get("type") != "profile")
        zones_html = f'<div style="width:30%;padding:24px;background-color:{bg_sidebar};">{sidebar}</div><div style="width:70%;padding:24px;"><div style="margin-bottom:24px;height:4px;width:64px;background-color:{accent};"></div>{main}</div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="min-height:297mm;display:flex;flex-direction:column;">{zones_html}</div>
</body></html>"""


def render_classic(instances: list[dict], customizations: dict, layout_config: dict | None = None) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    header_color = colors.get("header", "#000000")
    divider_color = colors.get("divider", "#d1d5db")
    body_font = fonts.get("body", "Georgia, Crimson, serif")
    heading_font = fonts.get("heading", "Georgia, Crimson, serif")
    section_gap = spacing.get("section_gap", "20px")

    # Use zone-based rendering if layout_config is provided
    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        panels = []
        for i, instance in enumerate(instances):
            panel = render_instance_panel(instance)
            if panel:
                panels.append(f'<div style="margin-bottom:{section_gap};">{panel}</div>')
                if i < len(instances) - 1:
                    panels.append(f'<hr style="border-color:{divider_color};margin:16px 0;" />')
        zones_html = f'<div style="padding:32px;">{"".join(panels)}</div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; color:{header_color}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="min-height:297mm;display:flex;flex-direction:column;">{zones_html}</div>
</body></html>"""


def render_minimal(instances: list[dict], customizations: dict, layout_config: dict | None = None) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    text_color = colors.get("text", "#374151")
    heading_color = colors.get("heading", "#111827")
    body_font = fonts.get("body", "system-ui, sans-serif")
    heading_font = fonts.get("heading", "system-ui, sans-serif")
    section_gap = spacing.get("section_gap", "16px")

    # Use zone-based rendering if layout_config is provided
    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        panels = "".join(
            f'<div style="margin-bottom:{section_gap};">{render_instance_panel(instance)}</div>'
            for instance in instances
        )
        zones_html = f'<div style="padding:32px;">{panels}</div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><style>
  body {{ margin:0; padding:0; font-family:{body_font}; color:{text_color}; }}
  h1,h2,h3,h4,h5,h6 {{ font-family:{heading_font}; color:{heading_color}; }}
  {PRINT_STYLES}
</style></head><body>
<div style="min-height:297mm;display:flex;flex-direction:column;">{zones_html}</div>
</body></html>"""


TEMPLATE_RENDERERS = {
    "generic-modern": render_modern,
    "generic-classic": render_classic,
    "generic-minimal": render_minimal,
}


def _substitute_css_vars(html: str, customizations: dict) -> str:
    """Replace CSS custom property placeholders with actual values from customizations."""
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})

    css_var_map = {
        "var(--accent)": colors.get("accent"),
        "var(--bg-sidebar)": colors.get("bg_sidebar"),
        "var(--header)": colors.get("header"),
        "var(--divider)": colors.get("divider"),
        "var(--text)": colors.get("text"),
        "var(--heading)": colors.get("heading"),
        "var(--body-font)": fonts.get("body"),
        "var(--heading-font)": fonts.get("heading"),
        "var(--section-gap)": spacing.get("section_gap"),
    }

    result = html
    for placeholder, value in css_var_map.items():
        if value is not None:
            result = result.replace(placeholder, value)

    return result


def render_user_template_unified(
    instances: list[dict],
    customizations: dict,
    layout_template: str,
    layout_config: dict | None = None,
    default_customizations: dict | None = None,
) -> str:
    """Render a user template using the zone-based system.

    Expects layout_template to be a full HTML document with bare {{zone_id}} placeholders,
    {{print_styles}}, {{body_font}}, {{heading_font}} placeholders.
    Returns a full HTML document with zones replaced and CSS vars substituted.
    """
    merged = _merge_customizations(default_customizations or {}, customizations)

    # Group instances by zone (pass template for smart zone detection)
    groups = _group_instances_by_zone(instances, layout_config, layout_template)

    # Track which zones got content so we can clean up unknown ones later
    populated_zone_ids: set[str] = set()

    html = layout_template

    # Iterate zones in layout_config order (not dict insertion order)
    # to ensure correct rendering sequence and that all defined zones are processed
    if layout_config and "zones" in layout_config:
        for zone in layout_config["zones"]:
            zone_id = zone.get("id", "")
            zone_instances = groups.get(zone_id, [])
            zone_styles = _build_zone_styles(zone)
            panels = "".join(
                f'<div style="margin-bottom:var(--section-gap, 24px);">{render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            html = html.replace(f"{{{{{zone_id}}}}}", f'<div style="{zone_styles}">{panels}</div>')
            populated_zone_ids.add(zone_id)
    else:
        for zone_id, zone_instances in groups.items():
            panels = "".join(
                f'<div style="margin-bottom:var(--section-gap, 24px);">{render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            html = html.replace(f"{{{{{zone_id}}}}}", panels)
            populated_zone_ids.add(zone_id)

    # Scan the original template for all {{...}} placeholders
    all_template_placeholders = _extract_zone_placeholders(layout_template)

    # Replace unknown zone placeholders with empty strings, but preserve data variables (e.g., {{name}})
    html = _replace_unknown_zones(html, layout_config, populated_zone_ids, all_template_placeholders)

    html = _substitute_css_vars(html, merged)

    print_styles = """
  @page { size: A4; margin: 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""

    fonts = merged.get("fonts", {})
    body_font = fonts.get("body", "system-ui, sans-serif")
    heading_font = fonts.get("heading", body_font)

    html = html.replace("{{print_styles}}", print_styles)
    html = html.replace("{{body_font}}", body_font)
    html = html.replace("{{heading_font}}", heading_font)

    return html


def _replace_unknown_zones(html: str, layout_config: dict | None, populated_zone_ids: set[str] | None = None, all_placeholders: set[str] | None = None) -> str:
    """Replace any {{zone_id}} placeholders that don't have corresponding instances with empty string.

    When all_placeholders is provided (from render_user_template_unified), only replace placeholders
    that look like zone IDs (present in populated_zone_ids or layout_config zones). Data variables
    like {{name}} are left intact since they appear in the template but aren't zone markers.

    A placeholder is treated as a zone ID if it matches common zone naming patterns:
    - It's in populated_zone_ids (it was a real zone)
    - It's in layout_config zones (it was defined but had no instances)
    - It looks like a zone name (main, sidebar, left, right, col, panel, zone, area)
    """
    import re
    placeholder_pattern = r'\{\{([a-zA-Z0-9_-]+)\}\}'

    defined_zone_ids = set()
    if layout_config and "zones" in layout_config:
        defined_zone_ids = {z.get("id") for z in layout_config["zones"] if isinstance(z, dict)}

    if populated_zone_ids is not None:
        # Called from render_user_template_unified — distinguish zones from data variables
        known_zones = set(populated_zone_ids)  # zones that got content

        def replace_placeholder(match):
            zone_id = match.group(1)
            # Keep it if it was populated
            if zone_id in known_zones:
                return match.group(0)
            # Keep it if it's defined in layout_config zones (even if empty)
            if zone_id in defined_zone_ids:
                return match.group(0)
            # Check if it's a data variable (not a zone-like name)
            if all_placeholders and zone_id not in all_placeholders:
                return match.group(0)
            # Heuristic: if the placeholder looks like a zone name, replace with empty
            zone_name_patterns = {"main", "sidebar", "header", "left", "right", "center",
                                  "col", "panel", "zone", "area", "top", "bottom", "nav",
                                  "footer", "foot", "aside", "primary", "secondary"}
            if zone_id in zone_name_patterns or any(zone_id.endswith(suffix) for suffix in ["-col", "-zone", "-panel"]):
                return ""
            # Otherwise leave it (likely a data variable like {{name}}, {{company}}, etc.)
            return match.group(0)

        html = re.sub(placeholder_pattern, replace_placeholder, html)
    elif layout_config and "zones" in layout_config:
        # Legacy path: use zones defined in layout_config.zones
        zones = layout_config["zones"]
        zone_ids = {z.get("id") for z in zones if isinstance(z, dict)}

        def replace_placeholder(match):
            zone_id = match.group(1)
            return "" if zone_id not in zone_ids else match.group(0)
        html = re.sub(placeholder_pattern, replace_placeholder, html)
    else:
        # No layout_config and no populated zones — nothing to replace; leave all placeholders as-is
        pass

    return html


def _merge_customizations(defaults: dict, overrides: dict) -> dict:
    """Deep merge overrides on top of defaults."""
    merged = {}
    for key in defaults:
        if key in overrides:
            if isinstance(defaults[key], dict) and isinstance(overrides[key], dict):
                merged[key] = {**defaults[key], **overrides[key]}
            else:
                merged[key] = overrides[key]
        else:
            merged[key] = defaults[key]
    for key in overrides:
        if key not in merged:
            merged[key] = overrides[key]
    return merged


def render_preview(
    instances: list[dict],
    customizations: dict,
    template_id: str,
    template_content: str | None = None,
    layout_template: str | None = None,
    layout_config: dict | None = None,
    default_customizations: dict | None = None,
) -> str:
    if layout_template is not None:
        return render_user_template_unified(
            instances, customizations, layout_template, layout_config, default_customizations
        )
    renderer = TEMPLATE_RENDERERS.get(template_id, render_modern)
    return renderer(instances, customizations, layout_config)
