"""Load and validate the editable portfolio tour storyboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import ShowcaseConfig


@dataclass(frozen=True, slots=True)
class StoryScene:
    id: str
    caption: str
    target_seconds: float

    @property
    def target_milliseconds(self) -> int:
        return round(self.target_seconds * 1_000)


@dataclass(frozen=True, slots=True)
class Storyboard:
    scenes: dict[str, StoryScene]

    def scene(self, scene_id: str) -> StoryScene:
        try:
            return self.scenes[scene_id]
        except KeyError as exc:
            raise KeyError(f"storyboard has no scene {scene_id!r}") from exc


def load_storyboard(config: ShowcaseConfig) -> Storyboard:
    with config.storyboard_path.open(encoding="utf-8") as handle:
        data: Any = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise ValueError("showcase storyboard must contain a scenes array")

    scenes: dict[str, StoryScene] = {}
    for index, raw_scene in enumerate(data["scenes"]):
        if not isinstance(raw_scene, dict):
            raise ValueError(f"storyboard scene {index} must be an object")
        scene_id = raw_scene.get("id")
        caption = raw_scene.get("caption")
        duration = raw_scene.get("target_seconds")
        if not isinstance(scene_id, str) or not scene_id.strip():
            raise ValueError(f"storyboard scene {index} has an invalid id")
        if scene_id in scenes:
            raise ValueError(f"storyboard scene id {scene_id!r} is duplicated")
        if not isinstance(caption, str) or not caption.strip():
            raise ValueError(f"storyboard scene {scene_id!r} has an invalid caption")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            raise ValueError(f"storyboard scene {scene_id!r} has an invalid duration")
        scenes[scene_id] = StoryScene(
            id=scene_id,
            caption=caption,
            target_seconds=float(duration),
        )

    for required_scene in ("intro", "dashboard", "outro"):
        if required_scene not in scenes:
            raise ValueError(f"storyboard is missing required scene {required_scene!r}")
    return Storyboard(scenes=scenes)
