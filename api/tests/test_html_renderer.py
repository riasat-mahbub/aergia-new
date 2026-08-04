"""HTML renderer smoke tests.

Verify the renderer emits a complete HTML5 document with the right CSS
variables, escapes user-provided text, and respects the policy's
``show_title`` flag."""

from __future__ import annotations

import re

from app.schema.models import (
    Customizations,
    Document,
    Entry,
    FieldBlock,
    Section,
    SectionPolicy,
    SubsectionStyle,
    TemplateManifest,
    TextStyle,
    TextRun,
    Zone,
)
from app.services.renderer import resolve
from app.services.renderer.html import HTMLDocumentRenderer



def _model():
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="main", styles={"width": "full"})],
        placement={"profile": "main"},
        global_styles={"accent_color": "#aabbcc", "body_font": "sans-serif", "heading_font": "sans-serif"},
    )
    doc = Document(sections=[
        Section(
            id="p", type="profile", title="P", enabled=True,
            policy=SectionPolicy(show_title=False),
            entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada<script>")])])],
        )
    ])
    return resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())


def test_renders_doctype_and_body():
    html = HTMLDocumentRenderer().render(_model())
    assert "<!DOCTYPE html>" in html
    assert "<body>" in html
    assert "</body>" in html


def test_renders_css_vars_as_root_block():
    model = _model()
    assert "--accent: #aabbcc;" in HTMLDocumentRenderer().render(model)
    assert "--body-font: Inter, system-ui, sans-serif;" in HTMLDocumentRenderer().render(model)


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
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert "<h2" in html
    assert "Experience" in html


def test_render_bytes_returns_utf8_bytes():
    html = HTMLDocumentRenderer().render_bytes(_model())
    assert isinstance(html, bytes)
    assert html.startswith(b"<!DOCTYPE html>")


def test_html_renderer_uses_resolved_css_not_manifest_css():
    """The renderer reads from ``RenderModel`` (resolved CSS), not from the
    manifest directly. A manifest with the ``narrow`` token must produce
    CSS containing the resolved percentage value, not the token name.
    """
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="main", styles={"width": "narrow", "padding": "comfortable"})],
        placement={"profile": "main"},
        global_styles={"accent_color": "#aabbcc", "body_font": "sans-serif", "heading_font": "sans-serif"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    # The resolved zone width is 30%, not the literal "narrow" token.
    assert "30%" in html
    assert "narrow" not in html
    # The resolved padding is 24px.
    assert "24px" in html
    # The resolved body font stack is the rendered value, not the token.
    assert "Inter, system-ui, sans-serif" in html
    # The accent color resolved through the manifest's hex literal.
    assert "#aabbcc" in html


def test_same_group_fields_render_in_one_row():
    """Fields sharing a group render inside a single .field-row div."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="name", group="main", runs=[TextRun(text="Ada")]),
            FieldBlock(key="email", group="contact", runs=[TextRun(text="a@b.com")]),
            FieldBlock(key="phone", group="contact", runs=[TextRun(text="123")]),
            FieldBlock(key="summary", group="summary", runs=[TextRun(text="Pioneer")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    rows = re.findall(r'<div class="field-row"[^>]*>((?:<div class="f-[^"]*"[^>]*>.*?</div>)+)</div>', html, re.S)
    assert len(rows) == 3  # main, contact, summary
    contact_row = next(r for r in rows if "a@b.com" in r)
    assert "123" in contact_row
    assert "Ada" not in contact_row  # name is in its own row


def test_social_field_renders_icon_when_known():
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="social_links.0", group="social", icon="x",
                       runs=[TextRun(text="X")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert '<span class="f-icon"' in html
    assert "<svg" in html
    assert "X" in html


def test_social_field_with_unknown_icon_renders_text_only():
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(key="social_links.0", group="social", icon="nonexistent-icon-key",
                           runs=[TextRun(text="Fedi")]),
        ])]),

    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert "<svg" not in html
    assert "Fedi" in html


def test_ungrouped_fields_render_each_in_their_own_row():
    """group=None fields keep the pre-rows stacked look — each field gets
    its own .field-row wrapper, consecutive None fields are NOT merged."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"},
    )
    doc = Document(sections=[
        Section(id="x", type="experience", title="Work", entries=[Entry(id="e", fields=[
            FieldBlock(key="position", runs=[TextRun(text="Dev")]),
            FieldBlock(key="company", runs=[TextRun(text="Co")]),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    rows = re.findall(r'<div class="field-row"[^>]*>.*?</div>', html, re.S)
    assert len(rows) == 2
    assert "Dev" in rows[0] and "Co" in rows[1]


def test_right_rail_date_gets_margin_left_auto():
    """A field with align=right is pushed to the row's right edge."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"})
    doc = Document(sections=[Section(id="x", type="experience", title="Work", entries=[Entry(id="e", fields=[
        FieldBlock(key="position", group="header", runs=[TextRun(text="Engineer")]),
        FieldBlock(key="date", group="header", align="right", runs=[TextRun(text="2026")]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'margin-left:auto' in html
    # the rail field sits in the same row as the header field
    row = re.search(r'<div class="field-row"[^>]*>((?:<div class="f-[^"]*"[^>]*>.*?</div>)+)</div>', html, re.S).group(0)
    assert 'Engineer' in row and '2026' in row


def test_centered_section_justifies_rows_center():
    """No rail: row justify-content mirrors the section's text_align."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"})
    doc = Document(sections=[Section(id="p", type="profile", title="Profile",
        subsection=SubsectionStyle(text_align="center"),
        entries=[Entry(id="e", fields=[
            FieldBlock(key="name", group="main", runs=[TextRun(text="Ada")]),
        ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'justify-content:center' in html


def test_rail_row_ignores_section_text_align():
    """Rail wins: a right rail stays right even if the section is centered."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"})
    doc = Document(sections=[Section(id="x", type="experience", title="Work",
        subsection=SubsectionStyle(text_align="center"),
        entries=[Entry(id="e", fields=[
            FieldBlock(key="position", group="header", runs=[TextRun(text="Engineer")]),
            FieldBlock(key="date", group="header", align="right", runs=[TextRun(text="2026")]),
        ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'margin-left:auto' in html  # rail present
    assert 'justify-content:center' not in html  # not applied to the rail row


def test_default_rows_use_flex_start():
    """No text_align, no rail: flex-start (the previous behavior)."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"})
    doc = Document(sections=[Section(id="x", type="experience", title="Work", entries=[Entry(id="e", fields=[
        FieldBlock(key="company", group="secondary", runs=[TextRun(text="Co")]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'justify-content:flex-start' in html


def test_link_field_renders_anchor_with_right_rail_and_arrow():
    """Link fields render as real anchors on the right rail with the
    .f-link arrow — the 'link text' pattern for projects/research/certs."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"projects": "main"})
    doc = Document(sections=[Section(id="pr", type="projects", title="Projects", entries=[Entry(id="e", fields=[
        FieldBlock(key="project", group="header", runs=[TextRun(text="Aergia")]),
        FieldBlock(key="link", group="secondary", align="right",
                   runs=[TextRun(text="Repo", style=TextStyle(link="https://aergia.dev"))]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert 'href="https://aergia.dev"' in html
    assert 'class="f-link"' in html
    assert "margin-left:auto" in html
    assert ".f-link::after" not in html
    assert "content: \" \u2197\"" not in html
    assert '<span aria-hidden="true"> ↗</span>' in html


def test_field_typography_groups_match_section_grammar():
    """Header titles share the 600-weight rule; venue/issuer join the
    secondary line; link joins the small-meta group — the experience/
    education grammar applied to projects/certifications/research."""
    html = HTMLDocumentRenderer().render(_model())

    # Weight-600 header rule now covers the renamed section titles.
    assert ".f-degree, .f-project, .f-certification, .f-paper { font-weight: 600;" in html
    # venue/issuer render at the secondary (0.875rem) size.
    assert ".f-category, .f-venue, .f-issuer { font-size: 0.875rem;" in html
    # link renders at the small-meta (0.75rem) size, matching dates.
    assert ", .f-gpa, .f-link, .f-tech" in html
    # The dead .f-url class is gone (no builder emits key='url').

    assert ".f-url" not in html


def test_chip_keys_render_field_as_inline_pill():
    """LayoutHints.chip_keys = ['tech'] renders the tech field as an
    inline chip pill span, not a block-level div. CSS rule emitted too."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"projects": "main"},
    )
    doc = Document(sections=[Section(id="pr", type="projects", title="Projects", entries=[Entry(id="e", fields=[
        FieldBlock(key="project", group="header", runs=[TextRun(text="Aergia")]),
        FieldBlock(key="tech", group="body", runs=[TextRun(text="Python")]),
    ])])])
    # Inject chip_keys into the resolved layout
    from app.services.renderer.builders import build_section_style
    style, policy = build_section_style("projects", None, manifest)
    doc.sections[0] = doc.sections[0].model_copy(update={
        "layout": (doc.sections[0].layout or __import__("app.schema.models", fromlist=["LayoutHints"]).LayoutHints()).model_copy(update={"chip_keys": ["tech"]}),
        "policy": policy,
    })
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert '<span class="f-chip">Python</span>' in html
    assert ".f-chip {" in html


def test_skills_inline_renders_category_and_tags_on_one_line():
    """policy.skill_variant = 'inline' renders each entry as
    'Category: tag, tag, tag' on a single line."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"skills": "main"},
    )
    doc = Document(sections=[Section(id="sk", type="skills", title="Skills", entries=[Entry(id="e", fields=[
        FieldBlock(key="category", group="body", runs=[TextRun(text="Languages")]),
        FieldBlock(key="tag.0", group="body", runs=[TextRun(text="Python")]),
        FieldBlock(key="tag.1", group="body", runs=[TextRun(text="Rust")]),
    ])])])
    doc.sections[0] = doc.sections[0].model_copy(update={
        "policy": SectionPolicy(skill_variant="inline"),
    })
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'f-skills-inline' in html
    assert 'Languages' in html
    assert 'Python, Rust' in html


def test_heading_divider_emits_border_bottom_and_padding():
    """policy.heading_divider = True adds border-bottom + padding-bottom
    to the heading <h2> style."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"},
    )
    doc = Document(sections=[Section(id="x", type="experience", title="Experience", entries=[Entry(id="e", fields=[
        FieldBlock(key="position", group="header", runs=[TextRun(text="Dev")]),
    ])])])
    doc.sections[0] = doc.sections[0].model_copy(update={
        "policy": SectionPolicy(show_title=True, heading_divider=True),
    })
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert 'border-bottom:1px solid var(--accent,#1f2937)' in html
    assert 'padding-bottom:4px' in html
