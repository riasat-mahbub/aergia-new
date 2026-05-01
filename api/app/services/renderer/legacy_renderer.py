"""Legacy renderer for backward compatibility with old system templates."""

from typing import Any
from .ir import _group_instances_by_zone, _render_instance_panel, _merge_customizations
from .section_renderers import render_section_preview

SECTION_LABELS = {
    "profile": "Profile",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "languages": "Languages",
    "certifications": "Certifications",
}

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
    import re
    matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', template)
    return set(matches)

def _replace_unknown_zones(html: str, layout_config: dict | None, populated_zone_ids: set[str] | None = None, all_placeholders: set[str] | None = None) -> str:
    import re
    placeholder_pattern = r'\{\{([a-zA-Z0-9_-]+)\}\}'

    defined_zone_ids = set()
    if layout_config and "zones" in layout_config:
        defined_zone_ids = {z.get("id") for z in layout_config["zones"] if isinstance(z, dict)}

    if populated_zone_ids is not None:
        known_zones = set(populated_zone_ids)

        def replace_placeholder(match):
            zone_id = match.group(1)
            if zone_id in known_zones:
                return match.group(0)
            if zone_id in defined_zone_ids:
                return match.group(0)
            if all_placeholders and zone_id not in all_placeholders:
                return match.group(0)
            zone_name_patterns = {"main", "sidebar", "header", "left", "right", "center",
                                  "col", "panel", "zone", "area", "top", "bottom", "nav",
                                  "footer", "foot", "aside", "primary", "secondary"}
            if zone_id in zone_name_patterns or any(zone_id.endswith(suffix) for suffix in ["-col", "-zone", "-panel"]):
                return ""
            return match.group(0)

        html = re.sub(placeholder_pattern, replace_placeholder, html)
    elif layout_config and "zones" in layout_config:
        zones = layout_config["zones"]
        zone_ids = {z.get("id") for z in zones if isinstance(z, dict)}

        def replace_placeholder(match):
            zone_id = match.group(1)
            return "" if zone_id not in zone_ids else match.group(0)
        html = re.sub(placeholder_pattern, replace_placeholder, html)
    else:
        pass

    return html


def _substitute_css_vars(html: str, customizations: dict) -> str:
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


def _render_zones(instances: list[dict], layout_config: dict | None) -> str:
    if not layout_config or "zones" not in layout_config:
        panels = []
        for instance in instances:
            panel = _render_instance_panel(instance)
            if panel:
                panels.append(f'<div style="margin-bottom:24px;">{panel}</div>')
        return "".join(panels)

    zones = layout_config["zones"]
    groups = _group_instances_by_zone(instances, layout_config)

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
                f'<div style="margin-bottom:var(--section-gap, 24px);">{_render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            zone_styles = _build_zone_styles(zone)
            rendered_zones.append(f'<div style="{zone_styles}">{panels}</div>')

        row_height_spec = row_heights.get(str(row_num))
        if row_height_spec:
            flex_val = f"{int(row_height_spec.replace('%', ''))} 0 0%"
        else:
            flex_val = "1 0 auto"
        rendered_rows.append(f'<div style="display:flex;flex:{flex_val};">{"".join(rendered_zones)}</div>')

    return "".join(rendered_rows)


def _render_instance_panel(instance: dict) -> str:
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


def render_modern(instances: list[dict], customizations: dict, layout_config: dict | None = None) -> str:
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    accent = colors.get("accent", "#2563eb")
    bg_sidebar = colors.get("bg_sidebar", "#f8fafc")
    body_font = fonts.get("body", "Inter, system-ui, sans-serif")
    heading_font = fonts.get("heading", "Inter, system-ui, sans-serif")

    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        sidebar = "".join(_render_instance_panel(i) for i in instances if i.get("type") == "profile")
        main = "".join(_render_instance_panel(i) for i in instances if i.get("type") != "profile")
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

    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        panels = []
        for i, instance in enumerate(instances):
            panel = _render_instance_panel(instance)
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

    if layout_config:
        zones_html = _render_zones(instances, layout_config)
    else:
        panels = "".join(
            f'<div style="margin-bottom:{section_gap};">{_render_instance_panel(instance)}</div>'
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


def render_user_template_unified(
    instances: list[dict],
    customizations: dict,
    layout_template: str,
    layout_config: dict | None = None,
    default_customizations: dict | None = None,
) -> str:
    merged = _merge_customizations(default_customizations or {}, customizations)

    groups = _group_instances_by_zone(instances, layout_config, layout_template)

    populated_zone_ids: set[str] = set()

    html = layout_template

    if layout_config and "zones" in layout_config:
        for zone in layout_config["zones"]:
            zone_id = zone.get("id", "")
            zone_instances = groups.get(zone_id, [])
            zone_styles = _build_zone_styles(zone)
            panels = "".join(
                f'<div style="margin-bottom:var(--section-gap, 24px);">{_render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            html = html.replace(f"{{{{{zone_id}}}}}", f'<div style="{zone_styles}">{panels}</div>')
            populated_zone_ids.add(zone_id)
    else:
        for zone_id, zone_instances in groups.items():
            panels = "".join(
                f'<div style="margin-bottom:var(--section-gap, 24px);">{_render_instance_panel(i)}</div>'
                for i in zone_instances
            )
            html = html.replace(f"{{{{{zone_id}}}}}", panels)
            populated_zone_ids.add(zone_id)

    all_template_placeholders = _extract_zone_placeholders(layout_template)

    html = _replace_unknown_zones(html, layout_config, populated_zone_ids, all_template_placeholders)

    html = _substitute_css_vars(html, merged)

    print_styles = PRINT_STYLES

    fonts = merged.get("fonts", {})
    body_font = fonts.get("body", "system-ui, sans-serif")
    heading_font = fonts.get("heading", body_font)

    html = html.replace("{{print_styles}}", print_styles)
    html = html.replace("{{body_font}}", body_font)
    html = html.replace("{{heading_font}}", heading_font)

    return html


def _extract_zone_placeholders(template: str) -> set[str]:
    import re
    matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', template)
    return set(matches)


def _substitute_css_vars(html: str, customizations: dict) -> str:
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


def render_legacy_preview(
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