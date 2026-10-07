from __future__ import annotations

import copy
from io import BytesIO
import re

import pdfplumber

from app.db.seed import SEED_TEMPLATES
from app.scanner.pdf_worker import _extract_pdfium_text
from app.services.renderer import prepare_render_source, render_source_html, render_source_pdf, resolve_source
from app.services.renderer._pdf_runtime import close_browser
from tests.test_pdf_readability import PROFILE_URL, PROJECT_URL, readability_sections


MINIMAL = next(seed["manifest"] for seed in SEED_TEMPLATES if seed["id"] == "generic-minimal")
LONG_URL = (
    "https://example.org/research/"
    "international-characterization-of-multilingual-document-recovery-and-"
    "accessible-application-workflows/technical-appendix-and-methodology"
)


def _font_sizes(page, phrase: str) -> set[float]:
    hits = page.search(phrase)
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
    if " " in phrase:
        hits = [hit for word in phrase.split() for hit in page.search(word)]
    return {
        round(char["size"], 2)
        for hit in hits
        for char in page.chars
        if char["x0"] >= hit["x0"] - 0.5
        and char["x1"] <= hit["x1"] + 0.5
        and char["top"] >= hit["top"] - 0.5
        and char["bottom"] <= hit["bottom"] + 0.5
    }


def _assert_page_bounds(document) -> None:
    for page in document.pages:
        assert all(
            -1 <= char["x0"] <= char["x1"] <= page.width + 1
            and -1 <= char["top"] <= char["bottom"] <= page.height + 1
            for char in page.chars
        )


def _long_sections() -> tuple[list[dict], str]:
    sections = readability_sections()
    profile = next(section for section in sections if section["type"] == "profile")["data"]
    profile.update(
        name="Zoë Nguyễn-Sørensen International Candidate",
        title="Principal Engineer, International Research Systems and Accessible Document Infrastructure",
        location="München, Deutschland",
        social_links=[{"url": "https://www.linkedin.com/in/zoe-nguyen-sorensen-international-systems", "icon": "linkedin"}],
    )
    experience = next(section for section in sections if section["type"] == "experience")
    entries = []
    for index in range(8):
        boundary = index == 7
        bullets = 8 if index < 3 else 4
        description = (
            [{"type": "paragraph", "items": [{"text": "Boundary entry body remains attached to its role heading and date."}]}]
            if boundary
            else [{"type": "bullet_list", "items": [
                {"text": f"Designed international document workflows for Montréal, München, and Ålesund teams; preserved evidence and reliable exports ({index}-{item})."}
                for item in range(bullets)
            ]}]
        )
        entries.append({
            "id": f"job-{index}",
            "position": "Boundary Systems Engineer" if boundary else f"Senior International Platform Engineer {index}",
            "company": "München Übersee-Forschungsgesellschaft for Multilingual Document Systems" if boundary else f"Northstar International Research Systems {index}",
            "location": "Montréal, Québec",
            "start_date": "2019-01" if boundary else f"{2030-index}-01",
            "end_date": "2021-12" if boundary else f"{2030-index}-12",
            "description": description,
        })
    experience["data"] = entries
    projects = next(section for section in sections if section["type"] == "projects")
    projects["data"][0]["url"] = LONG_URL
    sections.extend([
        {
            "id": "research", "type": "research", "title": "Research",
            "data": [{
                "id": "paper", "title": "Études in Multilingual Document Recovery", "publication_date": "2024-06",
                "publication_value": "International Journal of Document Systems", "paper_url": LONG_URL,
                "description": [
                    {"type": "paragraph", "items": [
                        {"text": "Inline styled evidence", "style": {"bold": True, "font_size": "large"}},
                        {"text": " retains its authored size and weight."},
                    ]},
                    {"type": "bullet_list", "items": [{"text": "Research notes preserve semantic list structure."}]},
                ],
            }],
        },
        {"id": "certifications", "type": "certifications", "title": "Certifications", "data": [
            {"id": "cert", "name": "International Accessibility Engineering Certificate", "date": "2024-06", "issuer": "München Standards Institute"},
        ]},
        {"id": "languages", "type": "languages", "title": "Languages", "data": [
            {"id": "lang-en", "language": "English", "proficiency": "Fluent"},
            {"id": "lang-fr", "language": "Français", "proficiency": "Professional"},
        ]},
    ])
    return sections, LONG_URL


def _find_hit(document, phrase: str) -> tuple[int, dict] | None:
    for page_number, page in enumerate(document.pages):
        hits = page.search(phrase)
        if hits:
            return page_number, hits[0]
    return None


async def test_minimal_short_pdf_measures_readable_text_and_retains_audit_content():
    source = prepare_render_source(readability_sections(), MINIMAL)
    try:
        pdf_bytes = await render_source_pdf(source)
    finally:
        await close_browser()

    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        assert len(document.pages) == 1
        _assert_page_bounds(document)
        page = document.pages[0]
        assert _font_sizes(page, "Example Candidate") == {18.0}
        assert _font_sizes(page, "Work Experience") == {12.0}
        assert _font_sizes(page, "Delivered tested applications") == {10.5}
        assert _font_sizes(page, "January 2022") == {10.5}
        links = {link["uri"] for page in document.pages for link in page.hyperlinks if link.get("uri")}
        assert {PROJECT_URL, PROFILE_URL, "https://example.com/tracker"} <= links
        pdfplumber_text = "\n".join(page.extract_text() or "" for page in document.pages)

    parser_texts = {
        "pdfplumber": pdfplumber_text,
        "pdfium": _extract_pdfium_text(pdf_bytes),
    }
    for parser, text in parser_texts.items():
        assert text is not None, parser
        compact = re.sub(r"\s+", "", text)
        assert all(skill in compact for skill in ("C++", "C#", ".NET", "CI/CD")), parser
        assert "ExampleCandidate" in compact and "WorkExperience" in compact, parser


async def test_minimal_long_pdf_keeps_boundary_entry_and_complex_text():
    sections, long_url = _long_sections()
    source = prepare_render_source(sections, MINIMAL)
    try:
        pdf_bytes = await render_source_pdf(source)
    finally:
        await close_browser()

    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        assert len(document.pages) >= 2
        _assert_page_bounds(document)
        boundary_hit = next(
            (page_number, hit)
            for page_number, page in enumerate(document.pages)
            for hit in page.search("Boundary Systems Engineer")
        )
        page_number, hit = boundary_hit
        page = document.pages[page_number]
        assert hit["top"] >= 36 - 0.6, (page_number, hit)
        assert hit["bottom"] <= page.height - 36 + 0.6, (page_number, hit)
        title_hit = _find_hit(document, "Boundary Systems Engineer")
        date_hit = _find_hit(document, "January 2019")
        company_hit = _find_hit(document, "München Übersee-Forschungsgesellschaft")
        body_hit = _find_hit(document, "Boundary entry body")
        assert title_hit and date_hit and company_hit and body_hit
        assert title_hit[0] == date_hit[0]
        assert abs(title_hit[1]["top"] - date_hit[1]["top"]) <= 8
        assert company_hit[0] == body_hit[0] == title_hit[0]
        assert company_hit[1]["top"] >= title_hit[1]["bottom"]
        assert body_hit[1]["top"] >= company_hit[1]["bottom"]
        links = {link["uri"] for page in document.pages for link in page.hyperlinks if link.get("uri")}
        assert long_url in links
        assert any(_font_sizes(page, "Inline styled evidence") == {13.5} for page in document.pages)
        pdfplumber_text = "\n".join(page.extract_text() or "" for page in document.pages)

    parser_texts = {
        "pdfplumber": pdfplumber_text,
        "pdfium": _extract_pdfium_text(pdf_bytes),
    }
    for parser, text in parser_texts.items():
        assert text is not None, parser
        flat = " ".join(text.split())
        compact = re.sub(r"\s+", "", text)
        assert "Zoë" in text and "Nguyễn-Sørensen" in text, parser
        assert "Research" in text and "Certifications" in text and "Languages" in text, parser
        assert "Inline styled evidence" in text and "Research notes preserve semantic list structure." in text, parser
        assert long_url.removeprefix("https://") in compact, parser
        assert all(token in flat for token in (
            "Boundary Systems Engineer", "January 2019", "München Übersee-Forschungsgesellschaft", "Boundary entry body",
        )), parser


async def test_renderer_boundary_preserves_override_precedence_reset_and_legacy_layout():
    sections = readability_sections()
    original_sections = copy.deepcopy(sections)
    default_source = prepare_render_source(sections, MINIMAL)
    default_model = resolve_source(default_source)
    assert default_model.css_vars["--body-size"] == "0.875rem"
    assert default_model.css_vars["--body-line-height"] == "1.4"
    assert default_model.css_vars["--spacing-section"] == "16px"
    assert default_model.css_vars["--spacing-entry"] == "8px"
    assert default_model.css_vars["--spacing-field"] == "4px"

    copied_layout = {
        "zones": copy.deepcopy(MINIMAL["zones"]),
        "placement": copy.deepcopy(MINIMAL["placement"]),
    }
    inherited_with_copy = resolve_source(prepare_render_source(
        sections, MINIMAL, {"layout": copied_layout},
    ))
    assert inherited_with_copy.zones == default_model.zones
    assert inherited_with_copy.zones[0].styles == {"width": "100%", "padding": "32px"}

    explicit = copy.deepcopy(sections)
    for section_type in ("profile", "experience"):
        section = next(item for item in explicit if item["type"] == section_type)
        section["style"] = {"typography": {"body": {"font_size": "large", "line_height": "tight"}}}
    experience = next(item for item in explicit if item["type"] == "experience")
    experience["style"]["subsection"] = {
        "entry_gap": "none", "field_gap": "roomy", "spacing_before": "none", "spacing_after": "none",
    }
    experience["data"][0]["description"] = [{"type": "paragraph", "items": [
        {"text": "Delivered tested applications", "style": {"bold": True, "font_size": "small"}},
        {"text": " with inherited section typography."},
    ]}]
    experience["data"][1]["description"] = "Maintained documentation across distributed teams."
    explicit_source = prepare_render_source(explicit, MINIMAL, {"spacing": "compact", "layout": copied_layout})
    explicit_model = resolve_source(explicit_source)
    explicit_html = render_source_html(explicit_source)
    assert explicit_model.css_vars["--spacing-section"] == "20px"
    assert explicit_model.css_vars["--spacing-entry"] == "0px"
    assert explicit_model.css_vars["--spacing-field"] == "0px"
    assert "--section-body-size:1.125rem" in explicit_html
    assert "line-height:1.2" in explicit_html
    assert "gap:0" in explicit_html and "gap:16px" in explicit_html

    reset_model = resolve_source(prepare_render_source(copy.deepcopy(original_sections), MINIMAL))
    assert reset_model.css_vars == default_model.css_vars
    assert reset_model.sections["experience"].typography is None
    assert sections == original_sections

    legacy = copy.deepcopy(MINIMAL)
    legacy["global_styles"].pop("body_font_size")
    legacy["global_styles"].pop("body_line_height")
    legacy["layout_defaults"].pop("entry_gap")
    legacy["layout_defaults"].pop("field_gap")
    legacy["layout_defaults"]["spacing"] = "none"
    legacy_source = prepare_render_source(sections, legacy)
    legacy_model = resolve_source(legacy_source)
    assert "--body-size" not in legacy_model.css_vars
    assert "--body-line-height" not in legacy_model.css_vars
    assert legacy_model.css_vars["--spacing-entry"] == "0px"
    assert legacy_model.css_vars["--spacing-field"] == "0px"

    try:
        explicit_pdf = await render_source_pdf(explicit_source)
        legacy_pdf = await render_source_pdf(legacy_source)
    finally:
        await close_browser()
    with pdfplumber.open(BytesIO(explicit_pdf)) as document:
        assert _font_sizes(document.pages[0], "Example Candidate") == {13.5}
        assert _font_sizes(document.pages[0], "Delivered tested applications") == {10.5}
        assert _font_sizes(document.pages[0], "Work Experience") == {12.0}
    with pdfplumber.open(BytesIO(legacy_pdf)) as document:
        assert _font_sizes(document.pages[0], "Delivered tested applications") == {9.0}
        assert _font_sizes(document.pages[0], "Example Candidate") == {18.0}
