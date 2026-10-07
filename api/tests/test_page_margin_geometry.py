from __future__ import annotations

from copy import deepcopy
from io import BytesIO

import pdfplumber

from app.db.seed import SEED_TEMPLATES
from app.services.renderer import prepare_render_source, render_source_html, render_source_pdf
from app.services.renderer._pdf_runtime import close_browser
from tests.test_pdf_readability import readability_sections


MINIMAL = next(seed["manifest"] for seed in SEED_TEMPLATES if seed["id"] == "generic-minimal")
PHYSICAL_MARGIN_PT = 36


def _long_sections(*, oversized: bool = False) -> list[dict]:
    sections = deepcopy(readability_sections())
    experience = next(section for section in sections if section["type"] == "experience")
    entries = []
    for index in range(12):
        if oversized and index == 0:
            description = [{"type": "bullet_list", "items": [
                {"text": f"Long evidence remains selectable and continues naturally across pages ({item}). "
                         "The preview should explain that this entry may split in PDF export."}
                for item in range(100)
            ]}]
        else:
            description = [{"type": "bullet_list", "items": [
                {"text": f"Workflow evidence {index}-{item}: built reliable document workflows for research and product teams."}
                for item in range(5)
            ]}]
        entries.append({
            "id": f"job-{index}",
            "position": f"Senior Software Engineer {index}",
            "company": f"Example Systems {index}",
            "start_date": "2022-01",
            "end_date": "2024-06",
            "description": description,
        })
    experience["data"] = entries
    return sections


def _assert_physical_margins(pdf_bytes: bytes, *, min_left_pt: float = PHYSICAL_MARGIN_PT) -> int:
    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        assert document.pages
        for page_number, page in enumerate(document.pages, start=1):
            assert page.chars, f"page {page_number} contains no selectable text"
            assert min(char["x0"] for char in page.chars) >= min_left_pt - 0.6, page_number
            assert min(char["top"] for char in page.chars) >= PHYSICAL_MARGIN_PT - 0.6, page_number
            assert max(char["x1"] for char in page.chars) <= page.width - min_left_pt + 0.6, page_number
            assert max(char["bottom"] for char in page.chars) <= page.height - PHYSICAL_MARGIN_PT + 0.6, page_number
            assert all(
                -1 <= char["x0"] <= char["x1"] <= page.width + 1
                and -1 <= char["top"] <= char["bottom"] <= page.height + 1
                for char in page.chars
            )
        return len(document.pages)


def _find_pdf_hit(document, phrase: str) -> tuple[int, dict]:
    for page_number, page in enumerate(document.pages):
        hits = page.search(phrase)
        if hits:
            return page_number, hits[0]
    raise AssertionError(f"PDF text not found: {phrase}")


async def test_print_margins_repeat_for_short_long_and_oversized_documents():
    sources = [
        prepare_render_source(readability_sections(), MINIMAL),
        prepare_render_source(_long_sections(), MINIMAL),
        prepare_render_source(_long_sections(oversized=True), MINIMAL),
    ]
    try:
        rendered = [(render_source_html(source), await render_source_pdf(source)) for source in sources]
    finally:
        await close_browser()

    page_counts = []
    for html, pdf_bytes in rendered:
        assert "@page { size: A4; margin: 48px 16px; }" in html
        assert ".zone:only-child { box-sizing:border-box; }" in html
        assert "padding:32px" in html
        page_counts.append(_assert_physical_margins(pdf_bytes))

    assert page_counts[0] >= 1
    assert page_counts[1] >= 2
    assert page_counts[2] >= 2

    with pdfplumber.open(BytesIO(rendered[1][1])) as document:
        for index in range(12):
            markers = [
                _find_pdf_hit(document, f"Senior Software Engineer {index}"),
                _find_pdf_hit(document, f"Example Systems {index}"),
                _find_pdf_hit(document, f"Workflow evidence {index}-0"),
                _find_pdf_hit(document, f"Workflow evidence {index}-4"),
            ]
            page_numbers = {page_number for page_number, _hit in markers}
            assert len(page_numbers) == 1, (index, markers)
            tops = [hit["top"] for _page_number, hit in markers]
            assert tops == sorted(tops), (index, markers)


async def test_saved_zone_padding_is_preserved_inside_physical_margins():
    layout = {
        "zones": deepcopy(MINIMAL["zones"]),
        "placement": deepcopy(MINIMAL["placement"]),
    }
    layout["zones"][0]["styles"]["padding"] = "comfortable"
    source = prepare_render_source(_long_sections(), MINIMAL, {"layout": layout})
    html = render_source_html(source)
    try:
        pdf_bytes = await render_source_pdf(source)
    finally:
        await close_browser()

    assert 'padding:24px' in html
    assert "@page { size: A4; margin: 48px 16px; }" in html
    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        assert len(document.pages) >= 2
        for page_number, page in enumerate(document.pages, start=1):
            assert page.chars, f"page {page_number} contains no selectable text"
            assert min(char["x0"] for char in page.chars) >= 30 - 0.6, page_number
            assert min(char["top"] for char in page.chars) >= PHYSICAL_MARGIN_PT - 0.6, page_number
            assert max(char["bottom"] for char in page.chars) <= page.height - PHYSICAL_MARGIN_PT + 0.6, page_number
