"""Builder contract tests for the ``extras`` section type.

This file is the consumer-side mirror of ``tests/test_builders.py`` for the
new first-class ``extras`` type. It locks:

- the ``FieldBlock.key`` order emitted by ``build_extras``;
- the empty-entry and malformed-row drop behaviour;
- URL-aware ``TextStyle.link`` injection via ``normalize_url_scheme``;
- dispatch via ``build_document`` / ``BUILDERS``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.schema.models import (
    Customizations,
    SectionInstance,
    TemplateManifest,
    TextStyle,
)
from app.services.renderer import HTMLDocumentRenderer, resolve
from app.services.renderer.builders import build_document, build_extras


def _cv(sections: list[dict]) -> Any:
    """Minimal stand-in for the CV row shape ``build_document`` consumes."""
    return SimpleNamespace(sections=sections)


def test_extras_emits_title_followed_by_labeled_fields_in_declared_order():
    inst = SectionInstance(
        id="e1",
        type="extras",
        title="Talks",
        enabled=True,
        data=[
            {
                "id": "t1",
                "title": "PyCon Talk",
                "fields": [
                    {"label": "Year", "value": "2024"},
                    {"label": "Venue", "value": "PyCon"},
                ],
            }
        ],
    )
    section = build_extras(inst)
    entry = section.entries[0]
    keys = [f.key for f in entry.fields]
    assert keys == ["title", "field:Year", "field:Venue"]


def test_extras_drops_empty_entries_and_skips_non_dict_rows():
    inst = SectionInstance(
        id="e1",
        type="extras",
        title="Talks",
        enabled=True,
        data=[
            {"id": "x", "title": "", "fields": []},  # empty — dropped
            {"id": "y", "title": "Real", "fields": [{"label": "Year", "value": "2024"}]},
            "not a dict",  # non-dict — skipped
            {"id": "z", "title": "TitleOnly"},  # title only — kept
            {"id": "w", "title": "", "fields": [{"label": "K", "value": "v"}]},  # no title but fields — kept
        ],
    )
    section = build_extras(inst)
    kept_ids = [e.id for e in section.entries]
    assert kept_ids == ["y", "z", "w"]


def test_extras_promotes_url_value_into_text_style_link():
    inst = SectionInstance(
        id="e1",
        type="extras",
        title="Links",
        enabled=True,
        data=[
            {
                "id": "l1",
                "title": "Site",
                "fields": [
                    {"label": "BareDomain", "value": "example.com"},
                    {"label": "ExplicitScheme", "value": "https://pycon.org"},
                    {"label": "WwwPrefix", "value": "www.example.org"},
                    {"label": "PlainText", "value": "a comment about nothing"},
                ],
            }
        ],
    )
    section = build_extras(inst)
    runs_by_key = {f.key: f.runs for f in section.entries[0].fields}
    site_run = runs_by_key["field:BareDomain"][0]
    sch_run = runs_by_key["field:ExplicitScheme"][0]
    www_run = runs_by_key["field:WwwPrefix"][0]
    plain_run = runs_by_key["field:PlainText"][0]
    assert isinstance(site_run.style, TextStyle) and site_run.style.link == "https://example.com"
    assert isinstance(sch_run.style, TextStyle) and sch_run.style.link == "https://pycon.org"
    assert isinstance(www_run.style, TextStyle) and www_run.style.link == "https://www.example.org"
    assert plain_run.style is None


def test_extras_skips_fields_with_empty_label_or_empty_value():
    inst = SectionInstance(
        id="e1",
        type="extras",
        title="Talks",
        enabled=True,
        data=[
            {
                "id": "t1",
                "title": "T",
                "fields": [
                    {"label": "", "value": "no label"},
                    {"label": "K", "value": ""},
                    {"label": "K", "value": "kept"},
                ],
            }
        ],
    )
    section = build_extras(inst)
    keys = [f.key for f in section.entries[0].fields]
    # `title`, plus the one surviving field; empty-label and empty-value
    # entries are dropped.
    assert keys == ["title", "field:K"]


def test_extras_registers_in_builders_dispatch():
    cv = _cv(
        [
            {
                "id": "e1",
                "type": "extras",
                "title": "Talks",
                "enabled": True,
                "data": [
                    {
                        "id": "t1",
                        "title": "PyCon Talk",
                        "fields": [{"label": "Year", "value": "2024"}],
                    }
                ],
            }
        ]
    )
    doc = build_document(cv)
    assert len(doc.sections) == 1
    assert doc.sections[0].type == "extras"
    assert doc.sections[0].id == "e1"


def test_extras_non_dict_field_entries_are_skipped_silently():
    """Non-dict field entries (string, None, list) are dropped — same
    precedent as build_skills dropping non-dict rows."""
    inst = SectionInstance(
        id="e1",
        type="extras",
        title="Talks",
        enabled=True,
        data=[
            {
                "id": "t1",
                "title": "T",
                "fields": [
                    "not a dict",
                    None,
                    ["nested"],
                    {"label": "K", "value": "kept"},
                ],
            }
        ],
    )
    section = build_extras(inst)
    keys = [f.key for f in section.entries[0].fields]
    assert keys == ["title", "field:K"]


def test_extras_full_pipeline_renders_to_html_without_branch():
    """The existing ``HTMLDocumentRenderer`` must handle ``extras`` via the
    generic field-row path — no per-type branch should be required."""
    cv = _cv(
        [
            {
                "id": "e1",
                "type": "extras",
                "title": "Talks",
                "enabled": True,
                "data": [
                    {
                        "id": "t1",
                        "title": "PyCon",
                        "fields": [
                            {"label": "Year", "value": "2024"},
                            {"label": "Site", "value": "https://pycon.org"},
                        ],
                    }
                ],
            }
        ]
    )
    manifest = TemplateManifest(name="M", zones=[])
    doc = build_document(cv, manifest)
    renderer = HTMLDocumentRenderer()
    model = resolve(doc, renderer, manifest, Customizations())
    html = renderer.render(model)
    assert "PyCon" in html
    assert "field:Year" in html
    assert "field:Site" in html
    assert 'href="https://pycon.org"' in html


def test_build_extras_is_exported_from_builder_package():
    from app.services.renderer.builders import BUILDERS
    from app.services.renderer.builders.extras import build_extras

    assert BUILDERS["extras"] is build_extras
