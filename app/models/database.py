"""ArkLog database engine and session factory."""

from __future__ import annotations

import os
from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


def normalize_database_url(value: str) -> str:
    """Accept standard Neon/Postgres URLs and select SQLAlchemy's asyncpg dialect.

    Neon connection strings may include ``channel_binding``, which asyncpg does
    not recognize as a connection option. Keeping it would make asyncpg forward
    the value as a PostgreSQL server setting and the connection would fail.
    """
    raw = value.strip()
    if raw.startswith("sqlite"):
        return raw

    parsed = urlsplit(raw)
    scheme = parsed.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    elif scheme != "postgresql+asyncpg":
        return raw

    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "channel_binding"
    ]
    return urlunsplit((scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


database_url = normalize_database_url(settings.database_url)
engine_options: dict = {"echo": settings.debug}

if database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    hostname = urlsplit(database_url).hostname or ""
    if os.getenv("VERCEL") or "-pooler." in hostname:
        # Serverless functions and transaction poolers should not retain a
        # process-local SQLAlchemy pool between unrelated invocations.
        engine_options["poolclass"] = NullPool

engine = create_async_engine(database_url, **engine_options)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    from app.models import tables  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in str(engine.url):
            user_columns = [
                ("timezone", "VARCHAR(100) DEFAULT 'America/Sao_Paulo'"),
                ("language", "VARCHAR(10) DEFAULT 'pt-BR'"),
                ("ark_user_id", "VARCHAR(64)"),
                ("ark_organization_id", "VARCHAR(64)"),
                ("is_platform_admin", "BOOLEAN NOT NULL DEFAULT 0"),
            ]
            for column, definition in user_columns:
                try:
                    await conn.exec_driver_sql(
                        f"ALTER TABLE users ADD COLUMN {column} {definition}"
                    )
                except Exception:
                    pass
            try:
                await conn.exec_driver_sql(
                    "ALTER TABLE arklog_access ADD COLUMN trial_granted_at DATETIME"
                )
            except Exception:
                pass
            try:
                await conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS users_ark_user_id_idx ON users(ark_user_id)"
                )
            except Exception:
                pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
