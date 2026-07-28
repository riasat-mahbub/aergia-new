"""End-to-end regression test against the benchmark resume PDF.

``resume-benchmark.pdf`` is the user's own CV (Riasat Mahbub, August
2026) — the corpus that exposed the parser's single-section failure
(profile-only output). It exercises the full extract → classify → map
pipeline against a real Chromium-exported PDF with:

- Type0 subset fonts (NotoSans-Bold / SemiBold / Regular / Medium)
- mixed-case bold section headers (Experience, Education, …)
- bold job titles inside Experience
- running-paragraph descriptions with no bullets
- education entries joined without blank lines
- category-labelled skills lines
- letter-spaced Chromium date labels next to research entries
- a bare-domain contact line ("rmahbub.com")

Every assertion below is a contract: if the parser regresses on any of
these shapes, this test fails.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parser import parse_cv

FIXTURE = Path(__file__).parent / "fixtures" / "resume-benchmark.pdf"


@pytest.fixture(scope="module")
def benchmark_result():
    if not FIXTURE.exists():
        pytest.skip("benchmark fixture missing at tests/fixtures/resume-benchmark.pdf")
    import asyncio

    return asyncio.run(parse_cv(FIXTURE.read_bytes(), "application/pdf"))


def _by_type(result, section_type: str):
    return next((s for s in result.sections if s.type == section_type), None)


def test_benchmark_emits_all_sections(benchmark_result):
    types = [s.type for s in benchmark_result.sections]
    for expected in ("profile", "experience", "education", "skills", "projects", "research"):
        assert expected in types, f"missing section {expected!r}; got {types}"


def test_benchmark_profile(benchmark_result):
    profile = _by_type(benchmark_result, "profile")
    assert profile is not None
    assert profile.data["name"] == "Riasat Mahbub"
    assert profile.data["email"] == "riasat1998@gmail.com"
    assert profile.data["phone"] == "+1 782 409 4525"
    assert profile.data["site_url"] == "https://rmahbub.com"


def test_benchmark_experience_two_entries_with_descriptions(benchmark_result):
    exp = _by_type(benchmark_result, "experience")
    assert exp is not None
    assert len(exp.data) == 2
    first, second = exp.data
    assert first["position"] == "Research Assistant"
    assert first["company"] == "Dalhousie University"
    assert first["start_date"] == "2023-09"
    assert first["end_date"] == "2025-10"
    assert "Worked with civil engineers and planners" in first["description"]
    assert "simulation systems." in first["description"]
    assert second["position"] == "Associate Software Engineer"
    assert second["company"] == "Brain Station 23"
    assert "Delivered features across a rotation of client projects" in second["description"]


def test_benchmark_education_two_entries(benchmark_result):
    edu = _by_type(benchmark_result, "education")
    assert edu is not None
    assert len(edu.data) == 2
    master, bachelor = edu.data
    assert master["degree"] == "Master of Computer Science"
    assert master["institution"] == "Dalhousie University"
    assert master["start_date"] == "2023-09"
    assert master["end_date"] == "2025-10"
    assert bachelor["degree"] == "Bachelor of Computer Science and Engineering"
    assert bachelor["institution"] == "BRAC University"
    assert bachelor["start_date"] == "2018-01"
    assert bachelor["end_date"] == "2022-01"


def test_benchmark_skills_categories_clean(benchmark_result):
    skills = _by_type(benchmark_result, "skills")
    assert skills is not None
    groups = skills.data
    assert len(groups) == 5
    by_cat = {g["category"]: g["items"] for g in groups}
    assert by_cat["Programming Languages"] == [
        "TypeScript", "JavaScript", "Python", "PHP", "SQL", "HTML/CSS",
    ]
    assert by_cat["AI/ML"] == [
        "PyTorch", "TensorFlow", "scikit-learn", "Keras", "llama.cpp", "ollama", "Pandas",
    ]
    # Letter-spaced Chromium date junk must not leak into skills.
    all_items = [item for g in groups for item in g["items"]]
    assert not any("A u g" in i or "2 0 2" in i for i in all_items)


def test_benchmark_projects_three_entries(benchmark_result):
    proj = _by_type(benchmark_result, "projects")
    assert proj is not None
    titles = [p["title"] for p in proj.data]
    assert titles == ["MBuddy", "Project Tracker Extension", "Aergia CV Builder"]
    assert "189,000 entries" in proj.data[0]["description"]


def test_benchmark_research_four_entries(benchmark_result):
    res = _by_type(benchmark_result, "research")
    assert res is not None
    titles = [r["title"] for r in res.data]
    assert len(titles) == 4
    assert titles[0].startswith("Understanding code smells")
    assert "City Recommender System" in titles[3]
