"""PDF backend — renders DocumentIR to PDF via Playwright."""

import asyncio

from ..ir import AbstractRenderer, build_ir
from ..types import DocumentIR
from .html import HTMLBackend


class PDFBackend(AbstractRenderer):
    """Renders DocumentIR to PDF via Playwright.
    
    Extends AbstractRenderer for the Template Method pattern.
    Overrides _format with async version for Playwright.
    """

    async def render_async(self, manifest: dict, cv_data: dict, customizations: dict) -> bytes:
        """Full pipeline: build IR then render to PDF (async)."""
        ir = build_ir(manifest, cv_data, customizations)
        return await self._format(ir)

    async def _format(self, ir: DocumentIR) -> bytes:
        """Render IR to PDF bytes asynchronously."""
        html = HTMLBackend()._format(ir)

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

    def render(self, manifest: dict, cv_data: dict, customizations: dict) -> bytes:
        """Sync wrapper."""
        return asyncio.run(self.render_async(manifest, cv_data, customizations))
