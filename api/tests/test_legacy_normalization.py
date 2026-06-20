"""Legacy-style normalization — one test per ADR mapping row."""

from __future__ import annotations

from app.services.renderer.builders import build_section_style
from app.schema.models import (
    LayoutHints,
    SectionInstanceStyle,
    SubsectionStyle,
    TemplateManifest,
    TextStyle,
)


def _manifest():
    return TemplateManifest(
        name="M",
        zones=[],
        placement={},
        policy_overrides={"by_type": {}},
    )


def _resolve(legacy):
    """Resolve with no instance_style and a manifest; legacy alone drives the cascade."""
    style, policy = build_section_style(
        instance_type="experience",
        instance_style=None,
        legacy=legacy,
        manifest=_manifest(),
    )
    return style, policy


def test_font_maps_to_layout_font_family():
    style, _ = _resolve({"font": "Inter"})
    assert style.layout.font_family == "Inter"


def test_color_maps_to_subsection_section_color():
    style, _ = _resolve({"color": "#abc"})
    assert style.subsection.section_color == "#abc"


def test_weight_bold_sets_bold_on_text_runs():
    style, _ = _resolve({"weight": "bold"})
    assert any(ts.bold for ts in style.text.values())


def test_weight_normal_clears_bold():
    style, _ = _resolve({"weight": "normal"})
    for ts in style.text.values():
        assert ts.bold is False


def test_text_align_maps_to_subsection_text_align():
    style, _ = _resolve({"text_align": "right"})
    assert style.subsection.text_align == "right"


def test_show_title_maps_to_policy_show_title():
    _, policy = _resolve({"show_title": False})
    assert policy.show_title is False
    _, policy = _resolve({"show_title": True})
    assert policy.show_title is True


def test_layout_inline_maps_to_policy_skill_variant():
    style, policy = build_section_style(
        instance_type="skills",
        instance_style=None,
        legacy={"layout": "inline"},
        manifest=_manifest(),
    )
    assert policy.skill_variant == "inline"


def test_layout_block_maps_to_policy_skill_variant():
    style, policy = build_section_style(
        instance_type="skills",
        instance_style=None,
        legacy={"layout": "block"},
        manifest=_manifest(),
    )
    assert policy.skill_variant == "block"


def test_field_styles_maps_to_text_per_field_key():
    style, _ = _resolve({"field_styles": {"name": {"weight": "bold"}}})
    assert "name" in style.text
    assert style.text["name"].bold is True


def test_date_style_dict_maps_to_layout_date_style():
    style, _ = _resolve({"date_style": {"key": "Mon YYYY", "range_sep": "-"}})
    assert style.layout.date_style is not None
    assert style.layout.date_style["key"] == "Mon YYYY"
    assert style.layout.date_style["range_sep"] == "-"


def test_subsection_gap_maps_to_subsection_spacing_after():
    style, _ = _resolve({"subsection_gap": "12px"})
    assert style.subsection.spacing_after == "12px"


def test_row_gap_maps_to_subsection_spacing_after():
    style, _ = _resolve({"row_gap": "8px"})
    assert style.subsection.spacing_after == "8px"


def test_legacy_overrides_instance_style_in_cascade():
    """The legacy overlay applies on top of the instance style, so legacy
    wins for fields it sets (per the ADR mapping table).
    """
    style, _ = build_section_style(
        instance_type="experience",
        instance_style=SectionInstanceStyle(subsection=SubsectionStyle(section_color="#new")),
        legacy={"color": "#legacy"},
        manifest=_manifest(),
    )
    assert style.subsection.section_color == "#legacy"
