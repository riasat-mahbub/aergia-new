"""Regression tests for per-section style cascading and zone column layout.

Covers:
- zones are rendered as side-by-side columns (the wrap is flex-direction:row).
- per-section color and font cascade to every descendant via the wrapper.
- the global --text color and body/heading fonts apply across the document.
- show_title controls the section heading; profile hides it by default.
"""

from app.services.renderer.ir import _build_section_panel, build_ir
from app.services.renderer.backends.html import HTMLBackend


SAMPLE = [
    {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Jane Doe", "title": "Engineer", "email": "jane@x.com",
                 "phone": "555", "location": "Berlin", "summary": "Hello.",
                 "photo_url": ""},
    },
    {
        "id": "sec_experience",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"id": "exp1", "company": "Acme", "position": "Engineer",
             "start_date": "2020", "end_date": None, "current": True,
             "location": "Berlin", "description": "Did things."}
        ],
    },
]


def _manifest(zones, placement=None):
    return {
        "zones": zones,
        "layout_config": {
            "zones": zones,
            "placement": placement or {sec["id"]: zones[0]["id"] for sec in SAMPLE},
        },
    }


def test_zones_wrap_is_flex_row_with_columns():
    """The zone container is flex-direction:row so zones render side-by-side."""
    ir = build_ir(
        _manifest(
            [
                {"id": "a", "styles": {"width": "30%", "background-color": "#eee", "padding": "24px"}},
                {"id": "b", "styles": {"width": "70%", "padding": "24px"}},
            ]
        ),
        {"instances": SAMPLE},
        {"colors": {"text": "#222", "heading": "#111", "accent": "#06f"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir)
    assert "flex-direction:row" in html
    # Both zones sit in the document with their widths so they render as columns.
    assert 'width:30%' in html
    assert 'width:70%' in html


def test_body_picks_up_global_text_color():
    """The global --text CSS var flows into body so unset text inherits it."""
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": SAMPLE},
        {"colors": {"text": "#abcdef", "heading": "#111", "accent": "#06f"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir)
    assert "--text: #abcdef" in html
    # The body element itself uses the CSS var so the color cascades.
    assert "color: var(--text" in html


def test_per_section_color_cascades_to_all_children():
    """A per-section color reaches the section heading AND its body text."""
    ir2 = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": [{**SAMPLE[0], "style": {"color": "#ff00aa",
                                              "show_title": True}}, SAMPLE[1]]},
        {"colors": {"text": "#222", "heading": "#111", "accent": "#06f"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir2)
    # The wrapper carries the per-section color.
    assert "color:#ff00aa" in html
    # No child element should hardcode var(--text); the wrapper's color cascades.
    assert "color:var(--text" not in html
    # var(--heading) is the template default for the section heading (which
    # then inherits the per-section color via the wrapper).
    assert "color:var(--heading" in html
    # No child inline `color:` override at all on body text (the bug).
    assert html.count("color:var(--accent") == 0  # experience has no links/photo


def test_per_section_font_reaches_heading_and_body():
    """A per-section font reaches both the section heading and the body text."""
    # Use experience (which shows its heading by default) so both the wrapper
    # and the heading emit the per-section font.
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": [SAMPLE[0], {**SAMPLE[1], "style": {"font": "Georgia, serif"}}]},
        {"colors": {"text": "#222", "heading": "#111"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir)
    # The per-section font appears on BOTH the wrapper and the heading so the
    # global `h1...h6 { font-family: heading_font }` rule cannot override it.
    assert html.count("font-family:Georgia, serif") >= 2


def test_global_body_font_change_reaches_all_text():
    """Changing the body font updates every text element (was the font bug).

    Previously each section renderer baked `font-family:Inter` inline on every
    child, blocking the global body-font change from cascading in. With the
    renderers cleaned up, the only `font-family:Inter` references in the HTML
    are the global `body` and `h1...h6` rules.
    """
    ir = build_ir(_manifest([{"id": "main", "styles": {"width": "100%"}}]),
                  {"instances": SAMPLE},
                  {"colors": {"text": "#222", "heading": "#111"},
                   "fonts": {"body": "Inter, system-ui, sans-serif",
                             "heading": "Inter, system-ui, sans-serif"}})
    html = HTMLBackend()._format(ir)
    # The global body and heading font rules are present (in <style>).
    assert "font-family: Inter, system-ui, sans-serif" in html
    # The body font is set on the global body rule and the h1...h6 rule only —
    # not inline on any section child. Count the total occurrences.
    head = html.split("<body>")[0]
    assert head.count("font-family: Inter, system-ui, sans-serif") == 2
    # Inside the body, no child element bakes an inline font-family.
    body = html.split("<body>")[1]
    assert "font-family: Inter" not in body
    assert "font-family:Georgia" not in body  # neither the old broken inlines


def test_profile_hides_title_by_default():
    """Profile omits its heading unless the user explicitly opts in."""
    panel = _build_section_panel(
        {"id": "p", "type": "profile", "title": "Profile", "enabled": True,
         "data": {"name": "Jane"}},
        None,
    )
    assert panel.title == ""  # the empty title drops the heading from the output


def test_non_profile_section_shows_title_by_default():
    """Sections other than profile show their title unless explicitly hidden."""
    panel = _build_section_panel(
        {"id": "e", "type": "experience", "title": "Experience", "enabled": True,
         "data": [{"id": "x", "company": "Acme", "position": "Eng",
                   "start_date": "2020", "end_date": None, "current": True}]},
        None,
    )
    assert panel.title == "Experience"


def test_profile_shows_title_when_explicitly_enabled():
    panel = _build_section_panel(
        {"id": "p", "type": "profile", "title": "Profile", "enabled": True,
         "style": {"show_title": True},
         "data": {"name": "Jane"}},
        None,
    )
    assert panel.title == "Profile"


def test_non_profile_hides_title_when_explicitly_disabled():
    panel = _build_section_panel(
        {"id": "e", "type": "experience", "title": "Experience", "enabled": True,
         "style": {"show_title": False},
         "data": [{"id": "x", "company": "Acme", "position": "Eng",
                   "start_date": "2020", "end_date": None, "current": True}]},
        None,
    )
    assert panel.title == ""


def test_empty_title_skips_heading_html():
    """When a section title is empty, the wrapper emits no <h2> at all.

    The section renderer (e.g. profile) may emit its own internal h2 for the
    name; that one is unrelated to the section heading wrapper.
    """
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        # Profile explicitly hides its section heading; only the profile
        # renderer's internal h2 (the name) should remain.
        {"instances": [{**SAMPLE[0]}]},
        {"colors": {"text": "#222", "heading": "#111"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir)
    # The wrapper h2 with the section title is omitted.
    assert ">Profile<" not in html
    assert '>Profile</h2>' not in html
    # The profile name (an internal h2) is still emitted.
    assert ">Jane Doe<" in html
