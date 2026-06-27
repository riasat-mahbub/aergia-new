"""T10: Pytest: template seed creates 3 templates"""

import pytest


async def register_and_login(client, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_seed_creates_three_templates(client):
    """Verify that the 3 generic templates are seeded on startup."""
    resp = await client.get("/api/v1/templates")
    assert resp.status_code == 200
    templates = resp.json()
    assert len(templates) == 3

    ids = {t["id"] for t in templates}
    assert ids == {"generic-modern", "generic-classic", "generic-minimal"}

    names = {t["name"] for t in templates}
    assert names == {"Modern", "Classic", "Minimal"}


@pytest.mark.asyncio
async def test_template_detail(client):
    """Verify template detail endpoint returns full config."""
    resp = await client.get("/api/v1/templates/generic-modern")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "generic-modern"
    assert "manifest" in data
    assert data.get("default_customizations") is None


@pytest.mark.asyncio
async def test_template_detail_not_found(client):
    resp = await client.get("/api/v1/templates/non-existent")
    assert resp.status_code == 404




@pytest.mark.asyncio
async def test_seed_templates_have_no_row_fields(client):
    """Seed manifests are row-free after the zone-only refactor."""
    for tmpl in ("generic-modern", "generic-classic", "generic-minimal"):
        resp = await client.get(f"/api/v1/templates/{tmpl}", headers=await register_and_login(client, f"tmpl-{tmpl}@example.com"))
        manifest = resp.json()["manifest"]
        for zone in manifest["zones"]:
            assert "row" not in zone
        assert "rowHeights" not in manifest
        assert "rowHeights" not in manifest.get("layout_config", {})



@pytest.mark.asyncio
async def test_create_user_template_with_v2_manifest(client):
    """POST /api/v1/templates/user accepts a v2 manifest payload.

    Persists the manifest on the template and derives the legacy
    ``default_customizations`` bucket for the CV builder.
    """
    headers = await register_and_login(client, "v2-template@example.com")
    payload = {
        "name": "T",
        "manifest": {
            "manifest_version": 2,
            "name": "T",
            "zones": [{"id": "main", "styles": {"width": "full"}}],
            "placement": {"profile": "main", "experience": "main"},
            "global_styles": {"accent_color": "#abcdef", "body_font": "sans-serif", "heading_font": "sans-serif"},
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["manifest"]["manifest_version"] == 2
    # The legacy bucket is gone; the manifest is the only template payload.
    assert data.get("default_customizations") is None
    assert data["manifest"]["global_styles"]["accent_color"] == "#abcdef"
    assert data["name"] == "T"


@pytest.mark.asyncio
async def test_create_user_template_rejects_v1_manifest(client):
    """A v1 manifest is rejected at the model boundary (400)."""
    headers = await register_and_login(client, "v1-rejected@example.com")
    payload = {
        "name": "Old",
        "manifest": {
            "manifest_version": 1,
            "name": "Old",
            "zones": [],
            "placement": {},
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_user_template_requires_manifest(client):
    """A request with no manifest field is rejected (422)."""
    headers = await register_and_login(client, "no-manifest@example.com")
    resp = await client.post("/api/v1/templates/user", json={"name": "T"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_user_template_does_not_persist_default_customizations(client):
    """The route persists the manifest only; the legacy bucket is not written."""
    headers = await register_and_login(client, "no-legacy@example.com")
    payload = {
        "name": "NoLegacy",
        "manifest": {
            "manifest_version": 2,
            "name": "NoLegacy",
            "zones": [{"id": "main", "styles": {"width": "full"}}],
            "placement": {"profile": "main"},
            "global_styles": {"accent_color": "#aabbcc", "body_font": "sans-serif", "heading_font": "sans-serif"},
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("default_customizations") is None
    assert data["manifest"]["global_styles"]["accent_color"] == "#aabbcc"


@pytest.mark.asyncio
async def test_create_user_template_rejects_css_strings(client):
    """A manifest carrying raw CSS in zone styles is rejected at the boundary."""
    headers = await register_and_login(client, "css-rejected@example.com")
    payload = {
        "name": "Css",
        "manifest": {
            "manifest_version": 2,
            "name": "Css",
            "zones": [{"id": "main", "styles": {"width": "30%"}}],
            "placement": {"profile": "main"},
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_user_template_rejects_extra_zone_keys(client):
    """A manifest with arbitrary CSS keys (e.g. ``display: flex``) is rejected."""
    headers = await register_and_login(client, "extra-rejected@example.com")
    payload = {
        "name": "Extra",
        "manifest": {
            "manifest_version": 2,
            "name": "Extra",
            "zones": [{"id": "main", "styles": {"width": "full", "display": "flex"}}],
            "placement": {"profile": "main"},
        },
    }
    resp = await client.post("/api/v1/templates/user", json=payload, headers=headers)
    assert resp.status_code == 422
