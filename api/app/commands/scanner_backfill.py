"""Populate scanner results alongside, but independently from, legacy analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.scanner.pdf_recovery import PDF_ANALYSIS_VERSION
from app.scanner.quality import QUALITY_VERSION
from app.scanner.scoring import LEXICAL_SCORE_VERSION, PDF_SCORE_VERSION, SEMANTIC_SCORE_VERSION
from app.scanner.service import LEXICAL_VERSION, MATCHER_VERSION, fingerprint_scan_inputs
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

    if not isinstance(result, Mapping) or result.get("schema_version") != "scanner-v1":
        return False
    raw_fingerprints = result.get("input_fingerprints")
    raw_versions = result.get("versions")
    if not isinstance(raw_fingerprints, Mapping) or not isinstance(raw_versions, Mapping):
        return False
    try:
        current = fingerprint_scan_inputs(job_description, cv)
    except (TypeError, ValueError):
        return False
    inputs_match = (
        raw_fingerprints.get("job_description_sha256") == current.job_description_sha256
        and raw_fingerprints.get("cv_content_sha256") == current.cv_content_sha256
    )
    expected_versions = {
        "matcher_version": MATCHER_VERSION,
        "lexical_version": LEXICAL_VERSION,
        "quality_version": QUALITY_VERSION,
        "pdf_analysis_version": PDF_ANALYSIS_VERSION,
        "semantic_score_version": SEMANTIC_SCORE_VERSION,
        "lexical_score_version": LEXICAL_SCORE_VERSION,
        "pdf_score_version": PDF_SCORE_VERSION,
    }
    if extractor_version is not None:
        expected_versions["extractor_version"] = extractor_version
    versions_match = all(raw_versions.get(name) == version for name, version in expected_versions.items())
    return inputs_match and versions_match


def _configured_extractor_version() -> str | None:
    """Read the configured model identity without loading its inference model."""

    from app.services.requirement_extractor import get_requirement_extractor

    provider = get_requirement_extractor()
    model_name = getattr(provider, "model_name", None)
    if not isinstance(model_name, str):
        return None
    revision = getattr(provider, "revision", "default")
    return f"{model_name}@{revision}"


async def _application_ids(
    session_factory: SessionFactory,
    *,
    batch_size: int,
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
    while True:
        async with session_factory() as session:
            statement = select(Application.id).order_by(Application.id).limit(batch_size)
            if last_id is not None:
                statement = statement.where(Application.id > last_id)
            result = await session.scalars(statement)
            batch = list(result.all())
        if not batch:
            return
        yield batch
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
            if existing_result is not None and not force:
                if only_missing or scanner_result_is_current(
                    existing_result,
                    application.job_description,
                    cv,
                    extractor_version=extractor_version,
                ):
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
    application_id: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    only_missing: bool = False,
) -> BackfillReport:
    """Scan eligible applications, committing each successful result separately."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if force and only_missing:
        raise ValueError("--force and --only-missing cannot be combined")

    report = BackfillReport()
    extractor_version = None if force or only_missing else _configured_extractor_version()
    async for batch in _application_ids(
        session_factory,
        batch_size=batch_size,
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
    parser.add_argument("--batch-size", type=int, default=100, help="Applications selected per database batch.")
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
