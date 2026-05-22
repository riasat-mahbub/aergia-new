"""Profile renderer: template-aware HTML with CSS-var fallbacks."""

from app.services.renderer.section_renderers.profile import render_profile


def _ctx(**overrides):
    base = {"body_font": "system-ui, sans-serif", "heading_font": "Inter, sans-serif", "css_vars": {}}
    base.update(overrides)
    return base


def test_profile_empty_fields_renders_fallback_name():
    html = render_profile({}, _ctx())
    assert "Your Name" in html
    assert "<h2" in html
    assert "font-weight:700" in html


def test_profile_without_photo_does_not_emit_img():
    html = render_profile({"name": "Alice"}, _ctx())
    assert "<img" not in html
    assert "Alice" in html


def test_profile_without_summary_omits_summary_paragraph():
    html = render_profile({"name": "Alice", "title": "Engineer"}, _ctx())
    assert "Engineer" in html
    # No standalone summary paragraph (only the contact/title blocks).
    assert html.count("<p") == 1


def test_profile_uses_heading_font_from_context():
    html = render_profile({"name": "Alice"}, _ctx(heading_font="Georgia, serif"))
    assert "font-family:Georgia, serif" in html


def test_profile_uses_css_var_for_accent_color():
    html = render_profile({"title": "Engineer"}, _ctx(css_vars={"--accent": "#ff00aa"}))
    assert "var(--accent, #2563eb)" in html
    # The hex fallback is in the inline style, so the resolved color follows the CSS var at runtime.
    assert "#ff00aa" not in html  # the actual color comes from the var; only the fallback hex lives in the style


def test_profile_name_size_uses_css_var_when_provided():
    html = render_profile({"name": "Alice"}, _ctx(css_vars={"--profile-name-size": "2.25rem"}))
    assert "font-size:2.25rem" in html


def test_profile_all_fields_render_in_order():
    html = render_profile(
        {
            "name": "Alice",
            "title": "Engineer",
            "email": "alice@example.com",
            "phone": "555-1234",
            "location": "Berlin",
            "summary": "Loves building things.",
            "photo_url": "https://example.com/a.jpg",
        },
        _ctx(),
    )
    img_pos = html.find("<img")
    name_pos = html.find("Alice")
    title_pos = html.find("Engineer")
    contact_pos = html.find("alice@example.com")
    summary_pos = html.find("Loves building things.")
    assert 0 <= img_pos < name_pos < title_pos < contact_pos < summary_pos
