"""Unit tests for api/scripts/smoke_live.py.

Drive the same ``run_smoke`` function the live smoke client uses, but
substitute the network with :class:`httpx.MockTransport` so the test
is fast and does not require a live backend. The handlers cover the
happy path, the wrong-template-set path, and a non-PDF body path.
"""

from __future__ import annotations

import json

import httpx
import pytest

from scripts import smoke_live


def _ok_json(payload: dict[str, object], status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _register_login_ready_handler(
    request: httpx.Request,
    *,
    templates: list[dict[str, str]] | None = None,
    pdf_body: bytes = b"%PDF-1.4\n% smoke",
    spa_html: str = '<!doctype html><html><body><div id="root"></div></body></html>',
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
        return _ok_json({"access_token": "token", "refresh_token": "refresh", "token_type": "bearer"})

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
        if request.url.path == "/api/v1/templates" and request.method == "GET":
            pass
        response = _register_login_ready_handler(request)
        if request.url.path == "/api/v1/templates" and request.method == "GET":
            for t in json.loads(response.content):
                seen["template_ids"].append(t["id"])
        return response

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    smoke_live.run_smoke(client, "http://testserver")

    assert sorted(seen["template_ids"]) == sorted(smoke_live.EXPECTED_TEMPLATES)
    assert seen["cv_create_titles"] == [
        "Smoke generic-modern",
        "Smoke generic-classic",
        "Smoke generic-minimal",
    ]


def test_run_smoke_rejects_wrong_template_set() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/templates" and request.method == "GET":
            return _ok_json(
                [
                    {"id": "generic-modern", "name": "Modern"},
                    {"id": "generic-legacy", "name": "Legacy"},
                ]
            )
        return _register_login_ready_handler(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(AssertionError, match="unexpected template set"):
        smoke_live.run_smoke(client, "http://testserver")


def test_run_smoke_rejects_non_pdf_body() -> None:
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

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(AssertionError, match="returned non-PDF body"):
        smoke_live.run_smoke(client, "http://testserver")


def test_run_smoke_rejects_missing_root_div() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/" and request.method == "GET":
            return httpx.Response(200, text="<!doctype html><html><body>no root</body></html>")
        return _register_login_ready_handler(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(AssertionError, match="missing the React root mount"):
        smoke_live.run_smoke(client, "http://testserver")
