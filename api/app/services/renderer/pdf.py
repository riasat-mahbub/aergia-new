"""PDF rendering entry point."""

from .types import DocumentIR
from .ir import build_ir
from .backends import get_backend


async def ir_to_pdf(ir: DocumentIR) -> bytes:
    """Render DocumentIR to PDF bytes (async)."""
    from .backends import PDFBackend
    backend = PDFBackend()
    return await backend.render_async(ir)


async def render_pdf(
    manifest: dict,
    cv_data: dict,
    customizations: dict
) -> bytes:
    """Convenience function: build IR and render to PDF (async)."""
    ir = build_ir(manifest, cv_data, customizations)
    return await ir_to_pdf(ir)


# Sync wrappers for backward compatibility
def ir_to_pdf_sync(ir: DocumentIR) -> bytes:
    """Sync wrapper for ir_to_pdf."""
    import asyncio
    return asyncio.run(ir_to_pdf(ir))


def render_pdf_sync(
    manifest: dict,
    cv_data: dict,
    customizations: dict
) -> bytes:
    """Sync wrapper for render_pdf."""
    import asyncio
    return asyncio.run(render_pdf(manifest, cv_data, customizations))