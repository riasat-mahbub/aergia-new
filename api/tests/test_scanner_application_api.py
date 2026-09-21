from uuid import uuid4

import pytest

from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.routes import applications as application_routes_module
from app.services import application as application_service_module
from app.services import pdf as pdf_service_module
from app.services.pdf import PDFUnavailableError


class _FixtureExtractor:
    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


async def _auth_headers(client) -> dict[str, str]:
    email = f"scanner-api-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


@pytest.mark.asyncio
async def test_scanner_endpoint_persists_new_result_separately_from_legacy_relevance(client, monkeypatch):
    headers = await _auth_headers(client)

    async def no_pdf(self, template_id, sections, customizations):
        raise PDFUnavailableError("test render skipped")

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", no_pdf)

    created = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Example Labs",
            "role": "Python Developer",
            "job_description": "What You Bring\nFamiliarity with Python.",
        },
    )
    assert created.status_code == 201
    assert created.json()["scanner_status"] == "not_scanned"
    application_id = created.json()["id"]

    missing_cv = await client.post(f"/api/v1/applications/{application_id}/scan", headers=headers)
    assert missing_cv.status_code == 409

    cv_response = await client.post(
        "/api/v1/cvs",
        headers=headers,
        json={
            "title": "Example CV",
            "sections": [
                {
                    "id": "profile",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"name": "Example Candidate", "email": "candidate@example.com", "title": "Python Developer"},
                },
                {
                    "id": "experience",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "python-job", "position": "Developer", "description": "Built Python APIs."}],
                },
            ],
        },
    )
    assert cv_response.status_code == 201
    cv_id = cv_response.json()["id"]
    linked = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"cv_id": cv_id},
    )
    assert linked.status_code == 200
    assert linked.json()["cv_id"] == cv_id
    assert linked.json()["scanner_status"] == "not_scanned"

    def scanner_factory():
        return ScannerService(extractor=_FixtureExtractor())

    monkeypatch.setattr(application_service_module, "ScannerService", scanner_factory)
    monkeypatch.setattr(
        application_routes_module,
        "configured_extractor_version",
        lambda: "gliner2.5-structured-v6",
    )

    scanned = await client.post(f"/api/v1/applications/{application_id}/scan", headers=headers)

    assert scanned.status_code == 200
    body = scanned.json()
    assert body["scanner_result"]["schema_version"] == "scanner-v1"
    assert body["scanner_result"]["semantic"]["status"] == "evaluated"
    assert body["scanner_result"]["lexical"]["terms"][0]["term"] == "Python"
    assert body["scanner_result"]["pdf_recovery"]["status"] == "unavailable"
    assert body["scanner_status"] == "current"
    assert body["relevance"] == linked.json()["relevance"]

    persisted = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert persisted.json()["scanner_result"]["schema_version"] == "scanner-v1"

    edited_job = await client.patch(
        f"/api/v1/applications/{application_id}",
        headers=headers,
        json={"job_description": "What You Bring\nFamiliarity with Python and Docker."},
    )
    assert edited_job.status_code == 200
    assert edited_job.json()["scanner_result"] is None
    assert edited_job.json()["scanner_status"] == "needs_rescan"

    rescanned = await client.post(f"/api/v1/applications/{application_id}/scan", headers=headers)
    assert rescanned.status_code == 200
    assert rescanned.json()["scanner_result"] is not None
    assert rescanned.json()["scanner_status"] == "current"

    edited_cv = await client.patch(
        f"/api/v1/cvs/{cv_id}",
        headers=headers,
        json={
            "sections": [
                {
                    "id": "profile",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"name": "Example Candidate", "email": "candidate@example.com", "title": "Python Developer"},
                },
                {
                    "id": "experience",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [
                        {
                            "id": "python-job",
                            "position": "Developer",
                            "description": "Built Python and Docker APIs.",
                        }
                    ],
                },
            ]
        },
    )
    assert edited_cv.status_code == 200
    refreshed = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["scanner_result"] is None
    assert refreshed.json()["scanner_status"] == "needs_rescan"

    rescanned_after_cv_edit = await client.post(f"/api/v1/applications/{application_id}/scan", headers=headers)
    assert rescanned_after_cv_edit.status_code == 200
    assert rescanned_after_cv_edit.json()["scanner_status"] == "current"
    assert rescanned_after_cv_edit.json()["scanner_result"]["input_fingerprints"]["cv_content_sha256"] != body[
        "scanner_result"
    ]["input_fingerprints"]["cv_content_sha256"]
    persisted_after_cv_edit = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert persisted_after_cv_edit.status_code == 200
    assert persisted_after_cv_edit.json()["scanner_result"]["schema_version"] == "scanner-v1"

    other_application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Other Labs", "role": "Engineer", "job_description": "Python"},
    )
    duplicate_link = await client.patch(
        f"/api/v1/applications/{other_application.json()['id']}",
        headers=headers,
        json={"cv_id": cv_id},
    )
    assert duplicate_link.status_code == 409
