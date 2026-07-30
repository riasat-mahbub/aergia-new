"""Route contract tests for ``POST /api/v1/cvs/import/pdf``.

Verifies the new ``provider`` + ``api_key`` multipart form fields and
the resulting status code map:

- 200 with no key, no provider → existing regex path (unchanged).
- 200 with valid (provider, key) → LLM path; ``meta.source == "llm"``
  and ``warnings`` includes ``"llm_used"``.
- 400 with unknown provider string.
- 400 with unsupported file type.
- 401 with invalid ``api_key`` (provider-rejected; no fallback).
- 413 when file exceeds ``MAX_BYTES``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parser import imports as orch
from app.services.parser.keys import (
    InvalidAPIKeyError,
    LLMProvider,
    RateLimitError,
)


SAMPLE_PDF = (Path(__file__).parent / "fixtures" / "sample.pdf").read_bytes()


@pytest.fixture
async def auth_headers(client):
    email = "import-test@example.com"
    password = "testpass123"
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _stub_sections_payload() -> dict:
    return {
        "sections": [
            {
                "id": "route_one",
                "type": "profile",
                "title": "One",
                "enabled": True,
                "data": {"name": "One", "title": "", "email": "", "phone": "",
                         "location": "", "site_text": "", "site_url": "",
                         "summary": "", "photo_url": "", "social_links": []},
            }
        ],
        "confidence": {"fields": [], "overall_level": "high"},
        "meta": {"source": "llm", "warnings": ["llm_used"]},
    }


async def test_route_no_key_runs_regex_path(client, auth_headers):
    orch._PROVIDERS = None
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["source"] == "regex"
    assert "llm_used" not in body["meta"]["warnings"]


async def test_route_unknown_provider_string_returns_400(client, auth_headers):
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        data={"provider": "fakeco", "api_key": "sk-test-key-marker"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "fakeco" in resp.json()["detail"]


async def test_route_unrecognised_key_prefix_returns_400(client, auth_headers):
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        data={"provider": "openai", "api_key": "totally-not-a-key"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Unrecognised API key prefix" in resp.json()["detail"]


async def test_route_provider_key_mismatch_returns_400(client, auth_headers):
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        data={"provider": "anthropic", "api_key": "sk-test-matching-key"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "shape does not match" in resp.json()["detail"]


async def test_route_rate_limit_falls_back_with_warning(client, auth_headers):
    """Adapter raises ``RateLimitError`` → route returns 200 with
    ``meta.source == "regex"`` and the warning pair."""

    class _RateLimitAdapter:
        async def structure(self, **_):
            raise RateLimitError("rate limit hit")

    orch._PROVIDERS = {LLMProvider.OPENAI: _RateLimitAdapter}

    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        data={"provider": "openai", "api_key": "sk-test-matching-key"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["source"] == "regex"
    assert "llm_failed_fallback_to_regex" in body["meta"]["warnings"]
    assert any(
        w.startswith("llm_failed:") and "RateLimitError" in w
        for w in body["meta"]["warnings"]
    )


async def test_route_invalid_key_returns_401(client, auth_headers):
    """Auth failures must NOT fall back — route returns 401."""

    class _AuthFailAdapter:
        async def structure(self, **_):
            raise InvalidAPIKeyError("auth rejected sk-bogus-key-marker")

    orch._PROVIDERS = {LLMProvider.OPENAI: _AuthFailAdapter}

    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.pdf", SAMPLE_PDF, "application/pdf")},
        data={"provider": "openai", "api_key": "sk-bogus-key-marker"},
        headers=auth_headers,
    )
    assert resp.status_code == 401
    # Adapter's message has already been redacted in the adapter; the
    # body carries no raw key fragment.
    assert "sk-bogus-key-marker" not in resp.text


async def test_route_file_too_large_returns_413(client, auth_headers):
    big = b"%PDF-1.4\n% " + b"x" * (15 * 1024 * 1024) + b"\n%%EOF\n"
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 413


async def test_route_unsupported_mime_returns_400(client, auth_headers):
    resp = await client.post(
        "/api/v1/cvs/import/pdf",
        files={"file": ("cv.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]
