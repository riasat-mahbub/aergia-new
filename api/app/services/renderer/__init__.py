"""Renderer package - unified IR-based rendering pipeline."""

from .html import render_html
from .pdf import render_pdf, render_pdf_sync
from .ir import build_ir, AbstractRenderer
from .ir import _group_instances_by_zone, _render_instance_panel, _merge_customizations
from .section_renderers import render_section_preview

__all__ = [
    "build_ir",
    "render_html",
    "render_pdf",
    "render_pdf_sync",
    "AbstractRenderer",
    "_group_instances_by_zone",
    "_render_instance_panel",
    "_merge_customizations",
    "render_section_preview",
    "render_preview",
]


def render_preview(
    instances: list[dict],
    customizations: dict,
    layout_config: dict | None = None,
    default_customizations: dict | None = None,
    global_style_schema: list | None = None,
) -> str:
    """Render preview HTML using the IR-based pipeline."""
    lc = layout_config or {"zones": [], "placement": {}}
    manifest = {
        "layout_config": lc,
        "zones": lc.get("zones", []),
        "globalStyleSchema": global_style_schema or [],
        "default_customizations": default_customizations or {},
    }
    return render_html(manifest, {"instances": instances}, customizations)
