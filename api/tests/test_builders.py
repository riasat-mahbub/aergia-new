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
    assert keys == ["name", "title", "email", "summary", "social_links.0"]
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
    assert keys == ["degree", "institution", "date", "gpa", "summary"]


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
    assert keys == ["name", "link", "date", "description", "tech.0", "tech.1"]


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
            {"id": "r1", "title": "Paper", "paper_url": "https://arxiv.org/abs/1", "paper_link_text": "PDF", "publication_date": "2023-01", "description": "Abstract"},
        ],
    }])
    doc = build_document(cv)
    keys = [f.key for f in doc.sections[0].entries[0].fields]
    assert keys == ["title", "link", "date", "description"]


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
