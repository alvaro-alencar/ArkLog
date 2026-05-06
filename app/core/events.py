"""
ArkLog - Application Lifecycle & Event Bus

Two responsibilities:
  1. Lifecycle hooks (on_startup / on_shutdown) called by FastAPI lifespan
  2. In-process EventBus for decoupled EDA communication between modules

Full event flow:
  github.push         → CommitService.handle_push_event
  commit.batch_ready  → ReportService.handle_commit_batch   [Phase 3]
  report.generated    → ClickUpPublisher.publish            [Phase 4]
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


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
    await _init_database()
    await _load_projects()
    await _wire_event_handlers()
    logger.info("startup_complete")


async def on_shutdown() -> None:
    logger.info("shutdown_begin")
    logger.info("shutdown_complete")


async def _init_database() -> None:
    try:
        from app.models.database import init_db
        await init_db()
        logger.info("database_initialized")
    except Exception as exc:
        logger.error("database_init_failed", error=str(exc))


async def _load_projects() -> None:
    try:
        from app.config.projects import projects_config
        count = len(projects_config.projects)
        logger.info("projects_loaded", count=count, names=[p.name for p in projects_config.projects])
    except Exception as exc:
        logger.warning("projects_load_failed", error=str(exc))


async def _wire_event_handlers() -> None:
    """
    Register all event bus subscriptions.
    This is the single place where the full event topology is visible.
    Add new subscribers here as phases expand.
    """
    from app.services.commit_service import CommitService
    from app.services.report_service import ReportService

    commit_svc = CommitService()
    report_svc = ReportService()

    event_bus.subscribe("github.push", commit_svc.handle_push_event)
    event_bus.subscribe("commit.batch_ready", report_svc.handle_commit_batch)

    logger.info("event_handlers_wired", subscriptions=2)
