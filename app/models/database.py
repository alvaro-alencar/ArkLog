"""ArkLog database engine and session factory."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

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
            columns = [
                ("timezone", "VARCHAR(100) DEFAULT 'America/Sao_Paulo'"),
                ("language", "VARCHAR(10) DEFAULT 'pt-BR'"),
                ("ark_user_id", "VARCHAR(64)"),
                ("ark_organization_id", "VARCHAR(64)"),
                ("is_platform_admin", "BOOLEAN NOT NULL DEFAULT 0"),
            ]
            for column, definition in columns:
                try:
                    await conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {definition}")
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
