"""Create templates table

Revision ID: 004
Revises: 003
Create Date: 2026-06-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("preview_image_url", sa.String(500), nullable=True),
        sa.Column("layout_config", postgresql.JSONB, nullable=False),
        sa.Column("section_schema", postgresql.JSONB, nullable=False),
        sa.Column("default_customizations", postgresql.JSONB, nullable=True),
        sa.Column("is_system", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("templates")
