import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import Base

# Import all models so Alembic autogenerate can detect them
import app.models.user  # noqa: F401
import app.models.cv  # noqa: F401
import app.models.library  # noqa: F401
import app.models.application  # noqa: F401
import app.models.template  # noqa: F401
import app.models.auth_session  # noqa: F401

SQLALCHEMY_URL_KEY = "sqlalchemy.url"

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option(SQLALCHEMY_URL_KEY, db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option(SQLALCHEMY_URL_KEY)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(config.get_main_option(SQLALCHEMY_URL_KEY), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
