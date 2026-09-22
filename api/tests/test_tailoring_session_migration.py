"""SQLite contract test for the protocol-v1 tailoring state cleanup."""

from pathlib import Path
import runpy

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest


_MIGRATION = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "m8n9o0p1_remove_tailoring_v1_session_state.py"
    )
)
_V5_MIGRATION = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "s4t5u6v7_tailoring_v5_evaluation.py"
    )
)
compact_tailoring_session_table = _MIGRATION["compact_tailoring_session_table"]
downgrade = _MIGRATION["downgrade"]
v5_upgrade = _V5_MIGRATION["upgrade"]


def test_cleanup_drops_patch_columns_and_preserves_reviewable_draft_state():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE applications (id VARCHAR(36) PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE cvs (id VARCHAR(36) PRIMARY KEY)")
        connection.exec_driver_sql(
            """CREATE TABLE tailoring_sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                application_id VARCHAR(36) NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                cv_id VARCHAR(36) REFERENCES cvs(id) ON DELETE CASCADE,
                draft_cv_id VARCHAR(36) REFERENCES cvs(id) ON DELETE SET NULL,
                code_hash VARCHAR(64) NOT NULL UNIQUE,
                capability_hash VARCHAR(64) UNIQUE,
                status VARCHAR(16) NOT NULL,
                expires_at DATETIME NOT NULL,
                exchanged_at DATETIME,
                submitted_at DATETIME,
                reviewed_at DATETIME,
                context_hash VARCHAR(64),
                attempts INTEGER NOT NULL DEFAULT 0,
                result JSON,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                base_cv_revision INTEGER,
                base_cv_hash VARCHAR(64),
                base_requirements_hash VARCHAR(64),
                base_profile_hash VARCHAR(64),
                library_snapshot JSON NOT NULL DEFAULT '{}',
                reported_gaps JSON NOT NULL DEFAULT '[]',
                provenance JSON NOT NULL DEFAULT '[]'
            )"""
        )
        connection.exec_driver_sql(
            "INSERT INTO tailoring_sessions "
            "(id, user_id, application_id, cv_id, draft_cv_id, code_hash, status, expires_at, "
            "context_hash, attempts, result, created_at, updated_at, library_snapshot, reported_gaps, provenance) "
            "VALUES ('s', 'u', 'a', 'source', 'draft', 'hash', 'draft_ready', '2030-01-01', "
            "'context', 1, '{\"candidate_hash\":\"kept\"}', '2026-01-01', '2026-01-01', '{}', '[]', '[]')"
        )

        compact_tailoring_session_table(Operations(MigrationContext.configure(connection)))

        columns = {column["name"] for column in sa.inspect(connection).get_columns("tailoring_sessions")}
        assert not {
            "base_cv_revision",
            "base_cv_hash",
            "base_requirements_hash",
            "base_profile_hash",
            "library_snapshot",
            "reported_gaps",
            "provenance",
        } & columns
        foreign_keys = sa.inspect(connection).get_foreign_keys("tailoring_sessions")
        source_fk = next(fk for fk in foreign_keys if fk["constrained_columns"] == ["cv_id"])
        assert source_fk["options"]["ondelete"] == "SET NULL"
        row = connection.execute(sa.text("SELECT status, draft_cv_id, result FROM tailoring_sessions")).one()
        assert row.status == "draft_ready"
        assert row.draft_cv_id == "draft"
        assert row.result == '{"candidate_hash":"kept"}'


def test_cutover_downgrade_requires_restoring_a_database_backup():
    with pytest.raises(RuntimeError, match="restore a database backup"):
        downgrade()


def test_v5_migration_changes_only_the_default_and_leaves_historical_rows_untouched():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE tailoring_sessions (id VARCHAR(36) PRIMARY KEY, protocol_version INTEGER NOT NULL DEFAULT 4)"
        )
        connection.exec_driver_sql("INSERT INTO tailoring_sessions (id, protocol_version) VALUES ('legacy', 4)")

        v5_upgrade.__globals__["op"] = Operations(MigrationContext.configure(connection))
        v5_upgrade()

        column = next(column for column in sa.inspect(connection).get_columns("tailoring_sessions") if column["name"] == "protocol_version")
        row = connection.execute(sa.text("SELECT protocol_version FROM tailoring_sessions WHERE id = 'legacy'")).scalar_one()

    assert str(column["default"]).strip("'") == "5"
    assert row == 4
