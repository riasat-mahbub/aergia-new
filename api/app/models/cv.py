import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from app.db.session import Base


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customizations: Mapped[dict] = mapped_column(JSON, default=dict)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="cvs")
    tailoring_sessions = relationship("TailoringSession", back_populates="cv", cascade="all, delete-orphan")
