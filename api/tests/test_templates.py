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
    assert "default_customizations" in data


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


