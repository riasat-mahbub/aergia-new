"""Short-lived capabilities for local CV tailoring sessions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TailoringSession(Base):
    """One narrowly scoped local-agent tailoring task.

    The exchange code and capability are never persisted in plaintext. A
    session is intentionally tied to the exact application/CV pair selected
    by the authenticated browser request.
    """

    __tablename__ = "tailoring_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cv_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    capability_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="created", server_default="created")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exchanged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Snapshot identity captured when the one-time code is created. Legacy
    # Phase 1 rows may be null; the widened protocol refuses to submit them so
    # they cannot bypass stale-write protection.
    base_cv_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_cv_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_requirements_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_profile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Maps Library entry IDs to the content digest seen by the agent. Keeping
    # hashes rather than source content prevents the session row becoming a
    # database synchronization mechanism while still making evidence scopes
    # replay-safe.
    library_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reported_gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    provenance: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    # A sanitized copy of the successful submission result for the browser's
    # status poll. It never contains the exchange code or capability.
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="tailoring_sessions")
    application = relationship("Application", back_populates="tailoring_sessions")
    cv = relationship("CV", back_populates="tailoring_sessions")

    __table_args__ = (
        Index("ix_tailoring_sessions_user_status", "user_id", "status"),
        Index("ix_tailoring_sessions_expires_at", "expires_at"),
    )


__all__ = ["TailoringSession"]
