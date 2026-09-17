"""Seed a fictional showcase account through Aergia's public API."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.async_api import APIRequestContext, APIResponse, Playwright, async_playwright

from .config import ShowcaseConfig


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Runtime identifiers needed by the browser storyboard."""

    email: str
    password: str
    authored_cv_id: str
    application_id: str
    generated_cv_id: str
    source_pdf: Path


async def _response_json(response: APIResponse, action: str) -> Any:
    if not response.ok:
        body = (await response.text()).strip().replace("\n", " ")
        # Keep failures useful without echoing request data or credentials.
        raise RuntimeError(f"{action} failed with HTTP {response.status}: {body[:300]}")
    body = await response.text()
    return json.loads(body) if body.strip() else None


async def _post_json(
    request: APIRequestContext,
    path: str,
    payload: dict[str, Any],
    action: str,
    *,
    timeout: float = 30_000,
) -> Any:
    response = await request.post(path, data=payload, timeout=timeout)
    return await _response_json(response, action)


async def _render_source_pdf(
    playwright: Playwright,
    config: ShowcaseConfig,
    runtime_dir: Path,
) -> Path:
    if not config.import_source_html.is_file():
        raise FileNotFoundError(f"showcase import fixture does not exist: {config.import_source_html}")
    source_pdf = runtime_dir / "source" / "maya-chen-product-engineer.pdf"
    source_pdf.parent.mkdir(parents=True, exist_ok=True)
    browser = await playwright.chromium.launch(headless=True)
    try:
        page = await browser.new_page()
        await page.set_content(config.import_source_html.read_text(encoding="utf-8"), wait_until="load")
        await page.pdf(
            path=str(source_pdf),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
    finally:
        await browser.close()
    if not source_pdf.is_file() or source_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("showcase import source is not a valid PDF")
    return source_pdf


async def seed_demo(
    config: ShowcaseConfig,
    fixture: dict[str, Any],
    runtime_dir: Path,
) -> SeedResult:
    """Create the minimum complete account state for one showcase run.

    The account is intentionally created through the same-origin API. This
    exercises the real ownership, validation, quota, and CSRF boundaries while
    keeping the normal development database untouched.
    """

    email = f"portfolio-{uuid4().hex[:12]}@aergia.dev"
    password = secrets.token_urlsafe(18)

    async with async_playwright() as playwright:
        print("[showcase] rendering the fictional import source", flush=True)
        source_pdf = await _render_source_pdf(playwright, config, runtime_dir)
        request = await playwright.request.new_context(
            base_url=config.web_url,
            extra_http_headers={
                "Accept": "application/json",
                "Origin": config.web_url,
            },
        )
        try:
            # The first response issues the browser-readable CSRF cookie. The
            # Origin header then satisfies the app's same-origin protection.
            await request.get("/")
            print("[showcase] creating the demo account", flush=True)
            await _post_json(
                request,
                "/api/v1/auth/register",
                {"email": email, "password": password},
                "register showcase account",
            )
            await _post_json(
                request,
                "/api/v1/auth/login",
                {"email": email, "password": password},
                "log in showcase account",
            )

            profile_update = await request.put("/api/v1/profile", data=fixture["profile"], timeout=30_000)
            print("[showcase] adding reusable library content", flush=True)
            await _response_json(profile_update, "update showcase profile")
            profile_response = await request.get("/api/v1/profile")
            await _response_json(profile_response, "verify showcase profile")

            for index, entry in enumerate(fixture["library"]):
                if not isinstance(entry, dict):
                    raise ValueError(f"library fixture item {index} must be an object")
                await _post_json(
                    request,
                    "/api/v1/library",
                    {"kind": entry["kind"], "payload": entry["payload"]},
                    f"create library entry {index + 1}",
                )

            cv_data = fixture["cv"]
            print("[showcase] creating the authored CV", flush=True)
            authored_cv = await _post_json(
                request,
                "/api/v1/cvs",
                {
                    "title": cv_data["title"],
                    "description": cv_data.get("description"),
                    "template_id": cv_data["template_id"],
                    "sections": cv_data["sections"],
                },
                "create authored showcase CV",
            )
            application = await _post_json(
                request,
                "/api/v1/applications",
                fixture["application"],
                "create showcase application",
            )

            print("[showcase] generating the tailored application CV", flush=True)
            generated = await _post_json(
                request,
                f"/api/v1/applications/{application['id']}/generate",
                {},
                "generate showcase application CV",
                timeout=180_000,
            )
            generated_application = generated.get("application", {})
            generated_cv_id = generated.get("cv_id")
            if generated_application.get("generation_status") != "ready" or not generated_cv_id:
                raise RuntimeError("showcase application CV generation did not finish with a ready CV")

            # Keep the tailored result visually continuous with the source CV.
            # Application generation intentionally defaults to Minimal in the
            # product; the portfolio fixture chooses the same Modern template
            # used throughout this particular tour.
            generated_cv_update = await request.patch(
                f"/api/v1/cvs/{generated_cv_id}",
                data={"template_id": cv_data["template_id"]},
                timeout=30_000,
            )
            await _response_json(generated_cv_update, "align generated showcase CV template")

            # The application detail page checks for its latest local-agent
            # tailoring session. Seed a valid short-lived session so that
            # request succeeds instead of producing a global 404 toast. The
            # one-time capability remains in memory and is immediately
            # discarded by this disposable environment.
            await _post_json(
                request,
                f"/api/v1/applications/{application['id']}/tailoring-sessions",
                {},
                "create showcase tailoring session",
            )

            return SeedResult(
                email=email,
                password=password,
                authored_cv_id=str(authored_cv["id"]),
                application_id=str(application["id"]),
                generated_cv_id=str(generated_cv_id),
                source_pdf=source_pdf,
            )
        finally:
            await request.dispose()
