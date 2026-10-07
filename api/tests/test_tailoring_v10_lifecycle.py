"""Owner review, acceptance, and cleanup lifecycle coverage for protocol v10."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.session import async_session
from app.http_schemas.cv import CVCreate
from app.models.application import Application
from app.models.cv import CV
from app.models.tailoring_evaluation import (
    TAILORING_EVALUATION_AGENT_PREVIEW,
    TAILORING_EVALUATION_OWNER_REVIEW,
    TailoringEvaluationRecord,
)
from app.models.tailoring_replacement_reservation import (
    TAILORING_REPLACEMENT_RELEASED,
    TailoringReplacementReservation,
)
from app.models.tailoring_session import TailoringSession
from app.models.template import Template
from app.models.user import User
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.services import pdf as pdf_service_module
from app.services import tailoring as tailoring_service_module
from app.services.cv import CVService
from app.services.tailoring import TailoringService


class _FixtureExtractor:
    extractor_version = "gliner2.5-structured-v11"

    def extract(self, description: str):
        return extract_requirements_from_entities(description, {"entities": {}})


class _FixtureScanner(ScannerService):
    def __init__(self):
        super().__init__(extractor=_FixtureExtractor())


@pytest.fixture(autouse=True)
def offline_tailoring_and_pdf(monkeypatch):
    from app.services import application as application_service_module

    monkeypatch.setattr(application_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module, "configured_extractor_version", lambda: "gliner2.5-structured-v11")
    rendered: list[bytes] = []

    async def render_manifest_payload(self, manifest, sections, customizations):
        description = "empty"
        for section in sections:
            if section.get("type") == "experience" and section.get("data"):
                description = str(section["data"][0].get("description", "empty"))
                break
        pdf = f"fixture-pdf:{description}".encode()
        rendered.append(pdf)
        return pdf

    monkeypatch.setattr(pdf_service_module.PDFService, "render_manifest_payload", render_manifest_payload)
    monkeypatch.setattr(tailoring_service_module, "pdf_page_count", lambda _pdf: 1)
    return rendered


def _profile(email: str) -> dict:
    return {
        "name": "Ada Lovelace",
        "title": "Research Engineer",
        "email": email,
        "phone": "+1 902 555 0100",
        "location": "Halifax, NS",
        "site_text": "Portfolio",
        "site_url": "https://ada.example/profile",
        "summary": "Original profile summary.",
        "email_link": True,
        "social_links": [],
    }


async def _owner_and_application(client, *, with_source: bool = False):
    email = f"tailoring-lifecycle-{uuid4().hex}@example.com"
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201, registered.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    profile = _profile(email)
    saved_profile = await client.put("/api/v1/profile", headers=headers, json=profile)
    assert saved_profile.status_code == 200, saved_profile.text
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Example Systems",
            "role": "Engineer",
            "job_description": "Build durable Python APIs and support production services.",
            "notes": "Keep claims grounded in the source experience.",
        },
    )
    assert application.status_code == 201, application.text
    source_id = None
    if with_source:
        source = await client.post(
            "/api/v1/cvs",
            headers=headers,
            json={
                "title": "Source CV",
                "template_id": "generic-minimal",
                "sections": [
                    {
                        "id": "profile",
                        "type": "profile",
                        "title": "Profile",
                        "enabled": True,
                        "data": {"name": profile["name"], "email": email, "email_link": True, "social_links": []},
                    }
                ],
                "customizations": {},
            },
        )
        assert source.status_code == 201, source.text
        source_id = source.json()["id"]
        linked = await client.patch(
            f"/api/v1/applications/{application.json()['id']}",
            headers=headers,
            json={"cv_id": source_id},
        )
        assert linked.status_code == 200, linked.text
    return headers, email, profile, application.json(), source_id


def _candidate(email: str, *, description: str = "Built durable Python APIs.") -> dict:
    return {
        "title": "Example — Engineer",
        "template_id": "generic-minimal",
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {"name": "Candidate Name", "email": email, "email_link": True, "social_links": []},
            },
            {
                "id": "experience",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [
                    {
                        "id": "experience-1",
                        "company": "Example Systems",
                        "position": "Engineer",
                        "start_date": "2020",
                        "end_date": None,
                        "current": True,
                        "description": description,
                    }
                ],
            },
        ],
        "customizations": {},
    }


async def _start_session(client, headers, application_id: str):
    created = await client.post(
        f"/api/v1/applications/{application_id}/tailoring-sessions",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    exchanged = await client.post(
        "/api/v1/tailoring/exchange",
        json={
            "protocol_version": 10,
            "session_id": created.json()["session_id"],
            "code": created.json()["code"],
        },
    )
    assert exchanged.status_code == 200, exchanged.text
    capability = {"X-Aergia-Tailoring-Capability": exchanged.json()["capability"]}
    context = await client.get("/api/v1/tailoring/context", headers=capability)
    assert context.status_code == 200, context.text
    return created.json(), capability, context.json()


async def _preview(client, capability, context, candidate):
    reservation = await client.post(
        "/api/v1/tailoring/preview-reservations",
        headers=capability,
        json={
            "context_hash": context["context_hash"],
            "candidate": candidate,
            "request_id": str(uuid4()),
        },
    )
    assert reservation.status_code == 200, reservation.text
    preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=capability,
        json={
            "context_hash": context["context_hash"],
            "candidate": candidate,
            "reservation_id": reservation.json()["reservation_id"],
        },
    )
    assert preview.status_code == 200, preview.text
    return preview.json()


def _fit_report(preview: dict) -> dict:
    return {
        "version": "fit-review-v1",
        "evaluation_id": preview["evaluation_id"],
        "candidate_hash": preview["candidate_hash"],
        "pdf_sha256": preview["pdf_sha256"],
        "status": "completed",
        "mode": "fresh_agent",
        "verdict": "generic",
        "rationale": "The PDF lists relevant tools but could tie its examples more directly to the role.",
        "strong_connections": ["Python API experience"],
        "weak_or_missing_connections": ["Production support ownership"],
        "recommended_changes": ["Connect the API example to a listed responsibility."],
    }


async def _submit(client, capability, context, preview, *, fit_review=None):
    payload = {
        "context_hash": context["context_hash"],
        "evaluation_id": preview["evaluation_id"],
        "candidate_hash": preview["candidate_hash"],
        "candidate": preview["candidate"],
        "review_notes": [],
    }
    if fit_review is not None:
        payload["fit_review"] = fit_review
    response = await client.post("/api/v1/tailoring/submit", headers=capability, json=payload)
    assert response.status_code == 200, response.text
    return response, payload


async def _submitted_draft(client, headers, email: str, application_id: str):
    created, capability, context = await _start_session(client, headers, application_id)
    preview = await _preview(client, capability, context, _candidate(email))
    submitted, _payload = await _submit(client, capability, context, preview)
    session_id = created["session_id"]
    status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert status.status_code == 200, status.text
    review = status.json()["draft_review"]
    assert review["state"] == "current"
    return created, preview, submitted, review


def _accept_payload(review: dict) -> dict:
    return {
        "expected_cv_revision": review["cv_revision"],
        "candidate_hash": review["candidate_hash"],
    }


@pytest.mark.asyncio
async def test_selected_pdf_replay_expiry_and_immediate_owner_acceptance(client, offline_tailoring_and_pdf):
    rendered = offline_tailoring_and_pdf
    headers, email, _profile_data, application, _source_id = await _owner_and_application(client)
    created, capability, context = await _start_session(client, headers, application["id"])
    selected = await _preview(client, capability, context, _candidate(email))
    unselected = await _preview(
        client,
        capability,
        context,
        _candidate(email, description="Different unselected API example."),
    )
    report = _fit_report(selected)
    submitted, request_payload = await _submit(client, capability, context, selected, fit_review=report)
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    selected_pdf = b"fixture-pdf:Built durable Python APIs."
    selected_sha = sha256(selected_pdf).hexdigest()
    assert selected["pdf_sha256"] == selected_sha
    assert submitted.json()["evaluation_id"] == selected["evaluation_id"]
    assert submitted.json()["fit_review"] == report
    # Submit and lost-response replay use the immutable selected ledger and
    # must not invoke the renderer or create another draft.
    assert rendered == [selected_pdf, b"fixture-pdf:Different unselected API example."]
    replay = await client.post("/api/v1/tailoring/submit", headers=capability, json=request_payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["draft_cv_id"] == draft_id
    assert replay.json()["evaluation_id"] == selected["evaluation_id"]
    assert rendered == [selected_pdf, b"fixture-pdf:Different unselected API example."]
    listed = await client.get("/api/v1/cvs", headers=headers)
    assert [item["id"] for item in listed.json()] == [draft_id]

    status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert status.status_code == 200, status.text
    review = status.json()["draft_review"]
    assert review["state"] == "current"
    assert review["pdf_sha256"] == selected_sha
    assert review["fit_review_applicability"] == "current"
    assert review["evaluation_id"]
    assert review["evaluation_id"] != selected["evaluation_id"]
    assert review["fit_review"] == report

    draft_context = await client.get(f"/api/v1/cvs/{draft_id}/tailoring-context", headers=headers)
    assert draft_context.status_code == 200, draft_context.text
    assert draft_context.json()["draft_review"]["state"] == "current"
    assert "source_scan" not in draft_context.json()["scanner_context"]
    assert draft_context.json()["job"]["description"] == application["job_description"]
    # The login helper also installs a cookie; clear it so this request carries
    # only the scoped tailoring capability.
    client.cookies.clear()
    agent_cannot_open_owner_status = await client.get(
        f"/api/v1/tailoring/sessions/{session_id}", headers=capability,
    )
    assert agent_cannot_open_owner_status.status_code == 401
    bodyless_v10_accept = await client.post(f"/api/v1/tailoring/sessions/{session_id}/accept", headers=headers)
    assert bodyless_v10_accept.status_code == 422
    assert bodyless_v10_accept.json()["code"] == "candidate_invalid"

    # Capability expiry revokes the agent while leaving owner review intact.
    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()
    expired_agent = await client.get("/api/v1/tailoring/context", headers=capability)
    assert expired_agent.status_code == 410
    owner_after_expiry = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert owner_after_expiry.status_code == 200, owner_after_expiry.text
    assert owner_after_expiry.json()["status"] == "draft_ready"
    assert owner_after_expiry.json()["draft_review"]["state"] == "current"
    duplicate = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "session_in_progress"

    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        assert session.submission_result["draft_cv_id"] == draft_id
        assert session.submission_result["pdf_sha256"] == selected_sha
        assert session.submission_result["fit_review"] == report
        assert session.result == session.submission_result
        records = list(
            (
                await db.execute(
                    select(TailoringEvaluationRecord).where(TailoringEvaluationRecord.session_id == session_id)
                )
            ).scalars()
        )
        selected_record = next(record for record in records if record.id == selected["evaluation_id"])
        unselected_record = next(record for record in records if record.id == unselected["evaluation_id"])
        owner_record = next(record for record in records if record.kind == TAILORING_EVALUATION_OWNER_REVIEW)
        assert selected_record.pdf_bytes == selected_pdf
        assert owner_record.pdf_bytes == selected_pdf
        assert owner_record.pdf_sha256 == selected_record.pdf_sha256 == selected_sha
        assert unselected_record.kind == TAILORING_EVALUATION_AGENT_PREVIEW
        assert unselected_record.pdf_bytes is None

    accepted = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/accept",
        headers=headers,
        json={
            "expected_cv_revision": review["cv_revision"],
            "candidate_hash": review["candidate_hash"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["cv_id"] == draft_id
    rejected_after_accept = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert rejected_after_accept.status_code == 409
    delete_linked_accepted_cv = await client.delete(f"/api/v1/cvs/{draft_id}", headers=headers)
    assert delete_linked_accepted_cv.status_code == 409
    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        assert session.result == session.submission_result


@pytest.mark.asyncio
async def test_contact_and_template_basis_and_cv_revision_gate_acceptance(client, offline_tailoring_and_pdf):
    headers, email, profile, application, _source_id = await _owner_and_application(client)
    created, capability, context = await _start_session(client, headers, application["id"])
    preview = await _preview(client, capability, context, _candidate(email))
    submitted, _payload = await _submit(client, capability, context, preview)
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    first_review = (await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)).json()["draft_review"]
    assert first_review["state"] == "current"

    unrelated_profile_edit = {
        **profile,
        "title": "Principal Research Engineer",
        "location": "Moncton, NB",
        "summary": "A new summary that does not change the contact or document basis.",
    }
    updated_profile = await client.put("/api/v1/profile", headers=headers, json=unrelated_profile_edit)
    assert updated_profile.status_code == 200, updated_profile.text
    status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert status.json()["draft_review"]["state"] == "current"
    assert status.json()["draft_review"]["candidate_hash"] == first_review["candidate_hash"]

    contact_edit = {**unrelated_profile_edit, "phone": "+1 902 555 0199"}
    updated_contact = await client.put("/api/v1/profile", headers=headers, json=contact_edit)
    assert updated_contact.status_code == 200, updated_contact.text
    status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    contact_review = status.json()["draft_review"]
    assert contact_review["state"] == "needs_reevaluation"
    stale_contact_accept = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/accept",
        headers=headers,
        json={
            "expected_cv_revision": contact_review["cv_revision"],
            "candidate_hash": contact_review["candidate_hash"],
        },
    )
    assert stale_contact_accept.status_code == 409
    assert stale_contact_accept.json()["code"] == "review_not_current"
    reevaluated_contact = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
        headers=headers,
        json={"expected_cv_revision": contact_review["cv_revision"]},
    )
    assert reevaluated_contact.status_code == 200, reevaluated_contact.text
    contact_review = reevaluated_contact.json()["draft_review"]
    assert contact_review["state"] == "current"
    assert contact_review["candidate_hash"] != first_review["candidate_hash"]

    async with async_session() as db:
        template = await db.get(Template, "generic-minimal")
        changed_manifest = deepcopy(template.manifest)
        changed_manifest["global_styles"]["accent_color"] = "#5b21b6"
        template.manifest = changed_manifest
        await db.commit()
    status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    template_review = status.json()["draft_review"]
    assert template_review["state"] == "needs_reevaluation"
    reevaluated_template = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
        headers=headers,
        json={"expected_cv_revision": template_review["cv_revision"]},
    )
    assert reevaluated_template.status_code == 200, reevaluated_template.text
    current_review = reevaluated_template.json()["draft_review"]
    assert current_review["state"] == "current"

    saved = await client.patch(
        f"/api/v1/cvs/{draft_id}",
        headers=headers,
        json={"title": "Owner edited title"},
    )
    assert saved.status_code == 200, saved.text
    edit_race = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/accept",
        headers=headers,
        json={
            "expected_cv_revision": current_review["cv_revision"],
            "candidate_hash": current_review["candidate_hash"],
        },
    )
    assert edit_race.status_code == 409
    assert edit_race.json()["code"] == "edited_draft"
    latest_status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    latest_review = latest_status.json()["draft_review"]
    assert latest_review["state"] == "needs_reevaluation"
    reevaluated_save = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
        headers=headers,
        json={"expected_cv_revision": latest_review["cv_revision"]},
    )
    assert reevaluated_save.status_code == 200, reevaluated_save.text
    final_review = reevaluated_save.json()["draft_review"]
    accepted = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/accept",
        headers=headers,
        json={
            "expected_cv_revision": final_review["cv_revision"],
            "candidate_hash": final_review["candidate_hash"],
        },
    )
    assert accepted.status_code == 200, accepted.text


@pytest.mark.asyncio
async def test_changed_source_keeps_stale_draft_inspectable_until_discard(client, offline_tailoring_and_pdf):
    headers, email, _profile_data, application, source_id = await _owner_and_application(client, with_source=True)
    created, capability, context = await _start_session(client, headers, application["id"])
    preview = await _preview(client, capability, context, _candidate(email))
    submitted, _payload = await _submit(client, capability, context, preview)
    draft_id = submitted.json()["draft_cv_id"]
    session_id = created["session_id"]
    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.email == email))
        source_count = owner.cv_count
        draft = await db.get(CV, draft_id)
        assert draft.quota_counted is False

    changed_source = await client.patch(
        f"/api/v1/cvs/{source_id}",
        headers=headers,
        json={"title": "Source revision changed"},
    )
    assert changed_source.status_code == 200, changed_source.text
    owner_status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert owner_status.status_code == 200, owner_status.text
    assert owner_status.json()["status"] == "stale"
    assert owner_status.json()["draft_review"]["state"] == "needs_reevaluation"
    stale_context = await client.get(f"/api/v1/cvs/{draft_id}/tailoring-context", headers=headers)
    assert stale_context.status_code == 200
    assert stale_context.json()["draft_cv_id"] == draft_id

    for _ in range(2):
        blocked = await client.post(
            f"/api/v1/applications/{application['id']}/tailoring-sessions",
            headers=headers,
        )
        assert blocked.status_code == 409
        assert blocked.json()["code"] == "session_in_progress"
    stale_reevaluation = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
        headers=headers,
        json={"expected_cv_revision": owner_status.json()["draft_review"]["cv_revision"]},
    )
    assert stale_reevaluation.status_code == 409
    assert stale_reevaluation.json()["code"] == "stale_target"

    async with async_session() as db:
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.application_id == application["id"]
            )
        )
        owner = await db.scalar(select(User).where(User.email == email))
        assert reservation.state == TAILORING_REPLACEMENT_RELEASED
        assert owner.cv_count == source_count
        assert (await db.get(CV, draft_id)).is_active is True

    discarded = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["status"] == "rejected"
    async with async_session() as db:
        assert (await db.get(CV, draft_id)).is_active is False
        owner = await db.scalar(select(User).where(User.email == email))
        assert owner.cv_count == source_count
    restarted = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert restarted.status_code == 201, restarted.text


@pytest.mark.asyncio
async def test_job_change_and_cv_delete_reconcile_same_transaction_and_allow_restart(client, offline_tailoring_and_pdf):
    headers, email, _profile_data, application, _source_id = await _owner_and_application(client, with_source=True)
    created, capability, context = await _start_session(client, headers, application["id"])
    preview = await _preview(client, capability, context, _candidate(email))
    submitted, _payload = await _submit(client, capability, context, preview)
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.email == email))
        original_count = owner.cv_count
        draft = await db.get(CV, draft_id)
        assert draft.quota_counted is False

    changed_job = await client.patch(
        f"/api/v1/applications/{application['id']}",
        headers=headers,
        json={"job_description": "A changed role needs a new tailoring session."},
    )
    assert changed_job.status_code == 200, changed_job.text
    # Deleting the pending draft must reconcile the session and its allowance
    # within the route transaction that retires the CV.
    deleted = await client.delete(f"/api/v1/cvs/{draft_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.application_id == application["id"]
            )
        )
        owner = await db.scalar(select(User).where(User.email == email))
        assert session.status == "stale"
        assert session.owner_review_state == "unavailable"
        assert (await db.get(CV, draft_id)).is_active is False
        assert reservation.state == TAILORING_REPLACEMENT_RELEASED
        assert owner.cv_count == original_count
    owner_status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert owner_status.status_code == 200, owner_status.text
    assert owner_status.json()["draft_review"]["state"] == "unavailable"
    missing_context = await client.get(f"/api/v1/cvs/{draft_id}/tailoring-context", headers=headers)
    assert missing_context.status_code == 404
    repeated_discard = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert repeated_discard.status_code == 200
    assert repeated_discard.json()["status"] == "rejected"
    restarted = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert restarted.status_code == 201, restarted.text


@pytest.mark.asyncio
async def test_actual_v9_row_keeps_bodyless_historical_acceptance(client):
    headers, _email, _profile_data, application, _source_id = await _owner_and_application(client)
    fixture = json.loads((Path(__file__).parent / "fixtures" / "tailoring-v9-submission.json").read_text())
    assert fixture["protocol_version"] == 9
    candidate = fixture["candidate"]
    candidate_hash = sha256(
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    assert candidate_hash == fixture["result"]["candidate_hash"]
    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
        app = await db.get(Application, application["id"])
        draft = await CVService(db).create_cv(
            owner.id,
            CVCreate.model_validate(
                {
                    "title": candidate["title"],
                    "template_id": candidate["template_id"],
                    "sections": candidate["sections"],
                    "customizations": candidate["customizations"],
                }
            ),
            application_id=app.id,
        )
        draft_id = draft.id
        scanner_result = _FixtureScanner().scan(app.job_description, candidate).model_dump(mode="json")
        session_id = str(uuid4())
        legacy_result = deepcopy(fixture["result"])
        legacy_result.update(
            session_id=session_id,
            application_id=app.id,
            draft_cv_id=draft_id,
            candidate=candidate,
            scanner_result=scanner_result,
        )
        session = TailoringSession(
            id=session_id,
            user_id=owner.id,
            application_id=app.id,
            cv_id=None,
            draft_cv_id=draft_id,
            code_hash=f"v9-fixture-{uuid4().hex}",
            status="draft_ready",
            protocol_version=9,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            submitted_at=datetime.now(timezone.utc),
            result=legacy_result,
        )
        db.add(session)
        await db.flush()
        session_id = session.id
        await db.commit()

    historical_status = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert historical_status.status_code == 200, historical_status.text
    assert historical_status.json()["protocol_version"] == 9
    assert historical_status.json()["draft_review"] is None
    accepted = await client.post(f"/api/v1/tailoring/sessions/{session_id}/accept", headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["protocol_version"] == 9
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["cv_id"] == draft_id
    rejected_after_accept = await client.post(
        f"/api/v1/tailoring/sessions/{session_id}/reject",
        headers=headers,
    )
    assert rejected_after_accept.status_code == 409


@pytest.mark.parametrize("legacy_status", ["stale", "expired"])
@pytest.mark.asyncio
async def test_historical_v9_submitted_draft_can_be_discarded_and_restarted(client, legacy_status):
    headers, _email, _profile_data, application, _source_id = await _owner_and_application(client)
    fixture = json.loads((Path(__file__).parent / "fixtures" / "tailoring-v9-submission.json").read_text())
    candidate = fixture["candidate"]
    candidate_hash = sha256(
        json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    assert candidate_hash == fixture["result"]["candidate_hash"]

    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
        app = await db.get(Application, application["id"])
        draft = await CVService(db).create_cv(
            owner.id,
            CVCreate.model_validate(
                {
                    "title": candidate["title"],
                    "template_id": candidate["template_id"],
                    "sections": candidate["sections"],
                    "customizations": candidate["customizations"],
                }
            ),
            application_id=app.id,
        )
        draft_id = draft.id
        scanner_result = _FixtureScanner().scan(app.job_description, candidate).model_dump(mode="json")
        session_id = str(uuid4())
        legacy_result = deepcopy(fixture["result"])
        legacy_result.update(
            session_id=session_id,
            application_id=app.id,
            draft_cv_id=draft_id,
            candidate=candidate,
            scanner_result=scanner_result,
        )
        db.add(
            TailoringSession(
                id=session_id,
                user_id=owner.id,
                application_id=app.id,
                cv_id=None,
                draft_cv_id=draft_id,
                code_hash=f"v9-discard-{uuid4().hex}",
                status=legacy_status,
                protocol_version=9,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                submitted_at=datetime.now(timezone.utc),
                result=legacy_result,
            )
        )
        await db.flush()
        count_before_discard = await db.scalar(select(User.cv_count).where(User.id == owner.id))
        await db.commit()

    blocked = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "session_in_progress"

    discarded = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["protocol_version"] == 9
    assert discarded.json()["status"] == "rejected"
    repeated = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "rejected"

    async with async_session() as db:
        owner_cv_count = await db.scalar(select(User.cv_count).where(User.id == application["user_id"]))
        reservation_count = await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == application["id"]
            )
        )
        session = await db.get(TailoringSession, session_id)
    assert session.status == "rejected"
    assert session.draft_cv_id == draft_id
    assert owner_cv_count == count_before_discard - 1
    assert reservation_count == 0

    restarted = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert restarted.status_code == 201, restarted.text


@pytest.mark.asyncio
async def test_historical_v9_missing_draft_can_be_discarded_without_quota_allowance(client):
    headers, _email, _profile_data, application, _source_id = await _owner_and_application(client)
    fixture = json.loads((Path(__file__).parent / "fixtures" / "tailoring-v9-submission.json").read_text())
    candidate = fixture["candidate"]
    session_id = str(uuid4())
    missing_draft_id = "deleted-historical-v9-draft"
    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
        app = await db.get(Application, application["id"])
        legacy_result = deepcopy(fixture["result"])
        legacy_result.update(
            session_id=session_id,
            application_id=app.id,
            draft_cv_id=missing_draft_id,
            candidate=candidate,
            scanner_result={"schema_version": "legacy-scanner-v0"},
        )
        db.add(
            TailoringSession(
                id=session_id,
                user_id=owner.id,
                application_id=app.id,
                cv_id=None,
                draft_cv_id=None,
                code_hash=f"v9-missing-{uuid4().hex}",
                status="stale",
                protocol_version=9,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                submitted_at=datetime.now(timezone.utc),
                result=legacy_result,
            )
        )
        await db.commit()

    discarded = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["status"] == "rejected"
    assert discarded.json()["draft_cv_id"] is None
    assert discarded.json()["scanner_result"] is None
    repeated = await client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "rejected"

    async with async_session() as db:
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
        reservation_count = await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == application["id"]
            )
        )
        session = await db.get(TailoringSession, session_id)
    assert owner.cv_count == 0
    assert reservation_count == 0
    assert session.status == "rejected"
    assert session.result["draft_cv_id"] == missing_draft_id

    restarted = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert restarted.status_code == 201, restarted.text


@pytest.mark.asyncio
async def test_expired_author_session_without_a_draft_can_be_restarted(client):
    headers, _email, _profile_data, application, _source_id = await _owner_and_application(client)
    created = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert created.status_code == 201, created.text

    async with async_session() as db:
        session = await db.get(TailoringSession, created.json()["session_id"])
        session.status = "expired"
        session.capability_hash = None
        await db.commit()

    restarted = await client.post(
        f"/api/v1/applications/{application['id']}/tailoring-sessions",
        headers=headers,
    )
    assert restarted.status_code == 201, restarted.text
    assert restarted.json()["session_id"] != created.json()["session_id"]


@pytest.mark.asyncio
async def test_owner_edit_during_render_fails_revision_cas_without_saving_review(client, monkeypatch, offline_tailoring_and_pdf):
    headers, email, _profile_data, application, _source_id = await _owner_and_application(client)
    created, _preview_result, submitted, review = await _submitted_draft(
        client,
        headers,
        email,
        application["id"],
    )
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(self, manifest, sections, customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"owner-review-render-before-edit"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_manifest_payload", blocked_render)
    reevaluation = asyncio.create_task(
        client.post(
            f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
            headers=headers,
            json={"expected_cv_revision": review["cv_revision"]},
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        # This PATCH uses an independent request/session while reevaluation is
        # rendering outside the final conditional write transaction.
        edited = await client.patch(
            f"/api/v1/cvs/{draft_id}",
            headers=headers,
            json={"title": "Concurrent owner edit"},
        )
        assert edited.status_code == 200, edited.text
        finish_render.set()
        response = await asyncio.wait_for(reevaluation, timeout=10)
        assert response.status_code == 409
        assert response.json()["code"] == "edited_draft"
    finally:
        finish_render.set()
        if not reevaluation.done():
            await asyncio.wait_for(reevaluation, timeout=10)

    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        draft = await db.get(CV, draft_id)
        owner_records = list(
            (
                await db.execute(
                    select(TailoringEvaluationRecord).where(
                        TailoringEvaluationRecord.session_id == session_id,
                        TailoringEvaluationRecord.kind == TAILORING_EVALUATION_OWNER_REVIEW,
                    )
                )
            ).scalars()
        )
    assert draft.revision == review["cv_revision"] + 1
    assert session.owner_evaluation_id == review["evaluation_id"]
    assert len(owner_records) == 1


@pytest.mark.parametrize("basis_change", ["contact", "template"])
@pytest.mark.asyncio
async def test_contact_or_template_change_during_render_cannot_publish_review(
    client,
    monkeypatch,
    offline_tailoring_and_pdf,
    basis_change,
):
    headers, email, profile, application, _source_id = await _owner_and_application(client)
    created, _preview_result, submitted, review = await _submitted_draft(
        client,
        headers,
        email,
        application["id"],
    )
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(self, manifest, sections, customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"owner-review-render-with-old-basis"

    monkeypatch.setattr(pdf_service_module.PDFService, "render_manifest_payload", blocked_render)
    reevaluation = asyncio.create_task(
        client.post(
            f"/api/v1/tailoring/sessions/{session_id}/reevaluate",
            headers=headers,
            json={"expected_cv_revision": review["cv_revision"]},
        )
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        if basis_change == "contact":
            changed = await client.put(
                "/api/v1/profile",
                headers=headers,
                json={**profile, "phone": "+1 902 555 0198"},
            )
            assert changed.status_code == 200, changed.text
        else:
            async with async_session() as db:
                template = await db.get(Template, "generic-minimal")
                manifest = deepcopy(template.manifest)
                manifest["global_styles"]["accent_color"] = "#0f766e"
                template.manifest = manifest
                await db.commit()
        finish_render.set()
        response = await asyncio.wait_for(reevaluation, timeout=10)
        assert response.status_code == 409
        assert response.json()["code"] == "review_not_current"
    finally:
        finish_render.set()
        if not reevaluation.done():
            await asyncio.wait_for(reevaluation, timeout=10)

    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        draft = await db.get(CV, draft_id)
        owner_record_count = await db.scalar(
            select(func.count(TailoringEvaluationRecord.id)).where(
                TailoringEvaluationRecord.session_id == session_id,
                TailoringEvaluationRecord.kind == TAILORING_EVALUATION_OWNER_REVIEW,
            )
        )
    assert session.owner_evaluation_id == review["evaluation_id"]
    assert owner_record_count == 1
    assert draft.revision == review["cv_revision"]
    latest = await client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert latest.json()["draft_review"]["state"] == "needs_reevaluation"


@pytest.mark.parametrize("competitor", ["reject", "delete"])
@pytest.mark.asyncio
async def test_accept_wins_barrier_against_reject_or_cv_delete(
    client,
    monkeypatch,
    offline_tailoring_and_pdf,
    competitor,
):
    headers, email, _profile_data, application, _source_id = await _owner_and_application(client)
    created, _preview_result, submitted, review = await _submitted_draft(
        client,
        headers,
        email,
        application["id"],
    )
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    entered_lock = asyncio.Event()
    release_lock = asyncio.Event()
    competitor_started = asyncio.Event()
    original_lock = TailoringService._lock_owner_rows

    async def blocked_owner_lock(self, session, current_draft_id, template_id):
        await original_lock(self, session, current_draft_id, template_id)
        if session.id == session_id:
            entered_lock.set()
            await asyncio.wait_for(release_lock.wait(), timeout=5)

    monkeypatch.setattr(TailoringService, "_lock_owner_rows", blocked_owner_lock)
    accept_task = asyncio.create_task(
        client.post(
            f"/api/v1/tailoring/sessions/{session_id}/accept",
            headers=headers,
            json=_accept_payload(review),
        )
    )
    competitor_task = None
    try:
        await asyncio.wait_for(entered_lock.wait(), timeout=5)
        if competitor == "reject":
            original_reject = TailoringService.reject_draft

            async def tracked_reject(self, current_session_id, user_id):
                competitor_started.set()
                return await original_reject(self, current_session_id, user_id)

            monkeypatch.setattr(TailoringService, "reject_draft", tracked_reject)
            competitor_task = asyncio.create_task(
                client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
            )
        else:
            original_delete = CVService.delete_cv

            async def tracked_delete(self, current_draft_id, user_id):
                if current_draft_id == draft_id:
                    competitor_started.set()
                return await original_delete(self, current_draft_id, user_id)

            monkeypatch.setattr(CVService, "delete_cv", tracked_delete)
            competitor_task = asyncio.create_task(client.delete(f"/api/v1/cvs/{draft_id}", headers=headers))
        await asyncio.wait_for(competitor_started.wait(), timeout=5)
        await asyncio.sleep(0)
        release_lock.set()
        accepted, lost = await asyncio.wait_for(asyncio.gather(accept_task, competitor_task), timeout=10)
    finally:
        release_lock.set()
        if not accept_task.done():
            await asyncio.wait_for(accept_task, timeout=10)
        if competitor_task is not None and not competitor_task.done():
            await asyncio.wait_for(competitor_task, timeout=10)

    assert accepted.status_code == 200, accepted.text
    assert lost.status_code == 409
    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        app = await db.get(Application, application["id"])
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
    assert session.status == "accepted"
    assert app.cv_id == draft_id
    assert owner.cv_count == 1


@pytest.mark.parametrize("winner", ["reject", "delete"])
@pytest.mark.asyncio
async def test_reject_or_cv_delete_wins_barrier_against_accept(client, monkeypatch, offline_tailoring_and_pdf, winner):
    headers, email, _profile_data, application, _source_id = await _owner_and_application(client)
    created, _preview_result, submitted, review = await _submitted_draft(
        client,
        headers,
        email,
        application["id"],
    )
    session_id = created["session_id"]
    draft_id = submitted.json()["draft_cv_id"]
    deletion_started = asyncio.Event()
    release_deletion = asyncio.Event()

    if winner == "reject":
        original_delete = CVService.delete_cv

        async def blocked_delete(self, current_draft_id, user_id):
            if current_draft_id == draft_id:
                # Rejection has already started its outer write transaction;
                # keep it held until the competing accept has begun.
                deletion_started.set()
                await asyncio.wait_for(release_deletion.wait(), timeout=5)
            return await original_delete(self, current_draft_id, user_id)

        monkeypatch.setattr(CVService, "delete_cv", blocked_delete)
        winner_task = asyncio.create_task(
            client.post(f"/api/v1/tailoring/sessions/{session_id}/reject", headers=headers)
        )
    else:
        original_delete = CVService.delete_cv

        async def blocked_delete(self, current_draft_id, user_id):
            if current_draft_id == draft_id:
                from app.services.quotas import QuotaService

                await QuotaService(self.db).ensure_write_transaction()
                deletion_started.set()
                await asyncio.wait_for(release_deletion.wait(), timeout=5)
            return await original_delete(self, current_draft_id, user_id)

        monkeypatch.setattr(CVService, "delete_cv", blocked_delete)
        winner_task = asyncio.create_task(client.delete(f"/api/v1/cvs/{draft_id}", headers=headers))

    accept_task = None
    try:
        await asyncio.wait_for(deletion_started.wait(), timeout=5)
        accept_task = asyncio.create_task(
            client.post(
                f"/api/v1/tailoring/sessions/{session_id}/accept",
                headers=headers,
                json=_accept_payload(review),
            )
        )
        await asyncio.sleep(0)
        release_deletion.set()
        winner_response, lost_accept = await asyncio.wait_for(asyncio.gather(winner_task, accept_task), timeout=10)
    finally:
        release_deletion.set()
        if not winner_task.done():
            await asyncio.wait_for(winner_task, timeout=10)
        if accept_task is not None and not accept_task.done():
            await asyncio.wait_for(accept_task, timeout=10)

    assert winner_response.status_code == (200 if winner == "reject" else 204), winner_response.text
    assert lost_accept.status_code == 409
    async with async_session() as db:
        session = await db.get(TailoringSession, session_id)
        app = await db.get(Application, application["id"])
        draft = await db.get(CV, draft_id)
        owner = await db.scalar(select(User).where(User.id == application["user_id"]))
    assert session.status in {"rejected", "stale"}
    assert app.cv_id is None
    assert draft.is_active is False
    assert owner.cv_count == 0
