"""add short-lived local tailoring sessions

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-08-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "g2h3i4j5k6l7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tailoring_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("cv_id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("capability_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="created"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exchanged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reported_gaps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
        sa.UniqueConstraint("capability_hash"),
    )
    op.create_index(
        "ix_tailoring_sessions_user_id",
        "tailoring_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_tailoring_sessions_user_status",
        "tailoring_sessions",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tailoring_sessions_expires_at",
        "tailoring_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_tailoring_sessions_application_id",
        "tailoring_sessions",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        "ix_tailoring_sessions_cv_id",
        "tailoring_sessions",
        ["cv_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tailoring_sessions_cv_id", table_name="tailoring_sessions")
    op.drop_index("ix_tailoring_sessions_application_id", table_name="tailoring_sessions")
    op.drop_index("ix_tailoring_sessions_expires_at", table_name="tailoring_sessions")
    op.drop_index("ix_tailoring_sessions_user_status", table_name="tailoring_sessions")
    op.drop_index("ix_tailoring_sessions_user_id", table_name="tailoring_sessions")
    op.drop_table("tailoring_sessions")
