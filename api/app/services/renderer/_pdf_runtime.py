"""Playwright runtime for HTML → PDF conversion.

This module owns the singleton Chromium instance used by the PDF renderer.
The browser is launched lazily on the first request and closed on app
shutdown (call :func:`close_browser` from the FastAPI lifespan event).

The browser is private to the renderer package — no other module should
launch a second browser.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser


_browser: "Browser | None" = None
_playwright: "object | None" = None
_lock: asyncio.Lock | None = None
_runtime_loop: asyncio.AbstractEventLoop | None = None


def _bind_runtime_to_current_loop() -> None:
    """Discard Playwright handles left by a different, closed event loop.

    Playwright's async transport is owned by the loop that started it. A
    module-level browser can otherwise look connected after a test runner or
    command has closed that loop, then fail later when ``new_page`` uses the
    closed transport. The production server keeps one loop for its lifetime;
    this guard also makes the renderer safe across sequential ``asyncio.run``
    invocations.
    """

    global _browser, _playwright, _lock, _runtime_loop
    loop = asyncio.get_running_loop()
    if _runtime_loop is loop:
        return
    if _runtime_loop is not None and _runtime_loop.is_running():
        raise RuntimeError("The PDF renderer cannot share a Playwright runtime across active event loops")

    # Handles from another loop cannot be awaited safely here. Once that loop
    # has stopped, discard its handles and start a fresh runtime for this loop
    # instead of returning a stale browser object.
    _browser = None
    _playwright = None
    _lock = asyncio.Lock()
    _runtime_loop = loop


async def _start_playwright() -> object:
    from playwright.async_api import async_playwright

    return await async_playwright().start()


async def _get_browser() -> "Browser":
    """Return a singleton browser instance, launching it once."""

    global _browser, _playwright, _lock
    _bind_runtime_to_current_loop()
    if _lock is None:  # Defensive; loop binding normally creates the lock.
        _lock = asyncio.Lock()
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        if _playwright is None:
            _playwright = await _start_playwright()
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
    _bind_runtime_to_current_loop()
    browser, playwright = _browser, _playwright
    _browser = None
    _playwright = None
    try:
        if browser is not None:
            await browser.close()
    finally:
        if playwright is not None:
            await playwright.stop()


async def html_to_pdf(html: str) -> bytes:
    """Render ``html`` to a PDF byte string via Chromium."""

    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.set_content(html, wait_until="networkidle")
        return await page.pdf(
            format="A4",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            print_background=True,
            prefer_css_page_size=True,
        )
    finally:
        await page.close()
