"""
ArkLog - ClickUp Report Publisher

Subscriber of "report.generated". Formats the AI-generated report
and posts it as a comment to the configured ClickUp task.

After publishing, updates the ReportRecord by ID (race-condition-safe).
"""

from typing import Any

import structlog

from app.core.config import settings
from app.integrations.base import BasePublisher
from app.integrations.clickup.client import ClickUpClient
from app.models.database import AsyncSessionLocal
from app.models.tables import ReportRecord
from app.utils.datetime_utils import naive_utcnow

logger = structlog.get_logger(__name__)


class ClickUpPublisher(BasePublisher):
    """Publishes generated reports to ClickUp tasks as comments."""

    def __init__(self) -> None:
        self._client = ClickUpClient()

    async def handle_report_generated(self, payload: dict[str, Any]) -> None:
        """Subscriber for report.generated events."""
        project_name = payload.get("project_name", "unknown")
        task_id = payload.get("clickup_task_id", "")
        content = payload.get("content", "")
        report_id = payload.get("report_id")

        if not settings.clickup_api_token:
            logger.warning("clickup_token_not_configured", project=project_name)
            return

        if not task_id:
            logger.warning("clickup_no_task_id", project=project_name)
            return

        if not content:
            logger.warning("clickup_empty_content", project=project_name)
            return

        formatted = self._format_for_clickup(payload)

        try:
            comment_id = await self._client.post_task_comment(task_id, formatted)
        except Exception as exc:
            logger.error("clickup_publish_failed", project=project_name, error=str(exc))
            return

        if report_id is not None:
            await self._mark_published(report_id, comment_id)

        logger.info(
            "report_published_to_clickup",
            project=project_name,
            task_id=task_id,
            comment_id=comment_id,
        )

    def _format_for_clickup(self, payload: dict[str, Any]) -> str:
        """Wrap the AI report with a metadata header for ClickUp readability."""
        from datetime import datetime, timezone, timedelta

        project = payload.get("project_name", "")
        commit_count = payload.get("commit_count", 0)
        trigger = payload.get("trigger", "webhook")
        content = payload.get("content", "")
        brasilia = timezone(timedelta(hours=-3))
        now = datetime.now(brasilia).strftime("%Y-%m-%d %H:%M (Brasília)")
        trigger_label = (
            "scheduled checkpoint"
            if trigger == "scheduled"
            else f"{commit_count} commit(s) analyzed"
        )

        return (
            f"🤖 **ArkLog Report** — {project}\n"
            f"📅 {now} | 📝 {trigger_label}\n\n"
            f"---\n\n"
            f"{content}"
        )

    async def _mark_published(self, report_id: int, comment_id: str) -> None:
        """Update the specific ReportRecord by ID — no race condition possible."""
        async with AsyncSessionLocal() as session:
            async with session.begin():
                record = await session.get(ReportRecord, report_id)
                if record:
                    record.clickup_comment_id = comment_id
                    record.status = "published"
                    record.published_at = naive_utcnow()

    async def close(self) -> None:
        await self._client.close()
