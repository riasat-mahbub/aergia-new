"""Non-profile section renderers + dispatcher: template-aware HTML."""

from app.services.renderer.section_renderers import render_section_preview, SECTION_RENDERERS


def _ctx(**overrides):
    base = {
        "body_font": "Inter, system-ui, sans-serif",
        "heading_font": "Georgia, serif",
        "css_vars": {
            "--accent": "#0a7",
            "--text": "#222",
            "--heading": "#111",
        },
    }
    base.update(overrides)
    return base


def test_dispatcher_forwards_context_to_renderer():
    """When a context is supplied, the dispatched renderer sees it."""
    # The profile renderer inlines the heading font in the h2 style.
    html = render_section_preview("profile", {"name": "Alice"}, _ctx(heading_font="Verdana"))
    assert "Verdana" in html


def test_dispatcher_unknown_type_raises():
    import pytest

    with pytest.raises(ValueError):
        render_section_preview("not-a-type", {})


def test_dispatcher_accepts_missing_context():
    """Dispatching with context=None must not crash; renderers fall back to defaults."""
    html = render_section_preview("experience", [])
    assert "No data" in html or "<div" in html


def test_experience_uses_heading_font_and_css_vars():
    html = render_section_preview(
        "experience",
        [
            {
                "id": "exp1",
                "company": "Acme",
                "position": "Engineer",
                "start_date": "2020",
                "end_date": None,
                "current": True,
                "description": "Did things.",
            }
        ],
        _ctx(),
    )
    assert "Acme" in html
    assert "Engineer" in html
    assert "var(--heading" in html
    assert "var(--text" in html
    assert "Georgia, serif" in html


def test_education_uses_heading_font_and_css_vars():
    html = render_section_preview(
        "education",
        [{"id": "e1", "institution": "MIT", "degree": "BS", "start_date": "2018", "end_date": "2022", "current": False}],
        _ctx(),
    )
    assert "MIT" in html
    assert "var(--heading" in html
    assert "var(--text" in html


def test_skills_uses_css_vars_for_item_text():
    html = render_section_preview(
        "skills",
        [{"id": "s1", "category": "Languages", "items": ["Python", "Rust"]}],
        _ctx(),
    )
    assert "Python" in html
    assert "Rust" in html
    assert "var(--text" in html
    assert "var(--heading" in html


def test_projects_uses_css_vars_and_accent():
    html = render_section_preview(
        "projects",
        [
            {
                "id": "p1",
                "name": "CV Builder",
                "url": "https://example.com",
                "start_date": "2025",
                "end_date": None,
                "description": "Tooling",
            }
        ],
        _ctx(),
    )
    assert "CV Builder" in html
    assert "https://example.com" in html
    assert "var(--heading" in html


def test_languages_uses_heading_color_for_name():
    html = render_section_preview(
        "languages",
        [{"id": "l1", "language": "English", "proficiency": "Native"}],
        _ctx(),
    )
    assert "English" in html
    assert "var(--heading" in html


def test_certifications_uses_css_vars():
    html = render_section_preview(
        "certifications",
        [{"id": "c1", "name": "AWS Architect", "issuer": "Amazon", "date": "2024"}],
        _ctx(),
    )
    assert "AWS Architect" in html
    assert "Amazon" in html
    assert "var(--heading" in html


def test_all_section_types_registered():
    for t in ["profile", "experience", "education", "skills", "projects", "languages", "certifications"]:
        assert t in SECTION_RENDERERS
