import os
import asyncio
import pytest
from typing import Generator
from httpx import ASGITransport, AsyncClient

# Set test environment before any app imports to disable rate limiting
os.environ["ENVIRONMENT"] = "test"

from app.app import app
from app.db.seed import seed_templates
from app.db.session import async_session


# Seed templates before any tests run (ASGITransport doesn't run app lifespan)
def _seed_templates():
    async def _run():
        async with async_session() as session:
            await seed_templates(session)
    asyncio.run(_run())


_seed_templates()


@pytest.fixture
def client() -> Generator[AsyncClient, None, None]:
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
