"""Checks for the one-time per-section customization data cutover."""

from pathlib import Path
import runpy


_MIGRATION = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "k6l7m8n9o0p1_move_section_overrides_into_instances.py"
    )
)
merge_per_section_styles = _MIGRATION["merge_per_section_styles"]


def test_per_section_values_move_to_instance_style_and_override_conflicts():
    sections = [
        {
            "id": "experience-1",
            "type": "experience",
            "style": {
                "text": {"position": {"bold": True}},
                "subsection": {"text_align": "left", "spacing_after": "loose"},
                "typography": {"body": {"color": "#111111", "italic": True}},
            },
        },
        {"id": "profile-1", "type": "profile", "style": None},
    ]
    customizations = {
        "accent_color": "#123456",
        "layout": {"placement": {"experience-1": "main"}},
        "per_section": {
            "experience-1": {
                "text": {"position": {"italic": True}},
                "subsection": {"text_align": "right"},
                "typography": {"body": {"color": "#222222"}},
            },
            "profile-1": {"policy": {"show_title": False}},
            "deleted-section": {"subsection": {"spacing_after": "tight"}},
        },
    }

    moved_sections, moved_customizations = merge_per_section_styles(sections, customizations)

    assert moved_sections[0]["style"] == {
        "text": {"position": {"bold": True, "italic": True}},
        "subsection": {"text_align": "right", "spacing_after": "loose"},
        "typography": {"body": {"color": "#222222", "italic": True}},
    }
    assert moved_sections[1]["style"] == {"policy": {"show_title": False}}
    assert moved_customizations == {
        "accent_color": "#123456",
        "layout": {"placement": {"experience-1": "main"}},
    }
    assert "per_section" in customizations

    second_sections, second_customizations = merge_per_section_styles(moved_sections, moved_customizations)
    assert (second_sections, second_customizations) == (moved_sections, moved_customizations)
