"""Protocol-v2 tailoring integration and public-bundle checks."""

from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest

from app.services import pdf as pdf_service_module
from app.services import tailoring as tailoring_service_module
from app.services.tailoring_skill import build_tailoring_skill_bundle


def test_tailoring_skill_bundle_contains_v2_candidate_workflow():
    bundle = build_tailoring_skill_bundle()
    with ZipFile(BytesIO(bundle.content)) as archive:
        names = set(archive.namelist())
        assert "aergia-tailor/SKILL.md" in names
        assert "aergia-tailor/scripts/session.mjs" in names
        assert "aergia-tailor/scripts/validate-candidate.mjs" in names
        assert not any(name.endswith("validate-patch.mjs") for name in names)
        skill = archive.read("aergia-tailor/SKILL.md").decode()
        assert 'protocol-version: "2"' in skill


@pytest.mark.asyncio
async def test_tailoring_submit_creates_an_unlinked_review_draft(client, monkeypatch):
    email = f"tailoring-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}

    profile = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={"name": "Ada Lovelace", "email": email, "email_link": True, "social_links": []},
    )
    assert profile.status_code == 200
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Example", "role": "Engineer", "job_description": "Build Python APIs on Linux"},
    )
    assert application.status_code == 201
    application_id = application.json()["id"]

    created = await client.post(f"/api/v1/applications/{application_id}/tailoring-sessions", headers=headers)
    assert created.status_code == 201
    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 2, "code": created.json()["code"]},
    )
    assert exchanged.status_code == 200
    capability_headers = {"X-Aergia-Tailoring-Capability": exchanged.json()["capability"]}
    context = await client.get("/api/v1/tailoring/context", headers=capability_headers)
    assert context.status_code == 200

    async def render_payload(self, template_id, sections, customizations):
        return b"pdf"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", render_payload)
    monkeypatch.setattr(tailoring_service_module, "pdf_page_count", lambda _pdf: 1)
    candidate = {
        "title": "Example — Engineer",
        "template_id": "generic-minimal",
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {"name": "Ada Lovelace", "email": email, "email_link": True, "social_links": []},
            }
        ],
        "customizations": {},
    }
    submitted = await client.post(
        "/api/v1/tailoring/submit",
        headers=capability_headers,
        json={"context_hash": context.json()["context_hash"], "candidate": candidate, "review_notes": []},
    )

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "draft_ready"
    assert submitted.json()["draft_cv_id"]
    unchanged_application = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert unchanged_application.json()["cv_id"] is None
