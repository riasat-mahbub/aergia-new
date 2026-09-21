"""add versioned scanner result storage to applications

Revision ID: o0p1q2r3
Revises: n9o0p1q2
Create Date: 2026-09-20 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "o0p1q2r3"
down_revision: str | None = "n9o0p1q2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("scanner_result", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "scanner_result")
