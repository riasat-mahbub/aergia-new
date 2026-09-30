"""add protocol-v10 tailoring review, reservation, and quota storage

Revision ID: w1x2y3z4
Revises: v0w1x2y3
Create Date: 2026-09-30 00:00:00

The v10 tables retain immutable evaluation bindings and coordinate the
single-session, preview-lease, and replacement-allowance invariants.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "w1x2y3z4"
down_revision: str | None = "v0w1x2y3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _reconcile_blocking_sessions(connection: sa.Connection) -> None:
    """Keep the newest ready draft, otherwise the newest in-flight session."""
    connection.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY application_id
                           ORDER BY CASE WHEN status = 'draft_ready' THEN 0 ELSE 1 END,
                                    created_at DESC,
                                    id DESC
                       ) AS position
                FROM tailoring_sessions
                WHERE status IN ('created', 'exchanged', 'draft_ready')
            )
            UPDATE tailoring_sessions
               SET status = 'stale',
                   capability_hash = NULL,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id IN (SELECT id FROM ranked WHERE position > 1)
            """
        )
    )


def upgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            existing_server_default="9",
            server_default="10",
        )
        batch.add_column(sa.Column("source_cv_revision", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("target_guard_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("submission_result", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("owner_review_state", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("owner_cv_revision", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("owner_candidate_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("owner_render_basis_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("owner_evaluation_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("owner_pdf_sha256", sa.String(length=64), nullable=True))
        batch.create_check_constraint(
            "ck_tailoring_sessions_owner_review_state",
            "owner_review_state IS NULL OR owner_review_state IN "
            "('current', 'needs_reevaluation', 'unavailable')",
        )

    connection = op.get_bind()
    _reconcile_blocking_sessions(connection)

    # V10 exchange cannot resume with a v9 helper. Submitted historical drafts
    # remain reviewable by the owner; only in-flight capabilities are revoked.
    connection.execute(
        sa.text(
            "UPDATE tailoring_sessions "
            "SET status = 'stale', capability_hash = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE protocol_version <= 9 AND status IN ('created', 'exchanged')"
        )
    )

    op.create_index(
        "uq_tailoring_sessions_one_blocking_per_application",
        "tailoring_sessions",
        ["application_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('created', 'exchanged', 'draft_ready')"),
        postgresql_where=sa.text("status IN ('created', 'exchanged', 'draft_ready')"),
    )

    op.add_column(
        "cvs",
        sa.Column("quota_counted", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    connection.execute(
        sa.text(
            """
            UPDATE users
               SET application_count = (
                       SELECT COUNT(*) FROM applications
                        WHERE applications.user_id = users.id
                   ),
                   cv_count = (
                       SELECT COUNT(*) FROM cvs
                        WHERE cvs.user_id = users.id
                          AND cvs.is_active = 1
                          AND cvs.quota_counted = 1
                   )
            """
        )
    )

    op.create_table(
        "tailoring_preview_reservations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_hash", sa.String(length=64), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("evaluation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('active', 'released', 'completed', 'expired')",
            name="ck_tailoring_preview_reservations_state",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["tailoring_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_tailoring_preview_reservations_session_request",
        "tailoring_preview_reservations",
        ["session_id", "request_id"],
        unique=True,
    )
    op.create_index(
        "uq_tailoring_preview_reservations_one_active_session",
        "tailoring_preview_reservations",
        ["session_id"],
        unique=True,
        sqlite_where=sa.text("state = 'active'"),
        postgresql_where=sa.text("state = 'active'"),
    )
    op.create_index(
        "uq_tailoring_preview_reservations_evaluation",
        "tailoring_preview_reservations",
        ["evaluation_id"],
        unique=True,
    )
    op.create_index(
        "ix_tailoring_preview_reservations_expires_at",
        "tailoring_preview_reservations",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "tailoring_evaluations",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("reservation_id", sa.String(length=36), nullable=True),
        sa.Column("candidate_hash", sa.String(length=64), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("scanner_result", sa.JSON(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("render_warnings", sa.JSON(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('agent_preview', 'owner_review')", name="ck_tailoring_evaluations_kind"),
        sa.ForeignKeyConstraint(["reservation_id"], ["tailoring_preview_reservations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["tailoring_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tailoring_evaluations_session_created",
        "tailoring_evaluations",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_tailoring_evaluations_reservation",
        "tailoring_evaluations",
        ["reservation_id"],
        unique=True,
    )

    op.create_table(
        "tailoring_replacement_reservations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("source_cv_id", sa.String(length=36), nullable=False),
        sa.Column("draft_cv_id", sa.String(length=36), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('pending', 'transferred', 'released')",
            name="ck_tailoring_replacement_reservations_state",
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_cv_id"], ["cvs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_cv_id"], ["cvs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_tailoring_replacement_reservations_one_pending_application",
        "tailoring_replacement_reservations",
        ["application_id"],
        unique=True,
        sqlite_where=sa.text("state = 'pending'"),
        postgresql_where=sa.text("state = 'pending'"),
    )
    op.create_index(
        "uq_tailoring_replacement_reservations_one_pending_source_cv",
        "tailoring_replacement_reservations",
        ["source_cv_id"],
        unique=True,
        sqlite_where=sa.text("state = 'pending'"),
        postgresql_where=sa.text("state = 'pending'"),
    )
    op.create_index(
        "ix_tailoring_replacement_reservations_draft_cv_id",
        "tailoring_replacement_reservations",
        ["draft_cv_id"],
        unique=False,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Protocol-v10 storage contains durable evaluation and quota history; "
        "restore a compatible database backup instead of downgrading."
    )
