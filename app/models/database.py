"""
ArkLog - Database Engine & Session Factory

Configures SQLAlchemy async engine. SQLite is used initially (zero ops overhead).
Migrating to PostgreSQL requires only changing DATABASE_URL — SQLAlchemy handles the rest.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def init_db() -> None:
    """Create all tables. Called once on startup."""
    from app.models import tables  # noqa: F401 — registers models with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session
