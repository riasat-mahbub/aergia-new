"""Photo upload, integrity, and owner-isolation contracts."""

import io
from uuid import uuid4

import pytest


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082"
)


async def _login(client, email: str) -> dict[str, str]:
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def auth_headers(client):
    return await _login(client, f"asset-test-{uuid4().hex}@example.com")


def _make_file(content: bytes, filename: str = "photo.png", content_type: str = "image/png"):
    return {"file": (filename, io.BytesIO(content), content_type)}


@pytest.mark.asyncio
async def test_upload_valid_file_is_private_and_readable_by_owner(client, auth_headers):
    response = await client.post("/api/v1/assets", files=_make_file(PNG_1X1), headers=auth_headers)
    assert response.status_code == 200
    url = response.json()["url"]
    assert url.startswith("/api/v1/assets/")

    downloaded = await client.get(url, headers=auth_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_1X1


@pytest.mark.asyncio
async def test_asset_delete_and_download_are_owner_scoped(client, auth_headers):
    response = await client.post("/api/v1/assets", files=_make_file(PNG_1X1), headers=auth_headers)
    filename = response.json()["url"].rsplit("/", 1)[-1]
    other_headers = await _login(client, f"asset-other-{uuid4().hex}@example.com")

    assert (await client.get(f"/api/v1/assets/{filename}", headers=other_headers)).status_code == 404
    assert (await client.delete(f"/api/v1/assets/{filename}", headers=other_headers)).status_code == 404
    assert (await client.get(f"/api/v1/assets/{filename}", headers=auth_headers)).status_code == 200
    assert (await client.delete(f"/api/v1/assets/{filename}", headers=auth_headers)).status_code == 200
    assert (await client.get(f"/api/v1/assets/{filename}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension_and_non_image(client, auth_headers):
    invalid_extension = await client.post(
        "/api/v1/assets", files=_make_file(PNG_1X1, "document.pdf", "application/pdf"), headers=auth_headers
    )
    assert invalid_extension.status_code == 400
    assert "Invalid file type" in invalid_extension.json()["detail"]

    fake_image = await client.post(
        "/api/v1/assets", files=_make_file(b"not-an-image", "photo.png", "image/png"), headers=auth_headers
    )
    assert fake_image.status_code == 400
    assert "image" in fake_image.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_file_too_large_is_rejected(client, auth_headers):
    large_content = b"x" * (6 * 1024 * 1024)
    response = await client.post("/api/v1/assets", files=_make_file(large_content), headers=auth_headers)
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_traversal_like_asset_names_cannot_delete_outside_upload_root(client, auth_headers):
    for filename in ("../outside", "../../etc/passwd", "not-owned.png", ".", ""):
        response = await client.delete(f"/api/v1/assets/{filename}", headers=auth_headers)
        assert response.status_code in {404, 405}
