"""Persistent deterministic and semantic candidate-index records."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CandidateIndexState(Base):
    """Records that legacy Library content has been backfilled into the index."""

    __tablename__ = "candidate_index_states"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    deterministic_version: Mapped[str] = mapped_column(String(128), nullable=False)
    backfilled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CandidateIndexSource(Base):
    """Always-current deterministic projection of one Library narrative."""

    __tablename__ = "candidate_index_sources"

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    library_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("library_entries.id", ondelete="CASCADE"), nullable=False
    )
    row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    identity: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    structured_facts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    canonical_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    semantic_record = relationship(
        "CandidateSemanticRecord", back_populates="source", cascade="all, delete-orphan",
        passive_deletes=True, uselist=False,
    )

    __table_args__ = (
        Index("ix_candidate_index_user_entry", "user_id", "library_entry_id"),
        Index("ix_candidate_index_user_kind", "user_id", "kind"),
        Index("ix_candidate_index_entry_row_field", "library_entry_id", "row_id", "field_path", unique=True),
    )


class CandidateSemanticRecord(Base):
    """Job-blind semantic extraction for exactly one current source fingerprint."""

    __tablename__ = "candidate_semantic_records"

    source_id: Mapped[str] = mapped_column(
        String(96), ForeignKey("candidate_index_sources.source_id", ondelete="CASCADE"), primary_key=True
    )
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    proposition_model: Mapped[str] = mapped_column(String(128), nullable=False)
    proposition_model_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    semantic_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    source = relationship("CandidateIndexSource", back_populates="semantic_record")

    __table_args__ = (Index("ix_candidate_semantic_fingerprint", "source_fingerprint"),)


class CandidateIndexTerm(Base):
    """Inverted whole-token lookup for deterministic candidate retrieval."""

    __tablename__ = "candidate_index_terms"

    source_id: Mapped[str] = mapped_column(
        String(96), ForeignKey("candidate_index_sources.source_id", ondelete="CASCADE"), primary_key=True
    )
    term: Mapped[str] = mapped_column(String(160), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (Index("ix_candidate_index_user_term", "user_id", "term"),)


__all__ = [
    "CandidateIndexSource",
    "CandidateIndexState",
    "CandidateIndexTerm",
    "CandidateSemanticRecord",
]
