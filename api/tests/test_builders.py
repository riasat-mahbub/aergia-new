"""Builder tests — one fixture per section type.

Each test verifies that ``build_document`` produces a ``Document`` with the
expected ``Section`` shape: one ``Section`` per ``SectionInstance``, the
expected ``FieldBlock`` keys, and a stable ``TextRun`` count. No HTML
matching — that's the renderer's job.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.renderer.builders import build_document


def _cv(sections):
    return SimpleNamespace(sections=sections)


def test_profile_emits_name_title_summary_and_social_fields():
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "title": "Engineer",
            "email": "a@b.com",
            "summary": "Summary",
            "social_links": [{"url": "https://x.dev", "label": "X"}],
        },
    }])
    doc = build_document(cv)
    assert len(doc.sections) == 1
    section = doc.sections[0]
    assert section.type == "profile"
    keys = [f.key for f in section.entries[0].fields]
    assert keys == ["name", "title", "email", "social_links.0", "summary"]
    assert section.entries[0].fields[0].runs[0].text == "Ada"


def test_experience_emits_one_entry_per_row_with_date_text_run():
    cv = _cv([{
        "id": "x",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"id": "e1", "position": "Dev", "company": "Co", "start_date": "2020-01", "end_date": "2022-06", "description": "did stuff"},
            {"id": "e2", "position": "Sr", "company": "Other", "start_date": "2022-07", "current": True},
        ],
    }])
    doc = build_document(cv)
    entries = doc.sections[0].entries
    assert len(entries) == 2
    first_keys = [f.key for f in entries[0].fields]
    assert "position" in first_keys and "company" in first_keys and "date" in first_keys and "description" in first_keys
    second_keys = [f.key for f in entries[1].fields]
    assert "date" in second_keys


def test_education_emits_degree_institution_date_gpa_summary():
    cv = _cv([{
        "id": "edu",
        "type": "education",
        "title": "Education",
        "enabled": True,
        "data": [
            {"id": "sc1", "degree": "BS", "institution": "MIT", "start_date": "2010-09", "end_date": "2014-06", "gpa": "3.9", "summary": "Honors"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["degree", "date", "institution", "gpa", "summary"]


def test_skills_emits_category_plus_tag_per_item():
    cv = _cv([{
        "id": "sk",
        "type": "skills",
        "title": "Skills",
        "enabled": True,
        "data": [
            {"id": "g1", "category": "Backend", "items": ["Python", "Go"]},
            {"id": "g2", "category": "Frontend", "items": ["React"]},
        ],
    }])
    doc = build_document(cv)
    assert len(doc.sections[0].entries) == 2
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["category", "tag.0", "tag.1"]


def test_projects_emits_name_link_date_description_tech():
    cv = _cv([{
        "id": "pr",
        "type": "projects",
        "title": "Projects",
        "enabled": True,
        "data": [
            {
                "id": "p1",
                "name": "X",
                "url": "https://x.dev",
                "link_text": "Repo",
                "start_date": "2024-01",
                "end_date": "2024-12",
                "description": "Did things",
                "tech_stack": ["Python", "FastAPI"],
            }
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["name", "date", "link", "description", "tech.0", "tech.1"]


def test_languages_emits_language_and_proficiency():
    cv = _cv([{
        "id": "lng",
        "type": "languages",
        "title": "Languages",
        "enabled": True,
        "data": [
            {"id": "l1", "language": "English", "proficiency": "Native"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["language", "proficiency"]


def test_certifications_emits_name_meta_link():
    cv = _cv([{
        "id": "cert",
        "type": "certifications",
        "title": "Certifications",
        "enabled": True,
        "data": [
            {"id": "c1", "name": "AWS SAA", "issuer": "AWS", "date": "2023-05", "credential_url": "https://aws.example"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["name", "meta", "link"]


def test_research_emits_title_link_date_description():
    cv = _cv([{
        "id": "res",
        "type": "research",
        "title": "Research",
        "enabled": True,
        "data": [
            {"id": "r1", "title": "Paper", "paper_url": "https://arxiv.org/abs/1", "paper_link_text": "PDF", "publication_date": "2023-01", "publication_value": "NeurIPS 2024", "description": "Abstract"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["title", "date", "venue", "link", "description"]


def test_research_omits_venue_when_publication_value_is_empty():
    cv = _cv([{
        "id": "res",
        "type": "research",
        "title": "Research",
        "enabled": True,
        "data": [
            {"id": "r1", "title": "Paper", "paper_url": "https://arxiv.org/abs/1", "publication_date": "2023-01", "description": "Abstract"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["title", "date", "link", "description"]


def test_disabled_section_is_dropped():
    cv = _cv([
        {"id": "s1", "type": "profile", "title": "P", "enabled": False, "data": {"name": "X"}},
        {"id": "s2", "type": "skills", "title": "S", "enabled": True, "data": []},
    ])
    doc = build_document(cv)
    assert len(doc.sections) == 1
    assert doc.sections[0].id == "s2"


def test_unknown_section_type_raises_value_error():
    cv = _cv([{"id": "s1", "type": "wat", "title": "X", "enabled": True, "data": {}}])
    with pytest.raises(ValueError):
        build_document(cv)


def test_build_section_style_uses_per_instance_policy_over_type_default():
    """An explicit per-instance policy on the wire wins over the type default.

    Two skills instances: one with no policy (default block), one with
    skill_variant=inline. The build stage must attach the instance policy
    to the AST node before the resolver applies capability gating.
    """
    from app.services.renderer.builders import build_section_style
    from app.schema.models import SectionInstanceStyle, SectionPolicy

    style_with, _ = build_section_style(
        instance_type="skills",
        instance_style=SectionInstanceStyle(
            policy=SectionPolicy(skill_variant="inline"),
        ),
        manifest=None,
    )
    assert style_with.policy.skill_variant == "inline"

    style_without, _ = build_section_style(
        instance_type="skills",
        instance_style=None,
        manifest=None,
    )
    assert style_without.policy.skill_variant == "block"


def test_build_section_style_uses_manifest_override_when_no_instance_policy():
    """Without an instance policy, build_section_style applies the manifest override."""
    from app.services.renderer.builders import build_section_style
    from app.schema.models import TemplateManifest

    manifest = TemplateManifest(
        name="M",
        policy_overrides={"by_type": {"skills": {"skill_variant": "inline"}}},
    )
    _, policy = build_section_style(
        instance_type="skills",
        instance_style=None,
        manifest=manifest,
    )
    assert policy.skill_variant == "inline"


def test_build_document_applies_manifest_policy_overrides():
    """``build_document`` must apply the manifest's ``policy_overrides``.

    The UI preview path passes the manifest to ``build_document``; the PDF
    path must do the same or the template's per-type policy (e.g. skills
    inline) is silently lost and the PDF renders the default policy while
    the preview renders the override.
    """
    from app.schema.models import TemplateManifest

    manifest = TemplateManifest(
        name="M",
        policy_overrides={"by_type": {"skills": {"skill_variant": "inline"}}},
    )
    cv = _cv([{
        "id": "s1",
        "type": "skills",
        "title": "Skills",
        "enabled": True,
        "data": [],
    }])
    doc = build_document(cv, manifest)
    assert doc.sections[0].policy.skill_variant == "inline"


def test_build_document_without_manifest_uses_type_default():
    """Without a manifest the type default applies — the divergence guard:
    the PDF path must pass the manifest, otherwise ``build_document(cv, None)``
    silently drops template policy overrides."""
    cv = _cv([{
        "id": "s1",
        "type": "skills",
        "title": "Skills",
        "enabled": True,
        "data": [],
    }])
    doc = build_document(cv, None)
    assert doc.sections[0].policy.skill_variant != "inline"


def test_build_document_attaches_per_field_styles_to_runs():
    """Per-field ``style.text[field_key]`` (bold/italic/color/font-size)
    must land on the AST runs — the renderer reads ``TextRun.style``.

    Without this, field-style edits from the customize panel never reach
    the preview or the PDF.
    """
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Ada", "title": "Engineer", "summary": "Pioneer"},
        "style": {
            "text": {
                "name": {"bold": True, "color": "#ff0000", "font_size": "xl"},
                "title": {"italic": True},
            }
        },
    }])
    doc = build_document(cv)
    section = doc.sections[0]
    fields = {f.key: f for f in section.entries[0].fields}

    name_run = fields["name"].runs[0]
    assert name_run.style is not None
    assert name_run.style.bold is True
    assert name_run.style.color == "#ff0000"
    assert name_run.style.font_size == "xl"

    title_run = fields["title"].runs[0]
    assert title_run.style is not None
    assert title_run.style.italic is True
    # Fields without a declared style keep a plain run.
    assert fields["summary"].runs[0].style is None


def test_profile_section_defaults_to_centered_text():
    """Profile content is centered by default (type-level default, not a
    user override)."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Ada"},
    }])
    doc = build_document(cv)
    assert doc.sections[0].subsection.text_align == "center"


def test_profile_section_respects_explicit_text_align():
    """A per-section text_align pick overrides the center default."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Ada"},
        "style": {"subsection": {"text_align": "left"}},
    }])
    doc = build_document(cv)
    assert doc.sections[0].subsection.text_align == "left"


def test_profile_fields_carry_row_groups_and_icons():
    """Profile fields are grouped into semantic rows: main (name), subtitle
    (title), contact (email/phone/location/site), social (links + icons),
    summary. This restores the sophisticated profile layout."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "title": "Engineer",
            "email": "a@b.com",
            "phone": "123",
            "location": "London",
            "site_text": "ada.dev",
            "summary": "Pioneer",
            "social_links": [
                {"label": "X", "url": "https://x.com/ada", "icon": "x"},
                {"label": "GitHub", "url": "https://github.com/ada", "icon": "github"},
            ],
        },
    }])
    doc = build_document(cv)
    fields = {f.key: f for f in doc.sections[0].entries[0].fields}

    assert fields["name"].group == "main"
    assert fields["title"].group == "subtitle"
    assert fields["email"].group == "contact"
    assert fields["phone"].group == "contact"
    assert fields["location"].group == "contact"
    assert fields["site_text"].group == "contact"
    assert fields["summary"].group == "summary"

    assert fields["social_links.0"].group == "social"
    assert fields["social_links.0"].icon == "x"
    assert fields["social_links.1"].group == "social"
    assert fields["social_links.1"].icon == "github"


def test_profile_social_links_without_icon_name_get_no_icon():
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "social_links": [{"label": "Site", "url": "https://ada.dev"}],
        },
    }])
    doc = build_document(cv)
    fields = {f.key: f for f in doc.sections[0].entries[0].fields}
    assert fields["social_links.0"].group == "social"
    assert fields["social_links.0"].icon is None


def test_experience_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "experience", "title": "Work", "enabled": True,
        "data": [{
            "id": "e1", "company": "BS23", "position": "Dev", "location": "Dhaka",
            "start_date": "2026-01", "end_date": None, "current": True,
            "description": "Built things",
        }],
    }])
    entry = build_document(cv).sections[0].entries[0]
    fields = {f.key: f for f in entry.fields}
    assert [f.key for f in entry.fields] == ["position", "date", "company", "location", "description"]
    assert fields["position"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["company"].group == "secondary"
    assert fields["location"].group == "secondary"
    assert fields["description"].group == "body"


def test_education_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "education", "title": "Ed", "enabled": True,
        "data": [{
            "id": "e1", "degree": "BSc", "institution": "U", "start_date": "2020-01",
            "end_date": "2024-01", "gpa": "3.9", "summary": "Studied",
        }],
    }])
    entry = build_document(cv).sections[0].entries[0]
    fields = {f.key: f for f in entry.fields}
    assert [f.key for f in entry.fields] == ["degree", "date", "institution", "gpa", "summary"]
    assert fields["degree"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["institution"].group == "secondary"
    assert fields["gpa"].group == "meta"
    assert fields["summary"].group == "summary"


def test_skills_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "skills", "title": "Skills", "enabled": True,
        "data": [{"id": "g1", "category": "Lang", "items": ["Python", "SQL"]}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["category"].group == "body"
    assert fields["tag.0"].group == fields["category"].group
    assert fields["tag.1"].group == fields["category"].group


def test_projects_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "projects", "title": "P", "enabled": True,
        "data": [{
            "id": "e1", "name": "Aergia", "url": "https://aergia.dev", "link_text": "site",
            "start_date": "2026-01", "end_date": None, "description": "CV builder",
            "tech_stack": ["Python", "React"],
        }],
    }])
    entry = build_document(cv).sections[0].entries[0]
    fields = {f.key: f for f in entry.fields}
    assert [f.key for f in entry.fields] == ["name", "date", "link", "description", "tech.0", "tech.1"]
    assert fields["name"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["link"].group == "secondary"
    assert fields["description"].group == "body"
    assert fields["tech.0"].group == "body"
    assert fields["tech.1"].group == "body"


def test_languages_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "languages", "title": "L", "enabled": True,
        "data": [{"id": "e1", "language": "English", "proficiency": "Native"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["language"].group == "header"
    assert fields["proficiency"].group == "header"
    assert fields["proficiency"].align == "right"


def test_certifications_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "certifications", "title": "C", "enabled": True,
        "data": [{"id": "e1", "name": "AWS", "issuer": "Amazon", "date": "2026-01", "credential_url": "https://x"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["name"].group == "header"
    assert fields["meta"].group == "secondary"
    assert fields["link"].group == "body"


def test_research_fields_carry_row_groups():
    cv = _cv([{
        "id": "s1", "type": "research", "title": "R", "enabled": True,
        "data": [{
            "id": "e1", "title": "Paper", "paper_url": "https://x", "paper_link_text": "pdf",
            "description": "Work", "publication_date": "2026-09", "publication_value": "Conf",
        }],
    }])
    entry = build_document(cv).sections[0].entries[0]
    fields = {f.key: f for f in entry.fields}
    assert [f.key for f in entry.fields] == ["title", "date", "venue", "link", "description"]
    assert fields["title"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["venue"].group == "secondary"
    assert fields["link"].group == "secondary"
    assert fields["description"].group == "body"


def test_profile_renders_social_links_before_summary():
    """Document order: name, contact, social links, THEN summary — the
    profile summary must not appear above the social row."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "email": "a@b.com",
            "summary": "Pioneer",
            "social_links": [{"label": "X", "url": "https://x.com", "icon": "x"}],
        },
    }])
    keys = [f.key for f in build_document(cv).sections[0].entries[0].fields]
    assert keys.index("social_links.0") < keys.index("summary")
