"""Regression: new zones must render in preview when a CV has custom zone layout.

The builder's live preview posts zones via manifest.layout_config.zones, keeping
the template's top-level manifest.zones stale. build_ir must derive the zone set
from layout_config.zones so newly-created zones appear in the output.
"""

from app.services.renderer.ir import build_ir
from app.services.renderer.types import DocumentIR


def _sample_instances():
    return [
        {
            "id": "sec_profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Jane Doe", "email": "jane@example.com"},
        },
        {
            "id": "sec_experience",
            "type": "experience",
            "title": "Experience",
            "enabled": True,
            "data": [
                {"id": "exp_1", "company": "Acme", "position": "Engineer",
                 "start_date": "2022", "end_date": None, "current": True,
                 "description": "Work"}
            ],
        },
    ]


def test_build_ir_uses_layout_config_zones_for_new_zone():
    """A newly-added zone present only in layout_config.zones is rendered."""
    # Template manifest carries the default zones baked in at seed time.
    manifest = {
        "zones": [
            {"id": "main", "styles": {"width": "100%", "padding": "24px"}},
        ],
        "layout_config": {
            # The CV's live layout includes NEW zones that the template
            # manifest's top-level zones do not know about.
            "zones": [
                {"id": "main", "styles": {"width": "50%", "padding": "24px"}},
                {"id": "new_zone", "styles": {"width": "50%", "background-color": "#f00"}},
                {"id": "extra_row", "styles": {"width": "100%", "padding": "8px"}},
            ],
            "placement": {
                "sec_profile": "new_zone",
                "sec_experience": "main",
            },
        },
    }

    ir: DocumentIR = build_ir(manifest, {"instances": _sample_instances()}, {})

    # Collect all zone ids across the flat zone list.
    zone_ids = [z.id for z in ir.zones]

    assert "new_zone" in zone_ids
    assert "extra_row" in zone_ids
    assert "main" in zone_ids
    # The new zone should carry its styles so it renders as a styled box.
    new_zone = next(z for z in ir.zones if z.id == "new_zone")
    assert new_zone.styles.get("background-color") == "#f00"


def test_build_ir_zone_styles_from_layout_config():
    """Zone styles from layout_config override the manifest defaults verbatim."""
    manifest = {
        "zones": [{"id": "main", "styles": {"width": "100%"}}],
        "layout_config": {
            "zones": [
                {"id": "main", "styles": {"width": "60%", "background-color": "#eee", "padding": "32px"}},
            ],
            "placement": {"sec_profile": "main"},
        },
    }
    ir: DocumentIR = build_ir(manifest, {"instances": _sample_instances()}, {})
    main_zone = next(z for z in ir.zones if z.id == "main")
    assert main_zone.styles["width"] == "60%"
    assert main_zone.styles["background-color"] == "#eee"
    assert main_zone.styles["padding"] == "32px"


def test_build_ir_returns_flat_zones():
    """build_ir exposes zones directly; no row grouping survives."""
    manifest = {
        "zones": [{"id": "a", "styles": {"width": "50%"}}, {"id": "b", "styles": {"width": "50%"}}],
        "layout_config": {"zones": [{"id": "a", "styles": {"width": "50%"}}, {"id": "b", "styles": {"width": "50%"}}], "placement": {}},
    }
    ir = build_ir(manifest, {"instances": _sample_instances()}, {})
    assert len(ir.zones) == 2
    assert all(z.id in {"a", "b"} for z in ir.zones)


def test_build_ir_section_text_align_applied_to_wrapper():
    """Per-section text_align lands on the panel wrapper so it cascades to body."""
    manifest = {"zones": [{"id": "main", "styles": {"width": "100%"}}], "layout_config": {"zones": [{"id": "main", "styles": {"width": "100%"}}], "placement": {"sec_profile": "main"}}}
    cv_data = {"instances": [{"id": "sec_profile", "type": "profile", "title": "Profile", "enabled": True, "data": {"name": "Jane"}, "style": {"text_align": "right"}}]}
    ir = build_ir(manifest, cv_data, {})
    panel = next(p for p in ir.zones[0].panels if p.type == "profile")
    assert "text-align: right" in panel.wrapper_style


def test_profile_renders_center_by_default():
    """Profile content is centered by default."""
    from app.services.renderer.section_renderers import render_section_preview
    html = render_section_preview("profile", {"name": "Jane"}, {})
    assert "text-align:center" in html


def test_profile_left_when_text_align_is_left():
    """An explicit text_align override replaces the profile center default."""
    from app.services.renderer.ir import _build_section_panel
    panel = _build_section_panel(
        {"id": "p", "type": "profile", "title": "Profile", "enabled": True, "data": {"name": "Jane"}, "style": {"text_align": "left"}},
        None,
    )
    assert "text-align: left" in panel.wrapper_style
    assert "text-align: center" not in panel.wrapper_style
