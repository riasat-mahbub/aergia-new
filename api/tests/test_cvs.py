"""T6-T8: Pytest: CV CRUD flow, copy, and data isolation"""

from uuid import uuid4

import pytest

from app.db.session import async_session
from app.models.application import Application


CUSTOMIZATIONS_PAYLOAD = {
    "layout": {
        "zones": [{"id": "sidebar", "styles": {"width": "narrow"}}],
        "placement": {"sec_profile": "sidebar"},
    },
    "flags": {"default_link_style": True},
    "per_section": {
        "sec_profile": {"text": {"name": {"bold": True}}},
    },
}


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
    assert cv["template_id"] == "generic-minimal"
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
async def test_cv_creation_installs_template_zones(client, auth_headers):
    """A new CV inherits the template's zones into ``customizations.layout``.

    The builder editor needs zones immediately after creation; without them
    every new CV opens with an empty layout and an unassignable section.
    """
    create_resp = await client.post(
        "/api/v1/cvs", json={"title": "Zones CV"}, headers=auth_headers
    )
    assert create_resp.status_code == 201
    cv = create_resp.json()
    layout = (cv.get("customizations") or {}).get("layout") or {}
    assert layout.get("zones"), "new CV must install the template's zones into customizations.layout"
    assert layout.get("placement"), "new CV must install the template's placement"
    assert {z["id"] for z in layout["zones"]} == {"main"}


@pytest.mark.asyncio
async def test_cv_creation_accepts_populated_customizations(client, auth_headers):
    response = await client.post(
        "/api/v1/cvs",
        json={"title": "Customized CV", "customizations": CUSTOMIZATIONS_PAYLOAD},
        headers=auth_headers,
    )

    assert response.status_code == 201
    customizations = response.json()["customizations"]
    assert customizations["layout"]["placement"] == {"sec_profile": "sidebar"}
    assert customizations["flags"] == {"default_link_style": True}
    assert customizations["per_section"]["sec_profile"]["text"]["name"]["bold"] is True


@pytest.mark.asyncio
async def test_cv_update_accepts_populated_customizations(client, auth_headers):
    created = await client.post("/api/v1/cvs", json={"title": "Customized CV"}, headers=auth_headers)
    assert created.status_code == 201

    response = await client.patch(
        f"/api/v1/cvs/{created.json()['id']}",
        json={"customizations": CUSTOMIZATIONS_PAYLOAD},
        headers=auth_headers,
    )

    assert response.status_code == 200
    customizations = response.json()["customizations"]
    assert customizations["layout"]["placement"] == {"sec_profile": "sidebar"}
    assert customizations["flags"] == {"default_link_style": True}
    assert customizations["per_section"]["sec_profile"]["text"]["name"]["bold"] is True


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
async def test_cv_list_includes_owned_application_summary_and_keeps_copies_unlinked(client, auth_headers):
    ordinary = await client.post(
        "/api/v1/cvs",
        json={"title": "Ordinary CV", "extra_metadata": {"application_id": "forged"}},
        headers=auth_headers,
    )
    assert ordinary.status_code == 201
    ordinary_id = ordinary.json()["id"]

    linked = await client.post(
        "/api/v1/cvs",
        json={
            "title": "Tailored CV",
            "extra_metadata": {
                "application_id": "legacy-app",
                "generated_by": "keyword-v1",
                "selected_sources": [],
                "extracted_keywords": [],
            },
        },
        headers=auth_headers,
    )
    assert linked.status_code == 201
    linked_id = linked.json()["id"]
    application = await client.post(
        "/api/v1/applications",
        json={"company": "Example Labs", "role": "Platform Engineer", "job_description": "Python"},
        headers=auth_headers,
    )
    assert application.status_code == 201
    application_id = application.json()["id"]

    async with async_session() as session:
        application_row = await session.get(Application, application_id)
        assert application_row is not None
        application_row.cv_id = linked_id
        await session.commit()

    copied = await client.post(f"/api/v1/cvs/{linked_id}/copy", headers=auth_headers)
    assert copied.status_code == 200
    assert copied.json()["extra_metadata"] == {}

    listed = await client.get("/api/v1/cvs", headers=auth_headers)
    assert listed.status_code == 200
    by_id = {item["id"]: item for item in listed.json()}
    assert by_id[ordinary_id]["application"] is None
    assert by_id[ordinary_id].get("extra_metadata") is None
    assert by_id[linked_id]["application"] == {
        "id": application_id,
        "company": "Example Labs",
        "role": "Platform Engineer",
        "status": "draft",
        "generation_status": "pending",
        "applied_at": None,
    }
    assert by_id[copied.json()["id"]]["application"] is None


@pytest.mark.asyncio
async def test_cv_list_does_not_expose_another_users_application_summary(client, auth_headers):
    foreign_email = f"foreign-cv-{uuid4().hex}@example.com"
    await client.post("/api/v1/auth/register", json={"email": foreign_email, "password": "testpass123"})
    foreign_login = await client.post(
        "/api/v1/auth/login", json={"email": foreign_email, "password": "testpass123"}
    )
    foreign_headers = {"Authorization": f"Bearer {foreign_login.json()['access_token']}"}
    owner_cv = await client.post("/api/v1/cvs", json={"title": "Owner CV"}, headers=auth_headers)
    foreign_application = await client.post(
        "/api/v1/applications",
        json={"company": "Foreign Co", "role": "Engineer", "job_description": "Python"},
        headers=foreign_headers,
    )

    async with async_session() as session:
        application_row = await session.get(Application, foreign_application.json()["id"])
        assert application_row is not None
        application_row.cv_id = owner_cv.json()["id"]
        await session.commit()

    listed = await client.get("/api/v1/cvs", headers=auth_headers)
    owner_item = next(item for item in listed.json() if item["id"] == owner_cv.json()["id"])
    assert owner_item["application"] is None


@pytest.mark.asyncio
async def test_cv_data_isolation(client):
    """T8: CV data isolation by user_id - users cannot access each other's CVs"""

    # Register user A
    await client.post("/api/v1/auth/register", json={"email": "user-a@example.com", "password": "testpass12"})
    login_a = await client.post("/api/v1/auth/login", json={"email": "user-a@example.com", "password": "testpass12"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register user B
    await client.post("/api/v1/auth/register", json={"email": "user-b@example.com", "password": "testpass12"})
    login_b = await client.post("/api/v1/auth/login", json={"email": "user-b@example.com", "password": "testpass12"})
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


