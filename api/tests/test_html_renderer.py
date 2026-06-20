"""HTML renderer smoke tests.

Verify the renderer emits a complete HTML5 document with the right CSS
variables, escapes user-provided text, and respects the policy's
``show_title`` flag."""

from __future__ import annotations

from app.schema.models import (
    Customizations,
    Document,
    Entry,
    FieldBlock,
    RenderModel,
    ResolvedZone,
    Section,
    SectionPolicy,
    TemplateManifest,
    TextRun,
    Zone,
)
from app.services.renderer import resolve
from app.services.renderer.html import HTMLDocumentRenderer



def _model():
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="main", styles={"width": "100%"})],
        placement={"profile": "main"},
        global_styles={"accent_color": "#abc", "body_font": "Inter"},
    )
    doc = Document(sections=[
        Section(
            id="p", type="profile", title="P", enabled=True,
            policy=SectionPolicy(show_title=False),
            entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada<script>")])])],
        )
    ])
    return resolve(doc, manifest, Customizations(), HTMLDocumentRenderer.support)


def test_renders_doctype_and_body():
    html = HTMLDocumentRenderer().render(_model())
    assert "<!DOCTYPE html>" in html
    assert "<body>" in html
    assert "</body>" in html


def test_renders_css_vars_as_root_block():
    model = _model()
    assert "--accent: #abc;" in HTMLDocumentRenderer().render(model)
    assert "--body-font: Inter;" in HTMLDocumentRenderer().render(model)


def test_escapes_user_provided_text():
    html = HTMLDocumentRenderer().render(_model())
    # <script> from the user-provided text becomes &lt;script&gt;
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_profile_section_omits_h2_when_show_title_is_false():
    model = _model()
    html = HTMLDocumentRenderer().render(model)
    assert "<h2" not in html


def test_section_shows_h2_when_show_title_is_true():
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"},
    )
    doc = Document(sections=[
        Section(
            id="x", type="experience", title="Experience", enabled=True,
            policy=SectionPolicy(show_title=True),
            entries=[Entry(id="e1", fields=[FieldBlock(key="position", runs=[TextRun(text="Dev")])])],
        )
    ])
    model = resolve(doc, manifest, Customizations(), HTMLDocumentRenderer.support)
    html = HTMLDocumentRenderer().render(model)
    assert "<h2" in html
    assert "Experience" in html


def test_render_bytes_returns_utf8_bytes():
    html = HTMLDocumentRenderer().render_bytes(_model())
    assert isinstance(html, bytes)
    assert html.startswith(b"<!DOCTYPE html>")
