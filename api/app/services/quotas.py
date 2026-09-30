"""Atomic per-account creation quotas and replacement allowances."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.abuse import log_abuse_event
from app.models.application import Application
from app.models.cv import CV
from app.models.tailoring_replacement_reservation import (
    TAILORING_REPLACEMENT_PENDING,
    TAILORING_REPLACEMENT_RELEASED,
    TAILORING_REPLACEMENT_TRANSFERRED,
    TailoringReplacementReservation,
)
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


class ReplacementReservationError(ValueError):
    """Base error for replacement-allowance lifecycle conflicts."""


class ReplacementSourceNotEligibleError(ReplacementReservationError):
    """The source is not the active, solely linked, counted CV for the app."""


class ReplacementAlreadyPendingError(ReplacementReservationError):
    """An application already has an allowance draft awaiting review."""


class ReplacementReservationConflictError(ReplacementReservationError):
    """A reservation was released, transferred, or invalidated concurrently."""


class QuotaService:
    """Reserve and release quota counters in the caller's transaction.

    Normal quota changes are conditional SQL updates. The database serializes
    those short writes, while the service leaves the caller's transaction and
    any already-flushed work intact. Replacement allowances are represented by
    a uniquely indexed pending reservation and do not change the normal CV
    counter until transfer.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reserve(self, user_id: str, resource: QuotaResource) -> None:
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
            statement = update(User).where(
                User.id == user_id,
                User.cv_count > 0,
            ).values(cv_count=User.cv_count - 1)
        await self.db.execute(statement)

    async def ensure_write_transaction(self) -> None:
        """Start SQLite's outer transaction without discarding caller work.

        The sqlite driver uses legacy transaction behavior and does not start
        a database transaction for SELECTs. Starting the outer transaction
        before a savepoint prevents SQLite from treating that savepoint as the
        transaction itself and committing it on RELEASE. If the caller already
        made a database write, its physical transaction remains untouched.
        """

        if self.db.get_bind().dialect.name != "sqlite":
            return
        connection = await self.db.connection()
        driver_connection = connection.sync_connection.connection.driver_connection
        if not driver_connection.in_transaction:
            await self.db.execute(text("BEGIN IMMEDIATE"))

    async def reserve_replacement(
        self,
        user_id: str,
        application_id: str,
        source_cv_id: str,
    ) -> TailoringReplacementReservation:
        """Reserve the one pending uncounted draft for an eligible source.

        This changes no normal quota counter. The partial unique indexes are
        the final arbiter for simultaneous requests on different sessions.
        An insert is isolated by a savepoint so an expected uniqueness race
        does not poison the route-owned transaction.
        """

        reservation = TailoringReplacementReservation(
            application_id=application_id,
            source_cv_id=source_cv_id,
            state=TAILORING_REPLACEMENT_PENDING,
        )
        pending_id = await self.db.scalar(
            select(TailoringReplacementReservation.id).where(
                TailoringReplacementReservation.application_id == application_id,
                TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
            ).limit(1)
        )
        if pending_id is not None:
            raise ReplacementAlreadyPendingError(
                "A replacement draft is already pending for this application; discard it before creating another."
            )
        try:
            await self.ensure_write_transaction()
            async with self.db.begin_nested():
                # Conditional no-op writes take short row locks on PostgreSQL
                # and the SQLite write lock before the eligibility recheck.
                # Application relinking and CV deletion use these same rows,
                # so they cannot invalidate the checked source before insert.
                app_lock = await self.db.execute(
                    update(Application)
                    .where(
                        Application.id == application_id,
                        Application.user_id == user_id,
                        Application.cv_id == source_cv_id,
                    )
                    .values(updated_at=Application.updated_at)
                )
                if app_lock.rowcount != 1:
                    raise ReplacementSourceNotEligibleError(
                        "The current CV cannot use a replacement allowance."
                    )

                cv_lock = await self.db.execute(
                    update(CV)
                    .where(
                        CV.id == source_cv_id,
                        CV.user_id == user_id,
                        CV.application_id == application_id,
                        CV.is_active.is_(True),
                        CV.quota_counted.is_(True),
                    )
                    .values(updated_at=CV.updated_at)
                )
                if cv_lock.rowcount != 1:
                    raise ReplacementSourceNotEligibleError(
                        "The current CV cannot use a replacement allowance."
                    )

                other_link = await self.db.scalar(
                    select(Application.id)
                    .where(Application.cv_id == source_cv_id, Application.id != application_id)
                    .limit(1)
                    .execution_options(populate_existing=True)
                )
                if other_link is not None:
                    raise ReplacementSourceNotEligibleError(
                        "The current CV cannot use a replacement allowance."
                    )

                pending_id = await self.db.scalar(
                    select(TailoringReplacementReservation.id).where(
                        TailoringReplacementReservation.application_id == application_id,
                        TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                    ).limit(1)
                )
                if pending_id is not None:
                    raise ReplacementAlreadyPendingError(
                        "A replacement draft is already pending for this application; discard it before creating another."
                    )
                self.db.add(reservation)
                await self.db.flush()
        except IntegrityError as exc:
            # Both unique partial indexes report an IntegrityError on SQLite
            # and PostgreSQL. Re-check the authoritative row after rolling
            # back only the savepoint, then report the app-level conflict.
            pending_id = await self.db.scalar(
                select(TailoringReplacementReservation.id).where(
                    TailoringReplacementReservation.application_id == application_id,
                    TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                ).limit(1)
            )
            if pending_id is not None:
                raise ReplacementAlreadyPendingError(
                    "A replacement draft is already pending for this application; discard it before creating another."
                ) from exc
            if not await self._replacement_source_is_eligible(user_id, application_id, source_cv_id):
                raise ReplacementSourceNotEligibleError(
                    "The current CV cannot use a replacement allowance."
                ) from exc
            raise
        return reservation

    async def release_replacement(
        self,
        user_id: str,
        application_id: str,
        *,
        source_cv_id: str | None = None,
        draft_cv_id: str | None = None,
        retire_draft: bool = True,
    ) -> bool:
        """Idempotently release an allowance and optionally retire its draft.

        Releasing an allowance never changes ``User.cv_count``. The draft is
        uncounted until transfer, so it must not free a normal slot when
        rejected, discarded, or cleaned up with its application/source.
        """

        conditions = [
            TailoringReplacementReservation.application_id == application_id,
            TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
            Application.id == application_id,
            Application.user_id == user_id,
        ]
        if source_cv_id is not None:
            conditions.append(TailoringReplacementReservation.source_cv_id == source_cv_id)
        if draft_cv_id is not None:
            conditions.append(TailoringReplacementReservation.draft_cv_id == draft_cv_id)
        reservation = await self.db.scalar(
            select(TailoringReplacementReservation)
            .join(Application, Application.id == TailoringReplacementReservation.application_id)
            .where(*conditions)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if reservation is None:
            return False

        now = datetime.now(timezone.utc)
        await self.ensure_write_transaction()
        async with self.db.begin_nested():
            result = await self.db.execute(
                update(TailoringReplacementReservation)
                .where(
                    TailoringReplacementReservation.id == reservation.id,
                    TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                )
                .values(state=TAILORING_REPLACEMENT_RELEASED, updated_at=now)
            )
            if result.rowcount != 1:
                return False

            if retire_draft and reservation.draft_cv_id is not None:
                await self.db.execute(
                    update(CV)
                    .where(
                        CV.id == reservation.draft_cv_id,
                        CV.user_id == user_id,
                        CV.is_active.is_(True),
                        CV.quota_counted.is_(False),
                    )
                    .values(
                        is_active=False,
                        application_id=None,
                        updated_at=now,
                    )
                )
        return True

    async def transfer_replacement(
        self,
        user_id: str,
        application_id: str,
        source_cv_id: str,
        draft_cv_id: str,
    ) -> TailoringReplacementReservation:
        """Transfer a pending allowance from the old source to its draft.

        The method binds ``Application.cv_id`` to the reviewed draft in the
        same savepoint as the provenance transfer. It also accepts a caller
        that already made that binding in its outer transaction. The normal
        counter is unchanged because one counted CV is replaced by one counted
        CV.
        """

        reservation = await self.db.scalar(
            select(TailoringReplacementReservation)
            .join(Application, Application.id == TailoringReplacementReservation.application_id)
            .where(
                TailoringReplacementReservation.application_id == application_id,
                TailoringReplacementReservation.source_cv_id == source_cv_id,
                TailoringReplacementReservation.draft_cv_id == draft_cv_id,
                TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                Application.user_id == user_id,
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        application = await self.db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user_id,
            ).execution_options(populate_existing=True)
        )
        source = await self.db.scalar(
            select(CV)
            .where(CV.id == source_cv_id, CV.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        draft = await self.db.scalar(
            select(CV)
            .where(CV.id == draft_cv_id, CV.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        if (
            reservation is None
            or application is None
            or application.cv_id not in {source_cv_id, draft_cv_id}
            or source is None
            or not source.is_active
            or not source.quota_counted
            or source.application_id not in {None, application_id}
            or draft is None
            or not draft.is_active
            or draft.quota_counted
            or draft.application_id != application_id
        ):
            raise ReplacementReservationConflictError(
                "The replacement reservation is no longer eligible for transfer."
            )

        other_link = await self.db.scalar(
            select(Application.id)
            .where(Application.cv_id == source_cv_id, Application.id != application_id)
            .limit(1)
        )
        if other_link is not None:
            raise ReplacementReservationConflictError(
                "The source CV is linked to another application."
            )

        now = datetime.now(timezone.utc)
        await self.ensure_write_transaction()
        async with self.db.begin_nested():
            app_lock = await self.db.execute(
                update(Application)
                .where(
                    Application.id == application_id,
                    Application.user_id == user_id,
                    Application.cv_id.in_([source_cv_id, draft_cv_id]),
                )
                .values(cv_id=draft_cv_id, updated_at=Application.updated_at)
            )
            if app_lock.rowcount != 1:
                raise ReplacementReservationConflictError(
                    "The application changed before the replacement could be accepted."
                )

            reservation_result = await self.db.execute(
                update(TailoringReplacementReservation)
                .where(
                    TailoringReplacementReservation.id == reservation.id,
                    TailoringReplacementReservation.state == TAILORING_REPLACEMENT_PENDING,
                )
                .values(state=TAILORING_REPLACEMENT_TRANSFERRED, updated_at=now)
            )
            if reservation_result.rowcount != 1:
                raise ReplacementReservationConflictError(
                    "The replacement reservation was already released or transferred."
                )

            source_result = await self.db.execute(
                update(CV)
                .where(
                    CV.id == source_cv_id,
                    CV.user_id == user_id,
                    CV.is_active.is_(True),
                    CV.quota_counted.is_(True),
                    or_(
                        CV.application_id.is_(None),
                        CV.application_id == application_id,
                    ),
                    ~select(Application.id)
                    .where(Application.cv_id == source_cv_id, Application.id != application_id)
                    .exists(),
                )
                .values(
                    is_active=False,
                    quota_counted=False,
                    application_id=None,
                    updated_at=now,
                )
            )
            draft_result = await self.db.execute(
                update(CV)
                .where(
                    CV.id == draft_cv_id,
                    CV.user_id == user_id,
                    CV.is_active.is_(True),
                    CV.quota_counted.is_(False),
                    CV.application_id == application_id,
                )
                .values(quota_counted=True, updated_at=now)
            )
            if source_result.rowcount != 1 or draft_result.rowcount != 1:
                raise ReplacementReservationConflictError(
                    "The replacement CV changed before its quota could be transferred."
                )
            if application.cv_id != draft_cv_id:
                application.cv_id = draft_cv_id
            application.cv = draft
            await self.db.flush()
        return reservation

    async def _replacement_source_is_eligible(
        self,
        user_id: str,
        application_id: str,
        source_cv_id: str,
    ) -> bool:
        source = await self.db.scalar(
            select(CV)
            .join(Application, Application.cv_id == CV.id)
            .where(
                Application.id == application_id,
                Application.user_id == user_id,
                CV.id == source_cv_id,
                CV.user_id == user_id,
                CV.application_id == application_id,
                CV.is_active.is_(True),
                CV.quota_counted.is_(True),
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if source is None:
            return False
        other_link = await self.db.scalar(
            select(Application.id)
            .where(Application.cv_id == source_cv_id, Application.id != application_id)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return other_link is None


__all__ = [
    "MAX_APPLICATIONS_PER_ACCOUNT",
    "MAX_CVS_PER_ACCOUNT",
    "QuotaExceededError",
    "QuotaResource",
    "QuotaService",
    "ReplacementAlreadyPendingError",
    "ReplacementReservationConflictError",
    "ReplacementReservationError",
    "ReplacementSourceNotEligibleError",
]
