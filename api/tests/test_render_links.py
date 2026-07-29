"""Route link transform — the live preview keeps working links.

Regression guard for the preview link contract:
``make_anchors_open_in_new_tab`` (render routes) keeps real hrefs and
forces ``target="_blank"`` so the sandboxed iframe never navigates away.

The PDF keeps the same real anchors (Chromium's print engine turns them
into clickable annotations) — the exported CV must be clickable.
"""

from __future__ import annotations

from app.routes.render import make_anchors_open_in_new_tab


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


def test_preview_keeps_pdf_anchors_intact():
    """The preview transform must not disturb the hrefs that also feed the
    PDF — the exported PDF relies on the very same anchors."""
    html = '<a href="https://aergia.dev">Repo</a>'
    out = make_anchors_open_in_new_tab(html)
    assert 'href="https://aergia.dev"' in out
    assert out.count("href=") == 1
