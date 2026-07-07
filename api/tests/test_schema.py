"""Round-trip tests for the new Pydantic schema models.

Build each model, serialize to JSON, deserialize, and assert equality.
Also assert the structural invariants the codegen relies on (manifest
version is 2, all Customizations fields are optional, three-axis style
is the right shape)."""

from __future__ import annotations


from app.schema.models import (
    Customizations,
    DateStyle,
    Document,
    Entry,
    FieldBlock,
    LayoutDefaults,
    LayoutHints,
    PolicyOverrides,
    RenderModel,
    ResolvedZone,
    Section,
    SectionPolicy,
    SubsectionStyle,
    TemplateManifest,
    TextRun,
    TextStyle,
    Zone,
    ZoneStyle,
)


def test_section_round_trips_via_json():
    section = Section(
        id="s1",
        type="profile",
        title="Profile",
        enabled=True,
        entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])],
        policy=SectionPolicy(show_title=False),
        subsection=SubsectionStyle(section_color="#abc"),
        layout=LayoutHints(font_family="Inter"),
    )
    payload = section.model_dump(mode="json")
    restored = Section.model_validate(payload)
    assert restored == section


def test_document_round_trips_via_json():
    doc = Document(sections=[
        Section(id="s1", type="profile", title="P", enabled=True,
                entries=[Entry(id="e1", fields=[FieldBlock(key="name", runs=[TextRun(text="Ada")])])]),
    ])
    payload = doc.model_dump(mode="json")
    assert Document.model_validate(payload) == doc


def test_template_manifest_version_must_be_two():
    m = TemplateManifest(name="Modern", zones=[Zone(id="main")])
    assert m.manifest_version == 2
    payload = m.model_dump(mode="json")
    assert payload["manifest_version"] == 2


def test_customizations_all_fields_optional():
    c = Customizations()
    assert c.accent_color is None
    assert c.body_font is None
    assert c.heading_font is None
    assert c.default_text_align is None
    assert c.spacing is None
    assert c.flags == {}
    assert c.per_section == {}


def test_layout_defaults_spacing_default_is_comfortable():
    assert LayoutDefaults().spacing == "comfortable"


def test_text_style_defaults_are_false():
    s = TextStyle()
    assert s.bold is False
    assert s.italic is False
    assert s.underline is False
    assert s.strike is False
    assert s.color is None
    assert s.link is None
    assert s.font_size is None




def test_render_model_round_trips():
    model = RenderModel(
        zones=[ResolvedZone(id="main", styles={"width": "100%"}, section_ids=["s1"])],
        css_vars={"--accent": "#aabbcc"},
        body_font="Inter, system-ui, sans-serif",
        heading_font="Inter, system-ui, sans-serif",
        link_styles="",
        print_styles="",
        sections={"s1": Section(id="s1", type="profile", title="P", enabled=True,
                                 entries=[Entry(id="e1", fields=[])])},
    )
    payload = model.model_dump(mode="json")
    assert RenderModel.model_validate(payload) == model


def test_date_style_defaults():
    assert DateStyle().key == "YYYY-MM"
    assert DateStyle().range_sep == " \u2013 "


def test_policy_overrides_default_empty():
    assert PolicyOverrides().by_type == {}


def test_zone_style_uses_closed_vocabulary():
    payload = {"width": "narrow", "background": "#aabbcc", "padding": "comfortable"}
    zone_style = ZoneStyle.model_validate(payload)
    dumped = zone_style.model_dump()
    assert dumped["width"] == "narrow"
    assert dumped["background"] == "#aabbcc"
    assert dumped["padding"] == "comfortable"


def test_customizations_rejects_legacy_top_level_colors():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Customizations.model_validate({"colors": {"accent": "#abc"}})


def test_customizations_rejects_legacy_top_level_fonts():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Customizations.model_validate({"fonts": {"body": "Inter"}})

def test_customizations_accepts_canonical_shape():
    c = Customizations.model_validate({"accent_color": "#aabbcc", "body_font": "sans-serif"})
    assert c.accent_color == "#aabbcc"
    assert c.body_font == "sans-serif"