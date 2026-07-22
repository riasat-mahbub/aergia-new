"""Route/runtime link transforms — preview keeps working links, PDF does not.

Regression guards for the preview-vs-PDF link contract:

- ``make_anchors_open_in_new_tab`` (render routes): the live preview keeps
  real hrefs and forces ``target="_blank"`` so the sandboxed iframe never
  navigates away.
- ``strip_anchor_markup`` (PDF runtime): Chromium's print engine turns real
  anchors into clickable PDF annotations; the PDF must be a static document,
  so anchors are replaced with non-clickable spans before printing.
"""

from __future__ import annotations

from app.routes.render import make_anchors_open_in_new_tab
from app.services.renderer._pdf_runtime import strip_anchor_markup


def test_preview_keeps_hrefs_and_adds_new_tab_target():
    html = '<a href="https://aergia.dev" style="color:red">Repo</a>'
    out = make_anchors_open_in_new_tab(html)
    assert 'href="https://aergia.dev"' in out
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out
    assert "Repo" in out


def test_preview_does_not_duplicate_target_attribute():
    html = '<a target="_self" href="https://aergia.dev">x</a>'
    out = make_anchors_open_in_new_tab(html)
    assert out.count("target=") == 1
    assert 'target="_self"' in out


def test_pdf_strip_removes_anchors_but_keeps_text_and_style():
    html = '<a href="https://aergia.dev" style="color:red">Repo</a>'
    out = strip_anchor_markup(html)
    assert "<a" not in out
    assert "</a" not in out
    assert "Repo" in out
    # Inline style survives on the replacement span; the href is dropped.
    assert 'style="color:red"' in out
    assert "href=" not in out
    assert "<span" in out


def test_pdf_strip_is_case_insensitive_for_close_tags():
    html = '<A HREF="https://x">PDF</A>'
    out = strip_anchor_markup(html)
    assert "<A" not in out
    assert "</A" not in out
    assert "PDF" in out


def test_pdf_strip_leaves_plain_text_untouched():
    html = '<div class="f-link">Repo <span>↗</span></div>'
    assert strip_anchor_markup(html) == html
