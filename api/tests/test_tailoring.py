"""Phase 1 local-agent tailoring protocol integration tests."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from app.db.session import async_session
from app.models.application import Application
from app.models.tailoring_session import TailoringSession


async def _auth_headers(client, prefix: str) -> dict[str, str]:
    email = f"{prefix}-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


async def _ready_application(client, headers: dict[str, str]) -> tuple[str, str]:
    application_response = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Example Labs",
            "role": "Platform Engineer",
            "job_description": "Build reliable Python API services",
        },
    )
    assert application_response.status_code == 201
    application_id = application_response.json()["id"]

    cv_response = await client.post(
        "/api/v1/cvs",
        headers=headers,
        json={
            "title": "Platform CV",
            "template_id": "generic-minimal",
            "sections": [
                {
                    "id": "section-experience",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [
                        {
                            "id": "entry-1",
                            "company": "Example Labs",
                            "position": "Engineer",
                            "description": "Built reliable API services.",
                        }
                    ],
                }
            ],
        },
    )
    assert cv_response.status_code == 201
    cv_id = cv_response.json()["id"]

    async with async_session() as session:
        application = await session.get(Application, application_id)
        assert application is not None
        application.cv_id = cv_id
        application.generation_status = "ready"
        await session.commit()
    return application_id, cv_id


async def test_tailoring_skill_bundle_is_public_and_installable(client):
    response = await client.get("/api/v1/tailoring/skill.zip")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="aergia-tailor.zip"'
    assert response.headers["x-aergia-skill-protocol-version"] == "1"
    with ZipFile(BytesIO(response.content)) as archive:
        assert "aergia-tailor/SKILL.md" in archive.namelist()
        assert "aergia-tailor/scripts/validate-patch.mjs" in archive.namelist()


async def test_tailoring_protocol_create_exchange_evidence_submit_apply_score(client, monkeypatch):
    headers = await _auth_headers(client, "tailoring-owner")
    application_id, cv_id = await _ready_application(client, headers)

    # The protocol must use the persisted requirement snapshot. If either
    # existing service refresh path is accidentally called, this test fails.
    import app.services.application as application_service_module
    import app.services.cv as cv_service_module

    def extractor_must_not_run(*_args, **_kwargs):
        raise AssertionError("tailoring submission must use stored requirements")

    monkeypatch.setattr(application_service_module, "extract_requirements", extractor_must_not_run)
    monkeypatch.setattr(cv_service_module, "extract_requirements", extractor_must_not_run)

    created = await client.post(
        f"/api/v1/applications/{application_id}/tailoring-sessions",
        headers=headers,
    )
    assert created.status_code == 201
    session = created.json()
    assert session["application_id"] == application_id
    assert session["cv_id"] == cv_id
    assert len(session["code"]) >= 32
    assert session["session_url"].endswith(f"/agent/tailor/{session['session_id']}")
    assert session["skill_url"].endswith("/api/v1/tailoring/skill.zip")
    assert "Use the Aergia tailoring skill" in session["prompt"]
    assert session["code"] in session["prompt"]
    assert session["skill_url"] in session["prompt"]

    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 1, "code": session["code"]},
    )
    assert exchanged.status_code == 200
    capability = exchanged.json()["capability"]
    assert capability != session["code"]

    evidence = await client.get(
        "/api/v1/tailoring/evidence",
        headers={"X-Aergia-Tailoring-Capability": capability},
    )
    assert evidence.status_code == 200
    evidence_body = evidence.json()
    assert evidence_body["protocol_version"] == 1
    assert evidence_body["cv"]["id"] == cv_id
    assert evidence_body["target_cv"]["id"] != cv_id
    assert all(
        not section["data"]
        for section in evidence_body["target_cv"]["sections"]
        if section["type"] != "profile"
    )
    assert all(
        section["enabled"] is False
        for section in evidence_body["target_cv"]["sections"]
        if section["type"] != "profile"
    )
    assert evidence_body["job"]["description"] == "Build reliable Python API services"
    assert "user_id" not in evidence_body
    assert "extra_metadata" not in evidence_body["cv"]
    assert evidence_body["protected_facts"]["profile"]
    assert evidence_body["requirements"]

    submitted = await client.post(
        "/api/v1/tailoring/submit",
        headers={"X-Aergia-Tailoring-Capability": capability},
        json={
            "protocol_version": 1,
            "base_revision": evidence_body["base_revision"],
            "base_hash": evidence_body["base_hash"],
            "changes": [
                {
                    "operation": "create_section",
                    "section": {
                        "id": "tailoring-highlights",
                        "type": "extras",
                        "title": "Selected Highlights",
                        "enabled": True,
                        "data": [
                            {
                                "id": "highlight-1",
                                "title": "Relevant delivery",
                                "fields": [
                                    {"label": "Evidence", "value": "Built reliable API services."}
                                ],
                            }
                        ],
                    },
                    "reason": "Add a concise section for evidence relevant to this application.",
                    "evidence": [
                        {
                            "source": "cv",
                            "section_id": "section-experience",
                            "entry_id": "entry-1",
                            "field_path": "*",
                        }
                    ],
                },
                {
                    "operation": "replace_rich_text",
                    "section_id": evidence_body["target_cv"]["sections"][0]["id"],
                    "field": "summary",
                    "value": "Built dependable API services.",
                    "reason": "Fixed protocol test patch",
                },
                {
                    "operation": "report_gap",
                    "requirement_id": evidence_body["requirements"][0]["id"],
                    "requirement": evidence_body["requirements"][0]["text"],
                    "reason": "No supporting evidence exists.",
                },
            ],
        },
    )
    assert submitted.status_code == 200
    submitted_body = submitted.json()
    assert submitted_body["application_id"] == application_id
    assert submitted_body["source_cv_id"] == cv_id
    assert submitted_body["cv_id"] != cv_id
    assert submitted_body["new_revision"] == 1
    assert submitted_body["applied_operations"] == ["create_section", "replace_rich_text", "report_gap"]
    assert submitted_body["gaps"] == [{"requirement": evidence_body["requirements"][0]["text"], "reason": "No supporting evidence exists."}]
    assert submitted_body["relevance"]["status"] == "evaluated"
    assert submitted_body["relevance"]["requirements"][0]["tailoring_feedback"] == ["No supporting evidence exists."]
    async with async_session() as session_db:
        persisted_session = await session_db.get(TailoringSession, session["session_id"])
        assert persisted_session is not None
        assert persisted_session.reported_gaps == submitted_body["gaps"]

    updated_cv = await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert updated_cv.status_code == 200
    assert updated_cv.json()["sections"][0]["data"][0]["description"] == "Built reliable API services."

    fresh_cv = await client.get(f"/api/v1/cvs/{submitted_body['cv_id']}", headers=headers)
    assert fresh_cv.status_code == 200
    assert fresh_cv.json()["sections"][0]["data"]["summary"] == "Built dependable API services."
    assert fresh_cv.json()["sections"][-1]["id"] == "tailoring-highlights"

    updated_application = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert updated_application.status_code == 200
    assert updated_application.json()["cv_id"] == submitted_body["cv_id"]
    assert updated_application.json()["relevance"] == submitted_body["relevance"]

    session_status = await client.get(
        f"/api/v1/tailoring/sessions/{session['session_id']}",
        headers=headers,
    )
    assert session_status.status_code == 200
    assert session_status.json()["status"] == "applied"
    assert session_status.json()["result"]["relevance"] == submitted_body["relevance"]


async def test_tailoring_rejects_invalid_target_atomically_and_allows_no_token(client):
    headers = await _auth_headers(client, "tailoring-invalid")
    application_id, cv_id = await _ready_application(client, headers)
    created = await client.post(f"/api/v1/applications/{application_id}/tailoring-sessions", headers=headers)
    assert created.status_code == 201
    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 1, "code": created.json()["code"]},
    )
    assert exchanged.status_code == 200
    capability = exchanged.json()["capability"]

    no_capability = await client.get("/api/v1/tailoring/evidence")
    assert no_capability.status_code == 401
    evidence = await client.get(
        "/api/v1/tailoring/evidence",
        headers={"X-Aergia-Tailoring-Capability": capability},
    )
    assert evidence.status_code == 200
    evidence_body = evidence.json()

    invalid = await client.post(
        "/api/v1/tailoring/submit",
        headers={"X-Aergia-Tailoring-Capability": capability},
        json={
            "protocol_version": 1,
            "base_revision": evidence_body["base_revision"],
            "base_hash": evidence_body["base_hash"],
            "changes": [
                {
                    "operation": "replace_description",
                    "section_id": "section-experience",
                    "entry_id": "missing-entry",
                    "value": "Must not be stored",
                }
            ],
        },
    )
    assert invalid.status_code == 422

    unchanged = await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["sections"][0]["data"][0]["description"] == "Built reliable API services."

    unsupported = await client.post(
        "/api/v1/tailoring/submit",
        headers={"X-Aergia-Tailoring-Capability": capability},
        json={
            "protocol_version": 1,
            "changes": [{"operation": "rewrite_rich_text", "value": []}],
        },
    )
    assert unsupported.status_code == 422


async def test_tailoring_code_is_one_time_and_expiry_is_enforced(client):
    headers = await _auth_headers(client, "tailoring-replay")
    application_id, _cv_id = await _ready_application(client, headers)
    created = await client.post(f"/api/v1/applications/{application_id}/tailoring-sessions", headers=headers)
    assert created.status_code == 201
    code = created.json()["code"]

    first_exchange = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 1, "code": code},
    )
    assert first_exchange.status_code == 200
    replay = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 1, "code": code},
    )
    assert replay.status_code == 409

    expired_created = await client.post(f"/api/v1/applications/{application_id}/tailoring-sessions", headers=headers)
    assert expired_created.status_code == 201
    expired_session_id = expired_created.json()["session_id"]
    async with async_session() as session:
        expired = await session.get(TailoringSession, expired_session_id)
        assert expired is not None
        expired.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await session.commit()

    expired_exchange = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 1, "code": expired_created.json()["code"]},
    )
    assert expired_exchange.status_code == 410
