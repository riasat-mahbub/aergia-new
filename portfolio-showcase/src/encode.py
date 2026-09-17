"""Turn the Playwright recording into portfolio-ready media assets."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ShowcaseConfig
from .capture import CaptureResult


@dataclass(frozen=True, slots=True)
class EncodeResult:
    mp4: Path
    webm: Path
    gif: Path
    poster: Path


def _run_ffmpeg(arguments: list[str], action: str) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        details = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"{action} failed: {details[-500:]}")


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        details = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"unable to inspect {path.name}: {details[-500:]}")
    return json.loads(result.stdout.decode("utf-8"))


def _video_dimensions(path: Path) -> tuple[int, int]:
    streams = _probe(path).get("streams", [])
    for stream in streams:
        if stream.get("width") and stream.get("height"):
            return int(stream["width"]), int(stream["height"])
    raise RuntimeError(f"{path.name} has no video dimensions")


def _duration(path: Path) -> float:
    value = _probe(path).get("format", {}).get("duration")
    if value is None:
        raise RuntimeError(f"{path.name} has no duration")
    return float(value)


def encode_showcase(config: ShowcaseConfig, capture: CaptureResult) -> EncodeResult:
    """Create MP4, WebM, GIF, and poster derivatives from one raw recording."""

    if not capture.raw_video.is_file():
        raise FileNotFoundError(f"raw showcase video does not exist: {capture.raw_video}")
    if not capture.exported_pdf.is_file() or capture.exported_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("showcase did not produce a valid exported PDF")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    mp4 = config.output_dir / "aergia-showcase.mp4"
    webm = config.output_dir / "aergia-showcase.webm"
    gif = config.output_dir / "aergia-showcase.gif"
    poster = config.output_dir / "aergia-showcase-poster.webp"

    _run_ffmpeg(
        [
            "-ss",
            str(config.recording_preroll_seconds),
            "-i",
            str(capture.raw_video),
            "-vf",
            f"fps=30,scale={config.viewport_width}:{config.viewport_height}:flags=lanczos",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(mp4),
        ],
        "MP4 encoding",
    )
    _run_ffmpeg(
        [
            "-ss",
            str(config.recording_preroll_seconds),
            "-i",
            str(capture.raw_video),
            "-vf",
            f"fps=30,scale={config.viewport_width}:{config.viewport_height}:flags=lanczos",
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "32",
            "-b:v",
            "0",
            "-row-mt",
            "1",
            "-an",
            str(webm),
        ],
        "WebM encoding",
    )
    _run_ffmpeg(
        [
            "-ss",
            str(config.recording_preroll_seconds),
            "-i",
            str(capture.raw_video),
            "-filter_complex",
            (
                f"fps={config.gif_fps},scale={config.gif_width}:-1:flags=lanczos,"
                "split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];"
                "[s1][p]paletteuse=dither=sierra2_4a"
            ),
            "-loop",
            "0",
            str(gif),
        ],
        "GIF encoding",
    )
    _run_ffmpeg(
        [
            "-ss",
            "0.8",
            "-i",
            str(mp4),
            "-frames:v",
            "1",
            "-vf",
            f"scale={config.gif_width}:-1:flags=lanczos",
            str(poster),
        ],
        "poster encoding",
    )

    _validate_outputs(config, EncodeResult(mp4=mp4, webm=webm, gif=gif, poster=poster))
    return EncodeResult(mp4=mp4, webm=webm, gif=gif, poster=poster)


def _validate_outputs(config: ShowcaseConfig, outputs: EncodeResult) -> None:
    for path in (outputs.mp4, outputs.webm, outputs.gif, outputs.poster):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"showcase output is empty: {path.name}")

    duration = _duration(outputs.mp4)
    if not config.min_duration_seconds <= duration <= config.max_duration_seconds:
        raise RuntimeError(
            f"showcase duration is {duration:.1f}s; expected between "
            f"{config.min_duration_seconds:.1f}s and {config.max_duration_seconds:.1f}s"
        )

    expected_dimensions = (config.viewport_width, config.viewport_height)
    if _video_dimensions(outputs.mp4) != expected_dimensions:
        raise RuntimeError(f"MP4 dimensions are not {expected_dimensions[0]}x{expected_dimensions[1]}")
    if _video_dimensions(outputs.webm) != expected_dimensions:
        raise RuntimeError(f"WebM dimensions are not {expected_dimensions[0]}x{expected_dimensions[1]}")

    if outputs.gif.stat().st_size > 30 * 1024 * 1024:
        raise RuntimeError("GIF is larger than 30 MiB; reduce gif_width or gif_fps")
