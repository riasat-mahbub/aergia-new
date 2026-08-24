"""Application generation provenance, fitting, and CV-link contracts."""

from uuid import uuid4

import pytest

from app.services import application as application_service_module
from app.services import pdf as pdf_service_module


async def _auth_headers(client, prefix: str) -> dict[str, str]:
    email = f"{prefix}-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


async def _set_profile(client, headers, name="Ada Lovelace"):
    response = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "name": name,
            "title": "Platform Engineer",
            "email": None,
            "phone": None,
            "location": "London",
            "site_text": None,
            "site_url": None,
            "summary": "Builds distributed systems.",
            "photo_url": None,
            "email_link": True,
            "social_links": [],
        },
    )
    assert response.status_code == 200


@pytest.fixture
def one_page_pdf(monkeypatch):
    async def render_payload(self, template_id, sections, customizations):
        return b"pdf"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", render_payload)
    monkeypatch.setattr(application_service_module, "pdf_page_count", lambda _: 1)


@pytest.mark.asyncio
async def test_generation_creates_ordered_editable_cv_with_fresh_copies(client, one_page_pdf):
    headers = await _auth_headers(client, "generation-order")
    await _set_profile(client, headers)
    library_rows = [
        ("education", {"id": "edu-source", "institution": "State University", "degree": "Python"}),
        ("skill", {"id": "skill-source", "category": "FastAPI", "items": ["PostgreSQL"]}),
        ("experience", {"id": "exp-source", "company": "Example Labs", "position": "Distributed Systems"}),
        ("language", {"id": "language-source", "language": "Spanish", "proficiency": "Professional"}),
        ("certification", {"id": "cert-source", "name": "Cloud Native"}),
        ("project", {"id": "project-source", "name": "Platform", "tech_stack": ["Python"]}),
        ("research", {"id": "research-source", "title": "Systems Research"}),
    ]
    for kind, row in library_rows:
        created = await client.post("/api/v1/library", headers=headers, json={"kind": kind, "payload": [row]})
        assert created.status_code == 201

    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Example Labs",
            "role": "Platform Engineer",
            "job_description": "Python\nFastAPI\nPostgreSQL\nDistributed Systems\nCloud Native\nPlatform\nSystems Research\nSpanish",
        },
    )
    assert application.status_code == 201
    application_id = application.json()["id"]

    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert generated.status_code == 200
    body = generated.json()
    assert body["cv_id"]
    assert body["application"]["generation_status"] == "ready"
    assert body["application"]["cv_id"] == body["cv_id"]

    cv = (await client.get(f"/api/v1/cvs/{body['cv_id']}", headers=headers)).json()
    assert [section["type"] for section in cv["sections"]] == [
        "profile",
        "education",
        "skills",
        "experience",
        "languages",
        "certifications",
        "projects",
        "research",
    ]
    assert cv["title"] == "Example Labs — Platform Engineer"
    assert cv["description"] == "Tailored for Platform Engineer at Example Labs"
    assert cv["template_id"] == "generic-minimal"
    assert cv["customizations"]["spacing"] == "none"
    assert cv["extra_metadata"]["application_id"] == application_id
    assert cv["extra_metadata"]["generated_by"] == "requirement-v1"
    assert cv["extra_metadata"]["extracted_requirements"]
    assert len({section["id"] for section in cv["sections"]}) == len(cv["sections"])
    row_ids = [row["id"] for section in cv["sections"] if isinstance(section["data"], list) for row in section["data"]]
    assert len(row_ids) == len(set(row_ids))
    assert all(source_id not in row_ids for source_id in [row[1]["id"] for row in library_rows])

    library = (await client.get("/api/v1/library", headers=headers)).json()
    assert {row["id"] for entry in library for row in entry["payload"]} == {
        row[1]["id"] for row in library_rows
    }


@pytest.mark.asyncio
async def test_failed_generation_is_retryable_and_linked_cv_blocks_delete(client, monkeypatch):
    headers = await _auth_headers(client, "generation-retry")
    await _set_profile(client, headers)
    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Retry Co", "role": "Engineer", "job_description": "Python"},
    )
    application_id = created.json()["id"]

    async def fail_render(self, template_id, sections, customizations):
        raise RuntimeError("database path and Chromium traceback must not leak")

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", fail_render)
    failed = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert failed.status_code == 200
    assert failed.json()["application"]["generation_status"] == "failed"
    assert failed.json()["application"]["cv_id"] is None
    assert failed.json()["application"]["generation_error"] == "CV generation failed. Please retry."
    assert "Chromium" not in failed.json()["application"]["generation_error"]

    async def one_page_render(self, template_id, sections, customizations):
        return b"pdf"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", one_page_render)
    monkeypatch.setattr(application_service_module, "pdf_page_count", lambda _: 1)
    retried = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert retried.status_code == 200
    cv_id = retried.json()["cv_id"]
    assert retried.json()["application"]["generation_status"] == "ready"

    blocked = await client.delete(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "CV is linked to an application"

    assert (await client.delete(f"/api/v1/applications/{application_id}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/v1/cvs/{cv_id}", headers=headers)).status_code == 204


@pytest.mark.asyncio
async def test_fit_trims_low_relevance_skill_items_before_rows(client, monkeypatch):
    headers = await _auth_headers(client, "generation-skill-fit")
    await _set_profile(client, headers)
    for kind, row in (
        ("skill", {"id": "skill-source", "category": "Backend", "items": ["Legacy", "Python"]}),
        ("research", {"id": "research-source", "title": "Research"}),
    ):
        created = await client.post("/api/v1/library", headers=headers, json={"kind": kind, "payload": [row]})
        assert created.status_code == 201

    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Fit Co", "role": "Engineer", "job_description": "Python Research"},
    )
    application_id = created.json()["id"]
    page_counts = iter([2, 1])
    async def render_payload(self, template_id, sections, customizations):
        return b"pdf"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", render_payload)
    monkeypatch.setattr(application_service_module, "pdf_page_count", lambda _: next(page_counts))

    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["application"]["fits_one_page"] is True
    cv = (await client.get(f"/api/v1/cvs/{generated.json()['cv_id']}", headers=headers)).json()
    skills = next(section for section in cv["sections"] if section["type"] == "skills")
    assert skills["data"][0]["items"] == ["Python"]
    assert any(section["type"] == "research" for section in cv["sections"])


@pytest.mark.asyncio
async def test_edit_after_generation_recomputes_relevance_without_rewriting_cv(client, one_page_pdf):
    headers = await _auth_headers(client, "generation-edit")
    await _set_profile(client, headers)
    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Edit Co", "role": "Engineer", "job_description": "Python"},
    )
    application_id = created.json()["id"]
    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    assert generated.status_code == 200
    cv_id = generated.json()["cv_id"]
    before_cv = (await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)).json()
    before_application = generated.json()["application"]

    edited = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"role": "Rust", "job_description": "Rust"},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == before_application["status"]
    assert edited.json()["generation_status"] == "ready"
    assert edited.json()["cv_id"] == cv_id
    assert edited.json()["relevance"]["requirements"][0]["requirement"]["text"] == "rust"
    assert before_application["relevance"]["requirements"][0]["requirement"]["text"] == "python"
    assert edited.json()["relevance"]["score"] <= before_application["relevance"]["score"]
    after_cv = (await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)).json()
    assert after_cv["sections"] == before_cv["sections"]


@pytest.mark.asyncio
async def test_direct_cv_save_recomputes_score_without_regenerating(client, one_page_pdf):
    headers = await _auth_headers(client, "generation-cv-save")
    await _set_profile(client, headers)
    library = await client.post(
        "/api/v1/library",
        headers=headers,
        json={"kind": "skill", "payload": [{"id": "skill-source", "category": "Backend", "items": ["Python"]}]},
    )
    assert library.status_code == 201
    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Save Co", "role": "Engineer", "job_description": "Python"},
    )
    application_id = created.json()["id"]
    generated = await client.post(f"/api/v1/applications/{application_id}/generate", headers=headers)
    cv_id = generated.json()["cv_id"]
    before = generated.json()["application"]["relevance"]["score"]
    before_cv = (await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)).json()
    changed_library = await client.patch(
        f"/api/v1/library/{library.json()['id']}",
        headers=headers,
        json={"payload": [{"id": "skill-source", "category": "Backend", "items": ["Rust"]}]},
    )
    assert changed_library.status_code == 200
    unchanged = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert unchanged.json()["relevance"]["score"] == before
    assert (await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)).json()["sections"] == before_cv["sections"]

    sections = before_cv["sections"]
    skills = next(section for section in sections if section["type"] == "skills")
    skills["data"][0]["items"] = ["Rust"]

    saved = await client.patch(f"/api/v1/cvs/{cv_id}", headers=headers, json={"sections": sections})
    assert saved.status_code == 200
    refreshed = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["relevance"]["score"] < before
    assert refreshed.json()["cv_id"] == cv_id
