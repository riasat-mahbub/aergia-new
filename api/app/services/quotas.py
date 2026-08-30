"""Atomic per-account creation quotas."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import or_, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abuse import log_abuse_event
from app.models.user import AccountTier, User

MAX_APPLICATIONS_PER_ACCOUNT = 3
MAX_CVS_PER_ACCOUNT = 3


class QuotaResource(StrEnum):
    APPLICATION = "application"
    CV = "cv"


class QuotaExceededError(ValueError):
    """Raised when an account has no remaining creation slot."""

    def __init__(self, resource: QuotaResource):
        self.resource = resource
        self.limit = (
            MAX_APPLICATIONS_PER_ACCOUNT
            if resource is QuotaResource.APPLICATION
            else MAX_CVS_PER_ACCOUNT
        )
        super().__init__(f"{resource.value} quota exceeded")


class QuotaService:
    """Reserve and release quota counters in the caller's transaction.

    SQLite serializes the write transaction opened by ``BEGIN IMMEDIATE``.
    The conditional counter update and the resource insert therefore commit
    or roll back together, so concurrent requests cannot reserve the same
    final slot.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reserve(self, user_id: str, resource: QuotaResource) -> None:
        await self._begin_write_transaction()
        if resource is QuotaResource.APPLICATION:
            statement = (
                update(User)
                .where(
                    User.id == user_id,
                    or_(
                        User.account_tier == AccountTier.PREMIUM.value,
                        User.application_count < MAX_APPLICATIONS_PER_ACCOUNT,
                    ),
                )
                .values(application_count=User.application_count + 1)
            )
        else:
            statement = (
                update(User)
                .where(
                    User.id == user_id,
                    or_(
                        User.account_tier == AccountTier.PREMIUM.value,
                        User.cv_count < MAX_CVS_PER_ACCOUNT,
                    ),
                )
                .values(cv_count=User.cv_count + 1)
            )

        result = await self.db.execute(statement)
        if result.rowcount != 1:
            event = (
                "application_quota_exceeded"
                if resource is QuotaResource.APPLICATION
                else "cv_quota_exceeded"
            )
            error = QuotaExceededError(resource)
            log_abuse_event(event, limit=error.limit)
            raise error

    async def release(self, user_id: str, resource: QuotaResource) -> None:
        if resource is QuotaResource.APPLICATION:
            statement = (
                update(User)
                .where(User.id == user_id, User.application_count > 0)
                .values(application_count=User.application_count - 1)
            )
        else:
            statement = update(User).where(User.id == user_id, User.cv_count > 0).values(cv_count=User.cv_count - 1)
        await self.db.execute(statement)

    async def _begin_write_transaction(self) -> None:
        """Acquire SQLite's write lock before reserving a slot.

        Authentication and template lookups can already have opened a read
        transaction on this session. Rolling that read transaction back is
        safe for the creation paths because no resource mutation has happened
        before reservation; it also avoids SQLite's read-to-write snapshot
        upgrade race under concurrent requests.
        """

        if self.db.in_transaction():
            await self.db.rollback()
        bind = self.db.get_bind()
        if bind.dialect.name == "sqlite":
            await self.db.execute(text("BEGIN IMMEDIATE"))


__all__ = [
    "MAX_APPLICATIONS_PER_ACCOUNT",
    "MAX_CVS_PER_ACCOUNT",
    "QuotaExceededError",
    "QuotaResource",
    "QuotaService",
]
