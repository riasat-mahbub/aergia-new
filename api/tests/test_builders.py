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
    fields = section.entries[0].fields
    keys = [f.key for f in fields]
    assert keys == ["name", "title", "email", "social", "summary"]
    assert fields[0].runs[0].text == "Ada"


def test_profile_social_run_carries_url_for_clickable_icon():
    """Each social link's TextRun must carry the URL on ``style.link`` so the
    renderer can wrap the icon and the label in a single ``<a href>``. Without
    this the icon is plain text in the rendered PDF and not clickable."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "social_links": [
                {"url": "https://github.com/ada", "label": "GitHub", "icon": "github"},
                {"url": "https://linkedin.com/in/ada", "label": "LinkedIn", "icon": "linkedin"},
            ],
        },
    }])
    section = build_document(cv).sections[0]
    social_fields = [f for f in section.entries[0].fields if f.key == "social"]
    assert len(social_fields) == 2
    assert social_fields[0].icon == "github"
    assert social_fields[0].runs[0].style.link == "https://github.com/ada"
    assert social_fields[1].icon == "linkedin"
    assert social_fields[1].runs[0].style.link == "https://linkedin.com/in/ada"


def test_profile_site_field_carries_url_when_present():
    """When ``site_url`` is set, the ``site`` field's run carries it on
    ``style.link`` so the renderer wraps the label in ``<a href>``. With
    only ``site_text`` (no URL) it stays a plain text label."""
    cv = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {
            "name": "Ada",
            "site_text": "aergia.dev",
            "site_url": "https://aergia.dev",
        },
    }])
    section = build_document(cv).sections[0]
    site = next(f for f in section.entries[0].fields if f.key == "site")
    assert site.runs[0].text == "aergia.dev"
    assert site.runs[0].style.link == "https://aergia.dev"

    # Without a URL, ``site_text`` becomes a plain ``site_text`` field.
    cv_no_url = _cv([{
        "id": "s1",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": "Ada", "site_text": "Plain label"},
    }])
    section = build_document(cv_no_url).sections[0]
    site_text = next(f for f in section.entries[0].fields if f.key == "site_text")
    assert site_text.runs[0].text == "Plain label"
    assert site_text.runs[0].style is None


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
    assert keys == ["project", "link", "date", "description", "tech", "tech"]


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
    assert keys == ["certification", "date", "issuer", "link"]


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
    assert keys == ["paper", "date", "venue", "link", "description"]


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
    assert keys == ["paper", "date", "link", "description"]


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

    field_list = doc.sections[0].entries[0].fields
    social_fields = [f for f in field_list if f.group == "social"]
    assert len(social_fields) == 2
    assert {f.icon for f in social_fields} == {"x", "github"}
    assert all(f.key == "social" for f in social_fields)


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
    social_fields = [f for f in fields.values() if f.group == "social"]
    assert len(social_fields) == 1
    assert social_fields[0].icon is None
    assert social_fields[0].key == "social"


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
    assert fields["location"].align == "right"
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
    assert fields["gpa"].group == "secondary"
    assert fields["gpa"].align == "right"
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
    assert [f.key for f in entry.fields] == ["project", "link", "date", "description", "tech", "tech"]
    assert fields["project"].group == "header"
    assert fields["date"].group == "secondary"
    assert fields["date"].align == "right"
    assert fields["link"].group == "header"
    assert fields["link"].align == "right"
    assert fields["link"].runs[0].style.link == "https://aergia.dev"
    assert fields["description"].group == "body"
    # Tech chips share the uniform 'tech' key; both land in the body row.
    assert [f.group for f in entry.fields if f.key == "tech"] == ["body", "body"]


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
    entry = build_document(cv).sections[0].entries[0]
    fields = {f.key: f for f in entry.fields}
    # Field order mirrors the research pattern: header (cert+date) → secondary (issuer+link).
    assert [f.key for f in entry.fields] == ["certification", "date", "issuer", "link"]
    assert fields["certification"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["issuer"].group == "secondary"
    assert fields["link"].group == "secondary"
    assert fields["link"].align == "right"
    assert fields["link"].runs[0].style.link == "https://x"


def test_certifications_link_text_defaults_to_certificate():
    """A credential URL without link_text renders 'Certificate' as the link."""
    cv = _cv([{
        "id": "s1", "type": "certifications", "title": "C", "enabled": True,
        "data": [{"id": "e1", "name": "AWS", "issuer": "Amazon", "date": "2026-01", "credential_url": "https://x"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["link"].runs[0].text == "Certificate"
    assert fields["link"].runs[0].style.link == "https://x"


def test_certifications_uses_link_text_when_provided():
    cv = _cv([{
        "id": "s1", "type": "certifications", "title": "C", "enabled": True,
        "data": [{"id": "e1", "name": "AWS", "issuer": "Amazon", "date": "2026-01", "credential_url": "https://x", "link_text": "Verify"}],
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    assert fields["link"].runs[0].text == "Verify"


def test_certifications_omit_issuer_and_date_when_empty():
    """issuer and date are independent optional fields after the meta split."""
    cv = _cv([{
        "id": "s1", "type": "certifications", "title": "C", "enabled": True,
        "data": [{"id": "e1", "name": "AWS", "credential_url": "https://x"}],
    }])
    keys = [f.key for f in build_document(cv).sections[0].entries[0].fields]
    assert keys == ["certification", "link"]


def test_apply_field_text_styles_preserves_builder_link_href():
    """A user TextStyle on a link field must merge, not replace: the
    builder-set href survives styling (bold/size/color edits)."""
    cv = _cv([{
        "id": "s1", "type": "projects", "title": "P", "enabled": True,
        "data": [{
            "id": "e1", "name": "Aergia", "url": "https://aergia.dev", "link_text": "site",
            "start_date": "2026-01", "end_date": None, "description": "CV builder", "tech_stack": [],
        }],
        "style": {"text": {"link": {"bold": True}}},
    }])
    fields = {f.key: f for f in build_document(cv).sections[0].entries[0].fields}
    link_run = fields["link"].runs[0]
    assert link_run.style.bold is True
    assert link_run.style.link == "https://aergia.dev"


def test_apply_field_text_styles_tag_base_key_reaches_tag_indexed_fields():
    """Customize panel binds a single 'tag' field per skills row, but the
    builder emits ``tag.0``, ``tag.1``, … for each item. The lookup must
    fall back to the base key so the per-row style reaches every item."""
    cv = _cv([{
        "id": "sk", "type": "skills", "title": "S", "enabled": True,
        "data": [
            {"id": "g1", "category": "Backend", "items": ["Python", "Go"]},
            {"id": "g2", "category": "Frontend", "items": ["React"]},
        ],
        "style": {"text": {"tag": {"font_size": "xs"}}},
    }])
    fields_by_entry = [
        {f.key: f for f in e.fields}
        for e in build_document(cv).sections[0].entries
    ]
    for entry in fields_by_entry:
        for key in (k for k in entry if k.startswith("tag.")):
            assert entry[key].runs[0].style.font_size == "xs", key


def test_research_and_cert_link_urls_get_a_scheme_when_missing():
    cv = _cv([
        {
            "id": "s1", "type": "research", "title": "R", "enabled": True,
            "data": [{"id": "e1", "title": "Paper", "paper_url": "arxiv.org/abs/1", "description": "Work"}],
        },
        {
            "id": "s2", "type": "certifications", "title": "C", "enabled": True,
            "data": [{"id": "e2", "name": "AWS", "issuer": "Amazon", "credential_url": "aws.amazon.com/cert"}],
        },
    ])
    sections = {s.id: s for s in build_document(cv).sections}
    res_link = {f.key: f for f in sections["s1"].entries[0].fields}["link"]
    cert_link = {f.key: f for f in sections["s2"].entries[0].fields}["link"]
    assert res_link.runs[0].style.link == "https://arxiv.org/abs/1"
    assert cert_link.runs[0].style.link == "https://aws.amazon.com/cert"


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
    assert [f.key for f in entry.fields] == ["paper", "date", "venue", "link", "description"]
    assert fields["paper"].group == "header"
    assert fields["date"].group == "header"
    assert fields["date"].align == "right"
    assert fields["venue"].group == "secondary"
    assert fields["link"].group == "secondary"
    assert fields["link"].align == "right"
    assert fields["link"].runs[0].style.link == "https://x"
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
    assert keys.index("social") < keys.index("summary")


# ---------------------------------------------------------------------------
# Rich text description tests
# ---------------------------------------------------------------------------


def test_experience_rich_text_description_produces_blocks():
    """RichTextBlock[] input produces a FieldBlock with blocks populated."""
    cv = _cv([{
        "id": "x",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {
                "id": "e1",
                "position": "Dev",
                "company": "Co",
                "start_date": "2020-01",
                "description": [
                    {"type": "paragraph", "items": [{"text": "Led team of "}, {"text": "5 engineers", "style": {"bold": True}}]},
                    {"type": "bullet_list", "items": [{"text": "Reduced latency"}, {"text": "Built CI/CD"}]},
                ],
            },
        ],
    }])
    doc = build_document(cv)
    desc = [f for f in doc.sections[0].entries[0].fields if f.key == "description"][0]
    assert desc.rich_text is True
    assert len(desc.blocks) == 2
    assert desc.blocks[0].type == "paragraph"
    assert desc.blocks[0].items[1].style.bold is True
    assert desc.blocks[1].type == "bullet_list"
    assert len(desc.blocks[1].items) == 2


def test_experience_legacy_string_description_still_works():
    """Legacy plain string description still produces a valid FieldBlock."""
    cv = _cv([{
        "id": "x",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"id": "e1", "position": "Dev", "company": "Co", "start_date": "2020-01", "description": "did stuff"},
        ],
    }])
    doc = build_document(cv)
    desc = [f for f in doc.sections[0].entries[0].fields if f.key == "description"][0]
    assert desc.rich_text is True
    assert len(desc.blocks) == 1
    assert desc.blocks[0].type == "paragraph"
    assert desc.blocks[0].items[0].text == "did stuff"
    assert desc.runs[0].text == "did stuff"


def test_empty_rich_text_description_produces_no_field():
    """Empty RichTextBlock[] produces no description FieldBlock."""
    cv = _cv([{
        "id": "x",
        "type": "experience",
        "title": "Experience",
        "enabled": True,
        "data": [
            {"id": "e1", "position": "Dev", "company": "Co", "start_date": "2020-01", "description": []},
        ],
    }])
    doc = build_document(cv)
    desc_keys = [f.key for f in doc.sections[0].entries[0].fields if f.key == "description"]
    assert len(desc_keys) == 0


def test_projects_rich_text_description():
    """Projects builder handles rich text description."""
    cv = _cv([{
        "id": "p",
        "type": "projects",
        "title": "Projects",
        "enabled": True,
        "data": [
            {
                "id": "proj1",
                "name": "My Project",
                "start_date": "2023-01",
                "description": [
                    {"type": "paragraph", "items": [{"text": "Built "}, {"text": "cool thing", "style": {"italic": True}}]},
                ],
            },
        ],
    }])
    doc = build_document(cv)
    desc = [f for f in doc.sections[0].entries[0].fields if f.key == "description"][0]
    assert desc.rich_text is True
    assert desc.blocks[0].items[1].style.italic is True


def test_research_rich_text_description():
    """Research builder handles rich text description."""
    cv = _cv([{
        "id": "r",
        "type": "research",
        "title": "Research",
        "enabled": True,
        "data": [
            {
                "id": "paper1",
                "title": "My Paper",
                "publication_date": "2024-01",
                "description": [
                    {"type": "paragraph", "items": [{"text": "Abstract text"}]},
                    {"type": "numbered_list", "items": [{"text": "Finding 1"}, {"text": "Finding 2"}]},
                ],
            },
        ],
    }])
    doc = build_document(cv)
    desc = [f for f in doc.sections[0].entries[0].fields if f.key == "description"][0]
    assert desc.rich_text is True
    assert len(desc.blocks) == 2
    assert desc.blocks[1].type == "numbered_list"
