"""add protocol-v2 tailoring draft state and optional source CV

Revision ID: l7m8n9o0p1
Revises: k6l7m8n9o0p1
Create Date: 2026-09-11 00:00:00.000000

Old patch sessions cannot safely be replayed under the whole-document
protocol, so they are expired at the cutover. Existing CV data remains
untouched; only session metadata changes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "l7m8n9o0p1"
down_revision: str | None = "k6l7m8n9o0p1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column("cv_id", existing_type=sa.String(length=36), nullable=True)
        batch.add_column(sa.Column("draft_cv_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("context_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_tailoring_sessions_draft_cv_id_cvs",
            "cvs",
            ["draft_cv_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_tailoring_sessions_draft_cv_id", ["draft_cv_id"], unique=False)

    # A v1 capability must never be accepted by the v2 service. Keeping the
    # old row is useful for audit/status history, but it is no longer live.
    op.execute(
        sa.text(
            "UPDATE tailoring_sessions "
            "SET status = 'expired', capability_hash = NULL "
            "WHERE status IN ('created', 'exchanged', 'submitted')"
        )
    )


def downgrade() -> None:
    # Downgrading would make optional source rows impossible to represent.
    # Leave the v2 session rows intact; the previous runtime cannot safely
    # replay them and a backup is the correct rollback mechanism.
    pass
