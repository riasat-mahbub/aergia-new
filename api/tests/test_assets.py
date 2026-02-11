"""T9: Pytest: photo upload (valid + invalid file, size limit)"""

import io
import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "asset-test@example.com", "password": "testpass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "asset-test@example.com", "password": "testpass123"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def _make_file(content: bytes, filename: str):
    return {"file": (filename, io.BytesIO(content), "image/jpeg")}


@pytest.mark.asyncio
async def test_upload_valid_file(client, auth_headers):
    content = b"fake-image-content" * 100
    files = _make_file(content, "photo.jpg")
    resp = await client.post("/api/v1/assets", files=files, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"].startswith("/uploads/")


@pytest.mark.asyncio
async def test_upload_invalid_extension(client, auth_headers):
    content = b"some-content"
    files = {"file": ("document.pdf", io.BytesIO(content), "application/pdf")}
    resp = await client.post("/api/v1/assets", files=files, headers=auth_headers)
    assert resp.status_code == 400
    assert "Invalid file type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large(client, auth_headers):
    large_content = b"x" * (6 * 1024 * 1024)  # 6MB
    files = _make_file(large_content, "large.jpg")
    resp = await client.post("/api/v1/assets", files=files, headers=auth_headers)
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()
