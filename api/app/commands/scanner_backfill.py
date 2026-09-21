"""Populate scanner results alongside, but independently from, legacy analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncIterator, Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.scanner.freshness import configured_extractor_version, scanner_result_freshness
from app.services.application import ApplicationService


SessionFactory = Callable[[], AsyncSession]


@dataclass(slots=True)
class BackfillReport:
    scanned: int = 0
    skipped: int = 0
    failed: int = 0
    unscannable: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)
    unscannable_applications: list[dict[str, str]] = field(default_factory=list)
    stale_results: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def scanner_result_is_current(
    result: object,
    job_description: str,
    cv: object,
    *,
    extractor_version: str | None = None,
) -> bool:
    """Check whether a stored scanner-v1 result describes these JD/CV inputs."""
    return scanner_result_freshness(
        result,
        job_description,
        cv,
        extractor_version=extractor_version,
    )["current"]


def _configured_extractor_version() -> str | None:
    """Read the configured model identity without loading its inference model."""
    return configured_extractor_version()


async def _application_ids(
    session_factory: SessionFactory,
    *,
    batch_size: int,
    limit: int | None,
    application_id: str | None,
    report: BackfillReport,
) -> AsyncIterator[list[str]]:
    if application_id is not None:
        async with session_factory() as session:
            found = await session.scalar(select(Application.id).where(Application.id == application_id))
        if found is None:
            report.unscannable += 1
            report.unscannable_applications.append(
                {"application_id": application_id, "reason": "application_not_found"}
            )
            return
        yield [found]
        return

    last_id: str | None = None
    selected_count = 0
    while limit is None or selected_count < limit:
        query_limit = batch_size if limit is None else min(batch_size, limit - selected_count)
        async with session_factory() as session:
            statement = select(Application.id).order_by(Application.id).limit(query_limit)
            if last_id is not None:
                statement = statement.where(Application.id > last_id)
            result = await session.scalars(statement)
            batch = list(result.all())
        if not batch:
            return
        yield batch
        selected_count += len(batch)
        last_id = batch[-1]


async def _process_application(
    session_factory: SessionFactory,
    application_id: str,
    report: BackfillReport,
    *,
    dry_run: bool,
    force: bool,
    only_missing: bool,
    extractor_version: str | None,
) -> None:
    async with session_factory() as session:
        try:
            application = await session.scalar(
                select(Application)
                .options(selectinload(Application.cv))
                .where(Application.id == application_id)
            )
            if application is None:
                report.unscannable += 1
                report.unscannable_applications.append(
                    {"application_id": application_id, "reason": "application_not_found"}
                )
                return

            cv = application.cv
            if not application.job_description or not application.job_description.strip():
                reason = "job_description_missing"
            elif (
                application.cv_id is None
                or cv is None
                or not cv.is_active
                or cv.user_id != application.user_id
            ):
                reason = "linked_cv_unavailable"
            else:
                reason = ""
            if reason:
                report.unscannable += 1
                report.unscannable_applications.append({"application_id": application_id, "reason": reason})
                return

            existing_result = application.scanner_result
            if existing_result is not None:
                freshness = scanner_result_freshness(
                    existing_result,
                    application.job_description,
                    cv,
                    extractor_version=extractor_version,
                )
                if not freshness["current"]:
                    report.stale_results.append(
                        {
                            "application_id": application.id,
                            "reasons": freshness["reasons"],
                        }
                    )
                if not force and (only_missing or freshness["current"]):
                    report.skipped += 1
                    return

            await ApplicationService(session).scan_application(application.id, application.user_id)
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
            report.scanned += 1
        except Exception as exc:  # noqa: BLE001 - isolate failures to one application
            await session.rollback()
            report.failed += 1
            report.failures.append(
                {"application_id": application_id, "error_type": type(exc).__name__}
            )


async def run_backfill(
    *,
    session_factory: SessionFactory,
    batch_size: int = 100,
    limit: int | None = None,
    application_id: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    only_missing: bool = False,
) -> BackfillReport:
    """Scan eligible applications, committing each successful result separately."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")
    if force and only_missing:
        raise ValueError("--force and --only-missing cannot be combined")

    report = BackfillReport()
    extractor_version = _configured_extractor_version()
    async for batch in _application_ids(
        session_factory,
        batch_size=batch_size,
        limit=limit,
        application_id=application_id,
        report=report,
    ):
        for current_id in batch:
            await _process_application(
                session_factory,
                current_id,
                report,
                dry_run=dry_run,
                force=force,
                only_missing=only_missing,
                extractor_version=extractor_version,
            )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scanner-backfill",
        description="Populate current scanner results without rewriting legacy analysis.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run scans and roll back all result writes.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Applications fetched per database page (does not limit the total run).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of application rows to consider in this invocation.",
    )
    parser.add_argument("--application-id", help="Limit the run to one application ID.")
    parser.add_argument("--force", action="store_true", help="Rescan every eligible application, including current results.")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip every application that already has a scanner result, even if its inputs are stale.",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    from app.db.session import async_session, engine
    from app.services.renderer._pdf_runtime import close_browser

    try:
        report = await run_backfill(
            session_factory=async_session,
            batch_size=args.batch_size,
            limit=args.limit,
            application_id=args.application_id,
            dry_run=args.dry_run,
            force=args.force,
            only_missing=args.only_missing,
        )
        print(json.dumps({"dry_run": args.dry_run, **report.as_dict()}, indent=2, sort_keys=True))
        return 1 if report.failed else 0
    finally:
        await close_browser()
        await engine.dispose()


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.force and args.only_missing:
        parser.error("--force and --only-missing cannot be combined")

    if sys.platform.startswith("linux"):
        try:
            import uvloop
        except ImportError as exc:  # pragma: no cover - project dependency guard
            raise RuntimeError("Linux scanner backfill requires uvloop for aiosqlite worker wakeups") from exc
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
