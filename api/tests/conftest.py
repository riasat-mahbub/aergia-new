import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient

from app.app import app


@pytest.fixture
def client() -> AsyncGenerator:
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
