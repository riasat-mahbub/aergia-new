"""use protocol v8 for new tailoring sessions

Revision ID: u9v0w1x2
Revises: t8u9v0w1
Create Date: 2026-09-24 00:00:00

Existing session rows retain their historical protocol and saved results.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "u9v0w1x2"
down_revision: str | None = "t8u9v0w1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="8",
        )


def downgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="7",
        )
