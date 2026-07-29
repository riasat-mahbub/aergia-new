"""Playwright runtime for HTML → PDF conversion.

This module owns the singleton Chromium instance used by the PDF renderer.
The browser is launched lazily on the first request and closed on app
shutdown (call :func:`close_browser` from the FastAPI lifespan event).

The browser is private to the renderer package — no other module should
launch a second browser.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser


_browser: "Browser | None" = None
_playwright: "object | None" = None
_lock: asyncio.Lock | None = None


# Chromium's print engine turns real <a href> elements into clickable PDF
# link annotations. The PDF is a static document: links are replaced with
# non-clickable spans so the exported file carries no link annotations.
# The inline style (if any) is preserved; the text and the .f-link arrow
# are unchanged. The href attribute is dropped with the anchor tag.
_ANCHOR_OPEN_RE = re.compile(r"<a\b", re.IGNORECASE)
_ANCHOR_CLOSE_RE = re.compile(r"</a\b", re.IGNORECASE)
_HREF_ATTR_RE = re.compile(r'\s*href\s*=\s*"[^"]*"', re.IGNORECASE)


def strip_anchor_markup(html: str) -> str:
    """Replace every anchor with a plain span, killing PDF link annotations.

    The renderer emits only anchors with an ``href``; after the conversion
    no ``href`` attribute remains anywhere in the document.
    """

    html = _ANCHOR_OPEN_RE.sub("<span", html)
    html = _ANCHOR_CLOSE_RE.sub("</span", html)
    return _HREF_ATTR_RE.sub("", html)


async def _get_browser() -> "Browser":
    """Return a singleton browser instance, launching it once."""

    global _browser, _playwright, _lock
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        from playwright.async_api import async_playwright

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


async def close_browser() -> None:
    """Close the singleton browser. Call on app shutdown."""

    global _browser, _playwright
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


async def html_to_pdf(html: str) -> bytes:
    """Render ``html`` to a PDF byte string via Chromium."""

    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.set_content(strip_anchor_markup(html), wait_until="networkidle")
        return await page.pdf(
            format="A4",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            print_background=True,
            prefer_css_page_size=True,
        )
    finally:
        await page.close()
