"""PDF backend using Playwright (async)."""

from . import RendererBackend
from ..types import DocumentIR
from .html import HTMLBackend


class PDFBackend(RendererBackend):
    """Renders DocumentIR to PDF via Playwright."""

    def __init__(self):
        self._html_backend = HTMLBackend()

    async def render_async(self, ir: DocumentIR) -> bytes:
        """Render IR to PDF bytes asynchronously."""
        # First render to HTML
        html = self._html_backend.render(ir)

        # Use Playwright to convert to PDF
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                print_background=True,
                prefer_css_page_size=True,
            )
            await browser.close()
            return pdf_bytes

    def render(self, ir: DocumentIR) -> bytes:
        """Sync wrapper for backward compatibility."""
        import asyncio
        return asyncio.run(self.render_async(ir))