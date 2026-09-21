"""remove local CV generation state from applications

Revision ID: p1q2r3s4
Revises: o0p1q2r3
Create Date: 2026-09-20 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p1q2r3s4"
down_revision: str | None = "o0p1q2r3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("applications", "fits_one_page")
    op.drop_column("applications", "generation_error")
    op.drop_column("applications", "generation_status")


def downgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("generation_status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.add_column("applications", sa.Column("generation_error", sa.String(length=500), nullable=True))
    op.add_column("applications", sa.Column("fits_one_page", sa.Boolean(), nullable=True))
