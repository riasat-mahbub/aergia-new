"""add applications tracker

Revision ID: a72e6d4c1b90
Revises: 9f3c5a8b7d21
Create Date: 2026-08-27 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a72e6d4c1b90"
down_revision: Union[str, None] = "9f3c5a8b7d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("cv_id", sa.String(length=36), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("job_url", sa.String(length=2048), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("generation_error", sa.String(length=500), nullable=True),
        sa.Column("extracted_keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("relevance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False, server_default="keyword-v1"),
        sa.Column("fits_one_page", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_index(op.f("ix_applications_cv_id"), "applications", ["cv_id"], unique=False)
    op.create_index("ix_applications_user_status", "applications", ["user_id", "status"], unique=False)
    op.create_index("ix_applications_user_updated_at", "applications", ["user_id", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_applications_user_updated_at", table_name="applications")
    op.drop_index("ix_applications_user_status", table_name="applications")
    op.drop_index(op.f("ix_applications_cv_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_table("applications")
