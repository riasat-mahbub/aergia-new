"""Diagnose Chromium, Aergia rendering, and pdfplumber recovery in order."""

from __future__ import annotations

import asyncio
import json
from typing import Any


_CHROMIUM_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
_SENTINEL = "Aergia PDF text recovery sentinel"


def _minimal_render_source():
    from app.document_schema.models import Customizations, TemplateManifest
    from app.services.renderer import prepare_render_source

    manifest = TemplateManifest.model_validate(
        {
            "manifest_version": 2,
            "name": "PDF smoke diagnostic",
            "zones": [
                {"id": "sidebar", "styles": {"width": "narrow"}},
                {"id": "main", "styles": {"width": "full"}},
            ],
            "placement": {"profile": "sidebar", "experience": "main"},
            "layout_defaults": {"spacing": "comfortable"},
            "policy_overrides": {"by_type": {}},
            "global_styles": {
                "accent_color": "#2563eb",
                "body_font": "sans-serif",
                "heading_font": "sans-serif",
            },
        }
    )
    sections = [
        {
            "id": "smoke-profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Aergia PDF Smoke", "title": "Diagnostic", "email": "smoke@example.invalid"},
        },
        {
            "id": "smoke-experience",
            "type": "experience",
            "title": "Experience",
            "enabled": True,
            "data": [
                {
                    "id": "smoke-entry",
                    "position": "PDF diagnostic",
                    "company": "Aergia",
                    "description": _SENTINEL,
                }
            ],
        },
    ]
    return prepare_render_source(sections, manifest, Customizations())


def _failure(exc: Exception) -> dict[str, str]:
    lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
    root_cause = next(
        (line for line in reversed(lines) if "FATAL:" in line or "Operation not permitted" in line),
        lines[0] if lines else type(exc).__name__,
    )
    return {"status": "fail", "error_type": type(exc).__name__, "detail": root_cause[:400]}


async def run_pdf_smoke() -> dict[str, Any]:
    """Return stage-specific runtime diagnostics without exposing document text."""

    from playwright.async_api import async_playwright

    from app.scanner.pdf_recovery import PDF_WORKER_TIMEOUT_SECONDS
    from app.services.parser._extract_pdfplumber import extract_with_pdfplumber
    from app.services.renderer import render_source_pdf
    from app.services.renderer._pdf_runtime import close_browser

    report: dict[str, Any] = {
        "stages": {
            "playwright_driver": {"status": "not_run"},
            "chromium_launch": {"status": "not_run"},
            "aergia_render": {"status": "not_run"},
            "pdfplumber_recovery": {"status": "not_run"},
        },
        "overall": "fail",
    }

    playwright = None
    browser = None
    try:
        try:
            playwright = await async_playwright().start()
            report["stages"]["playwright_driver"] = {"status": "pass"}
        except Exception as exc:  # noqa: BLE001 - diagnostic reports the failing stage
            report["stages"]["playwright_driver"] = _failure(exc)
            return report

        try:
            browser = await asyncio.wait_for(
                playwright.chromium.launch(headless=True, args=_CHROMIUM_ARGS),
                timeout=PDF_WORKER_TIMEOUT_SECONDS,
            )
            report["stages"]["chromium_launch"] = {"status": "pass"}
        except Exception as exc:  # noqa: BLE001 - diagnostic reports the failing stage
            report["stages"]["chromium_launch"] = _failure(exc)
            return report
        finally:
            if browser is not None:
                await browser.close()
                browser = None
            if playwright is not None:
                await playwright.stop()
                playwright = None

        try:
            await close_browser()
            pdf_bytes = await asyncio.wait_for(
                render_source_pdf(_minimal_render_source()),
                timeout=PDF_WORKER_TIMEOUT_SECONDS,
            )
            report["stages"]["aergia_render"] = {
                "status": "pass",
                "pdf_bytes": len(pdf_bytes),
                "pdf_signature_valid": pdf_bytes.startswith(b"%PDF"),
            }
        except Exception as exc:  # noqa: BLE001 - diagnostic reports the failing stage
            report["stages"]["aergia_render"] = _failure(exc)
            return report
        finally:
            await close_browser()

        try:
            extracted = await asyncio.to_thread(extract_with_pdfplumber, pdf_bytes)
            sentinel_recovered = _SENTINEL in extracted.plain_text
            report["stages"]["pdfplumber_recovery"] = {
                "status": "pass" if sentinel_recovered else "fail",
                "page_count": extracted.page_count,
                "sentinel_recovered": sentinel_recovered,
                "recovered_character_count": len(extracted.plain_text),
            }
        except Exception as exc:  # noqa: BLE001 - diagnostic reports the failing stage
            report["stages"]["pdfplumber_recovery"] = _failure(exc)

        report["overall"] = (
            "pass"
            if all(stage["status"] == "pass" for stage in report["stages"].values())
            else "fail"
        )
        return report
    finally:
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()
        await close_browser()


def main() -> None:
    report = asyncio.run(run_pdf_smoke())
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["overall"] == "pass" else 1)


if __name__ == "__main__":
    main()
