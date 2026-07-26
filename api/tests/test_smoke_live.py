"""Smoke script tests — drive ``scripts/smoke_live.run_smoke`` through
:class:`httpx.MockTransport` so we don't need a live uvicorn to assert
behaviour.
"""

from __future__ import annotations

import json

import httpx
import pytest

from scripts import smoke_live


def _ok_json(payload, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _register_login_ready_handler(
    request: httpx.Request,
    *,
    templates: list[dict[str, str]] | None = None,
    pdf_body: bytes = b"%PDF-1.4\n% smoke",
    spa_html: str = '<!doctype html><html><body><div id="root"></div></body></html>',
    import_payload: dict | None = None,
) -> httpx.Response:
    """Return a single handler that simulates a healthy backend for the
    exact flow ``run_smoke`` performs."""
    path = request.url.path
    method = request.method

    if path == "/readyz" and method == "GET":
        return _ok_json({"status": "ok", "database": "ok", "version": "0.1.0"})

    if path == "/api/v1/auth/register" and method == "POST":
        return httpx.Response(201, json=None)

    if path == "/api/v1/auth/login" and method == "POST":
        return _ok_json(
            {"access_token": "token", "refresh_token": "refresh", "token_type": "bearer"}
        )

    if path == "/api/v1/templates" and method == "GET":
        return _ok_json(
            templates
            or [
                {"id": "generic-modern", "name": "Modern"},
                {"id": "generic-classic", "name": "Classic"},
                {"id": "generic-minimal", "name": "Minimal"},
            ]
        )

    if path.startswith("/api/v1/cvs/") and path.endswith("/preview") and method == "GET":
        return _ok_json(
            {"html": "<!DOCTYPE html><html><head></head><body>preview</body></html>"}
        )

    if path == "/api/v1/cvs/import/pdf" and method == "POST":
        return _ok_json(
            import_payload
            or {
                "sections": [
                    {
                        "id": "imp_mock",
                        "type": "profile",
                        "title": "Profile",
                        "enabled": True,
                        "data": {},
                    }
                ],
                "confidence": {"fields": [], "overall_level": "high"},
                "meta": {"source": "regex", "warnings": []},
            }
        )

    if path.startswith("/api/v1/cvs/") and path.endswith("/export/pdf") and method == "POST":
        return httpx.Response(
            200,
            content=pdf_body,
            headers={"content-type": "application/pdf"},
        )

    if path == "/api/v1/cvs" and method == "POST":
        return _ok_json(
            {"id": "cv_smoke", "title": "Smoke CV", "template_id": "generic-modern"},
            status_code=201,
        )

    if path == "/" and method == "GET":
        return httpx.Response(200, text=spa_html)

    return httpx.Response(500, text=f"unhandled {method} {path}")


def test_run_smoke_happy_path_exercises_all_three_templates() -> None:
    seen: dict[str, list[str]] = {"template_ids": [], "cv_create_titles": []}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/cvs" and request.method == "POST":
            seen["cv_create_titles"].append(json.loads(request.content)["title"])
        if (
            request.url.path.endswith("/api/v1/cvs/import/pdf")
            and request.method == "POST"
        ):
            seen.setdefault("import_called", []).append(True)
        return _register_login_ready_handler(request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        smoke_live.run_smoke(client, "http://test")

    assert seen["cv_create_titles"] == [
        "Smoke generic-modern",
        "Smoke generic-classic",
        "Smoke generic-minimal",
    ]
    assert seen.get("import_called") == [True]


def test_run_smoke_rejects_non_pdf_body() -> None:
    """If the export/pdf endpoint returns HTML instead of bytes starting
    with ``%PDF``, run_smoke raises an AssertionError carrying the
    ``returned non-PDF body`` message."""
    def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.path.startswith("/api/v1/cvs/")
            and request.url.path.endswith("/export/pdf")
            and request.method == "POST"
        ):
            return httpx.Response(
                200,
                content=b"<html>not a pdf</html>",
                headers={"content-type": "application/pdf"},
            )
        return _register_login_ready_handler(request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        with pytest.raises(AssertionError, match="returned non-PDF body"):
            smoke_live.run_smoke(client, "http://test")


def test_run_smoke_rejects_missing_root_div() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _register_login_ready_handler(
            request,
            spa_html='<!doctype html><html><body>no root</body></html>',
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        with pytest.raises(AssertionError, match="missing the React root mount"):
            smoke_live.run_smoke(client, "http://test")
