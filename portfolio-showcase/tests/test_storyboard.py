from __future__ import annotations

import json
from pathlib import Path

from src.config import ShowcaseConfig, load_fixture
from src.storyboard import load_storyboard


def test_demo_fixture_has_the_three_cv_states_within_account_quota() -> None:
    config = ShowcaseConfig()
    fixture = load_fixture(config)

    assert fixture["cv"]["template_id"] == "generic-modern"
    assert fixture["profile"]["name"] == "Maya Chen"
    assert len(fixture["library"]) >= 5
    assert "FastAPI" in fixture["application"]["job_description"]


def test_storyboard_has_unique_scene_ids_and_a_portfolio_length() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "storyboard.json"
    storyboard = json.loads(path.read_text(encoding="utf-8"))
    scenes = storyboard["scenes"]
    scene_ids = [scene["id"] for scene in scenes]

    assert len(scene_ids) == len(set(scene_ids))
    assert scene_ids[0] == "intro"
    assert scene_ids[-1] == "outro"
    assert 20 <= sum(scene["target_seconds"] for scene in scenes) <= 60


def test_storyboard_is_consumable_by_the_capture_runner() -> None:
    storyboard = load_storyboard(ShowcaseConfig())

    assert storyboard.scene("import-dialog").caption == "Import that CV with the Modern template"
    assert storyboard.scene("applications-tab").target_milliseconds == 700
    assert storyboard.scene("export").target_milliseconds == 1_300


def test_showcase_paths_are_inside_the_repository() -> None:
    config = ShowcaseConfig()

    assert config.showcase_dir == config.repo_root / "portfolio-showcase"
    assert config.output_dir.parent == config.showcase_dir
    assert config.work_dir.parent == config.showcase_dir
    assert "Maya Chen" in config.import_source_html.read_text(encoding="utf-8")
    assert "Northstar Labs" in config.import_source_html.read_text(encoding="utf-8")


def test_title_card_uses_aergia_palette_and_hides_the_cursor() -> None:
    config = ShowcaseConfig()
    overlays = (config.showcase_dir / "src" / "overlays.py").read_text(encoding="utf-8").lower()

    assert "#059669" in overlays
    assert "#daffef" in overlays
    assert "#fcfffd" in overlays
    assert 'data-card-visible="true"' in overlays


def test_capture_starts_on_the_poster_and_seeds_a_valid_tailoring_session() -> None:
    config = ShowcaseConfig()
    capture = (config.showcase_dir / "src" / "capture.py").read_text(encoding="utf-8")
    seed = (config.showcase_dir / "src" / "seed.py").read_text(encoding="utf-8")

    assert capture.index("await show_card(") < capture.index('await _navigate(page, config, "/dashboard")')
    assert "/tailoring-sessions" in seed
