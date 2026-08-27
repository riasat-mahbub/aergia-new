"""Preview link transform — live preview has no working links.

Regression guard for the preview link contract:

- ``strip_anchor_hrefs`` (render routes) neutralizes preview hrefs to "#"
  so the sandboxed iframe never navigates away while editing; the anchor
  markup, inline styling, and the .f-link arrow are preserved.
"""

from __future__ import annotations

from app.routes.render import strip_anchor_hrefs


def test_preview_strips_hrefs_to_hash_but_keeps_markup():
    html = '<a href="https://aergia.dev" style="color:red">Repo</a>'
    out = strip_anchor_hrefs(html)
    assert 'href="#"' in out
    assert "https://aergia.dev" not in out
    assert 'style="color:red"' in out
    assert "Repo" in out


def test_preview_strip_handles_multiple_anchors_and_case():
    html = '<A HREF="https://one.dev">One</A><a href="https://two.dev">Two</a>'
    out = strip_anchor_hrefs(html)
    assert out.lower().count('href="#"') == 2
    assert "https://one.dev" not in out and "https://two.dev" not in out


def test_preview_strip_leaves_non_anchor_href_attributes_alone():
    html = '<div class="f-link" data-href="https://aergia.dev">Repo</div>'
    assert strip_anchor_hrefs(html) == html
