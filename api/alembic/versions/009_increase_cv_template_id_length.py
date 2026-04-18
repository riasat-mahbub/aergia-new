"""Increase cvs.template_id column from VARCHAR(50) to VARCHAR(100)

Revision ID: 009
Revises: 008
Create Date: 2026-06-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("cvs", "template_id", type_=sa.String(100), existing_type=sa.String(50))


def downgrade() -> None:
    op.alter_column("cvs", "template_id", type_=sa.String(50), existing_type=sa.String(100))
