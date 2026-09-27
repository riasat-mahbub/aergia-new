"""Protocol-v9 tailoring integration and public-bundle checks."""

from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest

from app.services import pdf as pdf_service_module
from app.services import tailoring as tailoring_service_module
from app.db.session import async_session
from app.models.tailoring_session import TailoringSession
from app.services.tailoring_skill import build_tailoring_skill_bundle
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.http_schemas.tailoring import PROTOCOL_VERSION
from app.http_schemas.tailoring_evaluation import TAILORING_EVALUATION_VERSION


def test_tailoring_skill_bundle_contains_the_skill_references_and_helper():
    bundle = build_tailoring_skill_bundle()
    with ZipFile(BytesIO(bundle.content)) as archive:
        assert archive.namelist() == [
            "aergia-tailor/SKILL.md",
            "aergia-tailor/references/cv-guidelines.md",
            "aergia-tailor/references/natural-writing.md",
            "aergia-tailor/scripts/session.mjs",
        ]
        assert PROTOCOL_VERSION == 9
        assert 'protocol-version: "9"' in archive.read("aergia-tailor/SKILL.md").decode()
        assert f"export const PROTOCOL_VERSION = {PROTOCOL_VERSION};" in archive.read(
            "aergia-tailor/scripts/session.mjs"
        ).decode()


@pytest.mark.asyncio
async def test_tailoring_skill_download_advertises_protocol_version(client):
    response = await client.get("/api/v1/tailoring/skill.zip")
    assert response.status_code == 200
    assert response.headers["X-Aergia-Skill-Protocol-Version"] == str(PROTOCOL_VERSION)


@pytest.mark.asyncio
async def test_protocol_v9_exposes_every_library_entry_and_rejects_stale_dossier_context(client, monkeypatch):
    from app.services import application as application_service_module

    class _FixtureExtractor:
        def extract(self, job_description):
            return extract_requirements_from_entities(job_description, {"entities": {}})

    class _FixtureScanner(ScannerService):
        def __init__(self):
            super().__init__(extractor=_FixtureExtractor())

    monkeypatch.setattr(application_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module, "configured_extractor_version", lambda: "gliner2.5-structured-v11")

    email = f"full-dossier-tailoring-{uuid4().hex}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "name": "Ada Lovelace",
            "title": "Research Engineer",
            "email": email,
            "phone": "+1 902 555 0100",
            "location": "Halifax, NS",
            "site_text": "Portfolio",
            "site_url": "https://ada.example/profile",
            "summary": [{
                "id": "profile-summary-block",
                "type": "paragraph",
                "items": [{
                    "id": "profile-summary-run",
                    "text": "PROFILE-SUMMARY-SENTINEL",
                    "style": {"link": "https://ada.example/summary"},
                }],
            }],
            "email_link": True,
            "social_links": [{
                "label": "LinkedIn",
                "url": "https://linkedin.example/ada",
                "icon": "linkedin",
            }],
        },
    )
    library_payloads = {
        "experience": [
            {
                "id": "experience-source-row-1",
                "company": "Example Systems",
                "position": "Engineer",
                "start_date": "2018-01",
                "end_date": "2020-12",
                "description": [{
                    "id": "experience-description-block",
                    "type": "paragraph",
                    "items": [{
                        "id": "experience-description-run",
                        "text": "EXPERIENCE-DOSSIER-SENTINEL",
                        "style": {"link": "https://example.test/experience-proof"},
                    }],
                }],
            },
            {"id": "experience-source-row-2", "company": "Independent Lab", "position": "Advisor"},
        ],
        "education": [
            {"id": "education-source-row-1", "institution": "Dalhousie University", "degree": "MSc", "start_date": "2012-09", "end_date": "2014-06"},
            {"id": "education-source-row-2", "institution": "North Star College", "degree": "BSc"},
        ],
        "skill": [
            {"id": "skill-source-row-1", "name": "Python", "category": "Programming"},
            {"id": "skill-source-row-2", "name": "Distributed systems"},
        ],
        "project": [
            {"id": "project-source-row-1", "name": "Community choir archive", "url": "https://projects.example/choir", "start_date": "2021-02", "end_date": "2022-03", "description": "PROJECT-DOSSIER-SENTINEL"},
            {"id": "project-source-row-2", "name": "Oral history index"},
        ],
        "certification": [
            {"id": "certification-source-row-1", "name": "Cloud Practitioner", "issuer": "Example Academy", "date": "2023-05", "credential_url": "https://credentials.example/ada"},
            {"id": "certification-source-row-2", "name": "Secure Systems"},
        ],
        "language": [
            {"id": "language-source-row-1", "language": "French", "proficiency": "Professional"},
            {"id": "language-source-row-2", "language": "English", "proficiency": "Native"},
        ],
        "research": [
            {"id": "research-source-row-1", "title": "Readable Systems", "publication_date": "2024-10", "paper_url": "https://papers.example/readable-systems", "description": "RESEARCH-DOSSIER-SENTINEL"},
            {"id": "research-source-row-2", "title": "Public Data Notes"},
        ],
    }
    library_entries = {}
    for kind, payload in library_payloads.items():
        response = await client.post(
            "/api/v1/library",
            headers=headers,
            json={"kind": kind, "payload": payload},
        )
        assert response.status_code == 201, response.text
        library_entries[kind] = response.json()
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Target",
            "role": "Engineer",
            "job_description": "Build Python APIs on Linux",
            "notes": "Keep the draft focused on evidence from my history.",
        },
    )
    assert application.status_code == 201
    created = await client.post(
        f"/api/v1/applications/{application.json()['id']}/tailoring-sessions?protocol_version={PROTOCOL_VERSION}",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": PROTOCOL_VERSION, "code": created.json()["code"]},
    )
    assert exchanged.status_code == 200
    capability = {"X-Aergia-Tailoring-Capability": exchanged.json()["capability"]}

    context = await client.get("/api/v1/tailoring/context", headers=capability)
    assert context.status_code == 200, context.text
    body = context.json()
    assert body["protocol_version"] == 9
    assert body["job"]["user_instructions"] == "Keep the draft focused on evidence from my history."
    dossier = body["dossier"]
    for profile_value in (
        "Ada Lovelace",
        "Research Engineer",
        email,
        "+1 902 555 0100",
        "Halifax, NS",
        "Portfolio",
        "https://ada.example/profile",
        "PROFILE-SUMMARY-SENTINEL",
        "https://ada.example/summary",
        "LinkedIn",
        "https://linkedin.example/ada",
    ):
        assert profile_value in dossier
    for kind, payload in library_payloads.items():
        assert kind in dossier.lower()
        assert library_entries[kind]["id"] in dossier
        for row in payload:
            assert row["id"] in dossier
    for source_value in (
        "EXPERIENCE-DOSSIER-SENTINEL",
        "https://example.test/experience-proof",
        "2018-01",
        "2020-12",
        "Dalhousie University",
        "2012-09",
        "North Star College",
        "Python",
        "Distributed systems",
        "PROJECT-DOSSIER-SENTINEL",
        "https://projects.example/choir",
        "2021-02",
        "Cloud Practitioner",
        "https://credentials.example/ada",
        "2023-05",
        "French",
        "Native",
        "RESEARCH-DOSSIER-SENTINEL",
        "https://papers.example/readable-systems",
        "2024-10",
        "Public Data Notes",
    ):
        assert source_value in dossier
    assert '"type":' not in dossier
    assert '"items":' not in dossier
    assert '"style":' not in dossier
    assert not {
        "profile",
        "library",
        "previous_cv",
        "scanner",
        "requirements",
        "candidate_index",
        "candidate_evidence",
        "opportunities",
        "retrieved_sources",
        "writer_context_characters",
    } & set(body)
    repeated_context = await client.get("/api/v1/tailoring/context", headers=capability)
    assert repeated_context.status_code == 200
    assert repeated_context.json()["context_hash"] == body["context_hash"]

    candidate = {
        "title": "Example — Engineer",
        "template_id": body["selected_template_id"],
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {"name": "Ada Lovelace", "email": email, "email_link": True, "social_links": []},
            },
            {
                "id": "experience",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [{
                    "id": "experience-source-row-1",
                    "company": "Example Systems",
                    "position": "Engineer",
                    "start_date": "2018-01",
                    "end_date": "2020-12",
                    "description": "EXPERIENCE-DOSSIER-SENTINEL",
                }],
            },
        ],
        "customizations": {},
    }
    async def render_payload(self, template_id, sections, customizations):
        return b"pdf"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", render_payload)
    monkeypatch.setattr(tailoring_service_module, "pdf_page_count", lambda _pdf: 1)
    preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=capability,
        json={"context_hash": body["context_hash"], "candidate": candidate},
    )
    assert preview.status_code == 200, preview.text
    changed = await client.patch(
        f"/api/v1/library/{library_entries['project']['id']}",
        headers=headers,
        json={"payload": [{
            "id": "project-1",
            "name": "Community choir archive",
            "description": "UPDATED-PROJECT-DOSSIER-SENTINEL",
        }]},
    )
    assert changed.status_code == 200, changed.text
    stale_context = await client.get("/api/v1/tailoring/context", headers=capability)
    assert stale_context.status_code == 409
    stale_preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=capability,
        json={"context_hash": body["context_hash"], "candidate": candidate},
    )
    assert stale_preview.status_code == 409
    assert "context changed" in stale_preview.json()["detail"]
    stale_submit = await client.post(
        "/api/v1/tailoring/submit",
        headers=capability,
        json={
            "context_hash": body["context_hash"],
            "evaluation_id": preview.json()["evaluation_id"],
            "candidate_hash": preview.json()["candidate_hash"],
            "candidate": preview.json()["candidate"],
        },
    )
    assert stale_submit.status_code == 409
    assert "context changed" in stale_submit.json()["detail"]
    status = await client.get(f"/api/v1/tailoring/sessions/{created.json()['session_id']}", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] == "stale"


@pytest.mark.asyncio
async def test_tailoring_submit_creates_owned_review_draft_without_promoting_it(client, monkeypatch):
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
    library_entry = await client.post(
        "/api/v1/library",
        headers=headers,
        json={
            "kind": "experience",
            "payload": [{
                "id": "library-experience",
                "company": "Example",
                "position": "Engineer",
                "description": "Built Python APIs.",
            }],
        },
    )
    assert library_entry.status_code == 201
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Example",
            "role": "Engineer",
            "job_description": "Build Python APIs on Linux",
            "notes": "Do not claim AWS; keep the draft user-reviewable.",
        },
    )
    assert application.status_code == 201
    application_id = application.json()["id"]
    legacy_snapshot = {
        key: application.json()[key]
        for key in ("relevance", "quality", "extracted_keywords", "algorithm_version")
    }

    class _FixtureExtractor:
        def extract(self, job_description):
            return extract_requirements_from_entities(job_description, {"entities": {}})

    class _FixtureScanner(ScannerService):
        def __init__(self):
            super().__init__(extractor=_FixtureExtractor())

    monkeypatch.setattr(tailoring_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module, "configured_extractor_version", lambda: "gliner2.5-structured-v11")
    evaluation_calls = 0
    original_evaluate = tailoring_service_module.evaluate_tailoring

    def counted_evaluate(*args, **kwargs):
        nonlocal evaluation_calls
        evaluation_calls += 1
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(tailoring_service_module, "evaluate_tailoring", counted_evaluate)

    created = await client.post(f"/api/v1/applications/{application_id}/tailoring-sessions", headers=headers)
    assert created.status_code == 201
    rejected_v7_exchange = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 7, "code": created.json()["code"]},
    )
    assert rejected_v7_exchange.status_code == 422
    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": PROTOCOL_VERSION, "code": created.json()["code"]},
    )
    assert exchanged.status_code == 200
    capability_headers = {"X-Aergia-Tailoring-Capability": exchanged.json()["capability"]}
    context = await client.get("/api/v1/tailoring/context", headers=capability_headers)
    assert context.status_code == 200
    context_body = context.json()
    assert context_body["job"]["user_instructions"] == "Do not claim AWS; keep the draft user-reviewable."
    assert "Built Python APIs." in context_body["dossier"]
    assert "Ada Lovelace" in context_body["dossier"]
    assert "candidate_index" not in context_body

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
                "data": {"name": "Untrusted Candidate Name", "email": email, "email_link": True, "social_links": []},
            },
            {
                "id": "experience",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [{
                    "id": "experience-1",
                    "company": "Example",
                    "position": "Engineer",
                    "start_date": "2020",
                    "end_date": None,
                    "current": True,
                    "description": "Built Kubernetes APIs.",
                }],
            }
        ],
        "customizations": {},
    }
    preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=capability_headers,
        json={"context_hash": context_body["context_hash"], "candidate": candidate},
    )
    assert preview.status_code == 200
    assert preview.json()["scanner_result"]["schema_version"] == "scanner-v1"
    assert preview.json()["scanner_result"]["versions"]["semantic_score_version"] == "job-fit-v4"
    assert preview.json()["evaluation"]["version"] == TAILORING_EVALUATION_VERSION
    assert preview.json()["evaluation"]["candidate_hash"] == preview.json()["candidate_hash"]
    assert preview.json()["evaluation_id"]
    assert preview.json()["candidate"]["sections"][0]["data"]["name"] == "Ada Lovelace"
    assert preview.json()["candidate"] != candidate
    assert "readiness" not in preview.json()["evaluation"]
    assert "blockers" not in preview.json()["evaluation"]
    assert preview.json()["evaluation"]["risk_findings"] == []

    other_candidate = {**candidate, "title": "Different Candidate"}
    other_preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=capability_headers,
        json={"context_hash": context_body["context_hash"], "candidate": other_candidate},
    )
    assert other_preview.status_code == 200
    mismatched_selection = await client.post(
        "/api/v1/tailoring/submit",
        headers=capability_headers,
        json={
            "context_hash": context_body["context_hash"],
            "evaluation_id": other_preview.json()["evaluation_id"],
            "candidate_hash": preview.json()["candidate_hash"],
            "candidate": preview.json()["candidate"],
        },
    )
    assert mismatched_selection.status_code == 409
    assert "different candidate" in mismatched_selection.json()["detail"]

    other_application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Other Example", "role": "Engineer", "job_description": "Build Python APIs on Linux"},
    )
    assert other_application.status_code == 201
    other_created = await client.post(
        f"/api/v1/applications/{other_application.json()['id']}/tailoring-sessions",
        headers=headers,
    )
    assert other_created.status_code == 201
    other_exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": PROTOCOL_VERSION, "code": other_created.json()["code"]},
    )
    assert other_exchanged.status_code == 200
    other_capability = {"X-Aergia-Tailoring-Capability": other_exchanged.json()["capability"]}
    other_context = await client.get("/api/v1/tailoring/context", headers=other_capability)
    assert other_context.status_code == 200
    wrong_session = await client.post(
        "/api/v1/tailoring/submit",
        headers=other_capability,
        json={
            "context_hash": other_context.json()["context_hash"],
            "evaluation_id": preview.json()["evaluation_id"],
            "candidate_hash": preview.json()["candidate_hash"],
            "candidate": preview.json()["candidate"],
        },
    )
    assert wrong_session.status_code == 409
    assert "unavailable in this session" in wrong_session.json()["detail"]

    stale_submission = await client.post(
        "/api/v1/tailoring/submit",
        headers=capability_headers,
        json={
            "context_hash": context_body["context_hash"],
            "evaluation_id": preview.json()["evaluation_id"],
            "candidate_hash": "f" * 64,
            "candidate": preview.json()["candidate"],
        },
    )
    assert stale_submission.status_code == 409
    assert "changed after preview" in stale_submission.json()["detail"]

    submission_payload = {
        "context_hash": context_body["context_hash"],
        "evaluation_id": preview.json()["evaluation_id"],
        "candidate_hash": preview.json()["candidate_hash"],
        "candidate": preview.json()["candidate"],
        "review_notes": [],
    }
    submitted = await client.post(
        "/api/v1/tailoring/submit",
        headers=capability_headers,
        json=submission_payload,
    )

    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "draft_ready"
    assert submitted.json()["draft_cv_id"]
    assert submitted.json()["evaluation_id"] == preview.json()["evaluation_id"]
    assert submitted.json()["candidate_hash"] == preview.json()["candidate_hash"]
    assert submitted.json()["candidate"] == preview.json()["candidate"]
    assert "editorial_review" not in submitted.json()
    assert submitted.json()["evaluation"]["candidate_hash"] == submitted.json()["candidate_hash"]
    assert evaluation_calls >= 2
    submitted_scan = submitted.json()["scanner_result"]
    preview_scan = preview.json()["scanner_result"]
    submitted_scan.pop("created_at", None)
    preview_scan.pop("created_at", None)
    assert submitted_scan == preview_scan
    replayed = await client.post("/api/v1/tailoring/submit", headers=capability_headers, json=submission_payload)
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["draft_cv_id"] == submitted.json()["draft_cv_id"]
    assert replayed.json()["evaluation_id"] == submitted.json()["evaluation_id"]
    changed_replay = {**submission_payload, "review_notes": ["different request"]}
    conflict = await client.post("/api/v1/tailoring/submit", headers=capability_headers, json=changed_replay)
    assert conflict.status_code == 409
    unchanged_application = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert unchanged_application.json()["cv_id"] is None
    listed_cvs = await client.get("/api/v1/cvs", headers=headers)
    draft_item = next(item for item in listed_cvs.json() if item["id"] == submitted.json()["draft_cv_id"])
    assert draft_item["application"]["id"] == application_id

    # Model a historical protocol-v8 draft with an editorial result. Owner
    # acceptance must keep using its frozen candidate and scanner binding.
    async with async_session() as db:
        stored_session = await db.get(TailoringSession, created.json()["session_id"])
        stored_session.protocol_version = 8
        stored_session.result = {
            **stored_session.result,
            "editorial_review": {
                "review_version": "aergia-editorial-review-v2",
                "evaluation_id": preview.json()["evaluation_id"],
                "candidate_hash": preview.json()["candidate_hash"],
                "findings": [],
            },
            "tailoring_evaluation": {
                "version": "tailoring-evaluation-v1",
                "pass_number": 1,
                "blockers": [{"kind": "blocker", "message": "Historical concern"}],
                "readiness": {"status": "blocked", "submission_allowed": False},
            },
        }
        await db.commit()

    accepted = await client.post(
        f"/api/v1/tailoring/sessions/{created.json()['session_id']}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["protocol_version"] == 8
    assert accepted.json()["cv_id"] == submitted.json()["draft_cv_id"]
    assert accepted.json()["scanner_result"]["schema_version"] == "scanner-v1"
    accepted_application = await client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert accepted_application.json()["cv_id"] == submitted.json()["draft_cv_id"]
    assert accepted_application.json()["scanner_result"]["schema_version"] == "scanner-v1"
    for key, value in legacy_snapshot.items():
        assert accepted_application.json()[key] == value
