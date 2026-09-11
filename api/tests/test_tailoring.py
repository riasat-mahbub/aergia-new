"""Small public-bundle contract check for protocol-v2 tailoring."""

from io import BytesIO
from zipfile import ZipFile

from app.services.tailoring_skill import build_tailoring_skill_bundle


def test_tailoring_skill_bundle_contains_v2_candidate_workflow():
    bundle = build_tailoring_skill_bundle()
    with ZipFile(BytesIO(bundle.content)) as archive:
        names = set(archive.namelist())
        assert "aergia-tailor/SKILL.md" in names
        assert "aergia-tailor/scripts/session.mjs" in names
        assert "aergia-tailor/scripts/validate-candidate.mjs" in names
        assert not any(name.endswith("validate-patch.mjs") for name in names)
        skill = archive.read("aergia-tailor/SKILL.md").decode()
        assert 'protocol-version: "2"' in skill
