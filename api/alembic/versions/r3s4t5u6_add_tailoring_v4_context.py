"""persist tailoring protocol and frozen scanner context

Revision ID: r3s4t5u6
Revises: q2r3s4t5
Create Date: 2026-09-21 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "r3s4t5u6"
down_revision: str | None = "q2r3s4t5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows are protocol-v2 history. New rows use the model/server
    # default of v4. Their result payloads remain untouched.
    op.add_column(
        "tailoring_sessions",
        sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="4"),
    )
    op.execute(sa.text("UPDATE tailoring_sessions SET protocol_version = 2"))
    op.add_column("tailoring_sessions", sa.Column("context_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tailoring_sessions", "context_snapshot")
    op.drop_column("tailoring_sessions", "protocol_version")
