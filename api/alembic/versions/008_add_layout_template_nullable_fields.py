"""Add layout_template column and make layout fields nullable for user templates

Revision ID: 008
Revises: 007
Create Date: 2026-06-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("layout_template", sa.Text, nullable=True))
    op.alter_column("templates", "layout_config", nullable=True)
    op.alter_column("templates", "section_schema", nullable=True)


def downgrade() -> None:
    op.alter_column("templates", "section_schema", nullable=False)
    op.alter_column("templates", "layout_config", nullable=False)
    op.drop_column("templates", "layout_template")
