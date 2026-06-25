"""Resolver tests — Document + manifest + customizations + support → RenderModel."""

from __future__ import annotations

from types import SimpleNamespace

from app.schema.models import (
    Customizations,
    Document,
    Entry,
    FieldBlock,
    LayoutHints,
    Section,
    SectionInstance,
    TemplateManifest,
    TextRun,
    Zone,
)

from app.services.renderer import build_document, resolve
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.support import RendererSupport, SupportLevel
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


def test_css_vars_include_spacing_section_body_font_heading_font_accent():
    model = resolve(_document(), _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert model.css_vars["--spacing-section"] == "24px"
    assert model.css_vars["--spacing-subsection"] == "16px"
    assert model.css_vars["--body-font"] == "Inter, system-ui, sans-serif"
    assert model.css_vars["--heading-font"] == "Inter, system-ui, sans-serif"
    assert model.css_vars["--accent"] == "#aabbcc"


def test_compact_spacing_maps_to_smaller_vars():
    model = resolve(_document(), _manifest("compact"), Customizations(), HTMLDocumentRenderer.support)
    assert model.css_vars["--spacing-section"] == "16px"
    assert model.css_vars["--spacing-subsection"] == "12px"


def test_minimal_spacing_maps_to_smallest_vars():
    model = resolve(_document(), _manifest("minimal"), Customizations(), HTMLDocumentRenderer.support)
    assert model.css_vars["--spacing-section"] == "8px"
    assert model.css_vars["--spacing-subsection"] == "8px"


def test_user_customizations_spacing_overrides_manifest():
    custom = Customizations(spacing="compact")
    model = resolve(_document(), _manifest(), custom, HTMLDocumentRenderer.support)
    assert model.css_vars["--spacing-section"] == "16px"


def test_zones_resolve_section_ids_from_manifest_placement():
    model = resolve(_document(), _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert len(model.zones) == 1
    zone = model.zones[0]
    assert zone.id == "main"
    assert set(zone.section_ids) == {"p", "x", "sk"}


def test_template_font_family_paints_section_layout():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    model = resolve(doc, _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert model.sections["p"].layout.font_family == "Inter, system-ui, sans-serif"


def test_user_accent_overrides_template_only_when_section_unset():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                subsection={"section_color": "#aabbcc"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    custom = Customizations(accent_color="#ddeeff")
    model = resolve(doc, _manifest(), custom, HTMLDocumentRenderer.support)
    assert model.sections["p"].subsection.section_color == "#aabbcc"


def test_policy_show_title_is_false_for_profile_by_default():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    model = resolve(doc, _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert model.sections["p"].policy.show_title is False


def test_policy_show_title_is_true_for_experience_by_default():
    doc = Document(sections=[
        Section(id="x", type="experience", title="X", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="position", runs=[TextRun(text="D")])])])
    ])
    model = resolve(doc, _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert model.sections["x"].policy.show_title is True


def test_policy_skill_variant_defaults_to_block_for_skills():
    doc = Document(sections=[
        Section(id="s", type="skills", title="S", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="X")])])])
    ])
    model = resolve(doc, _manifest(), Customizations(), HTMLDocumentRenderer.support)
    assert model.sections["s"].policy.skill_variant == "block"


def test_manifest_v1_raises_manifest_version_error():
    import pytest

    with pytest.raises(Exception) as exc:
        resolve(_document(), {"version": 1, "name": "Old"}, Customizations(), HTMLDocumentRenderer.support)
    assert "version" in str(exc.value).lower() or "manifest" in str(exc.value).lower()


def test_per_section_style_overlay_paints_onto_section():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                subsection={"text_align": "left"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])])
    ])
    custom = Customizations(per_section={"p": {"subsection": {"text_align": "right"}}})
    model = resolve(doc, _manifest(), custom, HTMLDocumentRenderer.support)
    assert model.sections["p"].subsection.text_align == "right"


def test_support_with_skills_inline_none_forces_block_variant():
    support = RendererSupport(feature_skills_inline=SupportLevel.NONE)
    doc = Document(sections=[
        Section(id="s", type="skills", title="S", enabled=True,
                policy={"skill_variant": "inline"},
                entries=[Entry(id="e1", fields=[FieldBlock(key="category", runs=[TextRun(text="X")])])])
    ])
    model = resolve(doc, _manifest(), Customizations(), support)
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
    sec = resolve(doc, None, Customizations(), support).sections["p"]
    assert sec.layout.break_before is False
    assert sec.layout.keep_together is False
    assert sec.layout.heading_keeps_with_first is False


def test_support_full_preserves_layout_hints():
    doc = Document(sections=[
        Section(id="p", type="profile", title="P", enabled=True,
                layout=LayoutHints(break_before=True),
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="")])])])
    ])
    sec = resolve(doc, None, Customizations(), RendererSupport()).sections["p"]
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
