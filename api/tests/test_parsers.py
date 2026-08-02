"""Parser layer unit tests.

Covers the per-helper contracts on the PDF parser that the
end-to-end ``test_parser_smoke`` regression doesn't exercise:

- :func:`app.services.parser._extract_pdfplumber._attach_hyperlinks_to_block`
  writes ``url`` and ``link_text`` on each block from the matching
  hyperlink rect.
- :func:`app.services.parser.mapper._build_simple_entries` writes
  ``url`` and ``link_text`` on each row from the underlying
  :class:`LabeledBlock` link list.
- :func:`app.services.parser.mapper._strip_title_tail` removes
  ``"Foo Paper↗"`` → ``"Foo"`` and preserves foreign tail text.
"""

from __future__ import annotations

from app.services.parser._extract_pdfplumber import _attach_hyperlinks_to_block
from app.services.parser.classify import LabeledBlock
from app.services.parser.mapper import _build_simple_entries, _strip_title_tail
from app.services.parser.schemas import TextBlock


def _labeled(text, *, links=None, is_bold=False, font_size=10.0):
    return LabeledBlock(
        text=text,
        x=0.0,
        y=0.0,
        width=0.0,
        height=0.0,
        font_size=font_size,
        is_bold=is_bold,
        page=0,
        section="extras",
        confidence="medium",
        source_heading=None,
        links=list(links or []),
    )


def test_attach_hyperlinks_to_block_attaches_contact_line_links():
    """Bug 1 regression: pdfplumber's hyperlink rects and TextBlock
    bboxes share the same top-down coordinate space, so a block whose
    y-range covers a link rect should pick the URI up. The block
    constructed here mimics a contact-line block at y=50..60 carrying
    a single line, with three link rects at the same y-range. All
    three URIs must land on the block."""
    block = TextBlock(
        text="riasat-mahbub Riasat Mahbub rmahbub.com",
        x=100.0,
        y=50.0,
        width=400.0,
        height=10.0,
        font_size=12.0,
        is_bold=False,
        page=0,
    )
    hyperlinks = [
        {"uri": "https://github.com/riasat-mahbub", "x0": 100.0, "top": 50.5, "x1": 200.0, "bottom": 58.0},
        {"uri": "https://www.linkedin.com/in/riasat-m-70682b115/", "x0": 200.0, "top": 50.5, "x1": 300.0, "bottom": 58.0},
        {"uri": "https://www.rmahbub.com/", "x0": 300.0, "top": 50.5, "x1": 400.0, "bottom": 58.0},
    ]
    _attach_hyperlinks_to_block(block, hyperlinks)
    assert block.links == [
        "https://github.com/riasat-mahbub",
        "https://www.linkedin.com/in/riasat-m-70682b115/",
        "https://www.rmahbub.com/",
    ]


def test_attach_hyperlinks_to_block_skips_non_overlapping_links():
    """A link rect whose y-range falls outside the block's y-range is
    not attached — the rect-overlap rule keeps distant annotations
    from leaking onto unrelated lines."""
    block = TextBlock(
        text="Contact line",
        x=0.0,
        y=50.0,
        width=400.0,
        height=10.0,
        font_size=12.0,
        is_bold=False,
        page=0,
    )
    hyperlinks = [
        {"uri": "https://unrelated.com", "x0": 0.0, "top": 200.0, "x1": 100.0, "bottom": 210.0},
    ]
    _attach_hyperlinks_to_block(block, hyperlinks)
    assert block.links == []


def test_build_simple_entries_carries_link_into_url():
    blocks = [
        _labeled("PROJECTS", is_bold=True, font_size=14),
        _labeled("MBuddy", is_bold=True, links=["https://github.com/riasat-mahbub/MBuddy"]),
        _labeled("A manga recommender.", links=[]),
    ]
    rows = _build_simple_entries(blocks, heading="Projects", title_field="name", link_field="url")
    assert rows[0]["name"] == "MBuddy"
    assert rows[0]["url"] == "https://github.com/riasat-mahbub/MBuddy"
    assert rows[0]["link_text"] == "↗"


def test_build_simple_entries_strips_paper_tail_from_title():
    blocks = [
        _labeled("RESEARCH", is_bold=True, font_size=14),
        _labeled("Understanding systems Paper↗", is_bold=True, links=["https://dal.scholaris.ca/items/abc"]),
        _labeled("A paper.", links=[]),
    ]
    rows = _build_simple_entries(
        blocks,
        heading="Research",
        title_field="title",
        link_field="paper_url",
        link_text_field="paper_link_text",
    )
    assert rows[0]["title"] == "Understanding systems"
    assert rows[0]["paper_url"] == "https://dal.scholaris.ca/items/abc"


def test_build_simple_entries_no_link_keeps_arrow_only():
    blocks = [
        _labeled("RESEARCH", is_bold=True, font_size=14),
        _labeled("Visiting Lecture Paper↗", is_bold=True, links=[]),
    ]
    rows = _build_simple_entries(
        blocks,
        heading="Research",
        title_field="title",
        link_field="paper_url",
        link_text_field="paper_link_text",
    )
    assert "paper_url" not in rows[0]
    assert rows[0]["paper_link_text"] == "↗"


def test_strip_title_tail_recognises_known_label_words():
    assert _strip_title_tail("Understanding systems Paper↗") == "Understanding systems"
    assert _strip_title_tail("Foo Certificate↗") == "Foo"
    # Foreign tail preserved.
    assert _strip_title_tail("Visiting Lecture") == "Visiting Lecture"


def test_strip_title_tail_case_insensitive():
    assert _strip_title_tail("Foo Github↗") == "Foo"
    assert _strip_title_tail("Foo certificate↗") == "Foo"
