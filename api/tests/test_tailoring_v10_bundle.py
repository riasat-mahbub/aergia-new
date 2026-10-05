"""Verify the installable skill in the repository and Docker filesystem layout."""

from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import subprocess
from zipfile import ZipFile

from app.http_schemas.tailoring import PROTOCOL_VERSION
from app.services import tailoring_skill


def test_extracted_bundle_resolves_references_and_loads_the_portable_helper(tmp_path):
    tailoring_skill.build_tailoring_skill_bundle.cache_clear()
    first = tailoring_skill.build_tailoring_skill_bundle()
    tailoring_skill.build_tailoring_skill_bundle.cache_clear()
    second = tailoring_skill.build_tailoring_skill_bundle()
    assert first.content == second.content
    assert first.sha256 == second.sha256
    with ZipFile(BytesIO(first.content)) as archive:
        archive.extractall(tmp_path)
    installed = tmp_path / "aergia-tailor"
    skill = (installed / "SKILL.md").read_text()
    for reference in re.findall(r"\]\((references/[^)]+)\)", skill):
        assert (installed / reference).is_file(), reference
    assert (installed / "scripts" / "fit-review.mjs").is_file()
    helper_url = (installed / "scripts" / "session.mjs").as_uri()
    result = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"const helper = await import({json.dumps(helper_url)}); console.log(helper.PROTOCOL_VERSION);"],
        check=True, capture_output=True, text=True, timeout=10,
    )
    assert result.stdout.strip() == str(PROTOCOL_VERSION)


def test_docker_copy_layout_includes_new_review_assets(tmp_path, monkeypatch):
    repository = Path(__file__).resolve().parents[2]
    dockerfile = (repository / "api" / "Dockerfile").read_text()
    assert "COPY tailoring-skill/skills/aergia-tailor /app/tailoring-skill/skills/aergia-tailor" in dockerfile
    container_app = tmp_path / "app"
    destination = container_app / "tailoring-skill" / "skills" / "aergia-tailor"
    shutil.copytree(repository / "tailoring-skill" / "skills" / "aergia-tailor", destination)
    monkeypatch.setattr(tailoring_skill, "__file__", str(container_app / "app" / "services" / "tailoring_skill.py"))
    tailoring_skill.build_tailoring_skill_bundle.cache_clear()
    try:
        bundle = tailoring_skill.build_tailoring_skill_bundle()
        with ZipFile(BytesIO(bundle.content)) as archive:
            assert archive.read("aergia-tailor/references/independent-review.md")
            assert archive.read("aergia-tailor/scripts/fit-review.mjs")
            assert f'protocol-version: "{PROTOCOL_VERSION}"' in archive.read("aergia-tailor/SKILL.md").decode()
    finally:
        tailoring_skill.build_tailoring_skill_bundle.cache_clear()
