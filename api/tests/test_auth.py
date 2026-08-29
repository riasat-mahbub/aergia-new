"""T3: Pytest: auth flow (register → login → refresh → logout) (integration)"""

import asyncio
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_auth_full_flow(client):
    email = "flow-test@example.com"
    password = "testpass123"

    # Register
    register_resp = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert register_resp.status_code == 201

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    refresh_token = data["refresh_token"]


    # Refresh token
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    refresh_data = refresh_resp.json()
    assert "access_token" in refresh_data
    current_refresh_token = refresh_data["refresh_token"]
    new_access_token = refresh_data["access_token"]


    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logout_resp.status_code == 200

    # Old refresh token should be invalid after logout
    stale_refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert stale_refresh_resp.status_code == 401
    revoked_refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": current_refresh_token})
    assert revoked_refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_is_idempotent_without_access_token(client):
    email = f"logout-refresh-only-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200

    client.cookies.delete("aergia_access_token")
    refresh_only = await client.post("/api/v1/auth/logout")
    assert refresh_only.status_code == 200


@pytest.mark.asyncio
async def test_multiple_logins_keep_refresh_sessions_independent(client):
    email = f"multi-session-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})

    first_login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    second_login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    first_refresh = first_login.json()["refresh_token"]
    second_refresh = second_login.json()["refresh_token"]

    first_rotation = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    second_rotation = await client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})

    assert first_rotation.status_code == 200
    assert second_rotation.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_refresh_allows_one_rotation_and_rejects_reuse(client):
    email = f"concurrent-refresh-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    refresh_token = login.json()["refresh_token"]

    responses = await asyncio.gather(
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}),
    )

    assert sorted(response.status_code for response in responses) == [200, 401]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    email = "duplicate@example.com"
    password = "testpass123"

    resp1 = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "wrongpass"})
    assert resp.status_code == 401

    resp2 = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrongpass"})
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_password_schema_and_bcrypt_limits_are_clean(client):
    short = await client.post(
        "/api/v1/auth/register", json={"email": f"short-{uuid4().hex}@example.com", "password": "1234567"}
    )
    assert short.status_code == 422

    email = f"long-login-{uuid4().hex}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "validpass123"})
    oversized_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "a" * 73})
    assert oversized_login.status_code == 401


@pytest.mark.asyncio
async def test_password_change_endpoint_is_removed(client):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "oldpass123", "new_password": "newpass123"},
    )
    # A built SPA's GET catch-all can match the path and report 405 for POST;
    # without the built SPA this is a normal 404. Either means the endpoint is
    # no longer exposed.
    assert response.status_code in {404, 405}


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token_here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client):
    # Logout is intentionally idempotent so a browser can clear a stale
    # session even after its access and refresh cookies have expired.
    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # Other authenticated routes still reject requests without credentials.
    protected_resp = await client.get("/api/v1/cvs")
    assert protected_resp.status_code == 401
