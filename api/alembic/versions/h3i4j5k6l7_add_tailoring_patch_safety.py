"""add CV revisions and tailoring evidence snapshots

Revision ID: h3i4j5k6l7
Revises: g2h3i4j5k6l7
Create Date: 2026-08-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "h3i4j5k6l7"
down_revision: str | None = "g2h3i4j5k6l7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing CVs start at revision 1. The server uses a conditional update
    # against this column when applying a tailoring patch.
    op.add_column(
        "cvs",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("base_cv_revision", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("base_cv_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("base_requirements_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("library_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("tailoring_sessions", "provenance")
    op.drop_column("tailoring_sessions", "library_snapshot")
    op.drop_column("tailoring_sessions", "base_requirements_hash")
    op.drop_column("tailoring_sessions", "base_cv_hash")
    op.drop_column("tailoring_sessions", "base_cv_revision")
    op.drop_column("cvs", "revision")
