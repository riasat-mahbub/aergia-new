"""Configuration and path helpers for the portfolio showcase harness."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


SHOWCASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SHOWCASE_DIR.parent


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not 1_024 <= parsed <= 65_535:
        raise ValueError(f"{name} must be between 1024 and 65535")
    return parsed


@dataclass(frozen=True, slots=True)
class ShowcaseConfig:
    """Runtime settings shared by the server, seed, capture, and encoder."""

    repo_root: Path = REPO_ROOT
    showcase_dir: Path = SHOWCASE_DIR
    api_port: int = _int_env("AERGIA_SHOWCASE_API_PORT", 8875)
    web_port: int = _int_env("AERGIA_SHOWCASE_WEB_PORT", 8876)
    viewport_width: int = 1280
    viewport_height: int = 800
    gif_width: int = 1200
    gif_fps: int = 12
    recording_preroll_seconds: float = 0.75
    min_duration_seconds: float = 20.0
    max_duration_seconds: float = 90.0

    @property
    def api_dir(self) -> Path:
        return self.repo_root / "api"

    @property
    def web_dir(self) -> Path:
        return self.repo_root / "web"

    @property
    def python_bin(self) -> Path:
        return self.api_dir / ".venv" / "bin" / "python"

    @property
    def alembic_bin(self) -> Path:
        return self.api_dir / ".venv" / "bin" / "alembic"

    @property
    def alembic_ini(self) -> Path:
        return self.api_dir / "alembic.ini"

    @property
    def alembic_dir(self) -> Path:
        return self.api_dir / "alembic"

    @property
    def fixture_path(self) -> Path:
        return self.showcase_dir / "fixtures" / "demo-data.json"

    @property
    def import_source_html(self) -> Path:
        return self.showcase_dir / "fixtures" / "source-cv.html"

    @property
    def storyboard_path(self) -> Path:
        return self.showcase_dir / "config" / "storyboard.json"

    @property
    def output_dir(self) -> Path:
        return self.showcase_dir / "output"

    @property
    def work_dir(self) -> Path:
        return self.showcase_dir / "work"

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    @property
    def web_url(self) -> str:
        return f"http://127.0.0.1:{self.web_port}"


def load_fixture(config: ShowcaseConfig) -> dict:
    """Load and minimally validate the JSON fixture."""

    import json

    with config.fixture_path.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if not isinstance(fixture, dict):
        raise ValueError("showcase fixture must be a JSON object")
    for key in ("profile", "library", "cv", "application"):
        if key not in fixture:
            raise ValueError(f"showcase fixture is missing {key!r}")
    return fixture
