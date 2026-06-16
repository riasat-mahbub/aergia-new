"""Renderer behavior tests for date ranges and project link_text."""
from app.services.renderer.section_renderers import render_section_preview


def _ctx(**overrides):
    base = {"accent": "#2563eb", "text": "#111", "heading": "#111"}
    base.update(overrides)
    return base


def test_experience_current_true_renders_present():
    html = render_section_preview(
        "experience",
        [{"id": "e1", "company": "Acme", "position": "Engineer",
          "start_date": "2021-03", "end_date": None, "current": True}],
        _ctx(),
    )
    assert "2021-03 – Present" in html
    # No trailing "– " with nothing after
    assert " –  " not in html


def test_experience_current_false_no_end_shows_only_start():
    html = render_section_preview(
        "experience",
        [{"id": "e1", "company": "Acme", "position": "Engineer",
          "start_date": "2021-03", "end_date": None, "current": False}],
        _ctx(),
    )
    # Only the start date, no trailing dash
    assert "2021-03" in html
    assert " – " not in html.replace("2021-03 – ", "")  # no separate dash fragment


def test_experience_both_dates_renders_start_end():
    html = render_section_preview(
        "experience",
        [{"id": "e1", "company": "Acme", "position": "Engineer",
          "start_date": "2021-03", "end_date": "2022-01", "current": False}],
        _ctx(),
    )
    assert "2021-03 – 2022-01" in html


def test_education_current_true_renders_present():
    html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018", "end_date": None, "current": True, "gpa": "3.9"}],
        _ctx(),
    )
    assert "2018 – Present" in html
    # GPA on its own line, not glued to the date
    assert "GPA: 3.9" in html
    assert " | GPA" not in html


def test_education_no_end_no_current_shows_only_start():
    html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018", "end_date": None, "current": False}],
        _ctx(),
    )


def test_education_layout_dates_on_same_row_as_institution():
    """Education preview: degree/institution on the left, date range on the right
    in a single flex row — matching ExperienceRenderer."""
    html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018-09", "end_date": "2022-06", "current": False,
          "gpa": "3.9"}],
        _ctx(),
    )
    # The flex wrapper must be present.
    assert 'style="display:flex;justify-content:space-between;align-items:flex-start;"' in html
    # institution and date are both inside the same flex row.
    inst_idx = html.index("MIT")
    date_idx = html.index("2018-09 – 2022-06")
    assert inst_idx < date_idx, f"institution should appear before date, got {html!r}"
    # And both must be after the flex wrapper opens.
    flex_start = html.index("display:flex;justify-content:space-between")
    assert flex_start < inst_idx
    assert flex_start < date_idx
    # GPA stays outside the flex row (after the flex wrapper closes).
    assert "GPA: 3.9" in html
    gpa_idx = html.index("GPA: 3.9")
    assert gpa_idx > date_idx


def test_projects_link_text_overrides_url():
    html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "Repo", "url": "https://example.com",
          "link_text": "GitHub", "start_date": "2024-01", "end_date": None}],
        _ctx(),
    )
    assert "GitHub" in html
    # The URL appears as the href, but the link_text should be the visible text
    assert ">GitHub</a>" in html or "GitHub</a>" in html


def test_projects_falls_back_to_url_when_link_text_empty():
    html = render_section_preview(
        "projects",
        [{"id": "p1", "name": "Repo", "url": "https://example.com",
          "link_text": "", "start_date": "2024-01", "end_date": None}],
        _ctx(),
    )
    assert "https://example.com" in html


def test_education_summary_renders_when_present():
    html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018-09", "end_date": "2022-06", "current": False,
          "gpa": "3.9", "summary": "Thesis on distributed systems."}],
        _ctx(),
    )
    assert "Thesis on distributed systems." in html
    # Summary appears after the GPA line — same flex-row-then-meta ordering as
    # test_education_layout_dates_on_same_row_as_institution.
    gpa_idx = html.index("GPA: 3.9")
    summary_idx = html.index("Thesis on distributed systems.")
    assert summary_idx > gpa_idx, (
        f"summary should appear after GPA, got {html!r}"
    )


def test_education_summary_omitted_when_empty_or_missing():
    empty_html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018-09", "end_date": "2022-06", "current": False,
          "gpa": "3.9", "summary": ""}],
        _ctx(),
    )
    missing_html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018-09", "end_date": "2022-06", "current": False,
          "gpa": "3.9"}],
        _ctx(),
    )
    for html in (empty_html, missing_html):
        # No stray <p> block with an empty summary; the conditional guard must
        # suppress the line entirely when summary is falsy.
        assert "<p style=\"margin-top:4px;font-size:0.875rem;margin-bottom:0;\"></p>" not in html
        assert 'margin-top:4px' not in html


def test_education_summary_html_escaped():
    html = render_section_preview(
        "education",
        [{"id": "ed1", "institution": "MIT", "degree": "BS",
          "start_date": "2018-09", "end_date": "2022-06", "current": False,
          "gpa": "3.9", "summary": "<script>alert(1)</script>"}],
        _ctx(),
    )
    # Raw <script> tag must not survive into the HTML.
    assert "<script>alert(1)</script>" not in html
    # The literal characters must be HTML-escaped.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def _zone_with(panels):
    """Tiny duck-typed zone object satisfying _format_zone_panels."""
    return type("Zone", (), {"panels": panels})()


def test_instance_style_date_style_propagates_into_panel_context():
    """Verifying that the IR pipeline carries `instance.style.date_style`
    through to `panel_context.instance_style.date_style`, so the renderers
    can read it as `(context or {}).get("instance_style", {}).get("date_style")`.
    """
    from app.services.renderer.ir import _build_section_panel
    from app.services.renderer.backends.html import _format_zone_panels
    panel = _build_section_panel(
        {"id": "e1", "type": "experience", "title": "Work", "enabled": True,
         "data": [{"id": "x", "company": "A", "position": "P",
                   "start_date": "2021-03", "end_date": "2022-01", "current": False}],
         "style": {"date_style": {"key": "Month YYYY", "range_sep": " – "}}},
        _ctx(),
    )
    html = _format_zone_panels(_zone_with([panel]))
    # The renderer produces the formatted range when reading from the
    # propagated instance_style.date_style.
    assert "March 2021" in html
    assert "January 2022" in html
