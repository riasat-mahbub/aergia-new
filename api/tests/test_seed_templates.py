"""Seed-template tests — assert the three seed manifests are v2 with the
correct spacing presets and empty policy overrides."""

import pytest

from app.db.seed import SEED_TEMPLATES
from app.schema.models import TemplateManifest


MODERN_ID = "generic-modern"
CLASSIC_ID = "generic-classic"
MINIMAL_ID = "generic-minimal"


def _manifest(template_id):
    seed = next(t for t in SEED_TEMPLATES if t["id"] == template_id)
    return TemplateManifest.model_validate(seed["manifest"])


def test_modern_template_spacing_is_comfortable():
    assert _manifest(MODERN_ID).layout_defaults.spacing == "comfortable"


def test_classic_template_spacing_is_compact():
    assert _manifest(CLASSIC_ID).layout_defaults.spacing == "compact"


def test_minimal_template_spacing_is_minimal():
    assert _manifest(MINIMAL_ID).layout_defaults.spacing == "minimal"


def test_minimal_seed_overrides_skills_to_inline():
    """The minimal template ships with skills in inline (comma-separated) mode
    so the rendered CV matches the single-column golden reference. The other
    two templates leave ``policy_overrides.by_type`` empty."""
    from app.schema.models import SectionPolicy
    assert _manifest(MINIMAL_ID).policy_overrides.by_type == {
        "skills": SectionPolicy(skill_variant="inline")
    }
    for template_id in (MODERN_ID, CLASSIC_ID):
        assert _manifest(template_id).policy_overrides.by_type == {}


def test_section_policies_default_entry_layout_by_type():
    """Per-type SECTION_POLICIES defaults set entry_layout='two-column'
    for projects, research, and certifications — the three sections whose
    body content and date/link benefit from a two-column grid (left =
    title/description/etc., right = date+link right-justified). Other
    types keep the stack layout (the existing rail pattern is correct
    for them)."""
    from app.services.renderer.policy import SECTION_POLICIES
    assert SECTION_POLICIES["research"].entry_layout == "two-column"
    assert SECTION_POLICIES["projects"].entry_layout == "two-column"
    assert SECTION_POLICIES["certifications"].entry_layout == "two-column"
    for type_ in ("experience", "education", "profile", "skills", "languages", "extras"):
        assert SECTION_POLICIES[type_].entry_layout == "stack", f"{type_} should be stack"

def test_seed_manifests_are_v2():
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        assert _manifest(template_id).manifest_version == 2


def test_seed_manifests_have_global_styles():
    """The customize panel reads ``global_styles``; every seed must populate it."""

    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        manifest = _manifest(template_id)
        # Modern has body_font + accent_color; Classic / Minimal vary.
        assert manifest.global_styles.body_font is not None


def test_seed_manifests_have_zones_and_placement():
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        manifest = _manifest(template_id)
        assert len(manifest.zones) >= 1
        assert "profile" in manifest.placement
        assert "experience" in manifest.placement


def test_seed_manifests_have_no_v1_fields():
    """Seed source no longer carries the legacy v1 fields.

    Phase 1 derived v2 manifests from a ``layout_config`` +
    ``default_customizations`` pair on the seed source. Phase 3
    re-authors the seeds as v2 manifests directly; the legacy keys must
    not appear on the seed dict (and must not appear on the manifest
    either)."""
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        seed = next(t for t in SEED_TEMPLATES if t["id"] == template_id)
        assert "layout_config" not in seed, f"{template_id} seed still carries layout_config"
        assert "default_customizations" not in seed, f"{template_id} seed still carries default_customizations"
        manifest = seed["manifest"]
        assert "layout_config" not in manifest, f"{template_id} manifest still carries layout_config"
        assert "default_customizations" not in manifest, f"{template_id} manifest still carries default_customizations"


def test_seed_manifests_use_constrained_vocabulary():
    """The three seeds use the closed design vocabulary: width/padding/font
    tokens, color refs, no raw CSS strings, no ``extra`` keys on zones.
    """
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        seed = next(t for t in SEED_TEMPLATES if t["id"] == template_id)
        manifest = seed["manifest"]
        for zone in manifest["zones"]:
            styles = zone.get("styles", {})
            assert "width" in styles
            assert styles["width"] in {"narrow", "half", "full", "auto"}, (
                f"{template_id} zone {zone['id']} width must be a token"
            )
            if "padding" in styles:
                assert styles["padding"] in {"none", "tight", "comfortable", "loose", "spacious"}, (
                    f"{template_id} zone {zone['id']} padding must be a token"
                )
            if "background" in styles:
                bg = styles["background"]
                assert (bg.startswith("#") and len(bg) == 7) or bg.startswith("palette."), (
                    f"{template_id} zone {zone['id']} background must be a hex or palette ref"
                )
        gs = manifest["global_styles"]
        assert gs.get("body_font") in {"sans-serif", "serif", "mono", "display"}
        assert gs.get("heading_font") in {"sans-serif", "serif", "mono", "display"}
        # No v1-era arbitrary CSS keys.
        for forbidden in ("display", "position", "transform", "gridTemplateColumns"):
            for zone in manifest["zones"]:
                styles = zone.get("styles", {})
                assert forbidden not in styles, (
                    f"{template_id} zone {zone['id']} has forbidden CSS key {forbidden!r}"
                )


@pytest.mark.asyncio
async def test_seed_does_not_persist_default_customizations(client):
    """The seed no longer populates the legacy ``default_customizations``
    column. The editor reads the manifest directly."""
    from app.models.template import Template
    from app.db.session import async_session
    async with async_session() as session:
        for tpl_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
            tpl = await session.get(Template, tpl_id)
            assert tpl is not None
            assert tpl.default_customizations is None, (
                f"{tpl_id} has a populated default_customizations; "
                f"the seed should leave it null"
            )
