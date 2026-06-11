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
    # The experience instance has no links/photo, so no var(--accent) escapes.
    # The profile is the first instance in the output; the experience block
    # starts at "Did things." and runs to the end.
    experience_block = html[html.find("Did things."):]
    assert "color:var(--accent" not in experience_block
    # The profile email renders as a clickable mailto link with the accent
    # color — this is an intentional design point, not a cascade bug.
    assert 'href="mailto:jane@x.com"' in html


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
def test_section_heading_underline_when_flag_true():
    """With the `underline_section_titles` flag on, the heading style gets a border-bottom."""
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        # Use a profile instance with the title explicitly shown so the h2 emits.
        {"instances": [{**SAMPLE[0], "style": {"show_title": True}}, SAMPLE[1]]},
        {
            "colors": {"text": "#222", "heading": "#111"},
            "fonts": {"body": "Inter", "heading": "Inter"},
            "flags": {"underline_section_titles": True},
        },
    )
    html = HTMLBackend()._format(ir)
    assert "border-bottom:1px solid var(--heading" in html
    # The rule lands inside the section heading <h2>, not elsewhere.

    h2_blocks = [seg for seg in html.split("<h2") if "border-bottom:1px solid var(--heading" in seg]
    assert h2_blocks, "expected border-bottom rule inside at least one <h2> heading element"


def test_section_heading_no_underline_when_flag_false_or_missing():
    """The default (no flag or flag=false) leaves the heading style untouched."""
    base = _manifest([{"id": "main", "styles": {"width": "100%"}}])
    instances = {"instances": [SAMPLE[0], SAMPLE[1]]}  # experience shows its title

    ir_missing = build_ir(
        base,
        instances,
        {"colors": {"text": "#222", "heading": "#111"},
         "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html_missing = HTMLBackend()._format(ir_missing)
    h2_blocks = [seg for seg in html_missing.split("<h2") if "border-bottom" in seg]
    assert h2_blocks == [], "no heading should carry border-bottom when the flag is unset"

    ir_false = build_ir(
        base,
        instances,
        {"colors": {"text": "#222", "heading": "#111"},
         "fonts": {"body": "Inter", "heading": "Inter"},
         "flags": {"underline_section_titles": False}},
    )
    html_false = HTMLBackend()._format(ir_false)
    h2_blocks = [seg for seg in html_false.split("<h2") if "border-bottom" in seg]
    assert h2_blocks == [], "no heading should carry border-bottom when the flag is false"


def test_underline_flag_uses_heading_color():
    """The border-bottom references var(--heading) so the heading color drives the underline."""
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": [{**SAMPLE[0], "style": {"show_title": True}}, SAMPLE[1]]},
        {
            "colors": {"text": "#222", "heading": "#ff0000"},
            "fonts": {"body": "Inter", "heading": "Inter"},
            "flags": {"underline_section_titles": True},
        },
    )
    html = HTMLBackend()._format(ir)
    h2_blocks = [seg for seg in html.split("<h2") if "border-bottom:1px solid var(--heading" in seg]
    assert h2_blocks, "expected the underline rule on a heading <h2>"
    # The visual cascade contract: the rule stays on the CSS var (the browser
    # resolves it at render time, so we only assert the reference).
    assert h2_blocks[0].count("var(--heading") >= 1
def test_default_link_style_off_renders_plain_anchors():
    """With the flag off (default), the HTML backend emits no anchor styling rule.

    Anchors blend in with surrounding text; they get no accent color and no
    underline from the global stylesheet. The existing per-renderer test in
    test_section_renderers.py covers the inline-style side; this covers the
    CSS-rule side.
    """
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": [SAMPLE[0]]},
        {
            "colors": {"text": "#222", "heading": "#111"},
            "fonts": {"body": "Inter", "heading": "Inter"},
        },
    )
    html = HTMLBackend()._format(ir)
    assert "a { color: var(--accent" not in html
    assert "text-decoration: underline" not in html
    # The off-state still emits a global rule to suppress the UA default underline
    # and force link color to inherit from the wrapper.
    assert "a { color: inherit" in html
    assert "text-decoration: none" in html


def test_default_link_style_on_emits_anchor_rule():
    """With the flag on, the backend emits the global anchor rule exactly once."""
    ir = build_ir(
        _manifest([{"id": "main", "styles": {"width": "100%"}}]),
        {"instances": [SAMPLE[0]]},
        {
            "colors": {"text": "#222", "heading": "#111"},
            "fonts": {"body": "Inter", "heading": "Inter"},
            "flags": {"default_link_style": True},
        },
    )
    html = HTMLBackend()._format(ir)
    expected = "a { color: var(--accent, #2563eb); text-decoration: underline; }"
    assert html.count(expected) == 1
    # Rule sits inside the <style> block.
    style_block = html.split("<style>")[1].split("</style>")[0]
    assert expected in style_block


def test_default_link_style_default_is_off():
    """A template seeded with default_link_style=False emits no anchor rule
    when the user has no override."""
    manifest = _manifest([{"id": "main", "styles": {"width": "100%"}}])
    manifest["default_customizations"] = {
        "flags": {"default_link_style": False}
    }
    ir = build_ir(
        manifest,
        {"instances": [SAMPLE[0]]},
        {"colors": {"text": "#222"}, "fonts": {"body": "Inter", "heading": "Inter"}},
    )
    html = HTMLBackend()._format(ir)
    assert "a { color: var(--accent" not in html


def test_default_link_style_seed_off_overridden_by_user_true():
    """User override wins over seed default: a True user override emits the rule
    even when the template seeds default_link_style=False."""
    manifest = _manifest([{"id": "main", "styles": {"width": "100%"}}])
    manifest["default_customizations"] = {
        "flags": {"default_link_style": False}
    }
    ir = build_ir(
        manifest,
        {"instances": [SAMPLE[0]]},
        {
            "colors": {"text": "#222"},
            "fonts": {"body": "Inter", "heading": "Inter"},
            "flags": {"default_link_style": True},
        },
    )
    html = HTMLBackend()._format(ir)
    assert "a { color: var(--accent, #2563eb); text-decoration: underline; }" in html
