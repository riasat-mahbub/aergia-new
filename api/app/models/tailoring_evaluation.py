"""Immutable canonical evaluations produced during tailoring and owner review."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


TAILORING_EVALUATION_AGENT_PREVIEW = "agent_preview"
TAILORING_EVALUATION_OWNER_REVIEW = "owner_review"


class TailoringEvaluationRecord(Base):
    """A selectable immutable evaluation and the exact PDF it assessed."""

    __tablename__ = "tailoring_evaluations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tailoring_sessions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # Null for owner evaluations. A unique identity lets retries find the one
    # preview evaluation created for a reservation.
    reservation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tailoring_preview_reservations.id", ondelete="SET NULL"), nullable=True
    )
    candidate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate: Mapped[dict] = mapped_column(JSON, nullable=False)
    scanner_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=False)
    render_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Kept private to owner/agent flows; response DTOs expose only the digest
    # and the authorized PDF download.
    pdf_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session = relationship("TailoringSession", back_populates="evaluations")

    __table_args__ = (
        CheckConstraint("kind IN ('agent_preview', 'owner_review')", name="ck_tailoring_evaluations_kind"),
        Index("ix_tailoring_evaluations_session_created", "session_id", "created_at"),
        Index("uq_tailoring_evaluations_reservation", "reservation_id", unique=True),
    )


__all__ = [
    "TAILORING_EVALUATION_AGENT_PREVIEW",
    "TAILORING_EVALUATION_OWNER_REVIEW",
    "TailoringEvaluationRecord",
]
