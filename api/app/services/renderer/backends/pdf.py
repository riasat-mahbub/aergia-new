"""PDF backend using Playwright."""

from . import RendererBackend
from ..types import DocumentIR
from ..html import ir_to_html


class PDFBackend(RendererBackend):
    """Renders DocumentIR to PDF via Playwright."""

    def __init__(self):
        self._html_backend = None

    def _get_html_backend(self):
        if self._html_backend is None:
            from ..html import HTMLBackend
            self._html_backend = HTMLBackend()
        return self._html_backend

    def render(self, ir: DocumentIR) -> bytes:
        """Render IR to PDF bytes."""
        # First render to HTML
        html = self._get_html_backend().render(ir)
        
        # Use Playwright to convert to PDF
        from playwright.async_api import async_playwright
        import asyncio

        async def _generate_pdf() -> bytes:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(html, wait_until="networkidle")
                pdf_bytes = await page.pdf(
                    format="A4",
                    margin={"top": 0, "bottom": 0, "left": 0, "right": 0},
                    print_background=True,
                    prefer_css_page_size=True,
                )
                await browser.close()
                return pdf_bytes

        return asyncio.run(_generate_pdf())