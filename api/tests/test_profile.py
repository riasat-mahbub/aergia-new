"""Singleton Library Profile API contracts."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import async_session
from app.models.user import User
from app.services.profile import ProfileService

async def _register_and_login(client, email: str) -> str:
    password = "testpass123"
    registered = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert registered.status_code == 201
    logged_in = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


@pytest.mark.asyncio
async def test_profile_falls_back_to_login_email_and_updates_without_auth_mutation(client):
    email = f"profile-{uuid4().hex}@example.com"
    token = await _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    initial = await client.get("/api/v1/profile", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["email"] == email
    assert initial.json()["social_links"] == []

    updated = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "name": "Ada Lovelace",
            "title": "Platform Engineer",
            "email": "contact@example.com",
            "phone": None,
            "location": "London",
            "site_text": None,
            "site_url": None,
            "summary": "Builds reliable systems.",
            "photo_url": None,
            "email_link": True,
            "social_links": [{"label": "GitHub", "url": "https://github.com/ada", "icon": "github"}],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Ada Lovelace"
    assert updated.json()["email"] == "contact@example.com"

    async with async_session() as session:
        stored = (await session.execute(select(User).where(User.email == email))).scalar_one()
        assert stored.email == email
        assert stored.profile_data["email"] == "contact@example.com"
        assert stored.password_hash


@pytest.mark.asyncio
async def test_profile_data_is_isolated_between_users(client):
    first_email = f"profile-first-{uuid4().hex}@example.com"
    second_email = f"profile-second-{uuid4().hex}@example.com"
    first_token = await _register_and_login(client, first_email)
    second_token = await _register_and_login(client, second_email)

    response = await client.put(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "name": "First User",
            "title": None,
            "email": None,
            "phone": None,
            "location": None,
            "site_text": None,
            "site_url": None,
            "summary": None,
            "photo_url": None,
            "email_link": True,
            "social_links": [],
        },
    )
    assert response.status_code == 200

    other = await client.get("/api/v1/profile", headers={"Authorization": f"Bearer {second_token}"})
    assert other.status_code == 200
    assert other.json()["name"] is None
    assert other.json()["email"] == second_email

@pytest.mark.asyncio
async def test_malformed_stored_profile_surfaces_validation_error(client):
    email = f"profile-malformed-{uuid4().hex}@example.com"
    await _register_and_login(client, email)
    async with async_session() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        user.profile_data = ["not", "an", "object"]
        await session.commit()
        with pytest.raises(ValidationError):
            await ProfileService(session).get_profile(user)
