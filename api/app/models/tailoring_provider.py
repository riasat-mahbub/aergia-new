"""Durable OAuth state for optional subscription-backed tailoring."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TailoringProviderConnection(Base):
    __tablename__ = "tailoring_provider_connections"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(12), primary_key=True)
    credentials: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(320))
    probe_id: Mapped[str | None] = mapped_column(String(36))
    probe_document: Mapped[str | None] = mapped_column(String(128))
    probe_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)


class TailoringOAuthAttempt(Base):
    __tablename__ = "tailoring_oauth_attempts"

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(12))
    proof: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
