"""store tailoring snapshot identity and the sanitized result for polling

Revision ID: i4j5k6l7m8
Revises: h3i4j5k6l7
Create Date: 2026-08-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "i4j5k6l7m8"
down_revision: str | None = "h3i4j5k6l7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tailoring_sessions",
        sa.Column("base_profile_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tailoring_sessions",
        sa.Column("result", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tailoring_sessions", "result")
    op.drop_column("tailoring_sessions", "base_profile_hash")
