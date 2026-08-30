"""Focused tests for Turnstile validation, trusted proxy parsing, and quotas."""

from __future__ import annotations

import asyncio
import inspect
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Response
from fastapi import Request as FastAPIRequest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select, update
from starlette.requests import Request

from app.app import rate_limit_exceeded_handler
from app.config import Settings
from app.core import rate_limit
from app.db.session import async_session
from app.models.user import AccountTier, User
from app.routes.auth import register
from app.services import turnstile


def _turnstile_settings(**overrides) -> Settings:
    values = {
        "environment": "test",
        "turnstile_site_key": "site-key",
        "turnstile_secret_key": "secret-key",
        "turnstile_expected_hostname": "app.example.com",
        "turnstile_expected_action": "register",
        "turnstile_bypass": False,
    }
    values.update(overrides)
    return Settings(**values)


class _FakeResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def json(self):
        return self.payload


class _FakeClient:
    response: _FakeResponse
    request_url: str | None = None
    request_data: dict | None = None
    timeout = None

    def __init__(self, *, timeout):
        type(self).timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url: str, *, data: dict):
        type(self).request_url = url
        type(self).request_data = data
        return type(self).response


async def test_turnstile_accepts_only_a_successful_matching_response(monkeypatch):
    _FakeClient.response = _FakeResponse(
        {"success": True, "action": "register", "hostname": "app.example.com"}
    )
    monkeypatch.setattr(turnstile.httpx, "AsyncClient", _FakeClient)

    await turnstile.verify_turnstile("token", settings=_turnstile_settings())

    assert _FakeClient.request_url == turnstile.TURNSTILE_VERIFY_URL
    assert _FakeClient.request_data == {"secret": "secret-key", "response": "token"}


@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "error-codes": ["invalid-input-response"]},
        {"success": True, "action": "login", "hostname": "app.example.com"},
        {"success": True, "action": "register", "hostname": "other.example.com"},
    ],
)
async def test_turnstile_rejects_provider_failure_or_context_mismatch(monkeypatch, payload):
    _FakeClient.response = _FakeResponse(payload)
    monkeypatch.setattr(turnstile.httpx, "AsyncClient", _FakeClient)

    with pytest.raises(turnstile.TurnstileRejected):
        await turnstile.verify_turnstile("token", settings=_turnstile_settings())


async def test_turnstile_fails_closed_on_timeout(monkeypatch):
    class TimeoutClient(_FakeClient):
        async def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("provider timeout")

    monkeypatch.setattr(turnstile.httpx, "AsyncClient", TimeoutClient)

    with pytest.raises(turnstile.TurnstileRejected) as error:
        await turnstile.verify_turnstile("token", settings=_turnstile_settings())
    assert error.value.reason == "provider_unavailable"


async def test_turnstile_missing_token_is_rejected_without_a_provider_call(monkeypatch):
    class UnexpectedClient:
        def __init__(self, **_kwargs):
            raise AssertionError("provider must not be called for a missing token")

    monkeypatch.setattr(turnstile.httpx, "AsyncClient", UnexpectedClient)

    with pytest.raises(turnstile.TurnstileRejected) as error:
        await turnstile.verify_turnstile(None, settings=_turnstile_settings())
    assert error.value.reason == "token_missing"


async def test_turnstile_bypass_requires_an_explicit_test_setting():
    await turnstile.verify_turnstile(
        None,
        settings=_turnstile_settings(
            turnstile_site_key="",
            turnstile_secret_key="",
            turnstile_expected_hostname="",
            turnstile_bypass=True,
        ),
    )


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 1234),
            "server": ("test", 80),
            "scheme": "http",
        }
    )


def test_rate_limit_ignores_forwarded_headers_from_an_untrusted_peer(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "trusted_proxy_ips", "")
    assert rate_limit.get_client_address(_request("198.51.100.20", "203.0.113.8")) == "198.51.100.20"


def test_rate_limit_walks_forwarded_chain_from_a_trusted_peer(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "trusted_proxy_ips", "10.0.0.0/8")
    request = _request("10.0.0.2", "198.51.100.20, 10.0.0.3")
    assert rate_limit.get_client_address(request) == "198.51.100.20"


def test_rate_limit_key_is_stable_without_exposing_the_client_address(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "trusted_proxy_ips", "")
    request = _request("198.51.100.20")
    key = rate_limit.get_rate_limit_key(request)
    assert key == rate_limit.get_rate_limit_key(request)
    assert key.startswith("ip:")
    assert "198.51.100.20" not in key


def test_registration_rate_limit_route_exposes_slowapi_response_parameter():
    parameters = inspect.signature(register).parameters
    assert "request" in parameters
    assert "response" in parameters


async def test_slowapi_route_limit_returns_429_with_the_application_handler():
    def client_key(request: FastAPIRequest) -> str:
        return "test-client"

    local_limiter = Limiter(key_func=client_key, storage_uri="memory://")
    test_app = FastAPI()
    test_app.state.limiter = local_limiter
    test_app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)

    @local_limiter.limit("2/minute")
    async def limited(request: FastAPIRequest, response: Response):
        return {"ok": True}

    test_app.add_api_route("/limited", limited, methods=["GET"])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        responses = [await client.get("/limited") for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 429]
    assert responses[-1].json() == {"detail": "Rate limit exceeded"}


async def _auth_headers(client) -> dict[str, str]:
    email = f"quota-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


async def _premium_auth_headers(client) -> tuple[dict[str, str], str]:
    email = f"premium-quota-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201

    async with async_session() as session:
        result = await session.execute(
            update(User).where(User.email == email).values(account_tier=AccountTier.PREMIUM.value)
        )
        await session.commit()
    assert result.rowcount == 1

    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}, email


async def test_premium_account_can_exceed_free_quotas_and_keeps_counters(client):
    headers, email = await _premium_auth_headers(client)

    for index in range(4):
        application = await client.post(
            "/api/v1/applications",
            headers=headers,
            json={"company": f"Premium Company {index}", "role": "Engineer", "job_description": "Python"},
        )
        assert application.status_code == 201

    for index in range(4):
        cv = await client.post(
            "/api/v1/cvs",
            headers=headers,
            json={"title": f"Premium CV {index}"},
        )
        assert cv.status_code == 201

    session = await client.get("/api/v1/auth/session", headers=headers)
    assert session.status_code == 200
    assert session.json() == {"authenticated": True, "account_tier": "premium"}

    async with async_session() as db_session:
        user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
        assert user.application_count == 4
        assert user.cv_count == 4


async def test_application_quota_is_separate_and_released_on_delete(client):
    headers = await _auth_headers(client)
    for index in range(3):
        response = await client.post(
            "/api/v1/applications",
            headers=headers,
            json={"company": f"Company {index}", "role": "Engineer", "job_description": "Python"},
        )
        assert response.status_code == 201

    blocked = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Blocked", "role": "Engineer", "job_description": "Python"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Application limit reached"

    listed = await client.get("/api/v1/applications", headers=headers)
    deleted = await client.delete(f"/api/v1/applications/{listed.json()[0]['id']}", headers=headers)
    assert deleted.status_code == 204
    released = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Released", "role": "Engineer", "job_description": "Python"},
    )
    assert released.status_code == 201


async def test_cv_quota_covers_copy_and_is_released_by_soft_delete(client):
    headers = await _auth_headers(client)
    ids = []
    for index in range(3):
        response = await client.post(
            "/api/v1/cvs",
            headers=headers,
            json={"title": f"CV {index}"},
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])

    blocked = await client.post(f"/api/v1/cvs/{ids[0]}/copy", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "CV limit reached"

    deleted = await client.delete(f"/api/v1/cvs/{ids[0]}", headers=headers)
    assert deleted.status_code == 204
    copied = await client.post(f"/api/v1/cvs/{ids[1]}/copy", headers=headers)
    assert copied.status_code == 200


async def test_concurrent_cv_creation_never_exceeds_the_quota(client):
    headers = await _auth_headers(client)
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/v1/cvs",
                headers=headers,
                json={"title": f"Concurrent CV {index}"},
            )
            for index in range(5)
        )
    )
    assert sorted(response.status_code for response in responses) == [201, 201, 201, 409, 409]
