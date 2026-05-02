"""PDF rendering entry point."""

from .backends.pdf import PDFBackend


async def render_pdf(manifest: dict, cv_data: dict, customizations: dict) -> bytes:
    """Build IR and render to PDF (async)."""
    backend = PDFBackend()
    return await backend.render_async(manifest, cv_data, customizations)


def render_pdf_sync(manifest: dict, cv_data: dict, customizations: dict) -> bytes:
    """Sync wrapper for render_pdf."""
    return PDFBackend().render(manifest, cv_data, customizations)
