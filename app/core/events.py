"""
ArkLog - Application Lifecycle & Event Bus

Two responsibilities:
  1. Lifecycle hooks (on_startup / on_shutdown) called by FastAPI lifespan
  2. In-process EventBus for decoupled EDA communication between modules

Complete event topology (add new subscribers here as phases expand):
  github.push         → CommitService.handle_push_event         [Phase 2]
  commit.batch_ready  → ReportService.handle_commit_batch        [Phase 3]
  report.generated    → <publisher>.handle_report_generated      [Phase 4+]
  schedule (cron)     → _run_scheduled_report (per project)      [Phase 5]

To add a new publisher: implement BasePublisher, instantiate it in
_wire_event_handlers(), append to _publishers, and subscribe to the event bus.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

if TYPE_CHECKING:
    from app.integrations.base import BasePublisher

logger = structlog.get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

_publishers: list["BasePublisher"] = []


class EventBus:
    """
    Async in-process event bus implementing the Observer pattern.

    Enables EDA without an external broker. If scale demands it later,
    this class can be reimplemented with Redis Pub/Sub or Kafka without
    changing any subscriber code.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)
        logger.debug("event_subscribed", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish to all subscribers concurrently. Exceptions are logged, not raised."""
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug("event_no_handlers", event_type=event_type)
            return

        logger.info("event_publishing", event_type=event_type, handlers=len(handlers))
        results = await asyncio.gather(
            *[handler(payload) for handler in handlers], return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("event_handler_error", event_type=event_type, error=str(result))


event_bus = EventBus()


async def on_startup() -> None:
    """Side effects executed once when the application starts."""
    logger.info("startup_begin")
    _validate_production_config()
    await _init_database()
    await _load_projects()
    await _wire_event_handlers()
    await _start_scheduler()
    logger.info("startup_complete")


async def on_shutdown() -> None:
    """Graceful shutdown — stop scheduler and close all publisher HTTP clients."""
    global _publishers
    logger.info("shutdown_begin")
    from app.schedulers.scheduler import stop_scheduler
    await stop_scheduler()
    for pub in _publishers:
        await pub.close()
    if _publishers:
        logger.info("publishers_closed", count=len(_publishers))
    _publishers.clear()
    logger.info("shutdown_complete")


def _validate_production_config() -> None:
    """Abort startup if required secrets are missing in production."""
    from app.core.config import settings
    if settings.is_production and not settings.github_webhook_secret:
        raise RuntimeError(
            "GITHUB_WEBHOOK_SECRET must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )


async def _init_database() -> None:
    try:
        from app.models.database import init_db
        await init_db()
        logger.info("database_initialized")
    except Exception as exc:
        logger.error("database_init_failed", error=str(exc))


async def _load_projects() -> None:
    """Projects are now loaded dynamically from the database."""
    logger.info("projects_loading_from_db")


async def _wire_event_handlers() -> None:
    """
    Register all event bus subscriptions.

    This is the single source of truth for the full event topology.
    To add a publisher: import it, instantiate, append to _publishers,
    and subscribe to "report.generated".
    """
    global _publishers
    from app.integrations.clickup.publisher import ClickUpPublisher
    from app.services.commit_service import CommitService
    from app.services.report_service import ReportService

    commit_svc = CommitService()
    report_svc = ReportService()

    clickup_pub = ClickUpPublisher()
    _publishers.append(clickup_pub)

    event_bus.subscribe("github.push", commit_svc.handle_push_event)
    event_bus.subscribe("commit.batch_ready", report_svc.handle_commit_batch)
    event_bus.subscribe("report.generated", clickup_pub.handle_report_generated)

    logger.info("event_handlers_wired", publishers=len(_publishers), subscriptions=3)


async def _start_scheduler() -> None:
    """Register project schedules from DB and start APScheduler."""
    try:
        from app.schedulers.report_scheduler import register_project_schedules
        from app.schedulers.scheduler import start_scheduler
        await register_project_schedules()
        await start_scheduler()
    except Exception as exc:
        logger.error("scheduler_start_failed", error=str(exc))
