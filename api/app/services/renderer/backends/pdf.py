"""PDF backend — renders DocumentIR to PDF via Playwright (singleton browser)."""

import asyncio
from typing import TYPE_CHECKING

from ..ir import AbstractRenderer, build_ir
from ..types import DocumentIR
from .html import HTMLBackend

if TYPE_CHECKING:
    from playwright.async_api import Browser


_browser: "Browser | None" = None
_playwright: "object | None" = None


async def _get_browser() -> "Browser":
    """Return a singleton browser instance, launching it once."""
    global _browser, _playwright
    from playwright.async_api import async_playwright

    if _browser is None or not _browser.is_connected():
        if _playwright is None:
            _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
    return _browser


async def _close_browser():
    """Close the singleton browser (call on app shutdown)."""
    global _browser, _playwright
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


class PDFBackend(AbstractRenderer):

    async def render_async(self, manifest: dict, cv_data: dict, customizations: dict) -> bytes:
        ir = build_ir(manifest, cv_data, customizations)
        return await self._format(ir)

    async def _format(self, ir: DocumentIR) -> bytes:
        html = HTMLBackend()._format(ir)
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            await page.set_content(html, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                print_background=True,
                prefer_css_page_size=True,
            )
            return pdf_bytes
        finally:
            await page.close()

    def render(self, manifest: dict, cv_data: dict, customizations: dict) -> bytes:
        return asyncio.run(self.render_async(manifest, cv_data, customizations))
