"""Database-backed regressions for protocol-v10 tailoring concurrency."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.app import app as fastapi_app
from app.db.session import async_session, get_db
from app.http_schemas.tailoring import TailoringScannerContext
from app.models.application import Application
from app.models.tailoring_evaluation import TailoringEvaluationRecord
from app.models.tailoring_preview_reservation import TailoringPreviewReservation
from app.models.tailoring_session import TailoringSession
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService, scanner_versions_for_extraction
from app.services import application as application_service_module
from app.services import pdf as pdf_service_module
from app.services import tailoring as tailoring_service_module
from app.services.relevance import extract_requirements_v2
from app.services.tailoring import TailoringService


async def _new_session(client, *, monkeypatch=None):
    email = f"v10-concurrency-{uuid4().hex}@example.com"
    password = "synthetic-test-password"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201, registered.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    owner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    application = await client.post(
        "/api/v1/applications",
        headers=owner_headers,
        json={
            "company": "Synthetic Systems",
            "role": "Software Engineer",
            "job_description": "Build Python APIs, CI tests, and reliable services.",
            "notes": "Use synthetic facts only.",
        },
    )
    assert application.status_code == 201, application.text
    created = await client.post(
        f"/api/v1/applications/{application.json()['id']}/tailoring-sessions?protocol_version=10",
        headers=owner_headers,
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
    capability_headers = {"X-Aergia-Tailoring-Capability": exchanged.json()["capability"]}
    context = await client.get("/api/v1/tailoring/context", headers=capability_headers)
    assert context.status_code == 200, context.text
    return {
        "owner_headers": owner_headers,
        "application": application.json(),
        "created": created.json(),
        "exchange": exchanged.json(),
        "capability_headers": capability_headers,
        "context": context.json(),
    }


@pytest.fixture(autouse=True)
def _use_offline_scanner_context(monkeypatch):
    class FixtureExtractor:
        def extract(self, job_description):
            return extract_requirements_from_entities(job_description, {"entities": {}})

    async def freeze_scanner_context(self, resources):
        extraction = extract_requirements_from_entities(
            resources["application"].job_description,
            {"entities": {}},
        )
        return TailoringScannerContext(
            versions=scanner_versions_for_extraction(extraction),
            requirement_extraction=extraction,
            source_scan=None,
        )

    monkeypatch.setattr(TailoringService, "_freeze_scanner_context", freeze_scanner_context)
    monkeypatch.setattr(tailoring_service_module, "configured_extractor_version", lambda: None)
    monkeypatch.setattr(tailoring_service_module, "ScannerService", lambda: ScannerService(extractor=FixtureExtractor()))
    monkeypatch.setattr(application_service_module, "extract_requirements", extract_requirements_v2)


def _candidate(context, title="Synthetic Software Engineer"):
    return {
        "title": title,
        "template_id": context["selected_template_id"],
        "sections": [
            {
                "id": "profile-section",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {
                    "name": "Synthetic Candidate",
                    "summary": [
                        {"type": "paragraph", "items": [{"text": "Builds useful software with careful testing."}]},
                        {
                            "id": "same-block",
                            "type": "paragraph",
                            "items": [{"id": "same-item", "text": "Explains technical work clearly."}],
                        },
                        {
                            "id": "same-block",
                            "type": "paragraph",
                            "items": [
                                {"id": "same-item", "text": "Coordinates collaborative project work."},
                                {"id": "same-item", "text": "Keeps changes reviewable."},
                                {"text": "Keeps changes reviewable."},
                            ],
                        },
                    ],
                    "social_links": [],
                },
            },
            {
                "id": "experience-section",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [
                    {
                        "id": "synthetic-experience",
                        "company": "Synthetic Systems",
                        "position": "Software Engineer",
                        "start_date": "2022-01",
                        "end_date": "2024-01",
                        "description": "Built Python APIs and maintained CI tests.",
                    }
                ],
            },
        ],
        "customizations": {},
    }


def _mock_rendering(monkeypatch, *, render=None):
    async def render_manifest_payload(self, manifest, sections, customizations):
        if render is not None:
            return await render(manifest, sections, customizations)
        payload = json.dumps(
            {"manifest": manifest.get("id"), "sections": sections, "customizations": customizations},
            sort_keys=True,
        ).encode()
        return b"synthetic-pdf:" + payload

    monkeypatch.setattr(pdf_service_module.PDFService, "render_manifest_payload", render_manifest_payload)
    monkeypatch.setattr(tailoring_service_module, "pdf_page_count", lambda _pdf: 1)


async def _reserve(client, setup, candidate, request_id=None):
    request_id = request_id or str(uuid4())
    response = await client.post(
        "/api/v1/tailoring/preview-reservations",
        headers=setup["capability_headers"],
        json={
            "context_hash": setup["context"]["context_hash"],
            "candidate": candidate,
            "request_id": request_id,
        },
    )
    return request_id, response


async def _cancel_blocked_preview(task: asyncio.Task, finish_render: asyncio.Event) -> None:
    finish_render.set()
    if task.done():
        return
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=3)
    except (asyncio.CancelledError, TimeoutError):
        pass
    except Exception:
        # The owning test already reports its failed assertion; cleanup must
        # still finish before pytest closes the event loop.
        pass


@pytest.mark.asyncio
async def test_exchange_rejects_wrong_url_session_before_consuming_code(client):
    email = f"wrong-session-{uuid4().hex}@example.com"
    password = "synthetic-test-password"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Synthetic Co", "role": "Engineer", "job_description": "Build software."},
    )
    created = await client.post(
        f"/api/v1/applications/{application.json()['id']}/tailoring-sessions?protocol_version=10",
        headers=headers,
    )
    code = created.json()["code"]
    wrong = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 10, "session_id": str(uuid4()), "code": code},
    )
    assert wrong.status_code == 409
    assert wrong.json()["code"] == "invalid_session"
    correct = await client.post(
        "/api/v1/tailoring/exchange",
        json={"protocol_version": 10, "session_id": created.json()["session_id"], "code": code},
    )
    assert correct.status_code == 200, correct.text


@pytest.mark.asyncio
async def test_simultaneous_session_creation_leaves_one_blocking_row(client, monkeypatch):
    email = f"create-race-{uuid4().hex}@example.com"
    password = "synthetic-test-password"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    application = await client.post(
        "/api/v1/applications",
        headers=headers,
        json={"company": "Synthetic Co", "role": "Engineer", "job_description": "Build software."},
    )
    application_id = application.json()["id"]

    barrier = asyncio.Event()
    arrived = 0
    original = TailoringService._context_parts

    async def synchronized_context(self, session, *, initialize=False):
        nonlocal arrived
        result = await original(self, session, initialize=initialize)
        if initialize:
            arrived += 1
            if arrived == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), timeout=5)
        return result

    monkeypatch.setattr(TailoringService, "_context_parts", synchronized_context)
    path = f"/api/v1/applications/{application_id}/tailoring-sessions?protocol_version=10"
    first, second = await asyncio.gather(
        client.post(path, headers=headers),
        client.post(path, headers=headers),
    )
    statuses = sorted([first.status_code, second.status_code])
    assert statuses == [201, 409], (first.text, second.text)
    conflict = first if first.status_code == 409 else second
    assert conflict.json()["code"] == "session_in_progress"
    async with async_session() as db:
        count = await db.scalar(
            select(func.count(TailoringSession.id)).where(
                TailoringSession.application_id == application_id,
                TailoringSession.status.in_(("created", "exchanged", "draft_ready")),
            )
        )
    assert count == 1


@pytest.mark.asyncio
async def test_simultaneous_same_reservation_requests_return_one_lease(client, monkeypatch):
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    request_id = str(uuid4())
    barrier = asyncio.Event()
    arrived = 0
    original = TailoringService._current_context

    async def synchronized_context(self, session, *args):
        nonlocal arrived
        result = await original(self, session, *args)
        arrived += 1
        if arrived == 2:
            barrier.set()
        await asyncio.wait_for(barrier.wait(), timeout=5)
        return result

    monkeypatch.setattr(TailoringService, "_current_context", synchronized_context)
    requests = await asyncio.gather(
        _reserve(client, setup, candidate, request_id),
        _reserve(client, setup, candidate, request_id),
    )
    assert [request[0] for request in requests] == [request_id, request_id]
    first, second = requests[0][1], requests[1][1]
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    assert first.json()["reservation_id"] == second.json()["reservation_id"]
    assert first.json()["candidate_hash"] == second.json()["candidate_hash"]

    other = _candidate(setup["context"], title="A distinct candidate")
    _other_id, blocked = await _reserve(client, setup, other)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "preview_in_progress"


@pytest.mark.asyncio
async def test_reservation_preserves_route_owned_preflushed_writes(client):
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    session_id = setup["created"]["session_id"]
    async with async_session() as db:
        initial_attempts = (await db.get(TailoringSession, session_id)).attempts

    async def db_with_preflushed_write():
        async with async_session() as db:
            await db.execute(
                update(TailoringSession)
                .where(TailoringSession.id == session_id)
                .values(attempts=TailoringSession.attempts + 7)
            )
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = db_with_preflushed_write
    try:
        _request_id, reserved = await _reserve(client, setup, candidate)
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)

    assert reserved.status_code == 200, reserved.text
    async with async_session() as db:
        saved_attempts = (await db.get(TailoringSession, session_id)).attempts
        reservation = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
    assert saved_attempts == initial_attempts + 7
    assert reservation.state == "active"


@pytest.mark.asyncio
async def test_reservation_race_retry_normalization_and_exact_pdf_replay(client, monkeypatch):
    _mock_rendering(monkeypatch)
    setup = await _new_session(client)
    raw_candidate = _candidate(setup["context"])
    request_id = str(uuid4())
    first_id, first = await _reserve(client, setup, raw_candidate, request_id)
    assert first.status_code == 200, first.text
    repeated_id, repeated = await _reserve(client, setup, raw_candidate, first_id)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["reservation_id"] == first.json()["reservation_id"]
    assert repeated.json()["candidate_hash"] == first.json()["candidate_hash"]

    preview_body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": first.json()["reservation_id"],
        "candidate": raw_candidate,
    }
    preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=setup["capability_headers"],
        json=preview_body,
    )
    assert preview.status_code == 200, preview.text
    preview_result = preview.json()
    assert preview_result["candidate_hash"] == first.json()["candidate_hash"]
    assert preview_result["pdf_sha256"] == hashlib.sha256(
        __import__("base64").b64decode(preview_result["pdf_base64"])
    ).hexdigest()
    canonical_summary = preview_result["candidate"]["sections"][0]["data"]["summary"]
    block_ids = [item["id"] for item in canonical_summary]
    assert len(block_ids) == len(set(block_ids))
    for block in canonical_summary:
        item_ids = [rich_item["id"] for rich_item in block["items"]]
        assert len(item_ids) == len(set(item_ids))

    retry = await client.post(
        "/api/v1/tailoring/preview",
        headers=setup["capability_headers"],
        json=preview_body,
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["pdf_base64"] == preview_result["pdf_base64"]
    assert retry.json()["pdf_sha256"] == preview_result["pdf_sha256"]
    assert retry.json()["evaluation_id"] == preview_result["evaluation_id"]
    async with async_session() as db:
        ledger_count = await db.scalar(
            select(func.count(TailoringEvaluationRecord.id)).where(
                TailoringEvaluationRecord.session_id == setup["created"]["session_id"],
                TailoringEvaluationRecord.kind == "agent_preview",
            )
        )
        session = await db.get(TailoringSession, setup["created"]["session_id"])
    assert ledger_count == 1
    assert "evaluation_history" not in session.context_snapshot


@pytest.mark.asyncio
async def test_render_timeout_releases_and_reuses_the_same_reservation(client, monkeypatch):
    async def timeout_render(_manifest, _sections, _customizations):
        raise TimeoutError("synthetic timeout")

    _mock_rendering(monkeypatch, render=timeout_render)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": reserved.json()["reservation_id"],
        "candidate": candidate,
    }
    failed = await client.post("/api/v1/tailoring/preview", headers=setup["capability_headers"], json=body)
    assert failed.status_code == 503
    assert failed.json()["code"] == "reservation_conflict"
    async with async_session() as db:
        row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
        assert row.state == "released"

    async def successful_render(_manifest, _sections, _customizations):
        return b"synthetic-pdf-retry"

    _mock_rendering(monkeypatch, render=successful_render)
    retry_id, reacquired = await _reserve(client, setup, candidate, request_id)
    assert retry_id == request_id
    assert reacquired.status_code == 200, reacquired.text
    assert reacquired.json()["reservation_id"] == reserved.json()["reservation_id"]
    succeeded = await client.post(
        "/api/v1/tailoring/preview",
        headers=setup["capability_headers"],
        json={**body, "reservation_id": reacquired.json()["reservation_id"]},
    )
    assert succeeded.status_code == 200, succeeded.text


@pytest.mark.asyncio
async def test_expired_lease_reclaim_fences_late_render_completion(client, monkeypatch):
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(_manifest, _sections, _customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"late-synthetic-pdf"

    _mock_rendering(monkeypatch, render=blocked_render)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    preview_body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": reserved.json()["reservation_id"],
        "candidate": candidate,
    }
    late_preview = asyncio.create_task(
        client.post("/api/v1/tailoring/preview", headers=setup["capability_headers"], json=preview_body)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        async with async_session() as db:
            await db.execute(
                update(TailoringPreviewReservation)
                .where(TailoringPreviewReservation.id == reserved.json()["reservation_id"])
                .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
            )
            await db.commit()

        retry_id, reclaimed = await _reserve(client, setup, candidate, request_id)
        assert retry_id == request_id
        assert reclaimed.status_code == 200, reclaimed.text
        assert reclaimed.json()["reservation_id"] == reserved.json()["reservation_id"]
        assert datetime.fromisoformat(reclaimed.json()["expires_at"].replace("Z", "+00:00")) > datetime.now(timezone.utc)
        finish_render.set()
        late_response = await asyncio.wait_for(late_preview, timeout=10)
        assert late_response.status_code == 409, late_response.text
        assert late_response.json()["code"] == "reservation_expired"
        async with async_session() as db:
            evaluation_count = await db.scalar(
                select(func.count(TailoringEvaluationRecord.id)).where(
                    TailoringEvaluationRecord.session_id == setup["created"]["session_id"],
                    TailoringEvaluationRecord.kind == "agent_preview",
                )
            )
            row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
        assert evaluation_count == 0
        assert row.state == "active"
    finally:
        await _cancel_blocked_preview(late_preview, finish_render)


@pytest.mark.asyncio
async def test_released_lease_reacquire_advances_fence_when_cap_keeps_expiry(client, monkeypatch):
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(_manifest, _sections, _customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"late-synthetic-pdf"

    _mock_rendering(monkeypatch, render=blocked_render)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    reservation_id = reserved.json()["reservation_id"]
    original_expiry = datetime.now(timezone.utc) + timedelta(seconds=45)
    async with async_session() as db:
        await db.execute(
            update(TailoringSession)
            .where(TailoringSession.id == setup["created"]["session_id"])
            .values(expires_at=original_expiry)
        )
        await db.execute(
            update(TailoringPreviewReservation)
            .where(TailoringPreviewReservation.id == reservation_id)
            .values(expires_at=original_expiry)
        )
        await db.commit()
        original_row = await db.get(TailoringPreviewReservation, reservation_id)
        original_fence = original_row.updated_at

    preview_body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": reservation_id,
        "candidate": candidate,
    }
    late_preview = asyncio.create_task(
        client.post("/api/v1/tailoring/preview", headers=setup["capability_headers"], json=preview_body)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        released = await client.post(
            f"/api/v1/tailoring/preview-reservations/{reservation_id}/release",
            headers=setup["capability_headers"],
        )
        assert released.status_code == 200, released.text

        retry_id, reacquired = await _reserve(client, setup, candidate, request_id)
        assert retry_id == request_id
        assert reacquired.status_code == 200, reacquired.text
        assert reacquired.json()["reservation_id"] == reservation_id
        returned_expiry = datetime.fromisoformat(reacquired.json()["expires_at"].replace("Z", "+00:00"))
        assert returned_expiry == original_expiry.replace(tzinfo=None) if returned_expiry.tzinfo is None else original_expiry
        async with async_session() as db:
            renewed_row = await db.get(TailoringPreviewReservation, reservation_id)
            assert renewed_row.updated_at != original_fence

        finish_render.set()
        late_response = await asyncio.wait_for(late_preview, timeout=10)
        assert late_response.status_code == 409, late_response.text
        assert late_response.json()["code"] == "reservation_expired"
        async with async_session() as db:
            evaluation_count = await db.scalar(
                select(func.count(TailoringEvaluationRecord.id)).where(
                    TailoringEvaluationRecord.session_id == setup["created"]["session_id"],
                    TailoringEvaluationRecord.kind == "agent_preview",
                )
            )
            row = await db.get(TailoringPreviewReservation, reservation_id)
        assert evaluation_count == 0
        assert row.state == "active"
    finally:
        await _cancel_blocked_preview(late_preview, finish_render)


@pytest.mark.asyncio
async def test_new_request_reclaims_expired_other_request_lease(client, monkeypatch):
    _mock_rendering(monkeypatch)
    setup = await _new_session(client)
    first_candidate = _candidate(setup["context"], title="First candidate")
    first_id, first = await _reserve(client, setup, first_candidate)
    assert first.status_code == 200, first.text
    async with async_session() as db:
        await db.execute(
            update(TailoringPreviewReservation)
            .where(TailoringPreviewReservation.id == first.json()["reservation_id"])
            .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        )
        await db.commit()

    second_candidate = _candidate(setup["context"], title="Second candidate")
    second_id, second = await _reserve(client, setup, second_candidate)
    assert second_id != first_id
    assert second.status_code == 200, second.text
    assert second.json()["reservation_id"] != first.json()["reservation_id"]
    async with async_session() as db:
        first_row = await db.get(TailoringPreviewReservation, first.json()["reservation_id"])
        second_row = await db.get(TailoringPreviewReservation, second.json()["reservation_id"])
    assert first_row.state == "expired"
    assert second_row.state == "active"


@pytest.mark.asyncio
async def test_only_five_successful_previews_count_and_any_saved_one_is_selectable(client, monkeypatch):
    _mock_rendering(monkeypatch)
    setup = await _new_session(client)
    previews = []
    for index in range(5):
        candidate = _candidate(setup["context"], title=f"Synthetic Engineer {index}")
        _request_id, reserved = await _reserve(client, setup, candidate)
        assert reserved.status_code == 200, reserved.text
        preview = await client.post(
            "/api/v1/tailoring/preview",
            headers=setup["capability_headers"],
            json={
                "context_hash": setup["context"]["context_hash"],
                "reservation_id": reserved.json()["reservation_id"],
                "candidate": candidate,
            },
        )
        assert preview.status_code == 200, preview.text
        previews.append(preview.json())

    sixth_candidate = _candidate(setup["context"], title="Synthetic Engineer 6")
    _sixth_request_id, sixth = await _reserve(client, setup, sixth_candidate)
    assert sixth.status_code == 409
    assert sixth.json()["code"] == "preview_limit"

    status = await client.get(
        f"/api/v1/tailoring/sessions/{setup['created']['session_id']}",
        headers=setup["owner_headers"],
    )
    assert status.status_code == 200, status.text
    assert status.json()["attempts"] == 5

    selected = previews[0]
    submitted = await client.post(
        "/api/v1/tailoring/submit",
        headers=setup["capability_headers"],
        json={
            "context_hash": setup["context"]["context_hash"],
            "evaluation_id": selected["evaluation_id"],
            "candidate_hash": selected["candidate_hash"],
            "candidate": selected["candidate"],
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["evaluation_id"] == selected["evaluation_id"]
    assert submitted.json()["candidate_hash"] == selected["candidate_hash"]

    async with async_session() as db:
        records = await db.scalars(
            select(TailoringEvaluationRecord)
            .where(
                TailoringEvaluationRecord.session_id == setup["created"]["session_id"],
                TailoringEvaluationRecord.kind == "agent_preview",
            )
        )
        saved_records = list(records.all())
    assert len(saved_records) == 5
    assert next(row for row in saved_records if row.id == selected["evaluation_id"]).pdf_bytes is not None


@pytest.mark.asyncio
async def test_stale_target_response_persists_cleanup_and_releases_active_session(client, monkeypatch):
    _mock_rendering(monkeypatch)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    _request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    preview = await client.post(
        "/api/v1/tailoring/preview",
        headers=setup["capability_headers"],
        json={
            "context_hash": setup["context"]["context_hash"],
            "reservation_id": reserved.json()["reservation_id"],
            "candidate": candidate,
        },
    )
    assert preview.status_code == 200, preview.text

    async with async_session() as db:
        application = await db.get(Application, setup["application"]["id"])
        application.job_description = "A materially different synthetic job description."
        await db.commit()

    _new_request_id, stale = await _reserve(client, setup, candidate)
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_target"

    restarted = await client.post(
        f"/api/v1/applications/{setup['application']['id']}/tailoring-sessions?protocol_version=10",
        headers=setup["owner_headers"],
    )
    assert restarted.status_code == 201, restarted.text
    async with async_session() as db:
        old_session = await db.get(TailoringSession, setup["created"]["session_id"])
        row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
        evaluation = await db.get(TailoringEvaluationRecord, preview.json()["evaluation_id"])
    assert old_session.status == "stale"
    assert row.state == "completed"
    assert evaluation.pdf_bytes is None


@pytest.mark.asyncio
async def test_create_reconciles_same_protocol_target_mismatch(client):
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    _request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text

    async with async_session() as db:
        application = await db.get(Application, setup["application"]["id"])
        application.job_description = "A changed synthetic job description."
        await db.commit()

    restarted = await client.post(
        f"/api/v1/applications/{setup['application']['id']}/tailoring-sessions?protocol_version=10",
        headers=setup["owner_headers"],
    )
    assert restarted.status_code == 201, restarted.text
    async with async_session() as db:
        old_session = await db.get(TailoringSession, setup["created"]["session_id"])
        row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
    assert old_session.status == "stale"
    assert row.state == "expired"


@pytest.mark.asyncio
async def test_target_change_during_render_fences_preview_completion(client, monkeypatch):
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(_manifest, _sections, _customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"target-raced-synthetic-pdf"

    _mock_rendering(monkeypatch, render=blocked_render)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    _request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    preview_body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": reserved.json()["reservation_id"],
        "candidate": candidate,
    }
    preview = asyncio.create_task(
        client.post("/api/v1/tailoring/preview", headers=setup["capability_headers"], json=preview_body)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        async with async_session() as db:
            application = await db.get(Application, setup["application"]["id"])
            application.job_description = "The target changed while rendering."
            await db.commit()

        finish_render.set()
        response = await asyncio.wait_for(preview, timeout=10)
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "stale_target"
        async with async_session() as db:
            session = await db.get(TailoringSession, setup["created"]["session_id"])
            row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
            evaluations = await db.scalar(
                select(func.count(TailoringEvaluationRecord.id)).where(
                    TailoringEvaluationRecord.session_id == session.id,
                    TailoringEvaluationRecord.kind == "agent_preview",
                )
            )
        assert session.status == "stale"
        assert row.state == "expired"
        assert evaluations == 0
    finally:
        await _cancel_blocked_preview(preview, finish_render)


@pytest.mark.asyncio
async def test_owner_cancellation_during_render_fences_preview_completion(client, monkeypatch):
    started = asyncio.Event()
    finish_render = asyncio.Event()

    async def blocked_render(_manifest, _sections, _customizations):
        started.set()
        await asyncio.wait_for(finish_render.wait(), timeout=5)
        return b"cancelled-synthetic-pdf"

    _mock_rendering(monkeypatch, render=blocked_render)
    setup = await _new_session(client)
    candidate = _candidate(setup["context"])
    _request_id, reserved = await _reserve(client, setup, candidate)
    assert reserved.status_code == 200, reserved.text
    preview_body = {
        "context_hash": setup["context"]["context_hash"],
        "reservation_id": reserved.json()["reservation_id"],
        "candidate": candidate,
    }
    preview = asyncio.create_task(
        client.post("/api/v1/tailoring/preview", headers=setup["capability_headers"], json=preview_body)
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        cancelled = await client.post(
            f"/api/v1/tailoring/sessions/{setup['created']['session_id']}/cancel",
            headers=setup["owner_headers"],
        )
        assert cancelled.status_code == 200, cancelled.text

        finish_render.set()
        response = await asyncio.wait_for(preview, timeout=10)
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "reservation_expired"
        async with async_session() as db:
            session = await db.get(TailoringSession, setup["created"]["session_id"])
            row = await db.get(TailoringPreviewReservation, reserved.json()["reservation_id"])
            evaluations = await db.scalar(
                select(func.count(TailoringEvaluationRecord.id)).where(
                    TailoringEvaluationRecord.session_id == session.id,
                    TailoringEvaluationRecord.kind == "agent_preview",
                )
            )
        assert session.status == "cancelled"
        assert row.state == "expired"
        assert evaluations == 0
    finally:
        await _cancel_blocked_preview(preview, finish_render)
