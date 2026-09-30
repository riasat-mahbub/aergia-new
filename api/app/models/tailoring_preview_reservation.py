"""Database-backed leases for concurrent preview requests."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


TAILORING_PREVIEW_RESERVATION_ACTIVE = "active"
TAILORING_PREVIEW_RESERVATION_RELEASED = "released"
TAILORING_PREVIEW_RESERVATION_COMPLETED = "completed"
TAILORING_PREVIEW_RESERVATION_EXPIRED = "expired"


class TailoringPreviewReservation(Base):
    """A retry-stable candidate reservation; only active holds the lock."""

    __tablename__ = "tailoring_preview_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tailoring_sessions.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    candidate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TAILORING_PREVIEW_RESERVATION_ACTIVE,
        server_default=TAILORING_PREVIEW_RESERVATION_ACTIVE,
    )
    # This pointer is intentionally not a foreign key: the evaluation row owns
    # the reservation FK, avoiding a table-creation cycle.
    evaluation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session = relationship("TailoringSession", back_populates="preview_reservations")

    __table_args__ = (
        CheckConstraint(
            "state IN ('active', 'released', 'completed', 'expired')",
            name="ck_tailoring_preview_reservations_state",
        ),
        Index(
            "uq_tailoring_preview_reservations_session_request",
            "session_id",
            "request_id",
            unique=True,
        ),
        Index(
            "uq_tailoring_preview_reservations_one_active_session",
            "session_id",
            unique=True,
            sqlite_where=text("state = 'active'"),
            postgresql_where=text("state = 'active'"),
        ),
        Index("uq_tailoring_preview_reservations_evaluation", "evaluation_id", unique=True),
        Index("ix_tailoring_preview_reservations_expires_at", "expires_at"),
    )


__all__ = [
    "TAILORING_PREVIEW_RESERVATION_ACTIVE",
    "TAILORING_PREVIEW_RESERVATION_COMPLETED",
    "TAILORING_PREVIEW_RESERVATION_EXPIRED",
    "TAILORING_PREVIEW_RESERVATION_RELEASED",
    "TailoringPreviewReservation",
]
