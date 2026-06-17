"""Seed-template tests — assert the three seed manifests are v2 with the
correct spacing presets and empty policy overrides."""

from __future__ import annotations

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


def test_policy_overrides_are_empty_for_every_seed():
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        assert _manifest(template_id).policy_overrides.by_type == {}


def test_seed_manifests_are_v2():
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        assert _manifest(template_id).manifest_version == 2


def test_seed_manifests_have_global_styles():
    """The customize panel reads ``global_styles``; every seed must populate it."""

    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        manifest = _manifest(template_id)
        # Modern has body_font + accent_color; Classic / Minimal vary.
        assert "body_font" in manifest.global_styles


def test_seed_manifests_have_zones_and_placement():
    for template_id in (MODERN_ID, CLASSIC_ID, MINIMAL_ID):
        manifest = _manifest(template_id)
        assert len(manifest.zones) >= 1
        assert "profile" in manifest.placement
        assert "experience" in manifest.placement
