import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    CASCADE_ALL = "all, delete-orphan"

    applications = relationship("Application", back_populates="user", cascade=CASCADE_ALL)
    cvs = relationship("CV", back_populates="user", cascade=CASCADE_ALL)
    libraries = relationship("Library", back_populates="user", cascade=CASCADE_ALL)
    auth_sessions = relationship("AuthSession", back_populates="user", cascade=CASCADE_ALL)
