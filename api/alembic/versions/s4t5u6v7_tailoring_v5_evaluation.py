"""make v5 the default for new tailoring sessions

Revision ID: s4t5u6v7
Revises: r3s4t5u6
Create Date: 2026-09-22 00:00:00

Existing rows are intentionally untouched.  Submitted v4 drafts retain their
historical protocol and can still be reviewed by the authenticated owner.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "s4t5u6v7"
down_revision: str | None = "r3s4t5u6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="5",
        )


def downgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="4",
        )
