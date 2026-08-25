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


def test_social_field_with_link_wraps_icon_and_label_in_anchor():
    """A known social icon plus its URL wraps the icon SVG and the label in
    a single ``<a href>`` so the icon itself becomes a clickable hyperlink
    in the rendered PDF. The icon+label pair intentionally omits the trailing
    ↗ glyph (it would clutter the icon row); without a URL the field falls
    back to a plain ``<span class="f-social">``."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(
                key="social_links.0",
                group="social",
                icon="x",
                runs=[TextRun(text="X", style=TextStyle(link="https://x.com/me"))],
            ),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert '<a href="https://x.com/me">' in html
    # Icon and label live inside the anchor; the glyph is intentionally absent.
    anchor = re.search(r'<a href="https://x\.com/me">(.+?)</a>', html, re.S)
    assert anchor is not None
    body = anchor.group(1)
    assert '<span class="f-icon"' in body
    assert "<svg" in body
    assert "X" in body
    assert '<span aria-hidden="true"> ↗</span>' not in body

def test_social_field_without_link_renders_span_only():
    """When no link is set the field is NOT wrapped in an anchor (avoids a
    dead ``<a href="">``). The plain-text icon+label still renders."""
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

    assert '<a href=' not in html
    assert '<span class="f-icon"' in html
    assert "<svg" in html
    assert "X" in html


def test_site_field_with_url_renders_anchor():
    """A ``site`` field whose run carries a link wraps the label in an
    ``<a href>`` with the trailing ↗ glyph so the URL is clickable in the
    rendered PDF."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"profile": "main"},
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="Profile", entries=[Entry(id="e", fields=[
            FieldBlock(
                key="site",
                group="contact",
                runs=[TextRun(
                    text="aergia.dev",
                    style=TextStyle(link="https://aergia.dev"),
                )],
            ),
        ])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)

    assert '<a href="https://aergia.dev"' in html
    assert 'class="f-site"' in html
    assert '<span aria-hidden="true"> ↗</span>' in html


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


def test_link_field_renders_anchor_in_two_column_right_block():
    """Link fields render as real anchors in the right column of a
    two-column entry, with the trailing .f-link arrow. The two-column
    layout supersedes the old right-rail pattern (no ``margin-left:auto``);
    the link is just one of the fields right-justified in entry-right."""
    manifest = TemplateManifest(name="M", zones=[Zone(id="main", styles={})], placement={"projects": "main"})
    doc = Document(sections=[Section(id="pr", type="projects", title="Projects", entries=[Entry(id="e", fields=[
        FieldBlock(key="project", group="header", runs=[TextRun(text="Aergia")]),
        FieldBlock(key="link", group="secondary", align="right",
                   runs=[TextRun(text="Repo", style=TextStyle(link="https://aergia.dev"))]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    # The link renders as a real anchor
    assert "grid-template-columns:5fr 1fr" in html
    assert 'class="f-link"' in html
    # In two-column, the link sits in the right column (right-justified
    # via the column's align-items:flex-end), not the old rail pattern
    assert "entry-right" in html
    right_m = re.search(r'<div class="entry-right"[^>]*>(.+?)</div></div>', html, re.S)
    assert right_m is not None
    assert "f-link" in right_m.group(1)
    # No more ::after pseudo-element or CSS variable arrow
    assert ".f-link::after" not in html
    assert "content: \" \u2197\"" not in html
    # The inline arrow is still present
    assert '<span aria-hidden="true"> ↗</span>' in html


def test_field_typography_groups_match_section_grammar():
    """Header titles share the 600-weight rule; venue/issuer join the
    secondary line; link joins the small-meta group — the experience/
    education grammar applied to projects/certifications/research."""
    html = HTMLDocumentRenderer().render(_model())

    # Weight-600 header rule now covers the renamed section titles.
    # ``.f-category`` is also in this rule: the skills category label is a
    # header-style token (it groups tags), so it gets the same emphasis.
    assert ".f-degree, .f-project, .f-certification, .f-paper, .f-category { font-weight: 600;" in html
    # venue/issuer render at the secondary (0.875rem) size; category shares it.
    assert ".f-category, .f-venue, .f-issuer { font-size: 0.875rem;" in html
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
    'Category: tag, tag, tag' on a single line. Each tag is a separate
    span so per-run :class:`TextStyle` (font-size/color/bold) survives
    the inline layout."""
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
    # Each tag carries its own run span; comma separator is its own span.
    assert '<span class="f-tag">Python</span>' in html
    assert '<span class="f-tag">Rust</span>' in html
    assert '<span class="f-tag-sep">,</span>' in html

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
    # Bottom margin is 0 when the divider is on; the border + padding
    # supply the gap. Without this lock the heading emits ``margin:0 0 2px``
    # on top of the divider's border + padding, pushing the body 7px below
    # the title row instead of the intended ~5px.
    h2_m = re.search(r'<h2[^>]*>', html)
    assert h2_m is not None
    assert 'margin:0 0 0' in h2_m.group(0)
    assert 'margin:0 0 2px' not in h2_m.group(0)


def test_two_column_entry_splits_date_and_link_into_right_column():
    """policy.entry_layout='two-column' emits a grid with
    grid-template-columns:5fr 1fr. The right column holds
    ONLY the date and link fields; everything else (paper title,
    venue, description) goes in the left column."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"research": "main"},
    )
    doc = Document(sections=[Section(id="r", type="research", title="Research", policy=SectionPolicy(entry_layout="two-column"), entries=[Entry(id="e", fields=[
        FieldBlock(key="paper", group="header", runs=[TextRun(text="Title")]),
        FieldBlock(key="date", group="header", align="right", runs=[TextRun(text="2026")]),
        FieldBlock(key="venue", group="secondary", runs=[TextRun(text="NeurIPS")]),
        FieldBlock(key="link", group="secondary", align="right",
                   runs=[TextRun(text="PDF", style=TextStyle(link="https://x"))]),
        FieldBlock(key="description", group="body", runs=[TextRun(text="Summary.")]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    # Grid: 2:1 ratio — left 2/3, right 1/3
    assert "entry-two-col" in html
    assert "display:grid" in html
    assert "grid-template-columns:5fr 1fr" in html
    # Left column: paper, venue, description (NOT date, NOT link)
    left_m = re.search(r'<div class="entry-left"[^>]*>(.+?)<div class="entry-right"', html, re.S)
    assert left_m is not None
    assert "f-paper" in left_m.group(1)
    assert "f-venue" in left_m.group(1)
    assert "f-description" in left_m.group(1)
    assert "f-date" not in left_m.group(1)
    assert "f-link" not in left_m.group(1)
    # Right column: ONLY date and link, right-justified
    right_m = re.search(r'<div class="entry-right"[^>]*>(.+?)</div></div>', html, re.S)
    assert right_m is not None
    assert "f-date" in right_m.group(1)
    assert "f-link" in right_m.group(1)
    assert "f-paper" not in right_m.group(1)
    assert "f-venue" not in right_m.group(1)
    assert "f-description" not in right_m.group(1)
    assert "align-items:flex-end" in right_m.group(0)


def test_two_column_research_without_venue_keeps_description_in_left_column():
    """A research entry with no publication_value still renders the
    description in the left column; only the link goes in the right
    column (no date either when absent). The right column simply has
    fewer fields — no gap band appears between the link and the
    description because they live in independent flex containers."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"research": "main"},
    )
    doc = Document(sections=[Section(id="r", type="research", title="Research", policy=SectionPolicy(entry_layout="two-column"), entries=[Entry(id="e", fields=[
        FieldBlock(key="paper", group="header", runs=[TextRun(text="Title")]),
        FieldBlock(key="date", group="header", align="right", runs=[TextRun(text="2026")]),
        FieldBlock(key="link", group="secondary", align="right",
                   runs=[TextRun(text="PDF", style=TextStyle(link="https://x"))]),
        FieldBlock(key="description", group="body", runs=[TextRun(text="Summary.")]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    assert "entry-two-col" in html
    left_m = re.search(r'<div class="entry-left"[^>]*>(.+?)<div class="entry-right"', html, re.S)
    right_m = re.search(r'<div class="entry-right"[^>]*>(.+?)</div></div>', html, re.S)
    # Left column: paper + description (date and link are right)
    assert "f-paper" in left_m.group(1)
    assert "f-description" in left_m.group(1)
    assert "f-date" not in left_m.group(1)
    assert "f-link" not in left_m.group(1)
    # Right column: ONLY date and link
    assert "f-date" in right_m.group(1)
    assert "f-link" in right_m.group(1)
    assert "f-paper" not in right_m.group(1)
    assert "f-description" not in right_m.group(1)


def test_stack_layout_is_default_for_experience():
    """The stack entry layout (the existing rail pattern) is preserved
    for sections whose SECTION_POLICIES default is 'stack' — experience,
    education, profile, skills, languages, extras."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"},
    )
    # experience with no explicit policy — falls through to SECTION_POLICIES
    doc = Document(sections=[Section(id="x", type="experience", title="Experience", entries=[Entry(id="e", fields=[
        FieldBlock(key="position", group="header", runs=[TextRun(text="Dev")]),
        FieldBlock(key="company", group="header", runs=[TextRun(text="Co")]),
        FieldBlock(key="date", group="secondary", align="right", runs=[TextRun(text="2026")]),
        FieldBlock(key="description", group="body", runs=[TextRun(text="Did things.")]),
    ])])])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    html = HTMLDocumentRenderer().render(model)
    # Stack: no entry-two-col class
    assert "entry-two-col" not in html
    # Stack uses display:flex;flex-direction:column
    entry_m = re.search(r'<div class="entry"[^>]*>', html)
    assert entry_m is not None
    assert "display:flex" in entry_m.group(0)
    assert "flex-direction:column" in entry_m.group(0)


# ---------------------------------------------------------------------------
# Rich text block rendering tests
# ---------------------------------------------------------------------------


def _render_field_html(field: FieldBlock) -> str:
    """Render a single FieldBlock through the full pipeline and return the HTML."""
    manifest = TemplateManifest(
        name="M", zones=[Zone(id="main", styles={})], placement={"experience": "main"},
    )
    doc = Document(sections=[Section(
        id="x", type="experience", title="Experience",
        entries=[Entry(id="e", fields=[field])],
    )])
    model = resolve(doc, HTMLDocumentRenderer(), manifest, Customizations())
    return HTMLDocumentRenderer().render(model)


def test_rich_text_paragraph_renders_p_tag():
    field = FieldBlock(
        key="description", group="body", runs=[], rich_text=True,
        blocks=[{"type": "paragraph", "items": [{"text": "Hello "}, {"text": "world", "style": {"bold": True}}]}],
    )
    html = _render_field_html(field)
    assert "<p>" in html
    assert "</p>" in html
    assert "Hello " in html
    assert "world" in html


def test_rich_text_bullet_list_renders_ul_li():
    field = FieldBlock(
        key="description", group="body", runs=[], rich_text=True,
        blocks=[{"type": "bullet_list", "items": [{"text": "Item 1"}, {"text": "Item 2"}]}],
    )
    html = _render_field_html(field)
    assert "<ul><li>Item 1</li><li>Item 2</li></ul>" in html


def test_rich_text_numbered_list_renders_ol_li():
    field = FieldBlock(
        key="description", group="body", runs=[], rich_text=True,
        blocks=[{"type": "numbered_list", "items": [{"text": "First"}, {"text": "Second"}]}],
    )
    html = _render_field_html(field)
    assert "<ol><li>First</li><li>Second</li></ol>" in html


def test_rich_text_mixed_blocks_renders_sequentially():
    field = FieldBlock(
        key="description", group="body", runs=[], rich_text=True,
        blocks=[
            {"type": "paragraph", "items": [{"text": "Summary text"}]},
            {"type": "bullet_list", "items": [{"text": "Bullet item"}]},
        ],
    )
    html = _render_field_html(field)
    assert "<p>Summary text</p>" in html
    assert "<ul><li>Bullet item</li></ul>" in html


def test_rich_text_bold_inline_renders_span():
    field = FieldBlock(
        key="description", group="body", runs=[], rich_text=True,
        blocks=[{"type": "paragraph", "items": [{"text": "normal "}, {"text": "bold", "style": {"bold": True}}]}],
    )
    html = _render_field_html(field)
    assert "font-weight:700" in html
    assert "bold" in html


def test_legacy_string_description_renders_unchanged():
    """Legacy string descriptions still render as before."""
    field = FieldBlock(key="description", group="body", runs=[TextRun(text="Legacy text")])
    html = _render_field_html(field)
    assert "Legacy text" in html
    assert "f-description" in html
