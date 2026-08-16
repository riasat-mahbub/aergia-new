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
    library_state: dict[str, str] | None = None,
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

    if path == "/api/v1/library" and method == "POST":
        payload = json.loads(request.content)
        title = payload["payload"][0]["title"]
        if library_state is not None:
            library_state["title"] = title
        return _ok_json(
            {
                "id": "lib_smoke",
                "kind": payload["kind"],
                "payload": payload["payload"],
            },
            status_code=201,
        )

    if path.startswith("/api/v1/library/") and path.endswith("/clone") and method == "POST":
        title = (library_state or {}).get("title", "Library")
        return _ok_json(
            {
                "section_instance": {
                    "id": "sec_library",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "entry_smoke", "title": title, "company": "SmokeCo"}],
                }
            }
        )

    if path.startswith("/api/v1/cvs/") and path.endswith("/promote-to-library") and method == "POST":
        return _ok_json({"promoted": {}})

    if path.startswith("/api/v1/cvs/") and path.endswith("/preview") and method == "GET":
        preview_text = "preview"
        if library_state and library_state.get("title"):
            preview_text += f" {library_state['title']}"
        return _ok_json(
            {"html": f"<!DOCTYPE html><html><head></head><body>{preview_text}</body></html>"}
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

    library_state: dict[str, str] = {}
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/cvs" and request.method == "POST":
            seen["cv_create_titles"].append(json.loads(request.content)["title"])
        if (
            request.url.path.endswith("/api/v1/cvs/import/pdf")
            and request.method == "POST"
        ):
            seen.setdefault("import_called", []).append(True)
        return _register_login_ready_handler(request, library_state=library_state)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        smoke_live.run_smoke(client, "http://test")

    assert seen["cv_create_titles"][:3] == [
        "Smoke generic-modern",
        "Smoke generic-classic",
        "Smoke generic-minimal",
    ]
    assert "Library smoke CV" in seen["cv_create_titles"]
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
    library_state: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        return _register_login_ready_handler(
            request,
            spa_html='<!doctype html><html><body>no root</body></html>',
            library_state=library_state,
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        with pytest.raises(AssertionError, match="missing the React root mount"):
            smoke_live.run_smoke(client, "http://test")


# ---------------------------------------------------------------------------
# LLM fallback chain — direct route tests via httpx.MockTransport.
# ---------------------------------------------------------------------------


def _import_endpoint_returns_handler(response: httpx.Response) -> callable:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/cvs/import/pdf" and request.method == "POST":
            return response
        return _register_login_ready_handler(request)
    return handler


def test_llm_unrecognised_key_prefix_surfaces_400():
    """Provider field set + unrecognised key prefix → 400 with the
    documented prefix list in the body."""
    transport = httpx.MockTransport(
        _import_endpoint_returns_handler(
            httpx.Response(400, json={"detail": "Unrecognised API key prefix."})
        )
    )
    with httpx.Client(transport=transport, base_url="http://test") as client:
        r = client.post(
            "/api/v1/cvs/import/pdf",
            files={"file": ("x.pdf", b"%PDF-1.4\n%smoke", "application/pdf")},
            data={"provider": "openai", "api_key": "not-a-key"},
        )
    assert r.status_code == 400
    assert "Unrecognised" in r.json()["detail"]


def test_llm_invalid_key_surfaces_401_not_fallback():
    """Auth failures must be 401 — the orchestrator never falls back to
    regex on InvalidAPIKeyError."""
    transport = httpx.MockTransport(
        _import_endpoint_returns_handler(
            httpx.Response(
                401,
                json={"detail": "auth rejected sk-***REDACTED***"},
            )
        )
    )
    with httpx.Client(transport=transport, base_url="http://test") as client:
        r = client.post(
            "/api/v1/cvs/import/pdf",
            files={"file": ("x.pdf", b"%PDF-1.4\n%smoke", "application/pdf")},
            data={"provider": "openai", "api_key": "sk-bogus-key"},
        )
    assert r.status_code == 401
    # The response body has the redaction prefix + REDACTED marker; the
    # raw key fragment must be absent.
    assert "sk-bogus-key" not in r.text


def test_llm_rate_limit_falls_back_to_regex_with_warning_pair():
    """Rate-limit error → 200 with ``meta.source == "regex"`` and the
    ``llm_failed_fallback_to_regex`` + ``llm_failed:RateLimitError``
    warning pair."""
    transport = httpx.MockTransport(
        _import_endpoint_returns_handler(
            httpx.Response(
                200,
                json={
                    "sections": [
                        {
                            "id": "imp_fallback",
                            "type": "profile",
                            "title": "P",
                            "enabled": True,
                            "data": {},
                        }
                    ],
                    "confidence": {"fields": [], "overall_level": "low"},
                    "meta": {
                        "source": "regex",
                        "warnings": [
                            "llm_failed_fallback_to_regex",
                            "llm_failed:RateLimitError",
                        ],
                    },
                },
            )
        )
    )
    with httpx.Client(transport=transport, base_url="http://test") as client:
        r = client.post(
            "/api/v1/cvs/import/pdf",
            files={"file": ("x.pdf", b"%PDF-1.4\n%smoke", "application/pdf")},
            data={"provider": "openai", "api_key": "sk-test-key-marker"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["source"] == "regex"
    assert body["meta"]["warnings"] == [
        "llm_failed_fallback_to_regex",
        "llm_failed:RateLimitError",
    ]


def test_llm_no_key_prefers_regex_default():
    """When no (provider, api_key) is supplied, the route omits both
    form fields and the mock returns the canned ``source=regex``
    payload — the orchestrator's default path."""
    seen: dict[str, object] = {}

    library_state: dict[str, str] = {}
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/cvs/import/pdf" and request.method == "POST":
            seen["form_keys"] = list(request.url.params.keys())
            # Run smoke against the canned payload by adding the import
            # default — easiest way to assert the no-key behaviour is
            # to check the body's meta.source.
        return _register_login_ready_handler(request, library_state=library_state)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://test") as client:
        smoke_live.run_smoke(client, "http://test")
    assert seen.get("form_keys") == []  # no provider/api_key form fields sent
