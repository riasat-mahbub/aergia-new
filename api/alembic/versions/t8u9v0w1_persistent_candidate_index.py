"""persist deterministic and semantic candidate-index sources

Revision ID: t8u9v0w1
Revises: s4t5u6v7
Create Date: 2026-09-24 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "t8u9v0w1"
down_revision: str | None = "s4t5u6v7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("library_entries", sa.Column("row_ids", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="7",
        )
    op.create_table(
        "candidate_index_states",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("deterministic_version", sa.String(length=128), nullable=False),
        sa.Column("backfilled_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "candidate_index_sources",
        sa.Column("source_id", sa.String(length=96), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("library_entry_id", sa.String(length=36), sa.ForeignKey("library_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_id", sa.String(length=128), nullable=False),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("identity", sa.JSON(), nullable=False),
        sa.Column("structured_facts", sa.JSON(), nullable=False),
        sa.Column("canonical_skills", sa.JSON(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidate_index_sources_user_id", "candidate_index_sources", ["user_id"])
    op.create_index("ix_candidate_index_user_entry", "candidate_index_sources", ["user_id", "library_entry_id"])
    op.create_index("ix_candidate_index_user_kind", "candidate_index_sources", ["user_id", "kind"])
    op.create_index("ix_candidate_index_entry_row_field", "candidate_index_sources", ["library_entry_id", "row_id", "field_path"], unique=True)
    op.create_table(
        "candidate_semantic_records",
        sa.Column("source_id", sa.String(length=96), sa.ForeignKey("candidate_index_sources.source_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("proposition_model", sa.String(length=128), nullable=False),
        sa.Column("proposition_model_revision", sa.String(length=128), nullable=False),
        sa.Column("extractor_version", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=128), nullable=False),
        sa.Column("semantic_result", sa.JSON(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidate_semantic_fingerprint", "candidate_semantic_records", ["source_fingerprint"])
    op.create_table(
        "candidate_index_terms",
        sa.Column("source_id", sa.String(length=96), sa.ForeignKey("candidate_index_sources.source_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("term", sa.String(length=160), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_candidate_index_user_term", "candidate_index_terms", ["user_id", "term"])


def downgrade() -> None:
    with op.batch_alter_table("tailoring_sessions", recreate="always") as batch:
        batch.alter_column(
            "protocol_version",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="5",
        )
    op.drop_index("ix_candidate_semantic_fingerprint", table_name="candidate_semantic_records")
    op.drop_table("candidate_semantic_records")
    op.drop_index("ix_candidate_index_user_term", table_name="candidate_index_terms")
    op.drop_table("candidate_index_terms")
    op.drop_table("candidate_index_states")
    op.drop_index("ix_candidate_index_entry_row_field", table_name="candidate_index_sources")
    op.drop_index("ix_candidate_index_user_kind", table_name="candidate_index_sources")
    op.drop_index("ix_candidate_index_user_entry", table_name="candidate_index_sources")
    op.drop_index("ix_candidate_index_sources_user_id", table_name="candidate_index_sources")
    op.drop_table("candidate_index_sources")
    op.drop_column("library_entries", "row_ids")
