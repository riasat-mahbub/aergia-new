"""Parser layer unit tests.

Covers the per-helper contracts on the PDF extraction path that the
end-to-end ``test_parser_smoke`` regression doesn't exercise:

- ``_collect_page_annotations`` returns ``(uri, x0, y0, x1, y1)`` for
  every ``/Annots [/A /URI]`` link, after the y-flip into the
  visitor's top-down space.
- ``_build_simple_entries`` writes ``url`` and ``link_text`` on each
  row from the underlying :class:`LabeledBlock` link list.
- ``_strip_title_tail`` removes ``"Foo Paper↗"`` → ``"Foo"`` and
  preserves foreign tail text.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.parser.classify import LabeledBlock, PROFILE
from app.services.parser.extract import _collect_page_annotations
from app.services.parser.mapper import _build_simple_entries, _strip_title_tail


class _FakeArray:
    def __init__(self, items):
        self._items = list(items)

    def __iter__(self):
        return iter(self._items)


class _FakeIndirect:
    def __init__(self, obj):
        self._obj = obj

    def get_object(self):
        return self._obj


def _make_page(annots):
    """Synthesise a page-like object exposing ``page.get('/Annots')``."""
    raw = _FakeArray([_FakeIndirect(a) for a in annots])
    page = SimpleNamespace(
        get=lambda key: raw if key == "/Annots" else None,
        mediabox=SimpleNamespace(width=595.0, height=841.92),
    )
    return page


def _annot(rect, uri):
    return {
        "/Subtype": "/Link",
        "/A": {"/URI": uri},
        "/Rect": list(rect),
    }


def test_collect_page_annotations_returns_uri_and_rect():
    # The walker exposes /Rect in PDF MediaBox bottom-up coordinates
    # (PDF-native). Block bboxes computed by
    # ``_group_spans_into_lines`` are also in MediaBox bottom-up (via
    # the ``page_h - 0.75 * tm_y`` transform), so they match
    # directly without further flipping.
    annots = [
        _annot((175.5, 768.4, 251.2, 781.2), "https://github.com/riasat-mahbub"),
    ]
    page = _make_page(annots)
    out = _collect_page_annotations(page, page_h=841.92)
    assert len(out) == 1
    uri, x0, y0, x1, y1 = out[0]
    assert uri == "https://github.com/riasat-mahbub"
    assert (x0, y0, x1, y1) == (175.5, 768.4, 251.2, 781.2)


def test_collect_page_annotations_skips_non_link_subtypes():
    annots = [
        _annot((0, 0, 100, 100), "https://ignored.com"),
    ]
    annots[0]["/Subtype"] = "/FreeText"  # not a link
    out = _collect_page_annotations(_make_page(annots))
    assert out == []


def test_collect_page_annotations_skips_uris_missing():
    annots = [
        {
            "/Subtype": "/Link",
            "/A": {},
            "/Rect": [0, 0, 100, 100],
        },
    ]
    out = _collect_page_annotations(_make_page(annots))
    assert out == []


def test_collect_page_annotations_handles_walker_failure():
    class _Boom:
        def get(self, key):
            raise RuntimeError("corrupt")

    # Should swallow the error and return [], not raise.
    assert _collect_page_annotations(_Boom()) == []


def _labeled(text, *, links=None, is_bold=False, font_size=10.0):
    return LabeledBlock(
        text=text,
        x=0.0,
        y=0.0,
        width=10.0,
        height=10.0,
        font_size=font_size,
        is_bold=is_bold,
        page=0,
        section=PROFILE,
        confidence="high",
        links=links or [],
    )


def test_build_simple_entries_carries_link_into_url():
    blocks = [
        _labeled("MBuddy", links=["https://github.com/riasat-mahbub/MBuddy"], is_bold=True),
        _labeled("Local manga recommendation engine.", is_bold=False),
    ]
    rows = _build_simple_entries(
        blocks,
        heading=None,
        prefix="proj",
        title_field="name",
        link_field="url",
        link_text_field="link_text",
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "MBuddy"
    assert rows[0]["url"] == "https://github.com/riasat-mahbub/MBuddy"
    assert rows[0]["link_text"] == "↗"


def test_build_simple_entries_strips_paper_tail_from_title():
    blocks = [
        _labeled(
            "Understanding code smells Paper↗",
            links=["https://dal.scholaris.ca/items/abc"],
            is_bold=True,
        ),
        _labeled("Masters Thesis", is_bold=False),
    ]
    rows = _build_simple_entries(
        blocks,
        heading=None,
        prefix="res",
        title_field="title",
        link_field="paper_url",
        link_text_field="paper_link_text",
    )
    assert rows[0]["title"] == "Understanding code smells"
    assert rows[0]["paper_url"] == "https://dal.scholaris.ca/items/abc"


def test_build_simple_entries_no_link_keeps_arrow_only():
    blocks = [
        _labeled("Standalone paper", is_bold=True),
        _labeled("Citation venue.", is_bold=False),
    ]
    rows = _build_simple_entries(
        blocks,
        heading=None,
        prefix="res",
        title_field="title",
        link_field="paper_url",
        link_text_field="paper_link_text",
    )
    assert "paper_url" not in rows[0]
    assert rows[0]["paper_link_text"] == "↗"


def test_strip_title_tail_recognises_known_label_words():
    assert _strip_title_tail("Understanding systems Paper↗") == "Understanding systems"
    assert _strip_title_tail("Project MBuddy GitHub↗") == "Project MBuddy"
    # Foreign tails pass through unchanged.
    assert _strip_title_tail("Visiting Lecture") == "Visiting Lecture"


def test_strip_title_tail_case_insensitive():
    assert _strip_title_tail("Foo Github↗") == "Foo"
    assert _strip_title_tail("Foo certificate↗") == "Foo"
