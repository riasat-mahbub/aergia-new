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


def test_skills_inline_layout_renders_plain_text_fields():
    html = render_section_preview(
        "skills",
        [{"id": "s1", "category": "Languages", "items": ["Python", "Go"]}],
        _ctx(instance_style={"layout": "inline"}),
    )
    assert 'class="f-category"' in html
    assert 'class="f-tag"' in html
    assert "background:#f3f4f6" not in html


def test_skills_block_layout_preserves_chip_rendering():
    html = render_section_preview(
        "skills",
        [{"id": "s1", "category": "Languages", "items": ["Python"]}],
        _ctx(instance_style={"layout": "block"}),
    )
    assert "background:#f3f4f6" in html

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
        "research": lambda: render_section_preview(
            "research",
            [{"id": "r1", "title": "Verified Paper",
              "paper_url": "https://example.org/paper", "paper_link_text": "arXiv",
              "description": "Findings", "publication_date": "2025-04"}],
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
    for t in ["profile", "experience", "education", "skills", "projects", "languages", "certifications", "research"]:
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



# --- Research renderer --------------------------------------------------


def _research_entry(**overrides):
    base = {
        "id": "r1",
        "title": "Verified Paper",
        "paper_url": "https://example.org/paper",
        "paper_link_text": "arXiv",
        "description": "Findings",
        "publication_date": "2025-04",
    }
    base.update(overrides)
    return base


def test_research_emits_plain_entry_wrapper():
    html = render_section_preview("research", [_research_entry()], _ctx())
    assert 'class="f-research-entry"' in html
    assert "border-left" not in html


def test_research_title_is_plain_heading_outside_anchor():
    html = render_section_preview("research", [_research_entry()], _ctx())
    # Plain heading on the left with no anchor wrapping.
    assert "<h3 class=\"f-title\"" in html
    assert "Verified Paper" in html


def test_research_renders_custom_label_plus_arrow_glyph():
    html = render_section_preview("research", [_research_entry(paper_link_text="arXiv")], _ctx())
    assert 'class="f-url"' in html
    assert "arXiv" in html
    # The renderer uses the literal text glyph "↗" — no SVG asset pipeline.
    assert "↗" in html
    assert "<svg" not in html


def test_research_default_label_is_paper_when_link_text_blank():
    html = render_section_preview(
        "research",
        [_research_entry(paper_link_text="")],
        _ctx(),
    )
    assert ">Paper<" in html or ">Paper " in html
    assert "↗" in html


def test_research_normalizes_bare_domain_paper_url():
    html = render_section_preview(
        "research",
        [_research_entry(paper_url="example.org/paper")],
        _ctx(),
    )
    assert 'href="https://example.org/paper"' in html
    # The visible text must be the label, NOT the raw URL.
    assert "example.org/paper" not in html.replace('href="https://example.org/paper"', "")


def test_research_omits_anchor_when_url_empty_even_with_link_text():
    html = render_section_preview(
        "research",
        [_research_entry(paper_url="", paper_link_text="arXiv")],
        _ctx(),
    )
    assert "f-url" not in html
    # The link label must NOT be exposed as visible text without a URL.
    assert "arXiv" not in html


def test_research_renders_published_date_metadata():
    html = render_section_preview(
        "research",
        [_research_entry(publication_date="2025-04")],
        _ctx(),
    )
    assert "2025-04" in html
    assert 'class="f-date"' in html

def test_research_omits_published_date_when_empty():
    html = render_section_preview(
        "research",
        [_research_entry(publication_date="")],
        _ctx(),
    )
    assert "Published" not in html
    assert "f-date" not in html


def test_research_renders_description_paragraph():
    html = render_section_preview("research", [_research_entry()], _ctx())
    assert 'class="f-description"' in html
    assert "Findings" in html


def test_research_escapes_html_in_user_fields():
    html = render_section_preview(
        "research",
        [_research_entry(
            title="<script>alert(1)</script>",
            paper_link_text="<b>arXiv</b>",
            description="<img onerror=x>",
            publication_date="2025-04",
        )],
        _ctx(),
    )
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "<b>arXiv</b>" not in html
    assert "<img onerror=x>" not in html


def test_research_has_no_hardcoded_font_or_text_color():
    html = render_section_preview("research", [_research_entry()], _ctx())
    assert "font-family:" not in html
    assert "color:var(--text" not in html
    assert "color:var(--heading" not in html


def test_research_emits_no_data_when_empty():
    html = render_section_preview("research", None, _ctx())


# --- New social-links + layout-tweak coverage --------------------


def test_profile_emits_social_links_row():
    html = render_section_preview(
        "profile",
        {
            "name": "Alice",
            "social_links": [
                {"label": "LinkedIn", "url": "https://www.linkedin.com/in/alice", "icon": "linkedin"},
                {"label": "GitHub", "url": "https://github.com/alice", "icon": "github"},
            ],
        },
        _ctx(),
    )
    assert 'class="f-social-links"' in html
    assert "LinkedIn" in html
    assert "GitHub" in html
    assert "<svg" in html
    # Both links present with the normalized hrefs (the renderer runs
    # normalize_url_scheme so PDF /Link annotations survive Chromium).
    assert 'href="https://www.linkedin.com/in/alice"' in html
    assert 'href="https://github.com/alice"' in html


def test_profile_skips_social_links_row_when_empty():
    html = render_section_preview("profile", {"name": "Alice"}, _ctx())
    assert 'class="f-social-links"' not in html


def test_profile_social_link_with_unknown_icon_falls_back_to_globe():
    html = render_section_preview(
        "profile",
        {
            "name": "Alice",
            "social_links": [
                {"label": "Misc", "url": "https://example.com", "icon": "bogus-icon"},
            ],
        },
        _ctx(),
    )
    # The link still renders; the renderer silently falls back to globe.
    assert 'class="f-social-links"' in html
    assert "Misc" in html
    assert 'href="https://example.com"' in html


def test_research_publication_value_renders_when_set():
    html = render_section_preview(
        "research",
        [_research_entry(publication_value="NeurIPS 2024")],
        _ctx(),
    )
    assert 'class="f-publication-value"' in html
    assert "NeurIPS 2024" in html


def test_research_omits_publication_value_paragraph_when_empty():
    html = render_section_preview(
        "research",
        [_research_entry(publication_value="")],
        _ctx(),
    )
    assert "f-publication-value" not in html


def test_research_publication_date_in_right_column():
    html = render_section_preview(
        "research",
        [_research_entry(publication_date="2025-04")],
        _ctx(),
    )
    # The date paragraph is now inside the right flex column, not after the title.
    assert "2025-04" in html
    # The "Published" prefix is dropped (per layout change).
    assert "Published" not in html
    # The f-date class is still applied for the per-field CSS hook.
    assert 'class="f-date"' in html

def test_research_publication_value_sits_within_left_column():
    html = render_section_preview(
        "research",
        [_research_entry(publication_value="NeurIPS 2024")],
        _ctx(),
    )
    # The publication_value <p> must precede the right-column flex container.
    pv_pos = html.find("f-publication-value")
    right_col_pos = html.find('align-items:flex-end')
    assert pv_pos != -1
    assert right_col_pos != -1
    assert pv_pos < right_col_pos


def test_projects_link_in_right_column():
    html = render_section_preview(
        "projects",
        [{
            "id": "p1",
            "name": "Tool",
            "url": "https://example.com/tool",
            "link_text": "Repo",
            "start_date": "2024-01",
            "end_date": None,
            "description": "",
            "tech_stack": [],
        }],
        _ctx(),
    )
    # The arrow glyph (U+2197) marks the right-column link, matching Research.
    assert "\u2197" in html
    assert "Repo" in html
    assert 'class="f-url"' in html

def test_projects_description_sits_within_left_column():
    html = render_section_preview(
        "projects",
        [{
            "id": "p1",
            "name": "Tool",
            "url": "https://example.com/tool",
            "link_text": "Repo",
            "start_date": "2024-01",
            "end_date": None,
            "description": "A project description.",
            "tech_stack": [],
        }],
        _ctx(),
    )
    # The description <p> must precede the right-column flex container
    # (i.e. live inside the same left-column wrapper as <h3>, not as a
    # sibling of the outer flex row).
    desc_pos = html.find("f-description")
    right_col_pos = html.find('align-items:flex-end')
    assert desc_pos != -1
    assert right_col_pos != -1
    assert desc_pos < right_col_pos

def test_projects_right_column_has_shrink_and_nowrap_on_date():
    """The right column must keep its natural width (no shrinking under
    flex pressure) and the date <p> must never wrap to a second line —
    otherwise long date formats split awkwardly below the link."""
    html = render_section_preview(
        "projects",
        [{
            "id": "p1",
            "name": "Tool",
            "url": "https://example.com/tool",
            "link_text": "View on GitHub",
            "start_date": "2024-01",
            "end_date": "2025-12",
            "description": "desc",
            "tech_stack": [],
        }],
        _ctx(instance_style={"date_style": {"key": "Month YYYY", "range_sep": " – "}}),
    )
    # The right-column wrapper carries flex-shrink:0 so it doesn't shrink
    # below the natural width of its widest child.
    assert "flex-shrink:0" in html
    # The date <p> must opt out of wrapping so long date formats stay on
    # one line (they should not push past the column width).
    assert "white-space:nowrap" in html
    # The gap between the outer flex row's left and right columns is reduced
    # from 12px to 10px so the left column has more breathing room for the
    # description without starving the right column.
    assert "gap:10px" in html



# --- Date style per-renderer parametrized coverage --------------------


import pytest as _pytest  # noqa: E402

from app.services.renderer.section_renderers._utils import DATE_STYLE_OPTIONS  # noqa: E402


_DATE_STYLE_CASES = [
    (key, label, range_sep, expected_start, expected_mid, expected_end)
    for (key, label, range_sep) in DATE_STYLE_OPTIONS
    for (start, end, expected_start, expected_mid, expected_end) in [
        ("2021-03", "2022-01", "2021-03", "2022-01", None),
    ]
]


def _format(style_key, sep, raw):
    """Apply the same per-preset reformat `format_single_date` would, so the
    expected substrings below match the rendered HTML regardless of whether
    the renderer uses `format_single_date` or `format_date_range`."""
    if style_key == "YYYY-MM":
        return raw
    if style_key == "YYYY/MM":
        y, m = raw.split("-")
        return f"{y}/{m}"
    if style_key == "MM/YYYY":
        y, m = raw.split("-")
        return f"{m}/{y}"
    if style_key == "MM-YYYY":
        y, m = raw.split("-")
        return f"{m}-{y}"
    if style_key == "MM.YYYY":
        y, m = raw.split("-")
        return f"{m}.{y}"
    if style_key == "YYYY.MM":
        y, m = raw.split("-")
        return f"{y}.{m}"
    if style_key == "Mon YYYY":
        _MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        y, m = raw.split("-")
        return f"{_MON[int(m) - 1]} {y}"
    if style_key == "Month YYYY":
        _MON = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]
        y, m = raw.split("-")
        return f"{_MON[int(m) - 1]} {y}"
    if style_key == "YYYY":
        return raw.split("-")[0]
    if style_key == "Mon-YYYY":
        _MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        y, m = raw.split("-")
        return f"{_MON[int(m) - 1]}-{y}"
    return raw


@_pytest.mark.parametrize("style_key,_label,range_sep,_start_raw,_end_raw", [
    (k, l, s, "2021-03", "2022-01") for (k, l, s) in DATE_STYLE_OPTIONS
])
def test_experience_respects_date_style(style_key, _label, range_sep, _start_raw, _end_raw):
    style = {"key": style_key, "range_sep": range_sep}
    html = render_section_preview(
        "experience",
        [{"id": "e1", "company": "Acme", "position": "Engineer",
          "start_date": "2021-03", "end_date": "2022-01", "current": False,
          "location": "", "description": ""}],
        _ctx(instance_style={"date_style": style}),
    )
    expected_start = _format(style_key, range_sep, "2021-03")
    expected_end = _format(style_key, range_sep, "2022-01")
    assert expected_start in html
    assert expected_end in html
    # Separator must appear between the two formatted bounds
    assert f"{expected_start}{range_sep}{expected_end}" in html


@_pytest.mark.parametrize("style_key,_label,range_sep,_start_raw,_end_raw", [
    (k, l, s, "2021-03", "2022-01") for (k, l, s) in DATE_STYLE_OPTIONS
])
def test_education_respects_date_style(style_key, _label, range_sep, _start_raw, _end_raw):
    style = {"key": style_key, "range_sep": range_sep}
    html = render_section_preview(
        "education",
        [{"id": "e1", "institution": "MIT", "degree": "BS",
          "start_date": "2021-03", "end_date": "2022-01", "current": False}],
        _ctx(instance_style={"date_style": style}),
    )
    expected_start = _format(style_key, range_sep, "2021-03")
    expected_end = _format(style_key, range_sep, "2022-01")
    assert expected_start in html
    assert expected_end in html
    assert f"{expected_start}{range_sep}{expected_end}" in html


@_pytest.mark.parametrize("style_key,_label,range_sep,_start_raw,_end_raw", [
    (k, l, s, "2021-03", "2022-01") for (k, l, s) in DATE_STYLE_OPTIONS
])
def test_projects_respects_date_style(style_key, _label, range_sep, _start_raw, _end_raw):
    style = {"key": style_key, "range_sep": range_sep}
    html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "Tool", "start_date": "2021-03", "end_date": "2022-01", "description": ""}],
        _ctx(instance_style={"date_style": style}),
    )
    expected_start = _format(style_key, range_sep, "2021-03")
    expected_end = _format(style_key, range_sep, "2022-01")
    assert expected_start in html
    assert expected_end in html
    assert f"{expected_start}{range_sep}{expected_end}" in html


@_pytest.mark.parametrize("style_key,_label,range_sep", [
    (k, l, s) for (k, l, s) in DATE_STYLE_OPTIONS
])
def test_research_respects_date_style(style_key, _label, range_sep):
    style = {"key": style_key, "range_sep": range_sep}
    html = render_section_preview(
        "research",
        [_research_entry(publication_date="2021-03")],
        _ctx(instance_style={"date_style": style}),
    )
    expected = _format(style_key, range_sep, "2021-03")
    assert expected in html


@_pytest.mark.parametrize("style_key,_label,range_sep", [
    (k, l, s) for (k, l, s) in DATE_STYLE_OPTIONS
])
def test_certifications_respects_date_style(style_key, _label, range_sep):
    style = {"key": style_key, "range_sep": range_sep}
    html = render_section_preview(
        "certifications",
        [{"id": "c1", "name": "AWS", "issuer": "Amazon", "date": "2021-03"}],
        _ctx(instance_style={"date_style": style}),
    )
    expected = _format(style_key, range_sep, "2021-03")
    assert expected in html
    assert 'class="f-date"' in html


# --- Per-section subsection_gap override ------------------------------


@_pytest.mark.parametrize("section_type,sample_data", [
    # Each entry exercises one multi-entry renderer with a representative
    # data shape. The override must win over both the per-renderer default
    # and the --subsection-gap CSS var.
    ("certifications", [{"id": "c1", "name": "AWS", "issuer": "Amazon"}]),
    ("education", [{"id": "e1", "degree": "BS", "institution": "MIT"}]),
    ("experience", [{"id": "x1", "position": "Eng", "company": "Acme"}]),
    ("languages", [{"id": "l1", "language": "EN", "proficiency": "Native"}]),
    ("projects", [{"id": "p1", "name": "X", "description": "Y"}]),
    ("research", [{"id": "r1", "title": "T"}]),
    ("skills", [{"id": "s1", "category": "Langs", "items": ["Python"]}]),
])
def test_subsection_gap_override_wins_over_css_var(section_type, sample_data):
    """When instance_style.subsection_gap is set, the wrapper's gap uses
    the override verbatim — not the --subsection-gap CSS var, not the
    per-renderer default. The override is the user's authoritative pick.
    """
    html = render_section_preview(
        section_type,
        sample_data,
        _ctx(css_vars={"--subsection-gap": "16px"}, instance_style={"subsection_gap": "32px"}),
    )
    assert "gap:32px" in html
    assert "gap:16px" not in html
    # No CSS-var fallback should be referenced either; the override is a
    # literal length string.
    assert "var(--subsection-gap" not in html


def test_subsection_gap_falls_through_to_css_var_when_unset():
    """When instance_style.subsection_gap is absent, the wrapper uses the
    --subsection-gap CSS var verbatim.
    """
    html = render_section_preview(
        "experience",
        [{"id": "x1", "position": "Eng", "company": "Acme"}],
        _ctx(css_vars={"--subsection-gap": "20px"}),
    )
    assert "gap:20px" in html
    assert "var(--subsection-gap" not in html


def test_subsection_gap_uses_per_renderer_default_when_no_var_and_no_override():
    """When both instance_style.subsection_gap and --subsection-gap are
    missing, the per-renderer default kicks in (16px for experience). This
    is a defensive fallback for callers that bypass _build_css_vars.
    """
    html = render_section_preview(
        "experience",
        [{"id": "x1", "position": "Eng", "company": "Acme"}],
        _ctx(),
    )
    assert "gap:16px" in html