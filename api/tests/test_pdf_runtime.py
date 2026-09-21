"""The Playwright singleton must not cross async event-loop boundaries."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services.renderer import _pdf_runtime


def test_runtime_restarts_when_a_different_event_loop_owns_the_old_handles(monkeypatch):
    stale_browser = SimpleNamespace(is_connected=lambda: True)
    fresh_browser = SimpleNamespace(is_connected=lambda: True)
    launch_calls: list[dict[str, object]] = []

    class Chromium:
        async def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return fresh_browser

    fresh_playwright = SimpleNamespace(chromium=Chromium())

    async def start_playwright():
        return fresh_playwright

    monkeypatch.setattr(_pdf_runtime, "_browser", stale_browser)
    monkeypatch.setattr(_pdf_runtime, "_playwright", object())
    stopped_loop = SimpleNamespace(is_running=lambda: False)
    monkeypatch.setattr(_pdf_runtime, "_runtime_loop", stopped_loop)
    monkeypatch.setattr(_pdf_runtime, "_lock", None)
    monkeypatch.setattr(_pdf_runtime, "_start_playwright", start_playwright)

    async def get_browser():
        return await _pdf_runtime._get_browser()

    assert asyncio.run(get_browser()) is fresh_browser
    assert len(launch_calls) == 1
    assert launch_calls[0]["headless"] is True
