import os
import asyncio
import atexit
import shutil
import tempfile
import pytest
from typing import Generator
from httpx import ASGITransport, AsyncClient

# Test isolation: API_TEST_DB_URL overrides DATABASE_URL before any app import.
# By default each pytest process gets a fresh temporary database. An explicit
# API_TEST_DB_URL remains available for focused debugging, but should never be
# pointed at data/aergia.db because that database carries user data. Live smoke
# runs must also use a fresh file, register a unique throwaway user, and remove
# the file afterward.
_test_db_dir: str | None = None
if "API_TEST_DB_URL" not in os.environ:
    _test_db_dir = tempfile.mkdtemp(prefix="aergia-pytest-")
    _test_db_path = os.path.join(_test_db_dir, "aergia.test.db")
    os.environ["API_TEST_DB_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"
    atexit.register(shutil.rmtree, _test_db_dir, ignore_errors=True)
os.environ["DATABASE_URL"] = os.environ["API_TEST_DB_URL"]

# Set test environment before any app imports to disable rate limiting
os.environ["ENVIRONMENT"] = "test"
# Integration tests retain the legacy bearer/body transport while the
# production configuration exercises the HttpOnly cookie transport.
os.environ["ALLOW_BEARER_TOKENS"] = "true"
os.environ["EXPOSE_TOKENS_IN_RESPONSE"] = "true"
os.environ["CSRF_PROTECTION_ENABLED"] = "false"

from app.app import app  # noqa: E402
from app.db.seed import seed_templates  # noqa: E402
from app.db.session import async_session  # noqa: E402


# Ensure the test DB has the schema applied. ASGITransport doesn't run app
# lifespan, and the temporary test DB starts empty — Alembic is the source of
# truth, so we invoke it once here via the venv CLI.
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
