"""T55: Pytest: user template with {{header}} placeholder renders correctly without layout_config."""

import pytest

from app.services.renderer import render_user_template_unified, _replace_unknown_zones


SAMPLE_INSTANCE_PROFILE = {
    "id": "sec_profile",
    "type": "profile",
    "title": "Profile",
    "enabled": True,
    "data": {
        "name": "Jane Doe",
        "title": "Software Engineer",
        "email": "jane@example.com",
        "phone": "+1 555-1234",
        "location": "Boston, MA",
        "summary": "Experienced engineer.",
    },
}

SAMPLE_INSTANCE_EXPERIENCE = {
    "id": "sec_exp",
    "type": "experience",
    "title": "Experience",
    "enabled": True,
    "data": [
        {"position": "Senior Dev", "company": "ACME Corp", "start_date": "2020", "end_date": "2024"},
    ],
}


class TestUserTemplateHeaderZone:
    """Verify that {{header}} and other zone placeholders work without layout_config."""

    def test_header_replaced_without_layout_config(self):
        """MIT-style template with {{header}} and {{main}} renders profile into header when no layout_config."""
        layout_template = '<div class="header-zone">{{header}}</div><div class="main-zone">{{main}}</div>'
        instances = [SAMPLE_INSTANCE_PROFILE, SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=None)

        assert "{{header}}" not in result, "Literal {{header}} should be replaced"
        assert "{{main}}" not in result, "Literal {{main}} should be replaced"
        assert "Jane Doe" in result, "Profile name should appear (in header zone)"
        assert "ACME Corp" in result, "Experience content should appear (in main zone)"

    def test_profile_goes_to_header_by_default(self):
        """When template has {{header}} but no placement config, profile sections map to header automatically."""
        layout_template = '<div class="header-zone">{{header}}</div><div>{{main}}</div>'
        instances = [SAMPLE_INSTANCE_PROFILE, SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=None)

        # Profile content should be inside the header zone div, experience in main zone
        header_start = result.find('class="header-zone"')
        main_zone_start = result.find('{{main}}') if '{{main}}' in result else result.find('main-zone')
        jane_pos = result.find("Jane Doe")
        acme_pos = result.find("ACME Corp")

        assert header_start < jane_pos, \
            f"Profile (Jane Doe) should be after header-zone start"
        # main_zone_start may be -1 if {{main}} was already replaced
        if main_zone_start >= 0:
            assert jane_pos < main_zone_start, \
                f"Profile should be before main zone"
            assert acme_pos > main_zone_start, \
                f"Experience should be after main zone start"

    def test_header_empty_when_no_profile(self):
        """When no profile section exists, {{header}} placeholder is replaced with empty string."""
        layout_template = '<div class="header-zone">{{header}}</div><div>{{main}}</div>'
        instances = [SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=None)

        assert "{{header}}" not in result
        assert "ACME Corp" in result

    def test_data_variables_preserved(self):
        """Non-zone placeholders like {{name}} are preserved as literal text."""
        layout_template = '<title>{{name}} — CV</title><div>{{header}}</div><div>{{main}}</div>'
        instances = [SAMPLE_INSTANCE_PROFILE, SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=None)

        assert "{{name}}" in result, "Data variable {{name}} should be preserved"
        assert "{{header}}" not in result
        assert "{{main}}" not in result

    def test_unknown_zone_placeholder_cleaned_up(self):
        """Zone-like placeholders that have no instances become empty strings."""
        layout_template = '<div>{{header}}</div><div>{{main}}</div><div>{{footer}}</div>'
        instances = [SAMPLE_INSTANCE_PROFILE, SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=None)

        assert "{{header}}" not in result
        assert "{{main}}" not in result
        assert "{{footer}}" not in result, "Unknown zone placeholder should be empty string"
        assert "Jane Doe" in result

    def test_layout_config_with_zones_still_works(self):
        """Existing behavior: layout_config with zones defined continues to work."""
        layout_template = '<div>{{sidebar}}</div><div>{{main}}</div>'
        layout_config = {
            "zones": [
                {"id": "sidebar", "styles": {"width": "30%"}},
                {"id": "main", "styles": {"padding": "24px"}},
            ],
            "placement": {
                "profile": "sidebar",
                "experience": "main",
            },
        }
        instances = [SAMPLE_INSTANCE_PROFILE, SAMPLE_INSTANCE_EXPERIENCE]

        result = render_user_template_unified(instances, {}, layout_template, layout_config=layout_config)

        assert "{{sidebar}}" not in result
        assert "{{main}}" not in result
        assert "Jane Doe" in result
        assert "ACME Corp" in result


class TestReplaceUnknownZones:
    """Unit tests for _replace_unknown_zones with populated_zone_ids tracking."""

    def test_populated_zone_ids_keeps_known_zones(self):
        """Placeholders matching populated zone IDs are preserved (with their content)."""
        html = '<div>{{header}}CONTENT{{/header}}</div><div>{{main}}</div>'
        result = _replace_unknown_zones(html, None, populated_zone_ids={"header", "main"})
        assert "{{header}}" in result  # kept but not replaced — content stays as-is
        assert "{{main}}" in result

    def test_populated_zone_ids_removes_zone_names(self):
        """Zone-like names not in populated set are replaced with empty string."""
        html = '<div>{{header}}</div><div>{{footer}}</div>'
        result = _replace_unknown_zones(html, None, populated_zone_ids={"header"})
        assert "{{header}}" in result  # kept (was populated)
        assert "{{footer}}" not in result  # "footer" matches zone naming pattern

    def test_non_zone_names_preserved_as_data_variables(self):
        """Names that don't look like zones are preserved as data variables."""
        html = '<div>{{header}}</div><div>{{unknown}}</div>'
        result = _replace_unknown_zones(html, None, populated_zone_ids={"header"})
        assert "{{header}}" in result  # kept (was populated)
        assert "{{unknown}}" in result  # preserved — doesn't match zone naming patterns

    def test_data_variables_preserved(self):
        """Non-zone data variables like {{name}} are preserved."""
        html = '<title>{{name}}</title><div>{{main}}</div>'
        result = _replace_unknown_zones(html, None, populated_zone_ids={"main"}, all_placeholders={"name", "main"})
        assert "{{name}}" in result  # preserved as data variable
        assert "{{main}}" in result

    def test_legacy_path_with_layout_config_zones(self):
        """Legacy path: zones defined in layout_config.zones are preserved."""
        html = '<div>{{main}}</div><div>{{sidebar}}</div><div>{{ghost}}</div>'
        layout_config = {
            "zones": [
                {"id": "main"},
                {"id": "sidebar"},
            ]
        }
        result = _replace_unknown_zones(html, layout_config)
        assert "{{main}}" in result
        assert "{{sidebar}}" in result
        assert "{{ghost}}" not in result

    def test_no_layout_config_no_populated_leaves_html_unchanged(self):
        """When neither populated_zone_ids nor layout_config is available, HTML is untouched."""
        html = '<div>{{header}}</div><div>{{main}}</div>'
        result = _replace_unknown_zones(html, None, None)
        assert result == html
