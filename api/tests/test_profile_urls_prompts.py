"""Visible profile URL opt-in and its persistence/rendering contracts."""

from __future__ import annotations

from io import BytesIO
import re
from uuid import uuid4

import pdfplumber
import pytest
from sqlalchemy import select

from app.db.seed import SEED_TEMPLATES
from app.db.session import async_session
from app.models.user import User
from app.scanner.pdf_worker import _extract_pdfium_text
from app.services.renderer import (
    build_document_from_sections,
    prepare_render_source,
    render_source_html,
    render_source_pdf,
)
from app.services.renderer._pdf_runtime import close_browser


SITE_URL = "https://www.example.com/portfolio?view=compact#projects"
SOCIAL_URL = "https://www.linkedin.com/in/ada?tab=profile#about"
SOCIAL_API_URL = "https://linkedin.com/in/ada?tab=profile#about"
SITE_ADDRESS = "example.com/portfolio?view=compact#projects"
SOCIAL_ADDRESS = "linkedin.com/in/ada?tab=profile#about"
MINIMAL = next(seed["manifest"] for seed in SEED_TEMPLATES if seed["id"] == "generic-minimal")


async def _register_and_login(client, email: str) -> str:
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


def _profile_section(data: dict) -> dict:
    return {
        "id": "profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": data,
    }


def _profile_data(show_urls: bool | None) -> dict:
    data = {
        "name": "Example Candidate",
        "site_text": "Personal Site",
        "site_url": SITE_URL,
        "social_links": [{"label": "LinkedIn", "url": SOCIAL_URL, "icon": "linkedin"}],
    }
    if show_urls is not None:
        data["show_urls"] = show_urls
    return data


def test_profile_builder_keeps_custom_labels_unless_visible_urls_are_enabled():
    legacy = build_document_from_sections([_profile_section(_profile_data(None))])
    disabled = build_document_from_sections([_profile_section(_profile_data(False))])
    enabled = build_document_from_sections([_profile_section(_profile_data(True))])

    def links(document):
        return [field.runs[0] for field in document.sections[0].entries[0].fields if field.key in {"site", "social"}]

    legacy_runs = links(legacy)
    disabled_runs = links(disabled)
    enabled_runs = links(enabled)
    assert [run.text for run in legacy_runs] == ["Personal Site", "LinkedIn"]
    assert [run.text for run in disabled_runs] == ["Personal Site", "LinkedIn"]
    assert [run.style.link for run in enabled_runs] == [SITE_URL, SOCIAL_URL]
    assert [run.text for run in enabled_runs] == [
        f"Personal Site — {SITE_ADDRESS}",
        f"LinkedIn — {SOCIAL_ADDRESS}",
    ]


def test_destination_labels_are_not_repeated_when_visible_urls_are_enabled():
    site_label = SITE_URL.removeprefix("https://")
    social_label = "http://www.linkedin.com/in/ada?tab=profile#about"
    data = {
        **_profile_data(True),
        "site_text": site_label,
        "social_links": [{"label": social_label, "url": SOCIAL_URL, "icon": "linkedin"}],
    }
    document = build_document_from_sections([_profile_section(data)])
    runs = [field.runs[0] for field in document.sections[0].entries[0].fields if field.key in {"site", "social"}]
    assert [run.text for run in runs] == [site_label, social_label]
    assert [run.style.link for run in runs] == [SITE_URL, SOCIAL_URL]

    root_url = build_document_from_sections([_profile_section({
        **_profile_data(True),
        "site_text": "example.com",
        "site_url": "https://www.example.com/",
        "social_links": [],
    })])
    root_site = next(field.runs[0] for field in root_url.sections[0].entries[0].fields if field.key == "site")
    assert root_site.text == "example.com"

    case_sensitive_path = build_document_from_sections([_profile_section({
        **_profile_data(True),
        "site_text": "example.com/Portfolio",
        "site_url": "https://example.com/portfolio",
        "social_links": [],
    })])
    path_site = next(field.runs[0] for field in case_sensitive_path.sections[0].entries[0].fields if field.key == "site")
    assert path_site.text == "example.com/Portfolio — example.com/portfolio"


async def test_visible_urls_reach_rendered_pdf_text_and_keep_full_clickable_destinations():
    source = prepare_render_source([_profile_section(_profile_data(True))], MINIMAL)
    html = render_source_html(source)
    assert f"Personal Site — {SITE_ADDRESS}" in html
    assert f"LinkedIn — {SOCIAL_ADDRESS}" in html
    assert f'href="{SITE_URL}"' in html
    assert f'href="{SOCIAL_URL}"' in html

    try:
        pdf_bytes = await render_source_pdf(source)
    finally:
        await close_browser()

    with pdfplumber.open(BytesIO(pdf_bytes)) as document:
        recovered_text = "\n".join(page.extract_text() or "" for page in document.pages)
        links = {link["uri"] for page in document.pages for link in page.hyperlinks if link.get("uri")}
    parser_texts = {"pdfplumber": recovered_text, "pdfium": _extract_pdfium_text(pdf_bytes)}
    assert {SITE_URL, SOCIAL_URL} <= links
    for parser, text in parser_texts.items():
        assert text is not None, parser
        compact = re.sub(r"\s+", "", text)
        assert SITE_ADDRESS in compact, parser
        assert SOCIAL_ADDRESS in compact, parser


@pytest.mark.asyncio
async def test_user_profile_url_setting_defaults_without_read_mutation_and_roundtrips(client):
    email = f"profile-urls-{uuid4().hex}@example.com"
    token = await _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    legacy_data = {
        "name": "Example Candidate",
        "site_text": "Personal Site",
        "site_url": "https://example.com/portfolio",
    }
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.profile_data = legacy_data.copy()
        await session.commit()

    loaded = await client.get("/api/v1/profile", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["show_urls"] is False
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        assert user.profile_data == legacy_data

    updated = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "site_text": "Personal Site",
            "site_url": "www.example.com/portfolio?view=compact#projects",
            "show_urls": True,
            "social_links": [{"label": "LinkedIn", "url": "linkedin.com/in/ada?tab=profile#about", "icon": "linkedin"}],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["show_urls"] is True
    assert updated.json()["site_url"] == SITE_URL
    assert updated.json()["social_links"][0]["url"] == SOCIAL_API_URL

    reloaded = await client.get("/api/v1/profile", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["show_urls"] is True
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        assert user.profile_data["show_urls"] is True


@pytest.mark.asyncio
async def test_cv_profile_section_retains_visible_url_setting_on_save_and_reload(client):
    email = f"cv-profile-urls-{uuid4().hex}@example.com"
    token = await _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/v1/cvs", json={"title": "URL Visibility CV"}, headers=headers)
    assert created.status_code == 201
    cv_id = created.json()["id"]
    section = _profile_section(_profile_data(True))

    saved = await client.patch(f"/api/v1/cvs/{cv_id}", json={"sections": [section]}, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["sections"][0]["data"]["show_urls"] is True
    reloaded = await client.get(f"/api/v1/cvs/{cv_id}", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["sections"][0]["data"]["show_urls"] is True
