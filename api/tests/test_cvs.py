"""T6-T8: Pytest: CV CRUD flow, copy, and data isolation"""

import pytest


@pytest.fixture
async def auth_headers(client):
    """Register a test user and return auth headers."""
    email = "cv-test@example.com"
    password = "testpass123"

    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_cv_crud_flow(client, auth_headers):
    """T6: Full CV CRUD flow (create → get → update → delete)"""

    # Create
    create_resp = await client.post("/api/v1/cvs", json={"title": "My Test CV"}, headers=auth_headers)
    assert create_resp.status_code == 201
    cv = create_resp.json()
    assert cv["title"] == "My Test CV"
    assert cv["template_id"] == "generic-modern"
    cv_id = cv["id"]

    # List
    list_resp = await client.get("/api/v1/cvs", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Get
    get_resp = await client.get(f"/api/v1/cvs/{cv_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "My Test CV"

    # Update
    update_resp = await client.patch(
        f"/api/v1/cvs/{cv_id}",
        json={"title": "Updated CV"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated CV"

    # Delete (soft-delete)
    delete_resp = await client.delete(f"/api/v1/cvs/{cv_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    # Verify deleted (list should be empty)
    list2_resp = await client.get("/api/v1/cvs", headers=auth_headers)
    assert list2_resp.status_code == 200
    assert len(list2_resp.json()) == 0


@pytest.mark.asyncio
async def test_cv_copy_independent(client, auth_headers):
    """T7: CV copy creates an independent clone"""

    # Create original
    create_resp = await client.post("/api/v1/cvs", json={"title": "Original CV"}, headers=auth_headers)
    original_id = create_resp.json()["id"]

    # Copy
    copy_resp = await client.post(f"/api/v1/cvs/{original_id}/copy", headers=auth_headers)
    assert copy_resp.status_code == 200
    copy = copy_resp.json()
    assert copy["title"] == "Original CV (Copy)"
    assert copy["id"] != original_id

    # Modify original - copy should not be affected
    await client.patch(f"/api/v1/cvs/{original_id}", json={"title": "Modified Original"}, headers=auth_headers)

    get_copy_resp = await client.get(f"/api/v1/cvs/{copy['id']}", headers=auth_headers)
    assert get_copy_resp.json()["title"] == "Original CV (Copy)"  # unchanged


@pytest.mark.asyncio
async def test_cv_data_isolation(client):
    """T8: CV data isolation by user_id - users cannot access each other's CVs"""

    # Register user A
    await client.post("/api/v1/auth/register", json={"email": "user-a@example.com", "password": "pass123"})
    login_a = await client.post("/api/v1/auth/login", json={"email": "user-a@example.com", "password": "pass123"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register user B
    await client.post("/api/v1/auth/register", json={"email": "user-b@example.com", "password": "pass123"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "user-b@example.com", "password": "pass123"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a CV
    cv_a = await client.post("/api/v1/cvs", json={"title": "User A's CV"}, headers=headers_a)
    cv_a_id = cv_a.json()["id"]

    # User B cannot see it
    list_b = await client.get("/api/v1/cvs", headers=headers_b)
    assert len(list_b.json()) == 0

    # User B cannot access it directly
    get_b = await client.get(f"/api/v1/cvs/{cv_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B cannot update it
    update_b = await client.patch(f"/api/v1/cvs/{cv_a_id}", json={"title": "Hacked"}, headers=headers_b)
    assert update_b.status_code == 404

    # User B cannot delete it
    delete_b = await client.delete(f"/api/v1/cvs/{cv_a_id}", headers=headers_b)
    assert delete_b.status_code == 404

    # User B cannot copy it
    copy_b = await client.post(f"/api/v1/cvs/{cv_a_id}/copy", headers=headers_b)
    assert copy_b.status_code == 404
