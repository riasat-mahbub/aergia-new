"""SQLite contract for adding and backfilling application-owned CV links."""

from pathlib import Path
import runpy

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


_MIGRATION = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "n9o0p1q2_add_cv_application_ownership.py"
    )
)
upgrade = _MIGRATION["upgrade"]
downgrade = _MIGRATION["downgrade"]


def test_application_ownership_migration_backfills_relational_history_only():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
        with connection.begin():
            _exercise_application_ownership_migration(connection)


def _exercise_application_ownership_migration(connection):
    connection.exec_driver_sql(
        "CREATE TABLE cvs (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE applications ("
        "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
        "cv_id VARCHAR(36) REFERENCES cvs(id) ON DELETE SET NULL)"
    )
    connection.exec_driver_sql(
        "CREATE TABLE tailoring_sessions ("
        "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
        "application_id VARCHAR(36) NOT NULL REFERENCES applications(id) ON DELETE CASCADE, "
        "cv_id VARCHAR(36) REFERENCES cvs(id) ON DELETE SET NULL, "
        "draft_cv_id VARCHAR(36) REFERENCES cvs(id) ON DELETE SET NULL)"
    )
    connection.exec_driver_sql(
        "INSERT INTO cvs (id, user_id) VALUES "
        "('current', 'owner'), ('old-source', 'owner'), ('accepted-draft', 'owner'), "
        "('ordinary', 'owner'), ('foreign-cv', 'foreign-owner'), ('ambiguous', 'owner')"
    )
    connection.exec_driver_sql(
        "INSERT INTO applications (id, user_id, cv_id) VALUES "
        "('app', 'owner', 'current'), ('other-app', 'owner', NULL)"
    )
    connection.exec_driver_sql(
        "INSERT INTO tailoring_sessions "
        "(id, user_id, application_id, cv_id, draft_cv_id) VALUES "
        "('accepted-session', 'owner', 'app', 'old-source', 'accepted-draft'), "
        "('wrong-owner-session', 'owner', 'app', 'foreign-cv', NULL), "
        "('first-ambiguous-session', 'owner', 'app', 'ambiguous', NULL), "
        "('second-ambiguous-session', 'owner', 'other-app', 'ambiguous', NULL)"
    )

    with Operations.context(MigrationContext.configure(connection)):
        upgrade()

    associations = dict(connection.execute(sa.text("SELECT id, application_id FROM cvs")).all())
    assert associations == {
        "current": "app",
        "old-source": "app",
        "accepted-draft": "app",
        "ordinary": None,
        "foreign-cv": None,
        "ambiguous": None,
    }

    foreign_keys = connection.exec_driver_sql("PRAGMA foreign_key_list(cvs)").all()
    application_fk = next(fk for fk in foreign_keys if fk[3] == "application_id")
    assert application_fk[2] == "applications"
    assert application_fk[6] == "SET NULL"

    indexes = sa.inspect(connection).get_indexes("cvs")
    application_index = next(index for index in indexes if index["name"] == "ix_cvs_application_id")
    assert application_index["column_names"] == ["application_id"]

    with Operations.context(MigrationContext.configure(connection)):
        downgrade()
    assert "application_id" not in {column["name"] for column in sa.inspect(connection).get_columns("cvs")}
