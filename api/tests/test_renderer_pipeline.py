"""Tests for the canonical renderer composition boundary."""

from app.services.renderer import build_source_document, prepare_render_source, render_source_html


def test_render_source_accepts_wire_sections_without_a_cv_namespace():
    source = prepare_render_source([
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "data": {"name": "Ada", "title": "Engineer"},
        },
    ])

    document = build_source_document(source)
    html = render_source_html(source)

    assert source.sections[0].id == "profile"
    assert document.sections[0].type == "profile"
    assert "Ada" in html
