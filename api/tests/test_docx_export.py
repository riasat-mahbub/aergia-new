"""Saved-CV Word export HTTP contract tests."""

from threading import get_ident
from uuid import uuid4

import pytest

import app.app as app_module
from app.app import app
from app.core.auth import CSRF_COOKIE_NAME
from app.services.cv import CVService
from app.services import docx as docx_service
from app.routes.cvs import DOCX_MEDIA_TYPE


@pytest.fixture
async def auth_headers(client):
    email = f"docx-export-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _profile_section(name: str) -> dict:
    return {
        "id": "sec_profile",
        "type": "profile",
        "title": "Profile",
        "enabled": True,
        "data": {"name": name},
    }


async def _create_cv(client, headers, *, name: str = "Ada Lovelace") -> str:
    response = await client.post(
        "/api/v1/cvs",
        json={"title": "Export fixture", "sections": [_profile_section(name)]},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _register_and_login(client, prefix: str) -> dict[str, str]:
    email = f"{prefix}-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_docx_export_requires_authentication(client):
    response = await client.post(f"/api/v1/cvs/{uuid4()}/export/docx")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_docx_export_returns_latest_saved_cv_as_binary_and_uses_worker_thread(
    client,
    auth_headers,
    monkeypatch,
):
    cv_id = await _create_cv(client, auth_headers)
    updated = await client.patch(
        f"/api/v1/cvs/{cv_id}",
        json={"sections": [_profile_section("Grace Hopper")]},
        headers=auth_headers,
    )
    assert updated.status_code == 200

    rendered_sources = []

    def fake_render(source):
        rendered_sources.append((source, get_ident()))
        return b"PK\x03\x04docx-fixture"

    monkeypatch.setattr(docx_service, "render_source_docx", fake_render)
    event_loop_thread = get_ident()
    response = await client.post(f"/api/v1/cvs/{cv_id}/export/docx", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"PK\x03\x04docx-fixture"
    assert response.headers["content-type"] == DOCX_MEDIA_TYPE
    assert response.headers["content-disposition"] == f'attachment; filename="cv-{cv_id}.docx"'
    assert response.headers["cache-control"] == "private, no-store"
    assert len(rendered_sources) == 1
    source, render_thread = rendered_sources[0]
    assert source.sections[0].data["name"] == "Grace Hopper"
    assert source.manifest is not None
    assert render_thread != event_loop_thread


@pytest.mark.asyncio
async def test_docx_export_returns_same_not_found_for_missing_inactive_and_foreign_cvs(
    client,
    auth_headers,
):
    cv_id = await _create_cv(client, auth_headers)
    foreign_headers = await _register_and_login(client, "docx-foreign")

    missing = await client.post(f"/api/v1/cvs/{uuid4()}/export/docx", headers=auth_headers)
    foreign = await client.post(f"/api/v1/cvs/{cv_id}/export/docx", headers=foreign_headers)
    deleted = await client.delete(f"/api/v1/cvs/{cv_id}", headers=auth_headers)
    inactive = await client.post(f"/api/v1/cvs/{cv_id}/export/docx", headers=auth_headers)

    assert deleted.status_code == 204
    assert [missing.status_code, foreign.status_code, inactive.status_code] == [404, 404, 404]
    assert missing.json() == foreign.json() == inactive.json() == {"detail": "CV not found"}


@pytest.mark.asyncio
async def test_docx_export_hides_manifest_and_generation_failures(client, auth_headers, monkeypatch, caplog):
    cv_id = await _create_cv(client, auth_headers)

    async def missing_manifest(_service, _template_id):
        return None

    with monkeypatch.context() as patch:
        patch.setattr(CVService, "get_template_data", missing_manifest)
        manifest_failure = await client.post(f"/api/v1/cvs/{cv_id}/export/docx", headers=auth_headers)

    def failed_generation(_source):
        raise RuntimeError("secret-marker-must-not-be-logged")

    with monkeypatch.context() as patch:
        patch.setattr(docx_service, "render_source_docx", failed_generation)
        generation_failure = await client.post(f"/api/v1/cvs/{cv_id}/export/docx", headers=auth_headers)

    assert manifest_failure.status_code == generation_failure.status_code == 500
    assert manifest_failure.json() == generation_failure.json() == {"detail": "Unable to export CV"}
    categories = {
        getattr(record, "error_category", None)
        for record in caplog.records
        if record.getMessage() == "cv_docx_export_failed"
    }
    assert categories == {"manifest", "generation"}
    assert "secret-marker-must-not-be-logged" not in caplog.text


@pytest.mark.asyncio
async def test_docx_export_requires_csrf_for_cookie_authenticated_mutations(client, monkeypatch):
    monkeypatch.setattr(app_module.settings, "csrf_protection_enabled", True)
    email = f"docx-csrf-{uuid4().hex}@example.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    assert csrf_token

    created = await client.post(
        "/api/v1/cvs",
        json={"title": "CSRF fixture", "sections": [_profile_section("Ada Lovelace")]},
        headers={
            "Origin": app_module.settings.frontend_url,
            "X-CSRF-Token": csrf_token,
        },
    )
    assert created.status_code == 201

    response = await client.post(
        f"/api/v1/cvs/{created.json()['id']}/export/docx",
        headers={"Origin": "https://external.example"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed"}


def test_docx_export_openapi_declares_binary_word_content():
    operation = app.openapi()["paths"]["/api/v1/cvs/{cv_id}/export/docx"]["post"]

    assert operation["responses"]["200"]["content"][DOCX_MEDIA_TYPE]["schema"] == {
        "type": "string",
        "format": "binary",
    }
