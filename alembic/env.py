"""
ArkLog - Alembic Environment

Configured for async SQLAlchemy. The database URL comes from app settings,
not from alembic.ini, so the same .env used at runtime drives migrations too.

Usage:
  alembic upgrade head       # apply all pending migrations
  alembic downgrade -1       # revert the last migration
  alembic revision --autogenerate -m "description"   # generate a new migration
  alembic stamp head         # mark existing DB as up-to-date (use on first run
                             # if the DB was already created via create_all)
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Load app models so Base.metadata knows all tables
from app.core.config import settings
from app.models import tables  # noqa: F401 — side-effect: registers ORM models
from app.models.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL to stdout)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live async database connection."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
