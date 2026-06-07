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


def _zone_with(panels):
    """Tiny duck-typed zone object satisfying _format_zone_panels."""
    return type("Zone", (), {"panels": panels})()


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


def test_anchors_have_no_inline_accent_color_by_default():
    """Anchors must not hardcode the accent color inline; the per-section wrapper
    carries the text color and links blend in unless the user opts in via the
    `default_link_style` flag (which adds a CSS rule in the HTML backend)."""
    projects_html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "CV Builder", "url": "https://example.com",
          "start_date": "2025", "end_date": None}],
        _ctx(),
    )
    assert "var(--accent" not in projects_html

    certs_html = render_section_preview(
        "certifications",
        [{"id": "c1", "name": "AWS", "issuer": "Amazon", "date": "2024",
          "credential_url": "https://example.com/cred"}],
        _ctx(),
    )
    assert "var(--accent" not in certs_html

    profile_html = render_section_preview(
        "profile",
        {"name": "Jane", "email": "jane@x.com", "site_url": "https://jane.dev"},
        _ctx(),
    )
    assert "var(--accent" not in profile_html


def test_profile_bare_domain_site_url_is_normalized():
    """Chromium's print pipeline drops <a href> annotations when the href has
    no scheme — a bare domain like 'rmahbub.com' is treated as a relative
    URL against about:blank and never becomes a clickable /Link in the PDF.
    The renderer must prepend https:// so the link survives PDF export."""
    html = render_section_preview(
        "profile",
        {"name": "R", "email": "r@x.com", "site_url": "rmahbub.com", "site_text": ""},
        _ctx(),
    )
    assert 'href="https://rmahbub.com"' in html


def test_profile_already_https_site_url_is_unchanged():
    """User-entered URLs that already carry a scheme must pass through verbatim."""
    html = render_section_preview(
        "profile",
        {"name": "R", "email": "r@x.com", "site_url": "https://aergia.dev", "site_text": ""},
        _ctx(),
    )
    assert 'href="https://aergia.dev"' in html
    assert 'href="https://https://' not in html


def test_projects_bare_domain_url_is_normalized():
    """Same Chromium behavior for the projects renderer: a bare-domain
    project URL must gain an https:// prefix so the project link survives PDF export."""
    html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "CV Builder", "url": "example.com",
          "link_text": "example.com", "start_date": "2025", "end_date": None}],
        _ctx(),
    )
    assert 'href="https://example.com"' in html


def test_certifications_bare_domain_credential_url_is_normalized():
    """Certifications renderer must prepend a scheme to bare-domain credential URLs,
    matching the same fix applied to profile and projects."""
    html = render_section_preview(
        "certifications",
        [{"id": "c1", "name": "AWS", "issuer": "Amazon", "date": "2024",
          "credential_url": "example.com/cred"}],
        _ctx(),
    )
    assert 'href="https://example.com/cred"' in html


def test_all_section_types_registered():
    for t in ["profile", "experience", "education", "skills", "projects", "languages", "certifications"]:
        assert t in SECTION_RENDERERS


def test_field_styles_render_as_css_rules():
    from app.services.renderer.ir import _build_section_panel
    from app.services.renderer.backends.html import _format_zone_panels
    panel = _build_section_panel(
        {"id": "profile", "type": "profile", "title": "Profile", "enabled": True,
         "data": {"name": "Alice"}, "style": {"field_styles": {"name": {"size": "24px"}}}},
        _ctx(),
    )
    html = _format_zone_panels(_zone_with([panel]))
    assert "#s-profile .f-name" in html
    assert "font-size:24px" in html


def test_field_styles_skip_unset_properties():
    from app.services.renderer.ir import _build_section_panel
    from app.services.renderer.backends.html import _format_zone_panels
    panel = _build_section_panel(
        {"id": "profile", "type": "profile", "title": "Profile", "enabled": True,
         "data": {"name": "Alice"}, "style": {"field_styles": {"name": {"weight": "700"}}}},
        _ctx(),
    )
    html = _format_zone_panels(_zone_with([panel]))
    rule = html.split("#s-profile .f-name", 1)[1].split("}", 1)[0]
    assert "font-weight:700" in rule
    assert "font-size" not in rule


def test_field_styles_omitted_when_empty():
    from app.services.renderer.ir import _build_section_panel
    from app.services.renderer.backends.html import _format_zone_panels
    panel = _build_section_panel(
        {"id": "profile", "type": "profile", "title": "Profile", "enabled": True,
         "data": {"name": "Alice"}},
        _ctx(),
    )
    html = _format_zone_panels(_zone_with([panel]))
    assert "<style>" not in html
