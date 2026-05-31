"""Intermediate representation builder and abstract renderer blueprint."""

from abc import ABC, abstractmethod
from .types import DocumentIR, RowIR, ZoneIR, SectionPanelIR
from .section_renderers import render_section_preview, SECTION_LABELS


PRINT_STYLES = """
  @page { size: A4; margin: 0; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    img { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
"""


def _build_zone_styles(zone: dict) -> dict[str, str]:
    styles = zone.get("styles", {})
    normalized = {}
    for k, v in styles.items():
        if v:
            normalized[k] = v
    return normalized


def _get_fallback_zone_id(zones: list[dict]) -> str | None:
    """Get the first zone's ID to use as fallback."""
    if not zones:
        return None
    sorted_zones = sorted(zones, key=lambda z: (z.get("row", 0), z.get("id", "")))
    return sorted_zones[0].get("id") or None


def _resolve_zone_id(placement: dict, instance: dict, fallback_zone_id: str | None) -> str:
    """Resolve zone ID for an instance, with fallback chain."""
    zone_id = placement.get(instance.get("id", ""))
    if zone_id:
        return zone_id
    zone_id = placement.get(instance.get("type", ""))
    if zone_id:
        return zone_id
    if fallback_zone_id:
        return fallback_zone_id
    raise ValueError(f"No zone defined for section type '{instance.get('type', '')}' and no fallback zone available")


def _group_instances_by_zone(
    instances: list[dict],
    layout_config: dict | None,
    zones: list[dict],
) -> dict[str, list[dict]]:
    if not layout_config or "placement" not in layout_config:
        raise ValueError("layout_config with placement is required")

    fallback_zone_id = _get_fallback_zone_id(zones)
    placement = layout_config["placement"]

    groups: dict[str, list[dict]] = {}
    for instance in instances:
        if not instance.get("enabled", True):
            continue
        if not instance.get("type"):
            raise ValueError("Section instance is missing 'type'")
        zone_id = _resolve_zone_id(placement, instance, fallback_zone_id)
        groups.setdefault(zone_id, []).append(instance)

    return groups


def _compute_row_flex_value(row_num: int, row_heights: dict) -> str:
    """Compute flex shorthand for a row based on rowHeights config."""
    height = row_heights.get(str(row_num)) or row_heights.get(row_num)
    if height:
        try:
            pct = int(str(height).replace("%", ""))
            if pct > 0:
                return f"{pct} 0 0%"
        except (ValueError, AttributeError):
            pass
    return "0 0 auto"


def _render_instance_panel(instance: dict, context: dict | None = None) -> str:
    """Render a single section instance's content HTML (no heading/wrapper)."""
    if not instance.get("enabled", True):
        return ""
    section_type = instance.get("type", "")
    if not section_type:
        raise ValueError("Section instance is missing 'type'")
    section_data = instance.get("data")
    return render_section_preview(section_type, section_data, context)

def _build_section_panel(instance: dict, context: dict | None = None) -> SectionPanelIR:
    """Build a SectionPanelIR from an instance, applying per-instance style overrides."""
    panel_html = _render_instance_panel(instance, context)
    if not panel_html:
        return None

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

    wrapper_style = "margin-bottom:24px"
    if wrapper_extra:
        wrapper_style = f"{wrapper_style};{wrapper_extra}"

    # The section heading sits in the wrapper; use template --heading so it follows
    # the template palette by default, then layer the per-instance override on top.
    heading_style = (
        "margin-bottom:8px;font-size:1rem;font-weight:700;"
        "text-transform:uppercase;letter-spacing:0.05em;"
        "color:var(--heading, #1f2937)"
    )
    if heading_extra:
        heading_style = f"{heading_style};{heading_extra}"

    section_type = instance.get("type", "")
    title = instance.get("title", SECTION_LABELS.get(section_type, section_type))
    return SectionPanelIR(
        type=section_type,
        title=title,
        html=panel_html,
        wrapper_style=wrapper_style,
        heading_style=heading_style,
    )


def _build_asset_panels(manifest: dict, zone_id: str) -> list[SectionPanelIR]:
    """Build SectionPanelIR entries for assets assigned to this zone."""
    panels = []
    for asset in manifest.get("asset_items", []):
        if manifest.get("asset_placement", {}).get(asset["id"]) != zone_id:
            continue
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
    return panels


def _build_css_vars(manifest: dict, customizations: dict) -> dict[str, str]:
    """Build resolved CSS variable map from manifest schema + user customizations."""
    default_customizations = {}
    schema = manifest.get("globalStyleSchema") or manifest.get("global_style_schema", [])
    for var in schema:
        default_customizations.setdefault(var["type"] + "s", {})[var["key"]] = var["default"]
    merged = _merge_customizations(default_customizations, customizations)

    colors = merged.get("colors", {})
    fonts = merged.get("fonts", {})
    # Lengths may arrive under either `spacing` (the user-facing default_customizations
    # convention) or `lengths` (the schema-derived default bucket). Merge both so the
    # same default_customizations shape survives an in-place seed without diverging.
    spacing = {**(merged.get("spacing") or {}), **(merged.get("lengths") or {})}

    all_vars = {
        "--accent": colors.get("accent"),
        "--bg-sidebar": colors.get("bg_sidebar"),
        "--header": colors.get("header"),
        "--divider": colors.get("divider"),
        "--text": colors.get("text"),
        "--heading": colors.get("heading"),
        "--body-font": fonts.get("body"),
        "--heading-font": fonts.get("heading"),
        "--section-gap": spacing.get("section_gap"),
        "--profile-name-size": spacing.get("profile_name_size"),
    }
    return {k: v for k, v in all_vars.items() if v is not None}


def _build_rows(
    manifest: dict,
    zones: list[dict],
    groups: dict[str, list[dict]],
    row_heights: dict,
    context: dict | None = None,
) -> list[RowIR]:
    """Build RowIR list from zone definitions and grouped instances."""
    rows_dict: dict[int, list[dict]] = {}
    for zone in zones:
        r = zone.get("row", 0)
        rows_dict.setdefault(r, []).append(zone)

    rows: list[RowIR] = []
    for row_num in sorted(rows_dict.keys()):
        row_zones = rows_dict[row_num]
        flex_value = _compute_row_flex_value(row_num, row_heights)
        zone_irs: list[ZoneIR] = []

        for zone in row_zones:
            zone_id = zone.get("id", "")
            zone_instances = groups.get(zone_id, [])
            zone_styles = _build_zone_styles(zone)

            panels: list[SectionPanelIR] = []
            for instance in zone_instances:
                panel = _build_section_panel(instance, context)
                if panel:
                    panels.append(panel)

            panels.extend(_build_asset_panels(manifest, zone_id))

            zone_irs.append(ZoneIR(id=zone_id, styles=zone_styles, panels=panels))

        rows.append(RowIR(index=row_num, zones=zone_irs, flex_value=flex_value))

    return rows
def _merge_customizations(defaults: dict, overrides: dict) -> dict:
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
    layout_config = manifest.get("layout_config") or {"zones": [], "placement": {}}

    instances = cv_data.get("instances", [])
    css_vars = _build_css_vars(manifest, customizations)
    fonts = css_vars.get("--body-font", "system-ui, sans-serif")

    # Build the render context that section renderers consult for template-aware styling.
    context = {
        "body_font": fonts,
        "heading_font": css_vars.get("--heading-font", fonts),
        "css_vars": css_vars,
    }

    zones = layout_config.get("zones") or manifest.get("zones", [])
    row_heights = layout_config.get("rowHeights", {})
    groups = _group_instances_by_zone(instances, layout_config, zones)
    rows = _build_rows(manifest, zones, groups, row_heights, context)
    return DocumentIR(
        rows=rows,
        css_vars=css_vars,
        print_styles=PRINT_STYLES,
        body_font=fonts,
        heading_font=css_vars.get("--heading-font", fonts),
    )


class AbstractRenderer(ABC):
    """Template Method: build_ir then _format.

    Subclasses override _format() to produce the target output format.
    The template method render() calls build_ir() then _format().
    """

    def render(self, manifest: dict, cv_data: dict, customizations: dict):
        ir = build_ir(manifest, cv_data, customizations)
        return self._format(ir)

    @abstractmethod
    def _format(self, ir: DocumentIR):
        pass
