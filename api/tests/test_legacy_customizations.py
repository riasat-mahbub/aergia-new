"""Tests for the legacy customizations migrator.

Phase 2 cut ``Customizations`` to canonical v2 fields. Legacy CVs in the
DB still carry the v1 ``{colors, fonts, spacing, flags}`` shape; this
migrator converts them at read time so legacy rows continue to render.
"""

from __future__ import annotations

from app.services.legacy_customizations import migrate_legacy_customizations


def test_no_legacy_keys_returns_input_unchanged():
    raw = {"accent_color": "#abc", "body_font": "Inter"}
    assert migrate_legacy_customizations(raw) is raw


def test_legacy_colors_accent_maps_to_accent_color():
    out = migrate_legacy_customizations({"colors": {"accent": "#ff0000"}})
    assert out["accent_color"] == "#ff0000"
    assert "colors" not in out


def test_legacy_fallback_header_used_when_accent_missing():
    out = migrate_legacy_customizations({"colors": {"header": "#000000"}})
    assert out["accent_color"] == "#000000"


def test_legacy_fonts_maps_to_body_and_heading():
    out = migrate_legacy_customizations({"fonts": {"body": "Inter", "heading": "Georgia"}})
    assert out["body_font"] == "Inter"
    assert out["heading_font"] == "Georgia"
    assert "fonts" not in out


def test_legacy_section_gap_20px_maps_to_compact():
    out = migrate_legacy_customizations({"spacing": {"section_gap": "20px"}})
    assert out["spacing"] == "compact"


def test_per_section_passthrough():
    raw = {
        "colors": {"accent": "#abc"},
        "per_section": {"p": {"subsection": {"section_color": "#f00"}}},
    }
    out = migrate_legacy_customizations(raw)
    assert out["per_section"] == {"p": {"subsection": {"section_color": "#f00"}}}


def test_empty_input_returns_empty():
    assert migrate_legacy_customizations({}) == {}


def test_none_input_returns_empty():
    assert migrate_legacy_customizations(None) == {}
