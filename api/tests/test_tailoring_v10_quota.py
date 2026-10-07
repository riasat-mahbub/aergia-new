"""Replacement allowance and counter lifecycle regression coverage."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.session import async_session
from app.http_schemas.application import ApplicationUpdate
from app.http_schemas.cv import CVCreate, CVUpdate
from app.models.application import Application
from app.models.cv import CV
from app.models.tailoring_replacement_reservation import (
    TAILORING_REPLACEMENT_PENDING,
    TAILORING_REPLACEMENT_RELEASED,
    TAILORING_REPLACEMENT_TRANSFERRED,
    TailoringReplacementReservation,
)
from app.models.tailoring_session import TailoringSession
from app.models.user import User
from app.services.application import ApplicationCVLinkError, ApplicationService
from app.services.cv import CVLinkedToApplicationError, CVService
from app.services.quotas import (
    QuotaExceededError,
    QuotaResource,
    QuotaService,
    ReplacementAlreadyPendingError,
    ReplacementReservationConflictError,
)


def _new_cv(user_id: str, *, application_id: str | None = None, title: str = "Fixture CV") -> CV:
    return CV(
        user_id=user_id,
        application_id=application_id,
        title=title,
        template_id="generic-minimal",
        sections=[],
        customizations={},
        extra_metadata={},
        quota_counted=True,
        is_active=True,
    )


async def _seed_account(
    *,
    cv_total: int,
    source: bool,
    shared_source: bool = False,
) -> dict[str, str | None]:
    """Create synthetic quota fixtures committed before each service action."""

    user_id = str(uuid4())
    async with async_session() as db:
        user = User(
            id=user_id,
            email=f"quota-{user_id}@example.test",
            password_hash="synthetic-test-hash",
            application_count=1 + int(shared_source),
            cv_count=cv_total,
        )
        application = Application(
            user_id=user_id,
            company="Fixture Company",
            role="Fixture Role",
            job_description="Fixture requirements",
        )
        db.add_all([user, application])
        await db.flush()

        source_cv_id: str | None = None
        if source and cv_total:
            source_cv = _new_cv(user_id, application_id=application.id, title="Source CV")
            db.add(source_cv)
            await db.flush()
            application.cv_id = source_cv.id
            source_cv_id = source_cv.id
            remaining = cv_total - 1
        else:
            remaining = cv_total

        for index in range(remaining):
            db.add(_new_cv(user_id, title=f"Counted CV {index}"))
        if shared_source and source_cv_id is not None:
            second_application = Application(
                user_id=user_id,
                cv_id=source_cv_id,
                company="Second Fixture Company",
                role="Second Fixture Role",
                job_description="Second fixture requirements",
            )
            db.add(second_application)
        await db.commit()
        return {
            "user_id": user_id,
            "application_id": application.id,
            "source_cv_id": source_cv_id,
        }


async def _create_replacement(
    *,
    user_id: str,
    application_id: str,
    source_cv_id: str | None,
    title: str = "Replacement Draft",
) -> str:
    async with async_session() as db:
        cv = await CVService(db).create_replacement_draft(
            user_id,
            CVCreate(title=title),
            application_id=application_id,
            source_cv_id=source_cv_id,
        )
        await db.commit()
        return cv.id


async def _user_cv_count(user_id: str) -> int:
    async with async_session() as db:
        user = await db.get(User, user_id)
        assert user is not None
        return user.cv_count


@pytest.mark.asyncio
async def test_replacement_allowance_works_at_limit_and_draft_lifecycle_is_count_neutral():
    fixture = await _seed_account(cv_total=3, source=True)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    source_cv_id = str(fixture["source_cv_id"])

    draft_cv_id = await _create_replacement(
        user_id=user_id,
        application_id=application_id,
        source_cv_id=source_cv_id,
    )
    assert await _user_cv_count(user_id) == 3

    async with async_session() as db:
        draft = await db.get(CV, draft_cv_id)
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.application_id == application_id,
                TailoringReplacementReservation.source_cv_id == source_cv_id,
            )
        )
        assert draft is not None and draft.is_active and not draft.quota_counted
        assert reservation is not None
        assert reservation.draft_cv_id == draft_cv_id
        assert reservation.state == TAILORING_REPLACEMENT_PENDING

    async with async_session() as db:
        with pytest.raises(QuotaExceededError):
            await CVService(db).copy_cv(draft_cv_id, user_id)
        await db.rollback()
    assert await _user_cv_count(user_id) == 3

    async with async_session() as db:
        assert await CVService(db).delete_cv(draft_cv_id, user_id)
        await db.commit()
    async with async_session() as db:
        assert not await CVService(db).delete_cv(draft_cv_id, user_id)
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.draft_cv_id == draft_cv_id
            )
        )
        draft = await db.get(CV, draft_cv_id)
        assert reservation is not None and reservation.state == TAILORING_REPLACEMENT_RELEASED
        assert draft is not None and not draft.is_active and not draft.quota_counted
    assert await _user_cv_count(user_id) == 3


@pytest.mark.asyncio
async def test_no_source_consumes_a_normal_slot_and_is_blocked_at_the_limit():
    available = await _seed_account(cv_total=0, source=False)
    draft_id = await _create_replacement(
        user_id=str(available["user_id"]),
        application_id=str(available["application_id"]),
        source_cv_id=None,
    )
    async with async_session() as db:
        draft = await db.get(CV, draft_id)
        assert draft is not None and draft.quota_counted
        assert await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == available["application_id"]
            )
        ) == 0
    assert await _user_cv_count(str(available["user_id"])) == 1

    full = await _seed_account(cv_total=3, source=False)
    async with async_session() as db:
        with pytest.raises(QuotaExceededError):
            await CVService(db).create_replacement_draft(
                str(full["user_id"]),
                CVCreate(title="No-source full quota"),
                application_id=str(full["application_id"]),
                source_cv_id=None,
            )
        await db.rollback()
    assert await _user_cv_count(str(full["user_id"])) == 3


@pytest.mark.asyncio
async def test_shared_source_is_not_allowed_to_claim_an_allowance():
    fixture = await _seed_account(cv_total=3, source=True, shared_source=True)
    async with async_session() as db:
        with pytest.raises(QuotaExceededError):
            await CVService(db).create_replacement_draft(
                str(fixture["user_id"]),
                CVCreate(title="Shared source candidate"),
                application_id=str(fixture["application_id"]),
                source_cv_id=str(fixture["source_cv_id"]),
            )
        await db.rollback()
        assert await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == fixture["application_id"],
                TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
            )
        ) == 0
    assert await _user_cv_count(str(fixture["user_id"])) == 3


@pytest.mark.asyncio
async def test_failed_replacement_persistence_rolls_back_reservation_and_keeps_caller_work(monkeypatch):
    fixture = await _seed_account(cv_total=3, source=True)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    caller_app_id = str(uuid4())

    async def fail_persist(self, *args, **kwargs):
        raise RuntimeError("synthetic CV persistence failure")

    monkeypatch.setattr(CVService, "_persist_cv", fail_persist)
    async with async_session() as db:
        db.add(
            Application(
                id=caller_app_id,
                user_id=user_id,
                company="Caller transaction fixture",
                role="Pending role",
                job_description="Caller work remains outside the failed savepoint",
            )
        )
        with pytest.raises(RuntimeError, match="synthetic CV persistence failure"):
            await CVService(db).create_replacement_draft(
                user_id,
                CVCreate(title="Cannot persist candidate"),
                application_id=application_id,
                source_cv_id=str(fixture["source_cv_id"]),
            )
        assert await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == application_id,
                TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
            )
        ) == 0
        await db.commit()

    async with async_session() as db:
        assert await db.get(Application, caller_app_id) is not None
        assert await db.scalar(
            select(func.count(CV.id)).where(
                CV.user_id == user_id,
                CV.is_active.is_(True),
                CV.quota_counted.is_(False),
            )
        ) == 0
        assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 3


@pytest.mark.asyncio
async def test_pending_allowance_draft_cannot_be_manually_linked():
    fixture = await _seed_account(cv_total=1, source=True)
    draft_cv_id = await _create_replacement(
        user_id=str(fixture["user_id"]),
        application_id=str(fixture["application_id"]),
        source_cv_id=str(fixture["source_cv_id"]),
    )
    async with async_session() as db:
        second_application = Application(
            user_id=str(fixture["user_id"]),
            company="Second Fixture Company",
            role="Second Fixture Role",
            job_description="Second fixture requirements",
        )
        db.add(second_application)
        await db.flush()
        second_application_id = second_application.id
        await db.commit()

    async with async_session() as db:
        with pytest.raises(ApplicationCVLinkError, match="review flow"):
            await ApplicationService(db).update_application(
                second_application_id,
                str(fixture["user_id"]),
                ApplicationUpdate(cv_id=draft_cv_id),
            )
        await db.rollback()

    async with async_session() as db:
        app = await db.get(Application, second_application_id)
        draft = await db.get(CV, draft_cv_id)
        assert app is not None and app.cv_id is None
        assert draft is not None and draft.is_active and not draft.quota_counted
    assert await _user_cv_count(str(fixture["user_id"])) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("session_status", ["draft_ready", "stale", "expired"])
async def test_counted_pending_draft_must_also_use_owner_review(session_status):
    fixture = await _seed_account(cv_total=0, source=False)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    draft_cv_id = await _create_replacement(
        user_id=user_id,
        application_id=application_id,
        source_cv_id=None,
    )
    async with async_session() as db:
        db.add(TailoringSession(
            user_id=user_id,
            application_id=application_id,
            draft_cv_id=draft_cv_id,
            status=session_status,
            code_hash=uuid4().hex * 2,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        await db.commit()

    async with async_session() as db:
        with pytest.raises(ApplicationCVLinkError, match="review flow"):
            await ApplicationService(db).update_application(
                application_id, user_id, ApplicationUpdate(cv_id=draft_cv_id),
            )
        await db.rollback()
    async with async_session() as db:
        application = await db.get(Application, application_id)
        assert application.cv_id is None
        assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 1


@pytest.mark.asyncio
async def test_application_deletion_retires_pending_draft_and_removes_reservation():
    fixture = await _seed_account(cv_total=3, source=True)
    draft_cv_id = await _create_replacement(
        user_id=str(fixture["user_id"]),
        application_id=str(fixture["application_id"]),
        source_cv_id=str(fixture["source_cv_id"]),
    )

    async with async_session() as db:
        service = ApplicationService(db)
        assert await service.delete_application(
            str(fixture["application_id"]),
            str(fixture["user_id"]),
        )
        await db.commit()
        assert not await service.delete_application(
            str(fixture["application_id"]),
            str(fixture["user_id"]),
        )

    async with async_session() as db:
        draft = await db.get(CV, draft_cv_id)
        source = await db.get(CV, str(fixture["source_cv_id"]))
        user = await db.get(User, str(fixture["user_id"]))
        reservation_count = await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == fixture["application_id"]
            )
        )
        assert draft is not None and not draft.is_active and not draft.quota_counted
        assert source is not None and source.is_active and source.quota_counted
        assert user is not None and user.application_count == 0 and user.cv_count == 3
        assert reservation_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("session_status", ["draft_ready", "stale", "expired"])
async def test_application_deletion_retires_pending_counted_no_source_session_draft(session_status):
    fixture = await _seed_account(cv_total=0, source=False)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    async with async_session() as db:
        draft = await CVService(db).create_cv(
            user_id,
            CVCreate(title="Pending no-source candidate"),
            application_id=application_id,
        )
        session = TailoringSession(
            user_id=user_id,
            application_id=application_id,
            code_hash=f"{uuid4().hex}{uuid4().hex}",
            status=session_status,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            draft_cv_id=draft.id,
        )
        db.add(session)
        await db.commit()
        draft_cv_id = draft.id
        session_id = session.id

    assert await _user_cv_count(user_id) == 1
    async with async_session() as db:
        assert await ApplicationService(db).delete_application(application_id, user_id)
        await db.commit()

    async with async_session() as db:
        draft = await db.get(CV, draft_cv_id)
        user = await db.get(User, user_id)
        session = await db.get(TailoringSession, session_id)
        assert draft is not None and not draft.is_active and draft.quota_counted
        assert draft.application_id is None
        assert user is not None and user.application_count == 0 and user.cv_count == 0
        assert session is None


@pytest.mark.asyncio
async def test_source_deletion_releases_draft_once_and_decrements_only_counted_source():
    fixture = await _seed_account(cv_total=3, source=True)
    draft_cv_id = await _create_replacement(
        user_id=str(fixture["user_id"]),
        application_id=str(fixture["application_id"]),
        source_cv_id=str(fixture["source_cv_id"]),
    )
    async with async_session() as db:
        app = await db.get(Application, str(fixture["application_id"]))
        source = await db.get(CV, str(fixture["source_cv_id"]))
        assert app is not None and source is not None
        app.cv_id = None
        source.application_id = None
        await db.commit()

    async with async_session() as db:
        assert await CVService(db).delete_cv(str(fixture["source_cv_id"]), str(fixture["user_id"]))
        await db.commit()
    async with async_session() as db:
        assert not await CVService(db).delete_cv(str(fixture["source_cv_id"]), str(fixture["user_id"]))
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.draft_cv_id == draft_cv_id
            )
        )
        source = await db.get(CV, str(fixture["source_cv_id"]))
        draft = await db.get(CV, draft_cv_id)
        assert reservation is not None and reservation.state == TAILORING_REPLACEMENT_RELEASED
        assert source is not None and not source.is_active and source.quota_counted
        assert draft is not None and not draft.is_active and not draft.quota_counted
    assert await _user_cv_count(str(fixture["user_id"])) == 2


@pytest.mark.asyncio
async def test_transfer_and_release_compete_without_double_changing_the_counter():
    fixture = await _seed_account(cv_total=3, source=True)
    draft_cv_id = await _create_replacement(
        user_id=str(fixture["user_id"]),
        application_id=str(fixture["application_id"]),
        source_cv_id=str(fixture["source_cv_id"]),
    )
    outcomes: list[str] = []

    async def transfer() -> None:
        async with async_session() as db:
            try:
                await QuotaService(db).transfer_replacement(
                    str(fixture["user_id"]),
                    str(fixture["application_id"]),
                    str(fixture["source_cv_id"]),
                    draft_cv_id,
                )
                await db.commit()
                outcomes.append("transferred")
            except ReplacementReservationConflictError:
                await db.rollback()
                outcomes.append("transfer_lost")

    async def release() -> None:
        async with async_session() as db:
            released = await QuotaService(db).release_replacement(
                str(fixture["user_id"]),
                str(fixture["application_id"]),
                source_cv_id=str(fixture["source_cv_id"]),
                draft_cv_id=draft_cv_id,
                retire_draft=True,
            )
            await db.commit()
            outcomes.append("released" if released else "release_lost")

    await asyncio.gather(transfer(), release())

    async with async_session() as db:
        reservation = await db.scalar(
            select(TailoringReplacementReservation).where(
                TailoringReplacementReservation.application_id == fixture["application_id"]
            )
        )
        source = await db.get(CV, str(fixture["source_cv_id"]))
        draft = await db.get(CV, draft_cv_id)
        assert reservation is not None and source is not None and draft is not None
        if reservation.state == TAILORING_REPLACEMENT_TRANSFERRED:
            assert outcomes.count("transferred") == 1
            assert source.is_active is False and source.quota_counted is False
            assert draft.is_active is True and draft.quota_counted is True
        else:
            assert reservation.state == TAILORING_REPLACEMENT_RELEASED
            assert outcomes.count("released") == 1
            assert source.is_active is True and source.quota_counted is True
            assert draft.is_active is False and draft.quota_counted is False
        assert await db.scalar(select(User.cv_count).where(User.id == fixture["user_id"])) == 3
    assert sorted(outcomes) in (["released", "transfer_lost"], ["release_lost", "transferred"])


@pytest.mark.asyncio
async def test_concurrent_replacement_creation_has_one_pending_allowance():
    fixture = await _seed_account(cv_total=3, source=True)

    async def create_one(index: int) -> str:
        async with async_session() as db:
            try:
                await CVService(db).create_replacement_draft(
                    str(fixture["user_id"]),
                    CVCreate(title=f"Concurrent candidate {index}"),
                    application_id=str(fixture["application_id"]),
                    source_cv_id=str(fixture["source_cv_id"]),
                )
                await db.commit()
                return "created"
            except ReplacementAlreadyPendingError:
                await db.rollback()
                return "blocked"

    assert sorted(await asyncio.gather(create_one(1), create_one(2))) == ["blocked", "created"]
    async with async_session() as db:
        assert await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == fixture["application_id"],
                TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
            )
        ) == 1
        assert await db.scalar(
            select(func.count(CV.id)).where(
                CV.user_id == fixture["user_id"],
                CV.is_active.is_(True),
                CV.quota_counted.is_(False),
            )
        ) == 1
        assert await db.scalar(select(User.cv_count).where(User.id == fixture["user_id"])) == 3


@pytest.mark.asyncio
async def test_application_delete_competes_safely_with_replacement_creation():
    fixture = await _seed_account(cv_total=3, source=True)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    source_cv_id = str(fixture["source_cv_id"])

    async def delete_application() -> str:
        async with async_session() as db:
            deleted = await ApplicationService(db).delete_application(application_id, user_id)
            await db.commit()
            return "deleted" if deleted else "delete_lost"

    async def create_replacement() -> str:
        async with async_session() as db:
            try:
                await CVService(db).create_replacement_draft(
                    user_id,
                    CVCreate(title="Concurrent replacement"),
                    application_id=application_id,
                    source_cv_id=source_cv_id,
                )
                await db.commit()
                return "created"
            except LookupError:
                await db.rollback()
                return "application_gone"

    outcomes = await asyncio.gather(delete_application(), create_replacement())
    assert "deleted" in outcomes
    assert set(outcomes) in ({"deleted", "application_gone"}, {"deleted", "created"})

    async with async_session() as db:
        assert await db.get(Application, application_id) is None
        assert await db.scalar(
            select(func.count(TailoringReplacementReservation.id)).where(
                TailoringReplacementReservation.application_id == application_id
            )
        ) == 0
        assert await db.scalar(
            select(func.count(CV.id)).where(
                CV.user_id == user_id,
                CV.application_id == application_id,
                CV.is_active.is_(True),
                CV.quota_counted.is_(False),
            )
        ) == 0
        assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 3
        assert await db.scalar(select(User.application_count).where(User.id == user_id)) == 0


@pytest.mark.asyncio
async def test_normal_quota_reservation_keeps_pending_caller_work_and_caps_concurrent_creates():
    fixture = await _seed_account(cv_total=0, source=False)
    user_id = str(fixture["user_id"])
    pending_app_id = str(uuid4())
    async with async_session() as db:
        db.add(
            Application(
                id=pending_app_id,
                user_id=user_id,
                company="Pending fixture",
                role="Pending role",
                job_description="Pending work survives quota reservation",
            )
        )
        await QuotaService(db).reserve(user_id, QuotaResource.CV)
        await db.commit()
    async with async_session() as db:
        assert await db.get(Application, pending_app_id) is not None
        assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 1

    concurrent = await _seed_account(cv_total=0, source=False)
    concurrent_user_id = str(concurrent["user_id"])

    async def create_normal(index: int) -> str:
        async with async_session() as db:
            try:
                await CVService(db).create_cv(
                    concurrent_user_id,
                    CVCreate(title=f"Concurrent normal {index}"),
                )
                await db.commit()
                return "created"
            except QuotaExceededError:
                await db.rollback()
                return "blocked"

    outcomes = await asyncio.gather(*(create_normal(index) for index in range(5)))
    assert outcomes.count("created") == 3
    assert outcomes.count("blocked") == 2
    assert await _user_cv_count(concurrent_user_id) == 3


@pytest.mark.asyncio
async def test_cv_delete_competes_safely_with_manual_application_link(monkeypatch):
    fixture = await _seed_account(cv_total=0, source=False)
    user_id = str(fixture["user_id"])
    application_id = str(fixture["application_id"])
    async with async_session() as db:
        cv = await CVService(db).create_cv(user_id, CVCreate(title="Link race candidate"))
        await db.commit()
        cv_id = cv.id

    async def no_recompute(self, application, owner_id):
        return None

    monkeypatch.setattr(ApplicationService, "_recompute", no_recompute)

    async def delete_cv():
        async with async_session() as db:
            try:
                deleted = await CVService(db).delete_cv(cv_id, user_id)
                await db.commit()
                return "deleted" if deleted else "already_deleted"
            except CVLinkedToApplicationError:
                await db.rollback()
                return "delete_blocked_by_link"

    async def link_cv():
        async with async_session() as db:
            try:
                linked = await ApplicationService(db).update_application(
                    application_id,
                    user_id,
                    ApplicationUpdate(cv_id=cv_id),
                )
                await db.commit()
                return "linked" if linked is not None else "application_missing"
            except ApplicationCVLinkError:
                await db.rollback()
                return "link_blocked_by_delete"

    outcomes = await asyncio.gather(delete_cv(), link_cv())
    assert outcomes.count("deleted") + outcomes.count("linked") == 1

    async with async_session() as db:
        cv = await db.get(CV, cv_id)
        application = await db.get(Application, application_id)
        assert cv is not None and application is not None
        if outcomes.count("deleted"):
            assert outcomes == ["deleted", "link_blocked_by_delete"]
            assert not cv.is_active and application.cv_id is None
            assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 0
        else:
            assert outcomes == ["delete_blocked_by_link", "linked"]
            assert cv.is_active and cv.quota_counted
            assert application.cv_id == cv_id
            assert await db.scalar(select(User.cv_count).where(User.id == user_id)) == 1


@pytest.mark.asyncio
async def test_cv_revision_changes_only_for_changed_guard_fields():
    fixture = await _seed_account(cv_total=0, source=False)
    async with async_session() as db:
        cv = await CVService(db).create_cv(
            str(fixture["user_id"]),
            CVCreate(title="Initial title", description="Initial description"),
        )
        await db.commit()
        cv_id = cv.id
        revision = cv.revision

    async with async_session() as db:
        cv = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(title="Initial title", description="Initial description"),
        )
        assert cv is not None and cv.revision == revision
        cv.extra_metadata = {"display_hint": "not a document guard field"}
        await db.flush()
        cv = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(title="Renamed title"),
        )
        assert cv is not None and cv.revision == revision + 1
        revision = cv.revision
        cv = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(title="Renamed title"),
        )
        assert cv is not None and cv.revision == revision
        await db.commit()

    async with async_session() as db:
        cv = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(description="Changed description"),
        )
        assert cv is not None and cv.revision == revision + 1
        revision = cv.revision
        same_sections = cv.sections
        cv = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(sections=same_sections, customizations=cv.customizations),
        )
        assert cv is not None and cv.revision == revision
        await db.commit()

    async with async_session() as db:
        cv = await db.get(CV, cv_id)
        assert cv is not None
        changed_sections = list(cv.sections)
        if changed_sections:
            changed_sections[0] = {**changed_sections[0], "title": "Changed section title"}
        else:
            changed_sections = [
                {
                    "id": "sec_profile",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"summary": "Changed content"},
                }
            ]
        updated = await CVService(db).update_cv(
            cv_id,
            str(fixture["user_id"]),
            CVUpdate(sections=changed_sections),
        )
        assert updated is not None and updated.revision == revision + 1
        await db.commit()
