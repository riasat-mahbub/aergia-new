"""add application history, follow-ups, and quality results

Revision ID: c4e1f2a3b4c5
Revises: a72e6d4c1b90
Create Date: 2026-08-28 00:00:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "c4e1f2a3b4c5"
down_revision: Union[str, None] = "a72e6d4c1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("next_follow_up_at", sa.Date(), nullable=True))
    op.add_column("applications", sa.Column("quality", sa.JSON(), nullable=False, server_default="{}"))
    op.create_index(
        "ix_applications_user_follow_up",
        "applications",
        ["user_id", "next_follow_up_at"],
        unique=False,
    )
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_application_status_history_application_id"),
        "application_status_history",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_status_history_application_changed",
        "application_status_history",
        ["application_id", "changed_at"],
        unique=False,
    )

    # Preserve the current state of existing applications as their first
    # visible history entry. Generate IDs in Python so the backfill remains
    # portable across database engines.
    bind = op.get_bind()
    existing_applications = bind.execute(sa.text(
        "SELECT id, status, created_at FROM applications"
    )).mappings().all()
    for application in existing_applications:
        bind.execute(
            sa.text(
                "INSERT INTO application_status_history "
                "(id, application_id, from_status, to_status, changed_at) "
                "VALUES (:id, :application_id, NULL, :to_status, :changed_at)"
            ),
            {
                "id": str(uuid4()),
                "application_id": application["id"],
                "to_status": application["status"],
                "changed_at": application["created_at"],
            },
        )


def downgrade() -> None:
    op.drop_index("ix_status_history_application_changed", table_name="application_status_history")
    op.drop_index(op.f("ix_application_status_history_application_id"), table_name="application_status_history")
    op.drop_table("application_status_history")
    op.drop_index("ix_applications_user_follow_up", table_name="applications")
    op.drop_column("applications", "quality")
    op.drop_column("applications", "next_follow_up_at")
