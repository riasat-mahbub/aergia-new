"""Profile renderer: template-aware HTML with CSS-var fallbacks.

The wrapper carries the per-section color and font, so the renderer no longer
bakes inline colors or fonts on its children. Hyperlink and contact affordance
still use --accent / --divider CSS vars.
"""

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


def test_profile_does_not_inline_color_or_font_on_body():
    """The renderer must not hardcode color or font; the wrapper carries them."""
    html = render_profile(
        {"name": "Alice", "title": "Engineer", "summary": "Hello."},
        _ctx(heading_font="Georgia, serif", body_font="Helvetica, sans-serif"),
    )
    # Inline font-family and var(--xxx) colors must be gone from body children.
    assert "font-family:" not in html
    assert "color:var(--text" not in html
    assert "color:var(--heading" not in html
    # No more accent on the professional title — that was the haphazard part.
    assert "color:var(--accent" not in html


def test_profile_keeps_divider_on_separator():
    """The contact separator is a visual divider, not text; it keeps --divider."""
    html = render_profile(
        {"name": "Alice", "email": "a@b.com", "phone": "555"},
        _ctx(),
    )
    assert "var(--divider" in html


def test_profile_keeps_accent_on_photo_border():
    """The photo outline uses --accent so it tints with the template palette."""
    html = render_profile(
        {"name": "Alice", "photo_url": "https://example.com/a.jpg"},
        _ctx(),
    )
    assert "var(--accent" in html


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
