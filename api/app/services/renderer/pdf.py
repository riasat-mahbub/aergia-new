"""PDF rendering entry point."""

from ..types import DocumentIR
from ..ir import build_ir
from .backends import get_backend


def ir_to_pdf(ir: DocumentIR) -> bytes:
    """Render DocumentIR to PDF bytes."""
    backend = get_backend("pdf")
    return backend.render(ir)


def render_pdf(
    manifest: dict,
    cv_data: dict,
    customizations: dict
) -> bytes:
    """Convenience function: build IR and render to PDF."""
    ir = build_ir(manifest, cv_data, customizations)
    return ir_to_pdf(ir)