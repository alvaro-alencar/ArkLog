"""
ArkLog - APScheduler Engine

Manages the AsyncIOScheduler singleton lifecycle.
Started on application startup, stopped on shutdown.

All scheduled jobs run in the same event loop as FastAPI,
so async jobs work natively without extra thread pools.
"""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = structlog.get_logger(__name__)

# Singleton scheduler — jobs are registered against this instance
scheduler = AsyncIOScheduler(timezone="UTC")


async def start_scheduler() -> None:
    """Start the APScheduler. Called from on_startup()."""
    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))


async def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Called from on_shutdown()."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
