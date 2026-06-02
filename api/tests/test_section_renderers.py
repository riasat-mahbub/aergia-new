"""Section renderers + dispatcher: template-aware HTML with cascading styles.

The per-section color and font live on the wrapper, so child elements must NOT
hardcode inline `color:var(--xxx)` or `font-family:xxx` styles — those would
override the wrapper's cascade and make per-section styles ineffective.
"""

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
    """The dispatcher must always pass context (even if the renderer ignores it)."""
    # Renderers no longer inline the font — they rely on the wrapper (set by
    # _build_section_panel) to carry the per-section color and font.
    html = render_section_preview("profile", {"name": "Alice"}, _ctx(heading_font="Verdana"))
    assert "Alice" in html


def test_dispatcher_unknown_type_raises():
    import pytest

    with pytest.raises(ValueError):
        render_section_preview("not-a-type", {})


def test_dispatcher_accepts_missing_context():
    """Dispatching with context=None must not crash; renderers fall back to defaults."""
    html = render_section_preview("experience", [])
    assert "No data" in html or "<div" in html


def test_renderers_emit_no_inline_color_or_font_in_body():
    """Section renderers must not hardcode inline color or font on body children.

    Per-section color and font are applied on the wrapper, so children should
    inherit. The only legitimate places to keep an inline color are the
    hyperlink accent and the contact separator (visual affordance, not text).
    """
    sample_html_by_type = {
        "experience": lambda: render_section_preview(
            "experience",
            [{"id": "exp1", "company": "Acme", "position": "Engineer",
              "start_date": "2020", "end_date": None, "current": True,
              "description": "Did things."}],
            _ctx(),
        ),
        "education": lambda: render_section_preview(
            "education",
            [{"id": "e1", "institution": "MIT", "degree": "BS",
              "start_date": "2018", "end_date": "2022", "current": False}],
            _ctx(),
        ),
        "skills": lambda: render_section_preview(
            "skills",
            [{"id": "s1", "category": "Languages", "items": ["Python"]}],
            _ctx(),
        ),
        "projects": lambda: render_section_preview(
            "projects",
            [{"id": "p1", "name": "CV Builder", "url": "https://example.com",
              "start_date": "2025", "end_date": None, "description": "Tooling"}],
            _ctx(),
        ),
        "languages": lambda: render_section_preview(
            "languages",
            [{"id": "l1", "language": "English", "proficiency": "Native"}],
            _ctx(),
        ),
        "certifications": lambda: render_section_preview(
            "certifications",
            [{"id": "c1", "name": "AWS Architect", "issuer": "Amazon", "date": "2024"}],
            _ctx(),
        ),
    }
    for t, render in sample_html_by_type.items():
        html = render()
        assert "font-family:" not in html, (
            f"{t} renderer bakes inline font-family; it should inherit from wrapper"
        )
        assert "color:var(--text" not in html, (
            f"{t} renderer bakes var(--text); it should inherit from wrapper"
        )
        assert "color:var(--heading" not in html, (
            f"{t} renderer bakes var(--heading); the section title can, but body text cannot"
        )


def test_projects_and_certifications_links_keep_accent():
    """Hyperlinks are visually distinct; keep the accent color on anchors only."""
    projects_html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "CV Builder", "url": "https://example.com",
          "start_date": "2025", "end_date": None}],
        _ctx(),
    )
    assert "var(--accent" in projects_html

    certs_html = render_section_preview(
        "certifications",
        [{"id": "c1", "name": "AWS", "issuer": "Amazon", "date": "2024",
          "credential_url": "https://example.com/cred"}],
        _ctx(),
    )
    assert "var(--accent" in certs_html


def test_all_section_types_registered():
    for t in ["profile", "experience", "education", "skills", "projects", "languages", "certifications"]:
        assert t in SECTION_RENDERERS
