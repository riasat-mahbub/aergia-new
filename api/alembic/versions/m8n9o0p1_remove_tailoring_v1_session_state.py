"""remove obsolete protocol-v1 tailoring session state

Revision ID: m8n9o0p1
Revises: l7m8n9o0p1
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "m8n9o0p1"
down_revision: str | None = "l7m8n9o0p1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def compact_tailoring_session_table(operations) -> None:
    """Drop patch-only columns and make source-CV deletion non-destructive."""

    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with operations.batch_alter_table(
        "tailoring_sessions",
        recreate="always",
        naming_convention=naming_convention,
    ) as batch:
        # The original SQLite migration created this FK anonymously, so the
        # convention supplies a stable temporary name for the table rebuild.
        batch.drop_constraint("fk_tailoring_sessions_cv_id_cvs", type_="foreignkey")
        batch.create_foreign_key(
            "fk_tailoring_sessions_cv_id_cvs",
            "cvs",
            ["cv_id"],
            ["id"],
            ondelete="SET NULL",
        )
        for column in (
            "base_cv_revision",
            "base_cv_hash",
            "base_requirements_hash",
            "base_profile_hash",
            "library_snapshot",
            "reported_gaps",
            "provenance",
        ):
            batch.drop_column(column)


def upgrade() -> None:
    # Earlier v1 patch sessions are already expired by the preceding cutover.
    # Preserve completed sessions as accepted so their status remains readable
    # by the v2 owner-facing history endpoint.
    op.execute(
        sa.text(
            "UPDATE tailoring_sessions "
            "SET status = 'accepted', capability_hash = NULL, result = NULL "
            "WHERE status = 'applied'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE tailoring_sessions "
            "SET capability_hash = NULL "
            "WHERE status IN ('expired', 'cancelled', 'failed', 'stale', 'rejected', 'accepted')"
        )
    )
    compact_tailoring_session_table(op)


def downgrade() -> None:
    # Reintroducing patch-only state would not make v1 sessions replay-safe;
    # refusing downgrade avoids claiming an old schema over missing data.
    raise RuntimeError("This tailoring cutover is irreversible; restore a database backup to roll back")


__all__ = ["compact_tailoring_session_table"]
