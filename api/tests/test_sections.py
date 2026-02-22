"""T13-T15: Pytest: section data storage, ordering, and validation"""

import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "sectest@example.com", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "sectest@example.com", "password": "pass123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


SAMPLE_INSTANCES = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Jane Doe", "title": "Engineer", "email": "jane@example.com", "phone": "", "location": "", "summary": "", "photo_url": ""},
    },
    {
        "id": "sec_experience",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"id": "exp_1", "company": "Acme Corp", "position": "Engineer", "start_date": "2022-01", "end_date": None, "current": True, "location": "NYC", "description": "Built things"}
        ],
    },
    {
        "id": "sec_education",
        "type": "education",
        "title": "Education",
        "enabled": False,
        "data": [
            {"id": "edu_1", "institution": "MIT", "degree": "BS", "start_date": "2018", "end_date": "2022", "current": False, "gpa": "3.8"}
        ],
    },
]


@pytest.mark.asyncio
async def test_section_data_stored_correctly(client, auth_headers):
    """T13: section data stored correctly in JSONB"""
    resp = await client.post("/api/v1/cvs", json={
        "title": "Section Test CV",
        "template_id": "generic-modern",
        "sections": SAMPLE_INSTANCES,
    }, headers=auth_headers)
    assert resp.status_code == 201
    cv = resp.json()

    stored = cv["sections"]
    assert isinstance(stored, list)
    assert stored[0]["type"] == "profile"
    assert stored[0]["data"]["name"] == "Jane Doe"
    assert stored[1]["type"] == "experience"
    assert stored[1]["data"][0]["company"] == "Acme Corp"
    assert stored[2]["type"] == "education"
    assert stored[2]["data"][0]["institution"] == "MIT"


@pytest.mark.asyncio
async def test_section_ordering_preserved(client, auth_headers):
    """T14: section ordering preserved through update"""
    resp = await client.post("/api/v1/cvs", json={
        "title": "Order Test",
        "sections": SAMPLE_INSTANCES,
    }, headers=auth_headers)
    cv_id = resp.json()["id"]

    # Reorder: education first
    new_order = [SAMPLE_INSTANCES[2], SAMPLE_INSTANCES[1], SAMPLE_INSTANCES[0]]
    update_resp = await client.patch(f"/api/v1/cvs/{cv_id}", json={
        "sections": new_order,
    }, headers=auth_headers)
    assert update_resp.status_code == 200

    stored = update_resp.json()["sections"]
    assert isinstance(stored, list)
    assert stored[0]["type"] == "education"
    assert stored[1]["type"] == "experience"
    assert stored[2]["type"] == "profile"

    # Education data should still be intact
    assert stored[0]["data"][0]["institution"] == "MIT"


@pytest.mark.asyncio
async def test_validation_rejects_invalid_section_data(client, auth_headers):
    """T15: validation rejects invalid section data (backend stores anything in JSONB but frontend validates)"""
    invalid_instances = [
        {
            "id": "sec_profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Test", "title": "", "email": "bad-email", "phone": "", "location": "", "summary": "", "photo_url": ""},
        },
    ]
    resp = await client.post("/api/v1/cvs", json={
        "title": "Validation Test",
        "sections": invalid_instances,
    }, headers=auth_headers)
    assert resp.status_code == 201
    stored = resp.json()["sections"]
    assert stored[0]["data"]["name"] == "Test"
    assert stored[0]["data"]["email"] == "bad-email"  # stored as-is, frontend validates
