"""Add content and user_id columns to templates table

Revision ID: 005
Revises: 004
Create Date: 2026-06-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("content", sa.Text, nullable=True))
    op.add_column("templates", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index("ix_templates_user_id", "templates", ["user_id"])
    op.create_foreign_key(
        "fk_templates_user_id",
        "templates",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_templates_user_id", "templates", type_="foreignkey")
    op.drop_index("ix_templates_user_id", "templates")
    op.drop_column("templates", "user_id")
    op.drop_column("templates", "content")
