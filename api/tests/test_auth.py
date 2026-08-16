"""T3: Pytest: auth flow (register → login → refresh → logout) (integration)"""

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
async def test_refresh_invalid_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token_here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client):

    # Try accessing a protected route without token - there's no dedicated protected
    # route yet in the API, but /auth/logout requires authentication
    resp2 = await client.post("/api/v1/auth/logout")
    assert resp2.status_code == 401  # 401 from HTTPBearer when no credentials
