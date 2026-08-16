import os
import asyncio
import pytest
from typing import Generator
from httpx import ASGITransport, AsyncClient

# Test isolation: API_TEST_DB_URL overrides DATABASE_URL before any app import.
# Default: data/aergia.test.db. Never run the test suite against data/aergia.db
# — it carries user data. Live smoke runs must point API_TEST_DB_URL at a
# per-run fresh file, run `alembic upgrade head` against it, register a unique
# throwaway user (e.g. f"smoke-{uuid4().hex[:8]}@example.com"), and delete the
# file afterward.
os.environ.setdefault("API_TEST_DB_URL", "sqlite+aiosqlite:///./data/aergia.test.db")
os.environ["DATABASE_URL"] = os.environ["API_TEST_DB_URL"]

# Set test environment before any app imports to disable rate limiting
os.environ["ENVIRONMENT"] = "test"
# Integration tests retain the legacy bearer/body transport while the
# production configuration exercises the HttpOnly cookie transport.
os.environ["ALLOW_BEARER_TOKENS"] = "true"
os.environ["EXPOSE_TOKENS_IN_RESPONSE"] = "true"
os.environ["CSRF_PROTECTION_ENABLED"] = "false"

from app.app import app
from app.db.seed import seed_templates
from app.db.session import async_session


# Ensure the test DB has the schema applied. ASGITransport doesn't run app
# lifespan, and the test DB starts empty — Alembic is the source of truth, so
# we invoke it once here via the venv CLI (the local `alembic/` package
# shadows `from alembic import command` AND `python -m alembic`, so we must
# exec the alembic entry-point script directly).
def _apply_migrations() -> None:
    import shutil
    import subprocess

    api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_bin = os.path.join(api_dir, ".venv", "bin", "alembic")
    if not os.path.exists(alembic_bin):
        alembic_bin = shutil.which("alembic") or "alembic"
    env = os.environ.copy()
    env["DATABASE_URL"] = os.environ["API_TEST_DB_URL"]
    subprocess.run([alembic_bin, "upgrade", "head"], check=True, cwd=api_dir, env=env)


_apply_migrations()


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
