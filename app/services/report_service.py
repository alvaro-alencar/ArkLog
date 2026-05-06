"""
ArkLog - Report Service

Subscriber of "commit.batch_ready". Orchestrates report generation:
  commit.batch_ready → generate AI report → persist → publish report.generated

Registered in app/core/events.py during on_startup().
"""

from typing import Any

import structlog
from sqlalchemy import select

from app.ai.report_generator import ReportGenerator
from app.core.events import event_bus
from app.domain.entities.report import ReportStatus, ReportTrigger
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord, ReportRecord

logger = structlog.get_logger(__name__)


class ReportService:
    """Handles commit.batch_ready events and produces AI-generated reports."""

    def __init__(self) -> None:
        self._generator = ReportGenerator()

    async def handle_commit_batch(self, payload: dict[str, Any]) -> None:
        project_name = payload.get("project_name", "unknown")
        trigger = payload.get("trigger", "webhook")
        log = logger.bind(project=project_name)

        log.info("report_service_triggered", commits=payload.get("commit_count", 0), trigger=trigger)

        try:
            content, summary = await self._generator.generate(payload)
        except Exception as exc:
            log.error("report_generation_failed", error=str(exc))
            return

        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(ProjectRecord)
                    .where(ProjectRecord.name == project_name)
                    .limit(1)
                )
                project_record = result.scalar_one_or_none()
                if project_record is None:
                    log.warning("project_not_found_in_db", project=project_name)
                    return

                record = ReportRecord(
                    trigger=trigger,
                    status=ReportStatus.GENERATED.value,
                    content=content,
                    summary=summary,
                    commit_count=payload.get("commit_count", 0),
                    project_id=project_record.id,
                )
                session.add(record)
                await session.flush()
                report_id = record.id

        preview = summary[:80] + "..." if len(summary) > 80 else summary
        log.info("report_persisted", preview=preview, report_id=report_id)

        await event_bus.publish(
            "report.generated",
            {
                "report_id": report_id,
                "project_name": project_name,
                "clickup_task_id": payload.get("clickup_task_id", ""),
                "content": content,
                "summary": summary,
                "commit_count": payload.get("commit_count", 0),
                "trigger": trigger,
            },
        )
