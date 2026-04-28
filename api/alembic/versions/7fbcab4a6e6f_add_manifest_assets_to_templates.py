"""add_manifest_assets_to_templates

Revision ID: 7fbcab4a6e6f
Revises: 009
Create Date: 2026-06-27 02:17:19.695582

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7fbcab4a6e6f'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('templates', sa.Column('manifest', postgresql.JSONB, nullable=True))
    op.add_column('templates', sa.Column('assets', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('templates', 'manifest')
    op.drop_column('templates', 'assets')
