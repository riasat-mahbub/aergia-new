"""Build intermediate representation (IR) from manifest + CV data."""

from .types import DocumentIR
from .section_renderers import render_section_preview
from .section_renderers import SECTION_LABELS


# Constants
PRINT_STYLES = """
  @page { size: A4; margin: 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def _build_zone_styles(zone: dict) -> dict[str, str]:
    """Extract and normalize zone styles."""
    styles = zone.get("styles", {})
    normalized = {}
    for k, v in styles.items():
        if v:
            normalized[k] = v
    return normalized


def _group_instances_by_zone(
    instances: list[dict],
    layout_config: dict | None,
    layout_template: str | None = None
) -> dict[str, list[dict]]:
    """Group section instances by their target zone."""
    if not layout_config or "placement" not in layout_config:
        # Smart default: scan template for zone placeholders
        if layout_template:
            import re
            matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', layout_template)
            zone_placeholders = set(matches)
            if "main" not in zone_placeholders and zone_placeholders:
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


def _render_instance_panel(instance: dict) -> str:
    """Render a single section instance to HTML panel."""
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


def build_ir(
    manifest: dict,
    cv_data: dict,
    customizations: dict
) -> DocumentIR:
    """Build DocumentIR from manifest, CV data, and customizations."""
    from .types import RowIR, ZoneIR, SectionPanelIR

    instances = cv_data.get("instances", [])
    layout_config = manifest.get("layout_config") or {}
    layout_template = manifest.get("layout_template")

    # Merge customizations with manifest defaults
    default_customizations = {}
    for var in manifest.get("globalStyleSchema", []):
        default_customizations.setdefault(var["type"] + "s", {})[var["key"]] = var["default"]
    merged_customizations = _merge_customizations(default_customizations, customizations)

    # Extract CSS variables
    colors = merged_customizations.get("colors", {})
    fonts = merged_customizations.get("fonts", {})
    spacing = merged_customizations.get("spacing", {})

    css_vars = {
        "--accent": colors.get("accent"),
        "--bg-sidebar": colors.get("bg_sidebar"),
        "--header": colors.get("header"),
        "--divider": colors.get("divider"),
        "--text": colors.get("text"),
        "--heading": colors.get("heading"),
        "--body-font": fonts.get("body"),
        "--heading-font": fonts.get("heading"),
        "--section-gap": spacing.get("section_gap"),
    }

    # Filter out None values
    css_vars = {k: v for k, v in css_vars.items() if v is not None}

    # Group instances by zone
    groups = _group_instances_by_zone(instances, layout_config, layout_template)

    # Build rows from manifest zones
    zones = manifest.get("zones", [])
    rows_dict: dict[int, list[dict]] = {}
    for zone in zones:
        row_num = zone.get("row", 0)
        if row_num not in rows_dict:
            rows_dict[row_num] = []
        rows_dict[row_num].append(zone)

    rows: list[RowIR] = []
    for row_num in sorted(rows_dict.keys()):
        row_zones = rows_dict[row_num]
        zone_irs: list[ZoneIR] = []

        for zone in row_zones:
            zone_id = zone.get("id", "")
            zone_instances = groups.get(zone_id, [])
            zone_styles = _build_zone_styles(zone)

            panels: list[SectionPanelIR] = []
            for instance in zone_instances:
                panel_html = _render_instance_panel(instance)
                if panel_html:
                    panels.append(SectionPanelIR(
                        type=instance.get("type", ""),
                        title=instance.get("title", SECTION_LABELS.get(instance.get("type", ""), instance.get("type", ""))),
                        html=panel_html,
                        wrapper_style="margin-bottom:24px",
                        heading_style="margin-bottom:8px;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#1f2937"
                    ))

            # Render assets assigned to this zone
            asset_items = manifest.get("asset_items", [])
            asset_placement = manifest.get("asset_placement", {})
            for asset in asset_items:
                if asset_placement.get(asset["id"]) == zone_id:
                    asset_html = (
                        f'<div style="margin-bottom:16px;text-align:center">'
                        f'<img src="{asset["data"]}" '
                        f'style="max-width:100%;height:auto;" '
                        f'alt="{asset["name"]}" />'
                        f'</div>'
                    )
                    panels.append(SectionPanelIR(
                        type="asset",
                        title=asset["name"],
                        html=asset_html,
                        wrapper_style="margin-bottom:16px",
                        heading_style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:#6b7280;margin-bottom:4px"
                    ))

            zone_irs.append(ZoneIR(
                id=zone_id,
                styles=zone_styles,
                panels=panels
            ))

        rows.append(RowIR(index=row_num, zones=zone_irs))

    return DocumentIR(
        rows=rows,
        css_vars=css_vars,
        print_styles=PRINT_STYLES,
        body_font=fonts.get("body", "system-ui, sans-serif"),
        heading_font=fonts.get("heading", fonts.get("body", "system-ui, sans-serif"))
    )