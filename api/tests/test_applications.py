"""Application tracker CRUD, ownership, and status contracts."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


async def _auth_headers(client, prefix: str) -> dict[str, str]:
    email = f"{prefix}-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


@pytest.mark.asyncio
async def test_application_crud_and_applied_date_transition(client):
    headers = await _auth_headers(client, "application-owner")
    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "  Example Labs  ",
            "role": " Platform Engineer ",
            "job_description": " Python FastAPI PostgreSQL ",
            "job_url": " https://example.com/jobs/1 ",
            "notes": "Keep this note",
            "cv_id": "must-not-be-set",
            "extracted_keywords": [{"text": "fake"}],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["company"] == "Example Labs"
    assert body["role"] == "Platform Engineer"
    assert body["job_description"] == "Python FastAPI PostgreSQL"
    assert body["job_url"] == "https://example.com/jobs/1"
    assert body["status"] == "draft"
    assert body["generation_status"] == "pending"
    assert body["cv_id"] is None
    application_id = body["id"]

    applied = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"status": "applied"},
    )
    assert applied.status_code == 200
    applied_at = applied.json()["applied_at"]
    assert applied_at is not None

    later = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"status": "interview"},
    )
    assert later.status_code == 200
    assert later.json()["applied_at"] == applied_at

    override = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    overridden = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"applied_at": override},
    )
    assert overridden.status_code == 200
    assert overridden.json()["applied_at"].startswith(override[:19])

    listed = await client.get("/api/v1/applications", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == application_id

    deleted = await client.delete(f"/api/v1/applications/{application_id}", headers=headers)
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_application_ownership_and_required_fields(client):
    owner = await _auth_headers(client, "application-owner-isolated")
    other = await _auth_headers(client, "application-other-isolated")
    created = await client.post(
        "/api/v1/applications",
        headers=owner,
        json={"company": "Owner Co", "role": "Engineer", "job_description": "Python"},
    )
    application_id = created.json()["id"]

    assert (await client.get(f"/api/v1/applications/{application_id}", headers=other)).status_code == 404
    assert (
        await client.patch(f"/api/v1/applications/{application_id}", headers=other, json={"notes": "x"})
    ).status_code == 404
    assert (await client.delete(f"/api/v1/applications/{application_id}", headers=other)).status_code == 404

    for payload in (
        {"company": "", "role": "Engineer", "job_description": "Python"},
        {"company": "Owner Co", "role": " ", "job_description": "Python"},
    ):
        response = await client.post("/api/v1/applications", headers=owner, json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_generation_requires_named_library_profile(client):
    headers = await _auth_headers(client, "application-profile-required")
    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Example Labs", "role": "Engineer", "job_description": "Python"},
    )
    application_id = created.json()["id"]

    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert generated.status_code == 422
    assert generated.json()["detail"] == "Complete your Library Profile before generating a CV"
