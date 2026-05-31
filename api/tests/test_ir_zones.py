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
            {"id": "main", "row": 0, "styles": {"width": "100%", "padding": "24px"}},
        ],
        "layout_config": {
            # The CV's live layout includes a NEW zone that the template
            # manifest's top-level zones do not know about.
            "zones": [
                {"id": "main", "row": 0, "styles": {"width": "50%", "padding": "24px"}},
                {"id": "new_zone", "row": 0, "styles": {"width": "50%", "background-color": "#f00"}},
                {"id": "extra_row", "row": 1, "styles": {"width": "100%", "padding": "8px"}},
            ],
            "placement": {
                "sec_profile": "new_zone",
                "sec_experience": "main",
            },
        },
    }

    ir: DocumentIR = build_ir(manifest, {"instances": _sample_instances()}, {})

    # Collect all zone ids across all rows.
    zone_ids = [z.id for row in ir.rows for z in row.zones]

    assert "new_zone" in zone_ids
    assert "extra_row" in zone_ids
    assert "main" in zone_ids
    # The new zone should carry its styles so it renders as a styled box.
    new_zone = next(z for row in ir.rows for z in row.zones if z.id == "new_zone")
    assert new_zone.styles.get("background-color") == "#f00"

def test_build_ir_zone_styles_from_layout_config():
    """Zone styles from layout_config override the manifest defaults verbatim."""
    manifest = {
        "zones": [{"id": "main", "row": 0, "styles": {"width": "100%"}}],
        "layout_config": {
            "zones": [
                {"id": "main", "row": 0, "styles": {"width": "60%", "background-color": "#eee", "padding": "32px"}},
            ],
            "placement": {"sec_profile": "main"},
        },
    }
    ir: DocumentIR = build_ir(manifest, {"instances": _sample_instances()}, {})
    main_zone = next(z for row in ir.rows for z in row.zones if z.id == "main")
    assert main_zone.styles["width"] == "60%"
    assert main_zone.styles["background-color"] == "#eee"
    assert main_zone.styles["padding"] == "32px"
