"""Integration tests for user template rendering with full HTML document format."""

import pytest
from app.services.renderer import render_user_template_unified


SAMPLE_INSTANCES = [
    {
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
    },
    {
        "id": "sec_exp",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"position": "Senior Dev", "company": "ACME Corp", "start_date": "2020", "end_date": "2024"},
        ],
    },
    {
        "id": "sec_edu",
        "type": "education",
        "title": "Education",
        "enabled": True,
        "data": [
            {"institution": "MIT", "degree": "MSc Computer Science", "start_date": "2018", "end_date": "2020"},
        ],
    },
    {
        "id": "sec_skills",
        "type": "skills",
        "title": "Skills",
        "enabled": True,
        "data": [
            {"category": "Programming", "items": ["Python", "TypeScript", "Go"]},
        ],
    },
]


CUSTOMIZATIONS = {
    "colors": {
        "accent": "#ff0000",
        "bg_sidebar": "#f0f0f0",
        "header": "#333333",
        "divider": "#cccccc",
        "text": "#555555",
        "heading": "#222222",
    },
    "fonts": {
        "body": "Arial, sans-serif",
        "heading": "Georgia, serif",
    },
    "spacing": {
        "section_gap": "20px",
    },
}

DEFAULT_CUSTOMIZATIONS = {
    "colors": {
        "accent": "#2563eb",
        "bg_sidebar": "#f8fafc",
    },
    "fonts": {
        "body": "Inter, system-ui, sans-serif",
        "heading": "Inter, system-ui, sans-serif",
    },
    "spacing": {
        "section_gap": "24px",
    },
}


def generate_test_html_with_zones() -> str:
    """Generate a test HTML template with sidebar and main zones."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { margin:0; font-family:{{body_font}}; color:var(--text); }
    h1,h2,h3 { font-family:{{heading_font}}; color:var(--heading); }
    .accent-bar { background-color: var(--accent); }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
  <div style="display:flex;flex:1 0 auto;">
    {{sidebar}}
    {{main}}
  </div>
</div>
</body>
</html>'''


LAYOUT_CONFIG_TWO_ZONES = {
    "zones": [
        {"id": "sidebar", "row": 0, "styles": {"width": "30%", "background-color": "#f8fafc", "padding": "24px"}},
        {"id": "main", "row": 0, "styles": {"width": "70%", "padding": "24px"}},
    ],
    "placement": {
        "profile": "sidebar",
        "experience": "main",
        "education": "main",
        "skills": "main",
    },
    "rowHeights": {"0": "100%"},
}


def test_user_template_renders_zones_correctly():
    """Test that user template with two zones renders content in correct zones."""
    layout_template = generate_test_html_with_zones()
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES, 
        CUSTOMIZATIONS, 
        layout_template, 
        LAYOUT_CONFIG_TWO_ZONES, 
        DEFAULT_CUSTOMIZATIONS
    )
    
    # Check that placeholders are replaced
    assert "{{sidebar}}" not in html, "Sidebar placeholder should be replaced"
    assert "{{main}}" not in html, "Main placeholder should be replaced"
    
    # Check that content appears in correct zones
    assert "Jane Doe" in html, "Profile name should appear"
    assert "Software Engineer" in html, "Profile title should appear"
    assert "ACME Corp" in html, "Experience company should appear"
    assert "Senior Dev" in html, "Experience position should appear"
    assert "MIT" in html, "Education institution should appear"
    assert "Python" in html, "Skill should appear"
    
    # Check CSS variable substitution
    assert "#ff0000" in html, "Custom accent color should be substituted"
    assert "Arial, sans-serif" in html, "Custom body font should be substituted"
    assert "Georgia, serif" in html, "Custom heading font should be substituted"
    
    # Check print styles injection
    assert "@page { size: A4" in html, "Print styles should be injected"
    
    # Check that data variables are preserved (if any)
    # Our template doesn't have data variables, but verify no unknown placeholders remain
    # (except possibly data variables which we don't have)


def test_user_template_single_zone():
    """Test template with single main zone."""
    single_zone_template = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { margin:0; font-family:{{body_font}}; }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
  <div style="display:flex;flex:1 0 auto;">
    {{main}}
  </div>
</div>
</body>
</html>'''
    
    layout_config = {
        "zones": [
            {"id": "main", "row": 0, "styles": {"width": "100%", "padding": "32px"}},
        ],
        "placement": {
            "profile": "main",
            "experience": "main",
            "education": "main",
            "skills": "main",
        },
    }
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES,
        CUSTOMIZATIONS,
        single_zone_template,
        layout_config,
        DEFAULT_CUSTOMIZATIONS
    )
    
    assert "{{main}}" not in html
    assert "Jane Doe" in html
    assert "ACME Corp" in html
    assert "MIT" in html
    assert "Python" in html


def test_user_template_multi_row():
    """Test template with multiple rows."""
    multi_row_template = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { margin:0; font-family:{{body_font}}; }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
  <div style="display:flex;flex:50 0 0%;">
    {{header}}
  </div>
  <div style="display:flex;flex:50 0 0%;">
    {{left}}
    {{right}}
  </div>
</div>
</body>
</html>'''
    
    layout_config = {
        "zones": [
            {"id": "header", "row": 0, "styles": {"width": "100%", "padding": "24px"}},
            {"id": "left", "row": 1, "styles": {"width": "50%", "padding": "24px"}},
            {"id": "right", "row": 1, "styles": {"width": "50%", "padding": "24px"}},
        ],
        "placement": {
            "profile": "header",
            "experience": "left",
            "education": "right",
            "skills": "right",
        },
        "rowHeights": {"0": "50%", "1": "50%"},
    }
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES,
        CUSTOMIZATIONS,
        multi_row_template,
        layout_config,
        DEFAULT_CUSTOMIZATIONS
    )
    
    assert "{{header}}" not in html
    assert "{{left}}" not in html
    assert "{{right}}" not in html
    assert "Jane Doe" in html  # in header
    assert "ACME Corp" in html  # in left
    assert "MIT" in html  # in right
    assert "Python" in html  # in right


def test_user_template_css_vars_in_style_block():
    """Test that CSS variables in the <style> block are substituted."""
    template_with_vars = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body { color: var(--text); background: var(--bg-sidebar); }
    h1 { color: var(--heading); }
    .accent { color: var(--accent); }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
  <div style="display:flex;flex:1 0 auto;">
    {{main}}
  </div>
</div>
</body>
</html>'''
    
    layout_config = {
        "zones": [{"id": "main", "row": 0, "styles": {"width": "100%"}}],
        "placement": {"profile": "main", "experience": "main"},
    }
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES,
        CUSTOMIZATIONS,
        template_with_vars,
        layout_config,
        DEFAULT_CUSTOMIZATIONS
    )
    
    # CSS vars should be substituted in the style block
    assert "var(--text)" not in html
    assert "var(--bg-sidebar)" not in html
    assert "var(--heading)" not in html
    assert "var(--accent)" not in html
    assert "#555555" in html  # text color
    assert "#f0f0f0" in html  # bg_sidebar
    assert "#222222" in html  # heading
    assert "#ff0000" in html  # accent


def test_user_template_preserves_data_variables():
    """Test that non-zone placeholders like {{name}} are preserved."""
    template_with_data_vars = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{name}} - CV</title>
  <style>
    body { font-family:{{body_font}}; }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
  <div style="display:flex;flex:1 0 auto;">
    {{main}}
  </div>
</div>
</body>
</html>'''
    
    layout_config = {
        "zones": [{"id": "main", "row": 0, "styles": {"width": "100%"}}],
        "placement": {"profile": "main", "experience": "main"},
    }
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES,
        CUSTOMIZATIONS,
        template_with_data_vars,
        layout_config,
        DEFAULT_CUSTOMIZATIONS
    )
    
    # Data variables should be preserved
    assert "{{name}}" in html
    # Zone placeholders should be replaced
    assert "{{main}}" not in html


def test_user_template_empty_zone_handled():
    """Test that zones with no assigned sections are handled gracefully."""
    template = generate_test_html_with_zones()
    
    # Only profile instance - experience, education, skills not included
    partial_instances = [SAMPLE_INSTANCES[0]]
    
    html = render_user_template_unified(
        partial_instances,
        CUSTOMIZATIONS,
        template,
        LAYOUT_CONFIG_TWO_ZONES,
        DEFAULT_CUSTOMIZATIONS
    )
    
    assert "{{sidebar}}" not in html
    assert "{{main}}" not in html
    assert "Jane Doe" in html
    # Main zone should be present but empty (or with empty div)
    # The renderer should not crash


def test_user_template_returns_full_html_document():
    """Test that the output is a complete HTML document."""
    layout_template = generate_test_html_with_zones()
    
    html = render_user_template_unified(
        SAMPLE_INSTANCES,
        CUSTOMIZATIONS,
        layout_template,
        LAYOUT_CONFIG_TWO_ZONES,
        DEFAULT_CUSTOMIZATIONS
    )
    
    # Should be a full HTML document
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "<html" in html
    assert "<head>" in html
    assert "<body>" in html
    assert "</html>" in html
    assert "{{print_styles}}" not in html  # Replaced
    assert "{{body_font}}" not in html  # Replaced
    assert "{{heading_font}}" not in html  # Replaced