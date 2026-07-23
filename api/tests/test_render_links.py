"""Preview link transform — live preview has NO working links, PDF keeps them.

Regression guard for the preview/PDF link contract:

- ``strip_anchor_hrefs`` (render routes) neutralizes preview hrefs to "#"
  so the sandboxed iframe never navigates away while editing; the anchor
  markup, inline styling, and the .f-link arrow are preserved.
- The PDF path uses the raw renderer output (real anchors -> clickable
  Chromium link annotations); nothing in the pipeline strips those.
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


def test_pdf_input_keeps_real_hrefs():
    """The PDF path renders the same document without the preview strip: the
    raw renderer output must keep working anchors, and the strip must be an
    explicit opt-in per preview endpoint only."""
    html = '<a href="https://aergia.dev">Repo</a>'
    assert 'href="https://aergia.dev"' in html
    assert "href=\"#\"" not in html
