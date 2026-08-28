"""One-page fit pass contracts for generated applications."""

from uuid import uuid4

import pytest

from app.services import application as application_service_module
from app.services import pdf as pdf_service_module


async def _auth_headers(client) -> dict[str, str]:
    email = f"fit-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


@pytest.mark.asyncio
async def test_fit_removes_lowest_row_with_reverse_section_priority(client, monkeypatch):
    headers = await _auth_headers(client)
    profile = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "name": "Fit User",
            "title": None,
            "email": None,
            "phone": None,
            "location": None,
            "site_text": None,
            "site_url": None,
            "summary": None,
            "photo_url": None,
            "email_link": True,
            "social_links": [],
        },
    )
    assert profile.status_code == 200
    for kind, row in (
        ("skill", {"id": "skill-source", "category": "Python"}),
        ("research", {"id": "research-source", "title": "Research"}),
    ):
        created = await client.post("/api/v1/library", headers=headers, json={"kind": kind, "payload": [row]})
        assert created.status_code == 201

    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Fit Co", "role": "Engineer", "job_description": "Python\nResearch"},
    )
    application_id = created.json()["id"]
    calls = 0

    async def render_payload(self, template_id, sections, customizations):
        nonlocal calls
        calls += 1
        return b"pdf"

    def page_count(_pdf):
        return 2 if calls == 1 else 1

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", render_payload)
    monkeypatch.setattr(application_service_module, "pdf_page_count", page_count)

    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["application"]["fits_one_page"] is True
    assert calls == 2

    cv = (await client.get(f"/api/v1/cvs/{generated.json()['cv_id']}", headers=headers)).json()
    assert [section["type"] for section in cv["sections"]] == ["profile", "skills"]
    assert cv["sections"][1]["data"][0]["category"] == "Python"
