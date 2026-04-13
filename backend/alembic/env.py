"""Alembic environment for FACEMETRICS.

This file bridges Alembic to our async SQLAlchemy stack:

* The DB URL is pulled from ``app.config.get_settings().database_url`` so dev
  (SQLite) and prod (PostgreSQL) share one source of truth.
* SQLAlchemy metadata is imported from ``app.db.Base`` after the model package
  is imported, so every table is registered before autogenerate runs.
* For async URLs (``sqlite+aiosqlite``, ``postgresql+asyncpg``) we drive
  migrations through ``AsyncEngine`` and ``connection.run_sync``.
* SQLite gets ``render_as_batch=True`` so ALTER TABLE migrations work on the
  dev database without raising ``OperationalError``.
"""
from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

# Make `app.*` importable when running `alembic` from backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.db import Base  # noqa: E402
from app import models  # noqa: E402,F401  — registers all mappers on Base.metadata

config = context.config

# Inject the runtime DB URL so alembic.ini stays a placeholder and secrets
# never have to live on disk.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _is_async_url(url: str) -> bool:
    return "+aiosqlite" in url or "+asyncpg" in url


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Generate SQL scripts without an active DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(url or ""),
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=_is_sqlite(url),
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable: AsyncEngine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Apply migrations against the live DB (sync or async driver)."""
    url = config.get_main_option("sqlalchemy.url") or ""

    if _is_async_url(url):
        asyncio.run(_run_async_migrations())
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        _do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
