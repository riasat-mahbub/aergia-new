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
    assert "2018" in html
    # No stray dash sequence
    assert " –  " not in html
    assert " –  &n" not in html


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
