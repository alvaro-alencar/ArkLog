"""
ArkLog - APScheduler Engine

AsyncIOScheduler with SQLAlchemyJobStore backed by the same database.

The job store provides distributed coordination: multiple instances sharing
the same database will not both fire the same job. Jobs are identified by
their `job_id` and the store tracks dispatch state.

- SQLite (single container): works via shared volume
- PostgreSQL (multi-container): works natively with a shared DB server

SCHEDULER_ENABLED env var lets you disable the scheduler per-container
as an additional safety valve when you want zero duplicate runs.
"""

import structlog
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _sync_db_url(url: str) -> str:
    """Convert async SQLAlchemy URL to sync (required by APScheduler job store)."""
    return (
        url
        .replace("sqlite+aiosqlite", "sqlite")
        .replace("postgresql+asyncpg", "postgresql+psycopg2")
        .replace("postgresql+aiopg", "postgresql+psycopg2")
    )


_jobstores = {
    "default": SQLAlchemyJobStore(
        url=_sync_db_url(settings.database_url),
        tablename="apscheduler_jobs",
    )
}

scheduler = AsyncIOScheduler(jobstores=_jobstores, timezone=settings.scheduler_timezone)


async def start_scheduler() -> None:
    """Start APScheduler. No-op if SCHEDULER_ENABLED=false."""
    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled", reason="SCHEDULER_ENABLED=false")
        return
    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))


async def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
