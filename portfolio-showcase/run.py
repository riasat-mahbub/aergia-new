#!/usr/bin/env python3
"""Run the complete Aergia portfolio showcase pipeline.

Examples:

    api/.venv/bin/python portfolio-showcase/run.py
    api/.venv/bin/python portfolio-showcase/run.py --skip-build --headed
    api/.venv/bin/python portfolio-showcase/run.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.capture import capture_tour
from src.config import ShowcaseConfig, load_fixture
from src.encode import encode_showcase
from src.environment import ShowcaseEnvironment
from src.seed import seed_demo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Aergia portfolio showcase media")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="use the existing web/.output build instead of rebuilding the web app",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="show Chromium while capturing the tour",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run the isolated seed and browser capture without encoding final media",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = ShowcaseConfig()
    fixture = load_fixture(config)

    print("[showcase] starting disposable Aergia instance", flush=True)
    with ShowcaseEnvironment(config, build=not args.skip_build) as environment:
        runtime_dir = environment.runtime_dir
        if runtime_dir is None:
            raise RuntimeError("showcase runtime directory is unavailable")
        seed = asyncio.run(seed_demo(config, fixture, runtime_dir))
        print("[showcase] recording browser storyboard", flush=True)
        capture = asyncio.run(
            capture_tour(
                config,
                seed,
                runtime_dir,
                headed=args.headed,
            )
        )
        if args.dry_run:
            print("SHOWCASE DRY RUN OK: seed, browser flow, import, preview, and PDF export")
            return 0

        print("[showcase] encoding MP4, WebM, GIF, and poster", flush=True)
        outputs = encode_showcase(config, capture)

    print(f"SHOWCASE OK: {outputs.gif}")
    print(f"MP4: {outputs.mp4}")
    print(f"WebM: {outputs.webm}")
    print(f"Poster: {outputs.poster}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Showcase cancelled", file=sys.stderr)
        raise SystemExit(130)
