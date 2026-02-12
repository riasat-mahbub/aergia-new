"""T10: Pytest: template seed creates 3 templates"""

import pytest


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
    assert "layout_config" in data
    assert "section_schema" in data
    assert "default_customizations" in data


@pytest.mark.asyncio
async def test_template_detail_not_found(client):
    resp = await client.get("/api/v1/templates/non-existent")
    assert resp.status_code == 404
