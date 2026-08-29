"""add atomic application and CV quota counters to users

Revision ID: e8f9a1b2c3d4
Revises: d7f8a1b2c3d4
Create Date: 2026-08-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e8f9a1b2c3d4"
down_revision: str | None = "d7f8a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("application_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("cv_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET application_count = "
            "(SELECT COUNT(*) FROM applications WHERE applications.user_id = users.id)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE users SET cv_count = "
            "(SELECT COUNT(*) FROM cvs WHERE cvs.user_id = users.id AND cvs.is_active = 1)"
        )
    )


def downgrade() -> None:
    op.drop_column("users", "cv_count")
    op.drop_column("users", "application_count")
