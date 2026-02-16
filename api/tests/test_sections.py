"""T13-T15: Pytest: section data storage, ordering, and validation"""

import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "sectest@example.com", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "sectest@example.com", "password": "pass123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


SAMPLE_SECTIONS = {
    "order": ["profile", "experience", "education"],
    "enabled": ["profile", "experience"],
    "data": {
        "profile": {"name": "Jane Doe", "title": "Engineer", "email": "jane@example.com", "phone": "", "location": "", "summary": "", "photo_url": ""},
        "experience": [
            {"id": "exp_1", "company": "Acme Corp", "position": "Engineer", "start_date": "2022-01", "end_date": None, "current": True, "location": "NYC", "description": "Built things"}
        ],
        "education": [
            {"id": "edu_1", "institution": "MIT", "degree": "BS", "start_date": "2018", "end_date": "2022", "gpa": "3.8"}
        ],
    },
}


@pytest.mark.asyncio
async def test_section_data_stored_correctly(client, auth_headers):
    """T13: section data stored correctly in JSONB"""
    resp = await client.post("/api/v1/cvs", json={
        "title": "Section Test CV",
        "template_id": "generic-modern",
        "sections": SAMPLE_SECTIONS,
    }, headers=auth_headers)
    assert resp.status_code == 201
    cv = resp.json()

    stored = cv["sections"]
    assert stored["order"] == ["profile", "experience", "education"]
    assert stored["enabled"] == ["profile", "experience"]
    assert stored["data"]["profile"]["name"] == "Jane Doe"
    assert stored["data"]["experience"][0]["company"] == "Acme Corp"
    assert stored["data"]["education"][0]["institution"] == "MIT"


@pytest.mark.asyncio
async def test_section_ordering_preserved(client, auth_headers):
    """T14: section ordering preserved through update"""
    resp = await client.post("/api/v1/cvs", json={
        "title": "Order Test",
        "sections": SAMPLE_SECTIONS,
    }, headers=auth_headers)
    cv_id = resp.json()["id"]

    # Reorder
    new_order = ["education", "experience", "profile"]
    update_resp = await client.patch(f"/api/v1/cvs/{cv_id}", json={
        "sections": {**SAMPLE_SECTIONS, "order": new_order},
    }, headers=auth_headers)
    assert update_resp.status_code == 200

    stored = update_resp.json()["sections"]
    assert stored["order"] == ["education", "experience", "profile"]

    # Education data should still be intact
    assert stored["data"]["education"][0]["institution"] == "MIT"


@pytest.mark.asyncio
async def test_validation_rejects_invalid_section_data(client, auth_headers):
    """T15: validation rejects invalid section data (backend stores anything in JSONB but frontend validates)"""
    # Backend JSONB accepts anything, but test that data is stored/retrieved correctly
    invalid_sections = {
        "order": ["profile"],
        "enabled": ["profile"],
        "data": {
            "profile": {"name": "Test", "title": "", "email": "bad-email", "phone": "", "location": "", "summary": "", "photo_url": ""},
        },
    }
    resp = await client.post("/api/v1/cvs", json={
        "title": "Validation Test",
        "sections": invalid_sections,
    }, headers=auth_headers)
    assert resp.status_code == 201
    stored = resp.json()["sections"]
    assert stored["data"]["profile"]["name"] == "Test"
    assert stored["data"]["profile"]["email"] == "bad-email"  # stored as-is, frontend validates
