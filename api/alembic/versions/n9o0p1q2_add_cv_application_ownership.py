"""record application ownership on generated and tailored CVs

Revision ID: n9o0p1q2
Revises: m8n9o0p1
Create Date: 2026-09-14 00:00:00.000000

"""

from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "n9o0p1q2"
down_revision: str | None = "m8n9o0p1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def backfill_cv_application_owners(connection: sa.Connection) -> None:
    """Use durable application and tailoring-session links, never CV metadata."""
    references = connection.execute(
        sa.text(
            """
            SELECT application_id, cv_id FROM (
                SELECT applications.id AS application_id, cvs.id AS cv_id
                FROM applications
                JOIN cvs
                  ON cvs.id = applications.cv_id
                 AND cvs.user_id = applications.user_id
                WHERE applications.cv_id IS NOT NULL

                UNION

                SELECT applications.id AS application_id, cvs.id AS cv_id
                FROM tailoring_sessions
                JOIN applications
                  ON applications.id = tailoring_sessions.application_id
                 AND applications.user_id = tailoring_sessions.user_id
                JOIN cvs
                  ON cvs.id = tailoring_sessions.cv_id
                 AND cvs.user_id = tailoring_sessions.user_id
                WHERE tailoring_sessions.cv_id IS NOT NULL

                UNION

                SELECT applications.id AS application_id, cvs.id AS cv_id
                FROM tailoring_sessions
                JOIN applications
                  ON applications.id = tailoring_sessions.application_id
                 AND applications.user_id = tailoring_sessions.user_id
                JOIN cvs
                  ON cvs.id = tailoring_sessions.draft_cv_id
                 AND cvs.user_id = tailoring_sessions.user_id
                WHERE tailoring_sessions.draft_cv_id IS NOT NULL
            )
            """
        )
    ).all()

    application_ids_by_cv: dict[str, set[str]] = defaultdict(set)
    for application_id, cv_id in references:
        application_ids_by_cv[cv_id].add(application_id)

    # A CV referenced by multiple applications has ambiguous provenance. Leave
    # it unassociated rather than hide it under the wrong application.
    updates = [
        {"cv_id": cv_id, "application_id": next(iter(application_ids))}
        for cv_id, application_ids in application_ids_by_cv.items()
        if len(application_ids) == 1
    ]
    if updates:
        connection.execute(
            sa.text("UPDATE cvs SET application_id = :application_id WHERE id = :cv_id"),
            updates,
        )


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # SQLite can add a nullable REFERENCES column directly when its default
        # is NULL. Keeping the FK inline avoids rebuilding cvs, which is
        # already referenced by applications and tailoring_sessions.
        connection.exec_driver_sql(
            "ALTER TABLE cvs ADD COLUMN application_id VARCHAR(36) "
            "CONSTRAINT fk_cvs_application_id_applications "
            "REFERENCES applications (id) ON DELETE SET NULL"
        )
    else:
        op.add_column(
            "cvs",
            sa.Column(
                "application_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "applications.id",
                    name="fk_cvs_application_id_applications",
                    ondelete="SET NULL",
                ),
                nullable=True,
            ),
        )
    op.create_index("ix_cvs_application_id", "cvs", ["application_id"], unique=False)
    backfill_cv_application_owners(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_cvs_application_id", table_name="cvs")
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("ALTER TABLE cvs DROP COLUMN application_id")
    else:
        op.drop_column("cvs", "application_id")


__all__ = ["backfill_cv_application_owners"]
