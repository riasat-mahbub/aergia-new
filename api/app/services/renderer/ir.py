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


def _normalize_manifest(manifest: dict) -> dict:
    """Normalize manifest to always have layout_config with zones/placement/rowHeights."""
    if "layout_config" in manifest:
        return manifest
    return {
        **manifest,
        "layout_config": {
            "zones": manifest.get("zones", []),
            "placement": manifest.get("placement", {}),
            "rowHeights": manifest.get("rowHeights", {}),
        },
    }


def _build_zone_styles(zone: dict) -> dict[str, str]:
    styles = zone.get("styles", {})
    normalized = {}
    for k, v in styles.items():
        if v:
            normalized[k] = v
    return normalized


def _group_instances_by_zone(
    instances: list[dict],
    layout_config: dict | None,
    zones: list[dict],
) -> dict[str, list[dict]]:
    if not layout_config or "placement" not in layout_config:
        raise ValueError("layout_config with placement is required")

    placement = layout_config["placement"]

    fallback_zone_id: str | None = None
    if zones:
        sorted_zones = sorted(zones, key=lambda z: (z.get("row", 0), z.get("id", "")))
        fallback_zone_id = sorted_zones[0].get("id", "")
        if not fallback_zone_id:
            fallback_zone_id = None

    groups: dict[str, list[dict]] = {}

    for instance in instances:
        if not instance.get("enabled", True):
            continue
        section_type = instance.get("type", "")
        if not section_type:
            raise ValueError("Section instance is missing 'type'")
        zone_id = placement.get(section_type)
        if not zone_id:
            if fallback_zone_id:
                zone_id = fallback_zone_id
            else:
                raise ValueError(f"No zone defined for section type '{section_type}' and no fallback zone available")
        if zone_id not in groups:
            groups[zone_id] = []
        groups[zone_id].append(instance)

    return groups


def _render_instance_panel(instance: dict) -> str:
    """Render a single section instance's content HTML (no heading/wrapper)."""
    if not instance.get("enabled", True):
        return ""
    section_type = instance.get("type", "")
    if not section_type:
        raise ValueError("Section instance is missing 'type'")
    section_data = instance.get("data")
    return render_section_preview(section_type, section_data)


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
    manifest = _normalize_manifest(manifest)
    layout_config = manifest["layout_config"]

    instances = cv_data.get("instances", [])

    default_customizations = {}
    for var in manifest.get("globalStyleSchema", []):
        default_customizations.setdefault(var["type"] + "s", {})[var["key"]] = var["default"]
    merged_customizations = _merge_customizations(default_customizations, customizations)

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
    css_vars = {k: v for k, v in css_vars.items() if v is not None}

    zones = manifest.get("zones", [])
    groups = _group_instances_by_zone(instances, layout_config, zones)
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
                    heading_style = "margin-bottom:8px;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#1f2937"
                    if heading_extra:
                        heading_style = f"{heading_style};{heading_extra}"
                    panels.append(SectionPanelIR(
                        type=instance.get("type", ""),
                        title=instance.get("title", SECTION_LABELS.get(instance.get("type", ""), instance.get("type", ""))),
                        html=panel_html,
                        wrapper_style=wrapper_style,
                        heading_style=heading_style,
                    ))

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
