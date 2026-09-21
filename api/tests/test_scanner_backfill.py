from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.session import async_session
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.freshness import scanner_result_freshness
from app.scanner.service import ScannerService
from app.scanner.service import LEXICAL_VERSION, MATCHER_VERSION, fingerprint_scan_inputs
from app.scanner.pdf_recovery import PDF_ANALYSIS_VERSION
from app.scanner.quality import QUALITY_VERSION
from app.scanner.scoring import (
    CLASSIFICATION_WARNING_VERSION,
    LEXICAL_SCORE_VERSION,
    PDF_SCORE_VERSION,
    SEMANTIC_SCORE_VERSION,
)
from app.services import application as application_service_module
from app.services import pdf as pdf_service_module
from app.services.pdf import PDFUnavailableError
from app.commands import scanner_backfill


def test_current_result_requires_matching_inputs_and_installed_versions():
    job_description = "Python developer"
    cv = {"sections": [{"type": "experience", "description": "Built APIs."}]}
    fingerprints = fingerprint_scan_inputs(job_description, cv).model_dump(mode="json")
    result = {
        "schema_version": "scanner-v1",
        "input_fingerprints": fingerprints,
        "versions": {
            "extractor_version": "model@revision",
            "matcher_version": MATCHER_VERSION,
            "lexical_version": LEXICAL_VERSION,
            "quality_version": QUALITY_VERSION,
            "pdf_analysis_version": PDF_ANALYSIS_VERSION,
            "semantic_score_version": SEMANTIC_SCORE_VERSION,
            "lexical_score_version": LEXICAL_SCORE_VERSION,
            "pdf_score_version": PDF_SCORE_VERSION,
            "classification_warning_version": CLASSIFICATION_WARNING_VERSION,
        },
    }

    assert scanner_backfill.scanner_result_is_current(
        result,
        job_description,
        cv,
        extractor_version="model@revision",
    )
    assert not scanner_backfill.scanner_result_is_current(
        result,
        "Updated Python developer role",
        cv,
        extractor_version="model@revision",
    )
    old_score_result = {**result, "versions": {**result["versions"], "semantic_score_version": "job-fit-v1"}}
    assert not scanner_backfill.scanner_result_is_current(
        old_score_result,
        job_description,
        cv,
        extractor_version="model@revision",
    )


def test_freshness_diagnostics_identify_changed_inputs_and_subsystems():
    job_description = "Python developer"
    cv = {"sections": [{"type": "experience", "description": "Built APIs."}]}
    result = {
        "schema_version": "scanner-v1",
        "input_fingerprints": fingerprint_scan_inputs(job_description, cv).model_dump(mode="json"),
        "versions": {
            "extractor_version": "model@revision",
            "matcher_version": MATCHER_VERSION,
            "lexical_version": LEXICAL_VERSION,
            "quality_version": QUALITY_VERSION,
            "pdf_analysis_version": PDF_ANALYSIS_VERSION,
            "semantic_score_version": SEMANTIC_SCORE_VERSION,
            "lexical_score_version": LEXICAL_SCORE_VERSION,
            "pdf_score_version": PDF_SCORE_VERSION,
            "classification_warning_version": CLASSIFICATION_WARNING_VERSION,
        },
    }

    current = scanner_result_freshness(result, job_description, cv, extractor_version="model@revision")
    assert current == {"current": True, "reasons": []}

    stale = scanner_result_freshness(
        {**result, "versions": {**result["versions"], "matcher_version": "old-matcher"}},
        "Updated Python developer",
        cv,
        extractor_version="new-model@revision",
    )
    assert stale["current"] is False
    assert stale["reasons"] == [
        "job_changed",
        "extractor_version_changed",
        "matcher_version_changed",
    ]

    version_reason_cases = [
        ("lexical_version", "lexical_version_changed"),
        ("quality_version", "quality_version_changed"),
        ("pdf_analysis_version", "pdf_version_changed"),
        ("semantic_score_version", "semantic_score_version_changed"),
        ("lexical_score_version", "lexical_score_version_changed"),
        ("pdf_score_version", "pdf_score_version_changed"),
        ("classification_warning_version", "classification_warning_version_changed"),
    ]
    for version_field, reason in version_reason_cases:
        old_version = {
            **result,
            "versions": {**result["versions"], version_field: "old-version"},
        }
        assert scanner_result_freshness(old_version, job_description, cv)["reasons"] == [reason]

    assert scanner_result_freshness({}, job_description, cv)["reasons"] == ["malformed_result"]


class _FixtureExtractor:
    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


async def _auth_headers(client) -> dict[str, str]:
    email = f"scanner-backfill-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


async def _create_application_with_cv(client, headers, *, role: str, description: str) -> tuple[str, str]:
    application_response = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Backfill Labs", "role": role, "job_description": description},
    )
    assert application_response.status_code == 201
    application_id = application_response.json()["id"]

    cv_response = await client.post(
        "/api/v1/cvs",
        headers=headers,
        json={
            "title": f"{role} CV",
            "sections": [
                {
                    "id": "profile",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"name": "Backfill Candidate", "email": "candidate@example.com"},
                },
                {
                    "id": "experience",
                    "type": "experience",
                    "title": "Experience",
                    "enabled": True,
                    "data": [{"id": "job", "position": "Developer", "description": "Built Python APIs."}],
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
    return application_id, cv_id


@pytest.mark.asyncio
async def test_backfill_is_idempotent_and_leaves_legacy_fields_untouched(client, monkeypatch):
    headers = await _auth_headers(client)

    async def no_pdf(self, template_id, sections, customizations):
        raise PDFUnavailableError("test render skipped")

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", no_pdf)

    application_id, _cv_id = await _create_application_with_cv(
        client,
        headers,
        role="Python Developer",
        description="What You Bring\nFamiliarity with Python.",
    )
    before = (await client.get(f"/api/v1/applications/{application_id}", headers=headers)).json()
    legacy_fields = {
        field: before[field]
        for field in ("relevance", "algorithm_version", "quality", "extracted_keywords")
    }

    monkeypatch.setattr(
        application_service_module,
        "ScannerService",
        lambda: ScannerService(extractor=_FixtureExtractor()),
    )
    monkeypatch.setattr(scanner_backfill, "_configured_extractor_version", lambda: "gliner2.5-structured-v7")

    dry_run = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        application_id=application_id,
        dry_run=True,
    )
    assert dry_run.scanned == 1
    assert dry_run.failed == 0
    after_dry_run = (await client.get(f"/api/v1/applications/{application_id}", headers=headers)).json()
    assert after_dry_run["scanner_result"] is None
    assert {field: after_dry_run[field] for field in legacy_fields} == legacy_fields

    first_run = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        application_id=application_id,
    )
    assert first_run.scanned == 1
    stored = (await client.get(f"/api/v1/applications/{application_id}", headers=headers)).json()
    assert stored["scanner_result"]["schema_version"] == "scanner-v1"
    assert {field: stored[field] for field in legacy_fields} == legacy_fields

    second_run = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        application_id=application_id,
    )
    assert second_run.scanned == 0
    assert second_run.skipped == 1

    missing_only_run = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        application_id=application_id,
        only_missing=True,
    )
    assert missing_only_run.skipped == 1

    forced_run = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        application_id=application_id,
        force=True,
    )
    assert forced_run.scanned == 1
    rescanned = (await client.get(f"/api/v1/applications/{application_id}", headers=headers)).json()
    assert {field: rescanned[field] for field in legacy_fields} == legacy_fields


@pytest.mark.asyncio
async def test_backfill_continues_after_one_application_fails(client, monkeypatch):
    headers = await _auth_headers(client)

    async def no_pdf(self, template_id, sections, customizations):
        raise PDFUnavailableError("test render skipped")

    monkeypatch.setattr(pdf_service_module.PDFService, "render_payload", no_pdf)

    good_application_id, _ = await _create_application_with_cv(
        client,
        headers,
        role="Python Developer",
        description="What You Bring\nFamiliarity with Python.",
    )
    failed_application_id, _ = await _create_application_with_cv(
        client,
        headers,
        role="Failing Developer",
        description="What You Bring\nFamiliarity with Docker.",
    )

    class _SelectiveScanner:
        def scan(self, job_description, cv, *, pdf_bytes=None):
            if "Docker" in job_description:
                raise RuntimeError("fixture failure")
            return ScannerService(extractor=_FixtureExtractor()).scan(job_description, cv, pdf_bytes=pdf_bytes)

    monkeypatch.setattr(application_service_module, "ScannerService", _SelectiveScanner)

    async def selected_ids(session_factory, *, batch_size, limit, application_id, report):
        assert limit is None
        yield [failed_application_id, good_application_id]

    monkeypatch.setattr(scanner_backfill, "_application_ids", selected_ids)
    report = await scanner_backfill.run_backfill(session_factory=async_session, batch_size=2)

    assert report.failed == 1
    assert report.scanned == 1
    assert report.failures == [{"application_id": failed_application_id, "error_type": "RuntimeError"}]
    assert (await client.get(f"/api/v1/applications/{good_application_id}", headers=headers)).json()["scanner_result"]


@pytest.mark.asyncio
async def test_backfill_limit_caps_total_applications_across_database_pages(client):
    headers = await _auth_headers(client)
    for index in range(3):
        response = await client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "company": "Limit Labs",
                "role": f"Developer {index}",
                "job_description": "What You Bring\nFamiliarity with Python.",
            },
        )
        assert response.status_code == 201

    report = await scanner_backfill.run_backfill(
        session_factory=async_session,
        batch_size=1,
        limit=2,
    )

    assert report.failed == 0
    assert report.scanned + report.skipped + report.unscannable == 2
