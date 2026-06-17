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
    # Name is rendered as a plain <div class="f-name"> (not <h2>) so the
    # UA-default heading line-height doesn't visually inflate the gap to
    # the row below.
    assert '<div class="f-name"' in html
    assert "<h2" not in html
    assert 'class="f-name"' in html

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
    assert 'class="f-name"' in html

def test_profile_all_fields_render_in_order():
    html = render_profile(
        {
            "name": "Alice",
            "title": "Engineer",
            "email": "alice@example.com",
            "phone": "555-1234",
            "location": "Berlin",
            "site_text": "My Site",
            "site_url": "https://example.com",
            "summary": "Loves building things.",
            "photo_url": "https://example.com/a.jpg",
        },
        _ctx(),
    )
    img_pos = html.find("<img")
    name_pos = html.find("Alice")
    title_pos = html.find("Engineer")
    contact_pos = html.find("alice@example.com")
    location_pos = html.find("Berlin")
    site_pos = html.find("My Site")
    summary_pos = html.find("Loves building things.")
    assert 0 <= img_pos < name_pos < title_pos < contact_pos < location_pos < site_pos < summary_pos


def test_profile_email_renders_as_mailto_link_by_default():
    html = render_profile({"email": "a@b.com"}, _ctx())
    assert 'href="mailto:a@b.com"' in html
    assert 'class="f-contact f-email"' in html
    assert '>a@b.com</a>' in html
    assert '<span class="f-contact f-email">a@b.com</span>' not in html

def test_profile_email_renders_plain_when_toggle_off():
    html = render_profile({"email": "a@b.com", "email_link": False}, _ctx())
    assert '<span class="f-contact f-email">a@b.com</span>' in html
    assert "mailto:" not in html


def test_profile_email_link_inactive_when_email_blank():
    html = render_profile({"email": ""}, _ctx())
    assert "mailto:" not in html
    assert "<a" not in html


def test_profile_site_url_only_renders_url_as_text():
    html = render_profile({"site_url": "https://x.dev"}, _ctx())
    assert 'href="https://x.dev"' in html
    assert ">https://x.dev</a>" in html


def test_profile_site_text_takes_precedence_when_set():
    html = render_profile(
        {"site_url": "https://x.dev", "site_text": "My Site"}, _ctx()
    )
    assert ">My Site</a>" in html
    assert ">https://x.dev</a>" not in html


def test_profile_email_unchanged_when_old_data_has_no_toggle():
    html = render_profile({"email": "a@b.com"}, _ctx())
    assert 'href="mailto:a@b.com"' in html



# --- Per-section row_gap override (Profile) -----------------------


def test_profile_row_gap_override_wins_over_css_var():
    """When instance_style.row_gap is set, the profile row wrapper uses
    the override verbatim — not the --row-gap CSS var, not the per-renderer
    default.
    """
    html = render_profile(
        {"name": "Alice", "title": "Engineer"},
        _ctx(css_vars={"--row-gap": "8px"}, instance_style={"row_gap": "16px"}),
    )
    assert "gap:16px" in html
    assert "gap:8px" not in html
    assert "var(--row-gap" not in html


def test_profile_row_gap_falls_through_to_css_var_when_unset():
    """When instance_style.row_gap is absent, the wrapper uses the
    --row-gap CSS var verbatim.
    """
    html = render_profile(
        {"name": "Alice"},
        _ctx(css_vars={"--row-gap": "12px"}),
    )
    assert "gap:12px" in html
    assert "var(--row-gap" not in html


def test_profile_row_gap_uses_default_when_no_var_and_no_override():
    """When both instance_style.row_gap and --row-gap are missing, the
    per-renderer default kicks in (8px). Defensive fallback.
    """
    html = render_profile({"name": "Alice"}, _ctx())
    assert "gap:8px" in html