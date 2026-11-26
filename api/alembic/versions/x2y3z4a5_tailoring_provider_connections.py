"""Add optional tailoring provider authorization.

Revision ID: x2y3z4a5
Revises: w1x2y3z4
"""

import sqlalchemy as sa

from alembic import op

revision = "x2y3z4a5"
down_revision = "w1x2y3z4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tailoring_provider_connections",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(12), primary_key=True),
        sa.Column("credentials", sa.Text()),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("probe_id", sa.String(36)),
        sa.Column("probe_document", sa.String(128)),
        sa.Column("probe_expires_at", sa.DateTime()),
        sa.Column("verified_at", sa.DateTime()),
    )
    op.create_table(
        "tailoring_oauth_attempts",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(12), nullable=False),
        sa.Column("proof", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tailoring_oauth_attempts_user_id", "tailoring_oauth_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_tailoring_oauth_attempts_user_id", table_name="tailoring_oauth_attempts")
    op.drop_table("tailoring_oauth_attempts")
    op.drop_table("tailoring_provider_connections")
