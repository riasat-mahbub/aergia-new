"""T10: Pytest: template seed creates 3 templates"""

import pytest


async def register_and_login(client, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_seed_creates_three_templates(client):
    """Verify that the 3 generic templates are seeded on startup."""
    resp = await client.get("/api/v1/templates")
    assert resp.status_code == 200
    templates = resp.json()
    names = {t["name"] for t in templates}
    assert names == {"Modern", "Classic", "Minimal"}


@pytest.mark.asyncio
async def test_list_templates_response_shape_drops_is_user_template(client):
    """Phase 6 step 1 dropped ``is_user_template`` from TemplateListItem/TemplateDetail."""
    resp = await client.get("/api/v1/templates")
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) == 3
    for item in templates:
        assert "is_user_template" not in item
        # Schema-shape locks: every list item is the canonical shape.
        assert set(item.keys()) == {"id", "name", "description", "preview_image_url"}


@pytest.mark.asyncio
async def test_get_template_returns_manifest_only(client):
    """TemplateDetail has no ``is_user_template`` and no ``default_customizations``."""
    resp = await client.get("/api/v1/templates/generic-modern")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_user_template" not in data
    assert data.get("default_customizations") is None
    assert data["manifest"]["manifest_version"] == 2



@pytest.mark.asyncio
async def test_template_detail_not_found(client):
    resp = await client.get("/api/v1/templates/non-existent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_user_template_route_does_not_exist(client):
    """Phase 6 step 1 deleted POST /api/v1/templates/user."""
    headers = await register_and_login(client, "user-tpl-route@example.com")
    payload = {
        "name": "T",
        "manifest": {
            "manifest_version": 2,
            "name": "T",
            "zones": [{"id": "main", "styles": {"width": "full"}}],
            "placement": {"profile": "main"},
            "global_styles": {
                "accent_color": "#abcdef",
                "body_font": "sans-serif",
                "heading_font": "sans-serif",
            },
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    # Router does not register /user; FastAPI returns 405 Method Not Allowed.
    assert resp.status_code == 405, resp.text


@pytest.mark.asyncio
async def test_delete_user_template_route_does_not_exist(client):
    """Phase 6 step 1 deleted DELETE /api/v1/templates/user/{id}."""
    headers = await register_and_login(client, "user-tpl-del@example.com")
    resp = await client.delete("/api/v1/templates/user/generic-modern", headers=headers)
    assert resp.status_code == 405, resp.text


@pytest.mark.asyncio
async def test_multipart_upload_route_does_not_exist(client):
    """Phase 6 step 1 deleted POST /api/v1/templates (multipart upload)."""
    headers = await register_and_login(client, "multipart-tpl@example.com")
    # multipart payload: a single manifest_json field; no actual file.
    files = {"manifest_json": (None, '{"manifest_version": 2, "name": "X"}')}
    resp = await client.post("/api/v1/templates", files=files, headers=headers)
    assert resp.status_code == 405, resp.text


def test_user_template_create_schema_is_not_exported():
    """``UserTemplateCreate`` was deleted from ``app.schema.models``."""
    import pytest
    from app import schema as schema_pkg

    with pytest.raises(ImportError):
        from app.schema.models import UserTemplateCreate  # noqa: F401
    assert "UserTemplateCreate" not in dir(schema_pkg.models)


def test_template_model_drops_is_system_and_user_id():
    """The ``Template`` model no longer carries the user-template discriminator."""
    from app.models.template import Template

    column_names = {col.name for col in Template.__table__.columns}
    assert "is_system" not in column_names
    assert "user_id" not in column_names


@pytest.mark.asyncio
async def test_migration_drops_user_id_and_is_system():
    """After the Phase 6 step 1 migration, ``templates`` has no ``user_id``/``is_system``."""
    from sqlalchemy import inspect
    from app.db.session import engine
    async with engine.connect() as conn:
        cols = await conn.run_sync(
            lambda sync_conn: [c["name"] for c in inspect(sync_conn).get_columns("templates")]
        )
        assert "is_system" not in cols
        assert "user_id" not in cols
