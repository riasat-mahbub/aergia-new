"""Protocol-v10 migration and database-invariant regressions."""

import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import (
    Application,
    CV,
    TailoringEvaluationRecord,
    TailoringPreviewReservation,
    TailoringReplacementReservation,
    TailoringSession,
    User,
)


API_DIR = Path(__file__).parents[1]
V9_REVISION = "v0w1x2y3"
V10_REVISION = "w1x2y3z4"


def _alembic_executable() -> str:
    local = API_DIR / ".venv" / "bin" / "alembic"
    return str(local) if local.exists() else (shutil.which("alembic") or "alembic")


def _run_alembic(database_path: Path, revision: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"
    result = subprocess.run(
        [_alembic_executable(), "upgrade", revision],
        cwd=API_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Alembic upgrade failed:\n{result.stdout}\n{result.stderr}"
    return result


def _fixture_value(column: sa.Column) -> object:
    if isinstance(column.type, sa.Boolean):
        return False
    if isinstance(column.type, sa.DateTime):
        return datetime(2026, 9, 1, tzinfo=timezone.utc)
    if isinstance(column.type, sa.JSON):
        return [] if column.name in {"extracted_keywords", "reported_gaps", "warnings"} else {}
    if isinstance(column.type, sa.Integer):
        return 0
    if isinstance(column.type, sa.String):
        return f"fixture-{column.name}"
    if isinstance(column.type, sa.Text):
        return f"fixture {column.name}"
    return None


def _insert_v9_row(connection: sa.Connection, table_name: str, values: dict[str, object]) -> None:
    table = sa.Table(table_name, sa.MetaData(), autoload_with=connection)
    row = dict(values)
    for column in table.columns:
        if column.name in row or column.nullable or column.server_default is not None or column.autoincrement:
            continue
        row[column.name] = _fixture_value(column)
    connection.execute(table.insert().values(row))


def _insert_user(connection: sa.Connection) -> None:
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    _insert_v9_row(
        connection,
        "users",
        {
            "id": "user-v9",
            "email": "synthetic-v9@example.test",
            "password_hash": "synthetic-hash",
            "profile_data": {},
            "account_tier": "free",
            "application_count": 91,
            "cv_count": 92,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
        },
    )


def _insert_application(connection: sa.Connection, application_id: str, cv_id: str) -> None:
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    _insert_v9_row(
        connection,
        "applications",
        {
            "id": application_id,
            "user_id": "user-v9",
            "cv_id": cv_id,
            "company": "Example Co",
            "role": "Engineer",
            "job_description": "Build reliable software.",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        },
    )


def _insert_cv(connection: sa.Connection, cv_id: str, *, is_active: bool = True) -> None:
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    _insert_v9_row(
        connection,
        "cvs",
        {
            "id": cv_id,
            "user_id": "user-v9",
            "application_id": None,
            "title": cv_id,
            "template_id": "minimal",
            "customizations": {},
            "sections": {},
            "metadata": {},
            "revision": 1,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        },
    )


def _insert_session(
    connection: sa.Connection,
    session_id: str,
    application_id: str,
    *,
    status: str,
    created_at: datetime,
    protocol_version: int = 9,
    draft_cv_id: str | None = None,
) -> None:
    result = {"historical_session": session_id, "draft_cv_id": draft_cv_id}
    _insert_v9_row(
        connection,
        "tailoring_sessions",
        {
            "id": session_id,
            "user_id": "user-v9",
            "application_id": application_id,
            "cv_id": "cv-source",
            "draft_cv_id": draft_cv_id,
            "code_hash": (f"code-{session_id}" + ("0" * 64))[:64],
            "capability_hash": (f"cap-{session_id}" + ("0" * 64))[:64],
            "status": status,
            "expires_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "protocol_version": protocol_version,
            "context_hash": "a" * 64,
            "context_snapshot": {"legacy": "context"},
            "attempts": 1,
            "result": result,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )


def test_upgrade_from_populated_v9_reconciles_sessions_and_repairs_counts(tmp_path: Path):
    database_path = tmp_path / "tailoring-v9-history.db"
    _run_alembic(database_path, V9_REVISION)

    with sa.create_engine(f"sqlite:///{database_path}").begin() as connection:
        _insert_user(connection)
        _insert_cv(connection, "cv-source")
        _insert_cv(connection, "cv-source-two")
        _insert_cv(connection, "cv-ready-deleted", is_active=False)
        for cv_id in ("cv-ready-latest", "cv-created", "cv-app-two-old", "cv-app-two-new"):
            _insert_cv(connection, cv_id)
        _insert_application(connection, "application-one", "cv-source")
        _insert_application(connection, "application-two", "cv-source-two")

        _insert_session(
            connection,
            "ready-old",
            "application-one",
            status="draft_ready",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            draft_cv_id="cv-ready-deleted",
        )
        _insert_session(
            connection,
            "ready-latest",
            "application-one",
            status="draft_ready",
            created_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
            draft_cv_id="cv-ready-latest",
        )
        # Newer in wall-clock order, but a submitted draft remains the
        # deterministic winner for this application's blocking session.
        _insert_session(
            connection,
            "created-newer",
            "application-one",
            status="created",
            created_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
            draft_cv_id="cv-created",
        )
        _insert_session(
            connection,
            "active-v4",
            "application-two",
            status="created",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            protocol_version=4,
            draft_cv_id="cv-app-two-old",
        )
        _insert_session(
            connection,
            "active-v9",
            "application-two",
            status="exchanged",
            created_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
            protocol_version=9,
            draft_cv_id="cv-app-two-new",
        )

    _run_alembic(database_path, "head")

    with sa.create_engine(f"sqlite:///{database_path}").connect() as connection:
        sessions = {
            row.id: row
            for row in connection.execute(
                sa.text(
                    "SELECT id, status, capability_hash, draft_cv_id, protocol_version, "
                    "context_snapshot, result FROM tailoring_sessions"
                )
            )
        }
        assert sessions["ready-latest"].status == "draft_ready"
        assert sessions["ready-old"].status == "stale"
        assert sessions["created-newer"].status == "stale"
        assert sessions["active-v4"].status == "stale"
        assert sessions["active-v9"].status == "stale"
        assert sessions["ready-old"].capability_hash is None
        assert sessions["created-newer"].capability_hash is None
        assert sessions["active-v4"].capability_hash is None
        assert sessions["active-v9"].capability_hash is None
        assert sessions["ready-old"].draft_cv_id == "cv-ready-deleted"
        assert json.loads(sessions["ready-old"].result) == {
            "historical_session": "ready-old",
            "draft_cv_id": "cv-ready-deleted",
        }
        assert json.loads(sessions["ready-latest"].context_snapshot) == {"legacy": "context"}
        assert sessions["active-v4"].protocol_version == 4
        assert sessions["active-v9"].protocol_version == 9

        counters = connection.execute(
            sa.text("SELECT application_count, cv_count FROM users WHERE id = 'user-v9'")
        ).one()
        assert counters == (2, 6)
        assert connection.execute(sa.text("SELECT COUNT(*) FROM cvs")).scalar_one() == 7
        counted_rows = connection.execute(
            sa.text("SELECT quota_counted FROM cvs WHERE id = 'cv-ready-deleted'")
        ).scalar_one()
        assert counted_rows == 1
        assert connection.execute(sa.text("SELECT COUNT(*) FROM tailoring_replacement_reservations")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT COUNT(*) FROM tailoring_evaluations")).scalar_one() == 0

        columns = {column["name"]: column for column in sa.inspect(connection).get_columns("tailoring_sessions")}
        assert str(columns["protocol_version"]["default"]).strip("'") == "10"
        cv_columns = {column["name"]: column for column in sa.inspect(connection).get_columns("cvs")}
        assert str(cv_columns["quota_counted"]["default"]).strip("()") in {"1", "true"}
        assert {
            "source_cv_revision",
            "target_guard_hash",
            "submission_result",
            "owner_review_state",
            "owner_cv_revision",
            "owner_candidate_hash",
            "owner_render_basis_hash",
            "owner_evaluation_id",
            "owner_pdf_sha256",
        } <= columns.keys()


def test_fresh_upgrade_has_v10_columns_indexes_and_non_destructive_downgrade_policy(tmp_path: Path):
    database_path = tmp_path / "tailoring-v10-fresh.db"
    _run_alembic(database_path, "head")

    expected_indexes = {
        "uq_tailoring_sessions_one_blocking_per_application",
        "uq_tailoring_preview_reservations_session_request",
        "uq_tailoring_preview_reservations_one_active_session",
        "uq_tailoring_preview_reservations_evaluation",
        "uq_tailoring_evaluations_reservation",
        "uq_tailoring_replacement_reservations_one_pending_application",
        "uq_tailoring_replacement_reservations_one_pending_source_cv",
    }
    with sa.create_engine(f"sqlite:///{database_path}").connect() as connection:
        index_names = {
            index["name"]
            for table_name in (
                "tailoring_sessions",
                "tailoring_preview_reservations",
                "tailoring_evaluations",
                "tailoring_replacement_reservations",
            )
            for index in sa.inspect(connection).get_indexes(table_name)
        }
        assert expected_indexes <= index_names

        statements = {
            row.name: row.sql
            for row in connection.execute(
                sa.text(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type = 'index' AND sql IS NOT NULL"
                )
            )
        }
        assert "'created', 'exchanged', 'draft_ready'" in statements[
            "uq_tailoring_sessions_one_blocking_per_application"
        ]
        assert "state = 'active'" in statements["uq_tailoring_preview_reservations_one_active_session"]
        assert "state = 'pending'" in statements[
            "uq_tailoring_replacement_reservations_one_pending_application"
        ]
        evaluation_columns = {
            column["name"]: column for column in sa.inspect(connection).get_columns("tailoring_evaluations")
        }
        assert evaluation_columns["pdf_bytes"]["nullable"] is True
        assert evaluation_columns["page_count"]["nullable"] is False

    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"
    downgrade = subprocess.run(
        [_alembic_executable(), "downgrade", V9_REVISION],
        cwd=API_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert downgrade.returncode != 0
    assert "restore a compatible database backup" in downgrade.stderr

    with sa.create_engine(f"sqlite:///{database_path}").connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == V10_REVISION
        assert connection.execute(sa.text("SELECT COUNT(*) FROM tailoring_evaluations")).scalar_one() == 0


def test_partial_uniqueness_holds_across_independent_async_sessions(tmp_path: Path):
    database_path = tmp_path / "tailoring-v10-constraints.db"
    _run_alembic(database_path, "head")

    async def exercise_constraints() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            poolclass=NullPool,
            connect_args={"timeout": 5},
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)

        user_id = str(uuid4())
        application_one = str(uuid4())
        application_two = str(uuid4())
        source_one = str(uuid4())
        source_two = str(uuid4())
        session_id = str(uuid4())
        reservation_id = str(uuid4())
        first_request_id = str(uuid4())

        async with factory() as db:
            user = User(
                id=user_id,
                email=f"{user_id}@example.test",
                password_hash="synthetic-hash",
                profile_data={},
                account_tier="free",
            )
            app_one = Application(
                id=application_one,
                user_id=user_id,
                company="Example One",
                role="Engineer",
                job_description="Build software.",
            )
            app_two = Application(
                id=application_two,
                user_id=user_id,
                company="Example Two",
                role="Designer",
                job_description="Design software.",
            )
            cv_one = CV(
                id=source_one,
                user_id=user_id,
                title="Source one",
                template_id="minimal",
                sections={},
                quota_counted=True,
                is_active=True,
            )
            cv_two = CV(
                id=source_two,
                user_id=user_id,
                title="Source two",
                template_id="minimal",
                sections={},
                quota_counted=True,
                is_active=True,
            )
            db.add_all([user, app_one, app_two, cv_one, cv_two])
            await db.flush()
            app_one.cv_id = source_one
            app_two.cv_id = source_two
            await db.commit()

        async with factory() as db:
            db.add(
                TailoringSession(
                    id=session_id,
                    user_id=user_id,
                    application_id=application_one,
                    code_hash="1" * 64,
                    expires_at=now + timedelta(hours=1),
                )
            )
            await db.commit()
            stored_session = await db.get(TailoringSession, session_id)
            assert stored_session is not None
            assert stored_session.protocol_version == 10

        async with factory() as independent:
            independent.add(
                TailoringSession(
                    user_id=user_id,
                    application_id=application_one,
                    code_hash="2" * 64,
                    expires_at=now + timedelta(hours=1),
                    status="exchanged",
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add(
                TailoringSession(
                    user_id=user_id,
                    application_id=application_one,
                    code_hash="3" * 64,
                    expires_at=now + timedelta(hours=1),
                    status="stale",
                )
            )
            await independent.commit()

        async with factory() as db:
            db.add(
                TailoringPreviewReservation(
                    id=reservation_id,
                    session_id=session_id,
                    request_id=first_request_id,
                    candidate_hash="a" * 64,
                    context_hash="b" * 64,
                    expires_at=now + timedelta(seconds=120),
                )
            )
            await db.commit()

        async with factory() as independent:
            independent.add(
                TailoringPreviewReservation(
                    session_id=session_id,
                    request_id=str(uuid4()),
                    candidate_hash="c" * 64,
                    context_hash="b" * 64,
                    expires_at=now + timedelta(seconds=120),
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add(
                TailoringPreviewReservation(
                    session_id=session_id,
                    request_id=first_request_id,
                    candidate_hash="a" * 64,
                    context_hash="b" * 64,
                    expires_at=now + timedelta(seconds=120),
                    state="released",
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add(
                TailoringPreviewReservation(
                    session_id=session_id,
                    request_id=str(uuid4()),
                    candidate_hash="c" * 64,
                    context_hash="b" * 64,
                    expires_at=now + timedelta(seconds=120),
                    state="released",
                )
            )
            await independent.commit()

        preview = TailoringEvaluationRecord(
            id="agent-preview-evaluation-001",
            session_id=session_id,
            kind="agent_preview",
            reservation_id=reservation_id,
            candidate_hash="a" * 64,
            candidate={"title": "Synthetic"},
            scanner_result={"schema_version": "scanner-v1"},
            evaluation={"version": "tailoring-evaluation-v2"},
            render_warnings=[],
            page_count=1,
            pdf_sha256="d" * 64,
            pdf_bytes=b"%PDF-synthetic",
        )
        async with factory() as db:
            db.add(preview)
            await db.commit()

        async with factory() as independent:
            independent.add(
                TailoringEvaluationRecord(
                    id="agent-preview-evaluation-002",
                    session_id=session_id,
                    kind="agent_preview",
                    reservation_id=reservation_id,
                    candidate_hash="a" * 64,
                    candidate={"title": "Synthetic"},
                    scanner_result={"schema_version": "scanner-v1"},
                    evaluation={"version": "tailoring-evaluation-v2"},
                    render_warnings=[],
                    page_count=1,
                    pdf_sha256="d" * 64,
                    pdf_bytes=b"%PDF-synthetic",
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add_all(
                [
                    TailoringEvaluationRecord(
                        id="owner-review-evaluation-0001",
                        session_id=session_id,
                        kind="owner_review",
                        candidate_hash="e" * 64,
                        candidate={"title": "Owner version one"},
                        scanner_result={"schema_version": "scanner-v1"},
                        evaluation={"version": "tailoring-evaluation-v2"},
                        render_warnings=[],
                        page_count=1,
                        pdf_sha256="f" * 64,
                        pdf_bytes=None,
                    ),
                    TailoringEvaluationRecord(
                        id="owner-review-evaluation-0002",
                        session_id=session_id,
                        kind="owner_review",
                        candidate_hash="e" * 64,
                        candidate={"title": "Owner version two"},
                        scanner_result={"schema_version": "scanner-v1"},
                        evaluation={"version": "tailoring-evaluation-v2"},
                        render_warnings=[],
                        page_count=1,
                        pdf_sha256="f" * 64,
                        pdf_bytes=None,
                    ),
                ]
            )
            await independent.commit()

        async with factory() as db:
            db.add(
                TailoringReplacementReservation(
                    application_id=application_one,
                    source_cv_id=source_one,
                    state="pending",
                )
            )
            await db.commit()

        async with factory() as independent:
            independent.add(
                TailoringReplacementReservation(
                    application_id=application_one,
                    source_cv_id=source_two,
                    state="pending",
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add(
                TailoringReplacementReservation(
                    application_id=application_two,
                    source_cv_id=source_one,
                    state="pending",
                )
            )
            with pytest.raises(IntegrityError):
                await independent.flush()
            await independent.rollback()

        async with factory() as independent:
            independent.add(
                TailoringReplacementReservation(
                    application_id=application_two,
                    source_cv_id=source_two,
                    state="pending",
                )
            )
            await independent.commit()

        await engine.dispose()

    asyncio.run(exercise_constraints())
