"""ArkLog application lifecycle and in-process event bus."""

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
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[handler(payload) for handler in handlers], return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("event_handler_error", event_type=event_type, error=str(result))


event_bus = EventBus()


async def on_startup() -> None:
    logger.info("startup_begin")
    _validate_production_config()
    await _init_database()
    await _wire_event_handlers()
    await _start_scheduler()
    logger.info("startup_complete")


async def on_shutdown() -> None:
    global _publishers
    from app.schedulers.scheduler import stop_scheduler

    await stop_scheduler()
    for publisher in _publishers:
        await publisher.close()
    _publishers.clear()


def _validate_production_config() -> None:
    from app.core.config import settings

    if not settings.is_production:
        return
    missing: list[str] = []
    if not settings.ai_api_key:
        missing.append("AI_API_KEY")
    if settings.database_url.startswith("sqlite"):
        missing.append("DATABASE_URL PostgreSQL")
    if not settings.ark_auth_me_url.startswith("https://"):
        missing.append("ARK_AUTH_ME_URL HTTPS")
    if missing:
        raise RuntimeError("Missing secure production configuration: " + ", ".join(missing))


async def _init_database() -> None:
    from app.models.database import init_db

    await init_db()


async def _wire_event_handlers() -> None:
    global _publishers
    from app.integrations.clickup.publisher import ClickUpPublisher
    from app.services.commit_service import CommitService
    from app.services.report_service import ReportService

    commit_service = CommitService()
    report_service = ReportService()
    clickup_publisher = ClickUpPublisher()
    _publishers.append(clickup_publisher)

    event_bus.subscribe("github.push", commit_service.handle_push_event)
    event_bus.subscribe("commit.batch_ready", report_service.handle_commit_batch)
    event_bus.subscribe("report.generated", clickup_publisher.handle_report_generated)


async def _start_scheduler() -> None:
    from app.core.config import settings

    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled")
        return
    try:
        from app.schedulers.report_scheduler import register_project_schedules
        from app.schedulers.scheduler import start_scheduler

        await register_project_schedules()
        await start_scheduler()
    except Exception as exc:
        logger.error("scheduler_start_failed", error=str(exc))
