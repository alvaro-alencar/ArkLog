"""
ArkLog - ClickUp Report Publisher

Subscriber of "report.generated". Formats the AI-generated report
and posts it as a comment to the configured ClickUp task.

After publishing, updates the ReportRecord with the ClickUp comment ID
for audit trail and idempotency checks.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.integrations.clickup.client import ClickUpClient
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord, ReportRecord

logger = structlog.get_logger(__name__)


class ClickUpPublisher:
    """Publishes generated reports to ClickUp tasks as comments."""

    def __init__(self) -> None:
        self._client = ClickUpClient()

    async def handle_report_generated(self, payload: dict[str, Any]) -> None:
        """Subscriber for report.generated events."""
        project_name = payload.get("project_name", "unknown")
        task_id = payload.get("clickup_task_id", "")
        content = payload.get("content", "")

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

        await self._mark_published(project_name, comment_id)
        logger.info(
            "report_published_to_clickup",
            project=project_name,
            task_id=task_id,
            comment_id=comment_id,
        )

    def _format_for_clickup(self, payload: dict[str, Any]) -> str:
        """Wrap the AI report with a metadata header for ClickUp readability."""
        project = payload.get("project_name", "")
        commit_count = payload.get("commit_count", 0)
        trigger = payload.get("trigger", "webhook")
        content = payload.get("content", "")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        trigger_label = "scheduled checkpoint" if trigger == "scheduled" else f"{commit_count} commit(s) analyzed"

        return (
            f"🤖 **ArkLog Report** — {project}\n"
            f"📅 {now} | 📝 {trigger_label}\n\n"
            f"---\n\n"
            f"{content}"
        )

    async def _mark_published(self, project_name: str, comment_id: str) -> None:
        """Update the most recent generated ReportRecord with the ClickUp comment ID."""
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(ReportRecord)
                    .join(ProjectRecord, ReportRecord.project_id == ProjectRecord.id)
                    .where(
                        ProjectRecord.name == project_name,
                        ReportRecord.status == "generated",
                    )
                    .order_by(ReportRecord.generated_at.desc())
                    .limit(1)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.clickup_comment_id = comment_id
                    record.status = "published"
                    record.published_at = datetime.utcnow()
