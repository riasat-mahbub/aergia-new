"""Summarize persisted scanner results without rerunning scans."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.scanner.audit import build_scanner_audit, format_scanner_audit
from app.scanner.freshness import configured_extractor_version, scanner_result_freshness


async def collect_scanner_audit(session_factory: Callable[[], AsyncSession]) -> dict[str, object]:
    """Read all applications and aggregate only results current for their inputs."""

    async with session_factory() as session:
        result = await session.scalars(
            select(Application)
            .options(selectinload(Application.cv))
            .order_by(Application.id)
        )
        applications = list(result.all())

    extractor_version = configured_extractor_version()
    records = []
    for application in applications:
        records.append(
            {
                "application_id": application.id,
                "scanner_result": application.scanner_result,
                "freshness": scanner_result_freshness(
                    application.scanner_result,
                    application.job_description,
                    application.cv,
                    extractor_version=extractor_version,
                ),
            }
        )
    return build_scanner_audit(records, total_applications=len(applications))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scanner-audit",
        description="Report aggregate freshness and scanner metrics without rerunning scans.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Also save the aggregate JSON report to this path.",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    from app.db.session import async_session, engine

    try:
        report = await collect_scanner_audit(async_session)
        serialized = json.dumps(report, indent=2, sort_keys=True)
        if args.json_output is not None:
            args.json_output.write_text(serialized + "\n", encoding="utf-8")
        print(format_scanner_audit(report))
        print("\nAGGREGATE JSON")
        print(serialized)
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    args = _parser().parse_args()
    if sys.platform.startswith("linux"):
        try:
            import uvloop
        except ImportError as exc:  # pragma: no cover - project dependency guard
            raise RuntimeError("Linux scanner audit requires uvloop for aiosqlite worker wakeups") from exc
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
