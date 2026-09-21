"""track applications whose scanner result needs an explicit rescan

Revision ID: q2r3s4t5
Revises: p1q2r3s4
Create Date: 2026-09-21 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "q2r3s4t5"
down_revision: str | None = "p1q2r3s4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("scanner_rescan_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("applications", "scanner_rescan_required")
