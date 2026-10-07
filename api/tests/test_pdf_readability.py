"""Real PDF regression coverage for metadata and URL readability in every template."""

from __future__ import annotations

from io import BytesIO
import re

import pdfplumber
import pytest

from app.db.seed import SEED_TEMPLATES
from app.scanner.pdf_worker import _extract_pdfium_text
from app.services.renderer import prepare_render_source, render_source_pdf
from app.services.renderer._pdf_runtime import close_browser


PROJECT_URL = (
    "https://github.com/example-candidate/document-library-and-application-tracker"
    "/blob/main/documentation/rendering-and-readability-reference.md?view=compact#setup"
)
PROFILE_URL = "https://www.linkedin.com/in/sample"


def _pdf_font_sizes(page, text: str) -> set[float]:
    """Return the actual PDF sizes painted for one visible text sample."""
    hits = page.search(text)
    if hits:
        sizes = {
            round(char["size"], 2)
            for hit in hits
            for char in page.chars
            if char["x0"] >= hit["x0"] - 0.5
            and char["x1"] <= hit["x1"] + 0.5
            and char["top"] >= hit["top"] - 0.5
            and char["bottom"] <= hit["bottom"] + 0.5
        }
        if len(sizes) <= 1:
            return sizes
    if " " in text:
        # Sidebar names can wrap onto separate PDF text lines even when the
        # text is visually one phrase. Measure each word independently.
        hits = [hit for word in text.split() for hit in page.search(word)]
    return {
        round(char["size"], 2)
        for hit in hits
        for char in page.chars
        if char["x0"] >= hit["x0"] - 0.5
        and char["x1"] <= hit["x1"] + 0.5
        and char["top"] >= hit["top"] - 0.5
        and char["bottom"] <= hit["bottom"] + 0.5
    }


def readability_sections(layout: str = "two-column", page_break: bool = False) -> list[dict]:
    """Synthetic content preserves the reported structure without personal data."""
    return [
        {
            "id": "profile", "type": "profile", "title": "Profile",
            "data": {
                "name": "Example Candidate", "email": "candidate@example.com",
                "site_url": "https://example.com", "location": "Halifax, NS",
                "social_links": [{"url": PROFILE_URL, "icon": "linkedin"}],
                "summary": "Building reliable document tools for teams.",
            },
        },
        {
            "id": "experience", "type": "experience", "title": "Work Experience",
            "data": [
                {
                    "id": f"job-{index}", "position": role, "company": company,
                    "start_date": "2022-01", "end_date": "2024-06",
                    "description": "Delivered tested applications and maintained deployment documentation.",
                }
                for index, role, company in [
                    (1, "Software Developer", "Example Company"),
                    (2, "Research Assistant", "Example University"),
                ]
            ],
        },
        {
            "id": "skills", "type": "skills", "title": "Skills",
            "data": [{"id": "skills-dev", "category": "Development", "items": ["Python", "C++", "C#", ".NET", "CI/CD"]}],
        },
        {
            "id": "projects", "type": "projects", "title": "Personal Projects",
            "style": {
                "policy": {"entry_layout": layout},
                "layout": {"break_before": page_break},
            },
            "data": [
                {
                    "id": "project-library", "name": "Document Library",
                    "start_date": "2026-04", "url": PROJECT_URL,
                    "description": "Library contribution: built a searchable document collection with automated exports.",
                    "tech_stack": ["Python", "React", "SQLAlchemy"],
                },
                {
                    "id": "project-tracker", "name": "Project Tracker",
                    "start_date": "2026-04", "url": "https://example.com/tracker",
                    "description": "Tracker contribution: implemented searchable project history and release checks.",
                    "tech_stack": ["TypeScript", "SQLite"],
                },
            ],
        },
        {
            "id": "education", "type": "education", "title": "Education",
            "data": [{"id": "degree", "degree": "Computer Science", "institution": "Example University"}],
        },
    ]


@pytest.mark.parametrize("seed", SEED_TEMPLATES, ids=lambda seed: seed["id"])
@pytest.mark.parametrize("layout", ["stack", "two-column"])
@pytest.mark.parametrize("page_break", [False, True], ids=["continuous", "page-break"])
async def test_template_pdf_keeps_project_metadata_before_body(seed, layout, page_break):
    source = prepare_render_source(readability_sections(layout, page_break), seed["manifest"])
    try:
        pdf_bytes = await render_source_pdf(source)
    finally:
        await close_browser()

    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        texts = {
            "pdfplumber": "\n".join(page.extract_text() or "" for page in document.pages),
            "pdfium": _extract_pdfium_text(pdf_bytes),
        }
        links = {link["uri"] for page in document.pages for link in page.hyperlinks if link.get("uri")}
        assert {PROJECT_URL, PROFILE_URL, "https://example.com/tracker"} <= links
        expected_body_size = 10.5 if seed["id"] == "generic-minimal" else 9.0
        if page_break:
            assert len(document.pages) >= 2
        for page in document.pages:
            # Text and links must stay inside the physical page, including the sidebar.
            assert all(
                -1 <= char["x0"] <= char["x1"] <= page.width + 1
                and -1 <= char["top"] <= char["bottom"] <= page.height + 1
                for char in page.chars
            )

        first_page = document.pages[0]
        # Modern's word "Candidate" also occurs in its email address, so its
        # measured set can contain contact text as well as the name glyphs.
        assert 18.0 in _pdf_font_sizes(first_page, "Example Candidate")
        assert _pdf_font_sizes(first_page, "Work Experience") == {12.0}
        assert _pdf_font_sizes(first_page, "Delivered tested applications") == {expected_body_size}
        assert _pdf_font_sizes(first_page, "candidate@example.com") == {expected_body_size}
        assert _pdf_font_sizes(first_page, "January 2022") == {expected_body_size}

    for parser, text in texts.items():
        assert text is not None, parser
        assert "↗" not in text, parser
        compact = re.sub(r"\s+", "", text)
        assert "linkedin.com/in/sample" in compact, parser
        assert PROJECT_URL.removeprefix("https://") in compact, parser
        assert all(skill in compact for skill in ("C++", "C#", ".NET", "CI/CD")), parser
        # PDF engines can introduce a line break inside an otherwise intact
        # title, especially after a page break with serif fonts.
        text = " ".join(text.split())
        for title, body, url in [
            ("Document Library", "Library contribution:", PROJECT_URL),
            ("Project Tracker", "Tracker contribution:", "https://example.com/tracker"),
        ]:
            start = text.index(title, text.index("Personal Projects"))
            body_start = text.index(body, start)
            metadata = text[start:body_start]
            assert "April 2026" in metadata, (parser, metadata)
            assert url.removeprefix("https://") in re.sub(r"\s+", "", metadata), (parser, metadata)
