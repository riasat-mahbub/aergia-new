"""Renderer package - unified IR-based rendering pipeline."""

from .ir import build_ir
from .html import ir_to_html, render_html
from .pdf import ir_to_pdf, render_pdf, render_pdf_sync
from .ir import _group_instances_by_zone, _render_instance_panel, _merge_customizations
from .section_renderers import render_section_preview

__all__ = [
    "build_ir",
    "ir_to_html",
    "ir_to_pdf",
    "render_html",
    "render_pdf",
    "render_pdf_sync",
    "_group_instances_by_zone",
    "_render_instance_panel",
    "_merge_customizations",
    "render_section_preview",
    "render_preview",
]

def render_preview(
    instances: list[dict],
    customizations: dict,
    template_id: str,
    template_content: str | None = None,
    layout_template: str | None = None,
    layout_config: dict | None = None,
    default_customizations: dict | None = None,
) -> str:
    """Legacy compatibility wrapper for the old render_preview function.
    
    This routes to the new unified renderer. If layout_template is provided,
    it uses the user template path. Otherwise, it falls back to the old
    template_id-based renderers (which now use the new IR pipeline).
    """
    if layout_template is not None:
        # User template path - use the manifest-based renderer
        # Build a minimal manifest from the provided data
        manifest = {
            "zones": layout_config.get("zones", []) if layout_config else [],
            "placement": layout_config.get("placement", {}) if layout_config else {},
            "globalStyleSchema": [],
            "default_customizations": default_customizations or {},
        }
        return render_html(manifest, {"instances": instances}, customizations)
    
    # System template path - for now, fall back to old behavior
    # In the future, system templates will also use manifests
    from .legacy_renderer import render_legacy_preview
    return render_legacy_preview(
        instances, customizations, template_id, template_content, layout_template, layout_config, default_customizations
    )