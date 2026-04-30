"""HTML rendering entry point."""

from ..types import DocumentIR
from ..ir import build_ir
from .backends import get_backend, RendererBackend


def ir_to_html(ir: DocumentIR) -> str:
    """Render DocumentIR to HTML string."""
    backend = get_backend("html")
    return backend.render(ir)


def render_html(
    manifest: dict,
    cv_data: dict,
    customizations: dict
) -> str:
    """Convenience function: build IR and render to HTML."""
    ir = build_ir(manifest, cv_data, customizations)
    return ir_to_html(ir)