"""Build the public, self-contained coding-agent skill bundle."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


@dataclass(frozen=True)
class TailoringSkillBundle:
    content: bytes
    sha256: str


def _skill_directory() -> Path:
    service_path = Path(__file__).resolve()
    candidates = (
        service_path.parents[3] / "tailoring-skill" / "skills" / "aergia-tailor",
        service_path.parents[2] / "tailoring-skill" / "skills" / "aergia-tailor",
    )
    for candidate in candidates:
        if (candidate / "SKILL.md").is_file():
            return candidate
    raise RuntimeError("The packaged aergia-tailor skill is unavailable")


def _bundle_files(skill_directory: Path) -> list[Path]:
    files = [skill_directory / "SKILL.md"]
    for directory in ("scripts", "references"):
        files.extend(
            path
            for path in (skill_directory / directory).rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    if any(not path.is_file() for path in files):
        raise RuntimeError("The packaged aergia-tailor skill is incomplete")
    return sorted(set(files), key=lambda path: path.relative_to(skill_directory).as_posix())


@lru_cache(maxsize=1)
def build_tailoring_skill_bundle() -> TailoringSkillBundle:
    """Return a deterministic ZIP containing one installable skill folder."""

    skill_directory = _skill_directory()
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source in _bundle_files(skill_directory):
            relative = source.relative_to(skill_directory)
            archive_name = (Path("aergia-tailor") / relative).as_posix()
            info = ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            mode = 0o755 if relative.parts[0] == "scripts" else 0o644
            info.external_attr = mode << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())
    content = output.getvalue()
    return TailoringSkillBundle(
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


__all__ = ["TailoringSkillBundle", "build_tailoring_skill_bundle"]
