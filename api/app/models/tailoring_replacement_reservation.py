"""Per-application quota allowance reservations for replacement drafts."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


TAILORING_REPLACEMENT_PENDING = "pending"
TAILORING_REPLACEMENT_TRANSFERRED = "transferred"
TAILORING_REPLACEMENT_RELEASED = "released"


class TailoringReplacementReservation(Base):
    """A quota allowance tied to one application and its current source CV."""

    __tablename__ = "tailoring_replacement_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    source_cv_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False
    )
    draft_cv_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TAILORING_REPLACEMENT_PENDING,
        server_default=TAILORING_REPLACEMENT_PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'transferred', 'released')",
            name="ck_tailoring_replacement_reservations_state",
        ),
        Index(
            "uq_tailoring_replacement_reservations_one_pending_application",
            "application_id",
            unique=True,
            sqlite_where=text("state = 'pending'"),
            postgresql_where=text("state = 'pending'"),
        ),
        Index(
            "uq_tailoring_replacement_reservations_one_pending_source_cv",
            "source_cv_id",
            unique=True,
            sqlite_where=text("state = 'pending'"),
            postgresql_where=text("state = 'pending'"),
        ),
        Index("ix_tailoring_replacement_reservations_draft_cv_id", "draft_cv_id"),
    )


__all__ = [
    "TAILORING_REPLACEMENT_PENDING",
    "TAILORING_REPLACEMENT_RELEASED",
    "TAILORING_REPLACEMENT_TRANSFERRED",
    "TailoringReplacementReservation",
]
