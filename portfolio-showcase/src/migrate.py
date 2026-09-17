"""Initialize the disposable showcase database with the real schema history."""

from __future__ import annotations

import runpy
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from .config import ShowcaseConfig


def migrate_database(config: ShowcaseConfig, database_path: Path) -> None:
    """Apply the repository's Alembic upgrades through a sync SQLite engine.

    Aergia's runtime intentionally uses ``sqlite+aiosqlite``. The showcase
    initializer uses a short-lived synchronous connection only for migrations
    so it remains usable on Python/runtime combinations where aiosqlite cannot
    open a worker connection. The migration functions themselves are the same
    functions used by the application's normal Alembic command.
    """

    alembic_config = Config(str(config.alembic_ini))
    alembic_config.set_main_option("script_location", str(config.alembic_dir))
    script = ScriptDirectory.from_config(alembic_config)
    revision_chain = _revision_chain(script)

    engine = sa.create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )

            current = connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if current is not None:
                raise RuntimeError(
                    f"showcase database is not empty; found Alembic revision {current!r}"
                )

            for revision in revision_chain:
                namespace = runpy.run_path(str(revision.path))
                upgrade = namespace.get("upgrade")
                if not callable(upgrade):
                    raise RuntimeError(f"migration {revision.revision} has no callable upgrade()")
                with Operations.context(MigrationContext.configure(connection)):
                    upgrade()
                if current is None:
                    connection.execute(
                        sa.text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                        {"revision": revision.revision},
                    )
                else:
                    connection.execute(
                        sa.text("UPDATE alembic_version SET version_num = :revision"),
                        {"revision": revision.revision},
                    )
                current = revision.revision

    finally:
        engine.dispose()


def _revision_chain(script: ScriptDirectory) -> list:
    """Return the linear repository migration chain from base to head."""

    head = script.get_current_head()
    if head is None:
        raise RuntimeError("no Alembic head found for the showcase database")

    revisions = []
    revision_id: str | None = head
    while revision_id is not None:
        revision = script.get_revision(revision_id)
        if revision is None:
            raise RuntimeError(f"Alembic revision {revision_id!r} is missing")
        revisions.append(revision)
        if isinstance(revision.down_revision, tuple):
            raise RuntimeError("showcase migrations must have one linear Alembic history")
        revision_id = revision.down_revision

    revisions.reverse()
    return revisions
