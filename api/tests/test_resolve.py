"""Resolver tests — Document + manifest + customizations + renderer → RenderModel."""

from __future__ import annotations

from types import SimpleNamespace

from app.schema.models import (
    Customizations,
    Document,
    Entry,
    FieldBlock,
    LayoutHints,
    Section,
    TemplateManifest,
    TextRun,
    Zone,
)

from app.services.renderer import resolve
from app.services.renderer.base import DocumentRenderer
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.support import RendererSupport, SupportLevel


class FakeRenderer(DocumentRenderer):
    """Test double — proves resolve() consumes the protocol, not a concrete class."""

    support = RendererSupport()

    def render(self, model):
        return f"<fake>{len(model.sections)}</fake>"


def _manifest(spacing="comfortable"):
    return TemplateManifest(
        name="M",
        zones=[Zone(id="main", styles={"width": "full", "padding": "comfortable"})],
        placement={
            "profile": "main",
            "experience": "main",
            "skills": "main",
        },
        layout_defaults={"spacing": spacing},
        global_styles={"accent_color": "#aabbcc", "body_font": "sans-serif", "heading_font": "sans-serif"},
    )


def _cv(sections):
    return SimpleNamespace(sections=sections)


def _document():
    return Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])]),
        Section(id="x", type="experience", title="X", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="position", runs=[TextRun(text="Dev")])])]),
        Section(id="sk", type="skills", title="S", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="Backend")])])]),
    ])


def test_resolve_accepts_fake_renderer():
    """The resolver consumes DocumentRenderer; any conforming object works."""
    model = resolve(_document(), FakeRenderer(), _manifest(), Customizations())
    assert set(model.sections.keys()) == {"p", "x", "sk"}
    assert model.zones


def test_css_vars_include_spacing_section_body_font_heading_font_accent():
    model = resolve(_document(), HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.css_vars["--spacing-section"] == "24px"
    assert model.css_vars["--spacing-subsection"] == "16px"
    assert model.css_vars["--body-font"] == "Inter, system-ui, sans-serif"
    assert model.css_vars["--heading-font"] == "Inter, system-ui, sans-serif"
    assert model.css_vars["--accent"] == "#aabbcc"


def test_compact_spacing_maps_to_smaller_vars():
    model = resolve(_document(), HTMLDocumentRenderer(), _manifest("compact"), Customizations())
    assert model.css_vars["--spacing-section"] == "16px"
    assert model.css_vars["--spacing-subsection"] == "12px"


def test_minimal_spacing_maps_to_smallest_vars():
    model = resolve(_document(), HTMLDocumentRenderer(), _manifest("minimal"), Customizations())
    assert model.css_vars["--spacing-section"] == "8px"
    assert model.css_vars["--spacing-subsection"] == "8px"


def test_user_customizations_spacing_overrides_manifest():
    custom = Customizations(spacing="compact")
    model = resolve(_document(), HTMLDocumentRenderer(), _manifest(), custom)
    assert model.css_vars["--spacing-section"] == "16px"


def test_user_customizations_body_font_overrides_manifest_global_styles():
    """Per-CV Customizations.body_font wins over manifest.global_styles.body_font."""
    doc = Document(sections=[
        Section(
            id="p", type="profile", title="Profile",
            entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])],
        ),
    ])
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="main")],
        placement={"profile": "main"},
        global_styles={"accent_color": "#aabbcc", "body_font": "serif", "heading_font": "serif"},
    )
    custom = Customizations(body_font="sans-serif")
    renderer = HTMLDocumentRenderer()
    model = resolve(doc, renderer, manifest, custom)
    assert model.sections["p"].layout.font_family == "Inter, system-ui, sans-serif"


def test_user_accent_overrides_template_section_color():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                subsection={"section_color": "#aabbcc"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    custom = Customizations(accent_color="#ddeeff")
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), custom)
    assert model.sections["p"].subsection.section_color == "#ddeeff"

def test_template_font_family_paints_section_layout():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["p"].layout.font_family == "Inter, system-ui, sans-serif"



def test_policy_show_title_is_false_for_profile_by_default():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["p"].policy.show_title is False


def test_policy_show_title_is_true_for_experience_by_default():
    doc = Document(sections=[
        Section(id="x", type="experience", title="X", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="position", runs=[TextRun(text="D")])])])
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["x"].policy.show_title is True


def test_policy_skill_variant_defaults_to_block_for_skills():
    doc = Document(sections=[
        Section(id="s", type="skills", title="S", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="X")])])])
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["s"].policy.skill_variant == "block"


def test_manifest_v1_raises_manifest_version_error():
    import pytest

    with pytest.raises(Exception) as exc:
        resolve(_document(), HTMLDocumentRenderer(), {"version": 1, "name": "Old"}, Customizations())
    assert "version" in str(exc.value).lower() or "manifest" in str(exc.value).lower()


def test_per_section_style_overlay_paints_onto_section():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                subsection={"text_align": "left"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    custom = Customizations(per_section={"p": {"subsection": {"text_align": "right"}}})
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), custom)
    assert model.sections["p"].subsection.text_align == "right"


def test_resolver_preserves_per_instance_policy():
    """An explicit per-instance SectionPolicy on the AST survives resolve().

    Two skills instances carry different skill_variant overrides; the
    resolver honours them instead of falling back to the type default.
    """
    from app.schema.models import SectionPolicy

    doc = Document(sections=[
        Section(id="s_block", type="skills", title="Backend",
                policy=SectionPolicy(skill_variant="block"),
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="Backend")])])]),
        Section(id="s_inline", type="skills", title="Frontend",
                policy=SectionPolicy(skill_variant="inline"),
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="Frontend")])])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["s_block"].policy.skill_variant == "block"
    assert model.sections["s_inline"].policy.skill_variant == "inline"


def test_resolver_preserves_per_instance_policy_when_fallback_type_default_differs():
    """An explicit show_title override on an instance beats the type default."""
    from app.schema.models import SectionPolicy

    # profile has show_title=False by default; override to True on this instance.
    doc = Document(sections=[
        Section(id="p_named", type="profile", title="P",
                policy=SectionPolicy(show_title=True),
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["p_named"].policy.show_title is True


def test_resolver_falls_back_to_type_default_when_no_per_instance_policy():
    """Without an explicit instance policy, resolve applies the type default."""
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="")])])]),
    ])
    model = resolve(doc, HTMLDocumentRenderer(), _manifest(), Customizations())
    assert model.sections["p"].policy.show_title is False


def test_support_with_skills_inline_none_forces_block_variant():
    support = RendererSupport(feature_skills_inline=SupportLevel.NONE)
    doc = Document(sections=[
        Section(id="s", type="skills", title="S", enabled=True,
                policy={"skill_variant": "inline"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="X")])])])
    ])
    renderer = FakeRenderer()
    renderer.support = support
    model = resolve(doc, renderer, _manifest(), Customizations())
    assert model.sections["s"].policy.skill_variant == "block"


def test_support_none_zeroes_layout_hints():
    support = RendererSupport(
        break_before=SupportLevel.NONE,
        keep_together=SupportLevel.NONE,
        heading_keeps_with_first=SupportLevel.NONE,
    )
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                layout=LayoutHints(
                    break_before=True,
                    keep_together=True,
                    heading_keeps_with_first=True,
                ),
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="")])])])
    ])
    renderer = FakeRenderer()
    renderer.support = support
    sec = resolve(doc, renderer, None, Customizations()).sections["p"]
    assert sec.layout.break_before is False
    assert sec.layout.keep_together is False
    assert sec.layout.heading_keeps_with_first is False


def test_support_full_preserves_layout_hints():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                layout=LayoutHints(break_before=True),
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="")])])])
    ])
    sec = resolve(doc, FakeRenderer(), None, Customizations()).sections["p"]
    assert sec.layout.break_before is True


def test_resolver_maps_width_tokens():
    """``narrow`` → 30%, ``half`` → 50%, ``full`` → 100%, ``auto`` → auto."""
    from app.services.renderer.resolve import _resolve_zone_styles
    from app.schema.models import Zone
    for token, expected in [("narrow", "30%"), ("half", "50%"), ("full", "100%"), ("auto", "auto")]:
        zone = Zone(id="z", styles={"width": token})
        assert _resolve_zone_styles(zone)["width"] == expected


def test_resolver_maps_padding_tokens():
    """``none`` → 0, ``tight`` → 12px, ``comfortable`` → 24px, ``loose`` → 32px."""
    from app.services.renderer.resolve import _resolve_zone_styles
    from app.schema.models import Zone
    for token, expected in [("none", "0"), ("tight", "12px"), ("comfortable", "24px"), ("loose", "32px")]:
        zone = Zone(id="z", styles={"padding": token})
        assert _resolve_zone_styles(zone)["padding"] == expected


def test_resolver_maps_color_palette_reference():
    """A ``palette.<name>`` reference resolves through :data:`DEFAULT_PALETTE`."""
    from app.services.renderer.resolve import _resolve_zone_styles
    from app.schema.models import Zone
    zone = Zone(id="z", styles={"background": "palette.surface-2"})
    assert _resolve_zone_styles(zone)["background-color"] == "#f8fafc"


def test_resolver_falls_back_to_hex_literal():
    """A ``#RRGGBB`` literal is returned unchanged."""
    from app.services.renderer.resolve import _resolve_zone_styles
    from app.schema.models import Zone
    zone = Zone(id="z", styles={"background": "#aabbcc"})
    assert _resolve_zone_styles(zone)["background-color"] == "#aabbcc"


def test_resolve_uses_customizations_layout_over_manifest():
    """Per-CV ``customizations.layout`` zones/placement win over the manifest.

    This is the contract the editor's zone authoring (Add Zone / drag-drop)
    depends on: the customize panel writes ``customizations.layout`` and the
    resolver must render those zones, not the template's static ones.
    """
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="template-zone")],
        placement={"profile": "template-zone"},
    )
    custom = Customizations(
        layout={
            "zones": [Zone(id="cv-zone")],
            "placement": {"p": "cv-zone"},
        }
    )
    model = resolve(_document(), FakeRenderer(), manifest, custom)
    assert [z.id for z in model.zones] == ["cv-zone"]
    assert model.zones[0].section_ids == ["p", "x", "sk"]


def test_resolve_placement_matches_instance_id_before_type():
    """Per-CV layout placement is keyed by instance id; the resolver must
    honor ``placement[section.id]`` as well as ``placement[section.type]``."""
    manifest = TemplateManifest(
        name="M",
        zones=[Zone(id="main"), Zone(id="side")],
        placement={"profile": "main", "experience": "main", "skills": "main"},
    )
    custom = Customizations(
        layout={
            "zones": [Zone(id="main"), Zone(id="side")],
            "placement": {"p": "side"},  # instance id, not the type key
        }
    )
    model = resolve(_document(), FakeRenderer(), manifest, custom)
    by_zone = {z.id: z.section_ids for z in model.zones}
    assert by_zone["side"] == ["p"]
    assert by_zone["main"] == ["x", "sk"]
