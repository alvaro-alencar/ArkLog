"""Report generation orchestration and quota ledger completion."""

from typing import Any

import structlog
from sqlalchemy import select

from app.ai.report_generator import ReportGenerator
from app.core.events import event_bus
from app.domain.entities.report import ReportStatus
from app.models.database import AsyncSessionLocal
from app.models.tables import ArkLogAccessRecord, ProjectRecord, ReportRecord
from app.security.access import complete_usage, fail_usage

logger = structlog.get_logger(__name__)


class ReportService:
    def __init__(self) -> None:
        self._generator = ReportGenerator()

    async def handle_commit_batch(self, payload: dict[str, Any]) -> None:
        project_name = payload.get("project_name", "unknown")
        trigger = payload.get("trigger", "webhook")
        usage_id = payload.get("usage_id")
        log = logger.bind(project=project_name, trigger=trigger, usage_id=usage_id)

        project_id = payload.get("project_id")
        user_id = payload.get("user_id")
        statement = select(ProjectRecord, ArkLogAccessRecord).join(
            ArkLogAccessRecord,
            ArkLogAccessRecord.user_id == ProjectRecord.user_id,
        )
        if project_id is not None:
            statement = statement.where(ProjectRecord.id == int(project_id))
            if user_id is not None:
                statement = statement.where(ProjectRecord.user_id == int(user_id))
        else:
            statement = statement.where(
                ProjectRecord.name == project_name,
                ArkLogAccessRecord.is_admin.is_(True),
            )

        async with AsyncSessionLocal() as session:
            result = await session.execute(statement.limit(1))
            row = result.first()
        if row is None:
            await fail_usage(usage_id, "Project not found")
            return
        project_record, access = row

        if trigger != "instant" and not (access.is_admin and access.status == "ACTIVE"):
            log.warning(
                "automated_report_blocked_for_untrusted_access",
                status=access.status,
                is_admin=access.is_admin,
            )
            return
        if trigger == "instant" and not usage_id:
            log.warning("instant_report_without_usage_reservation")
            return

        try:
            content, summary = await self._generator.generate(payload)
        except Exception as exc:
            log.error("report_generation_failed", error=str(exc))
            await fail_usage(usage_id, str(exc))
            return

        async with AsyncSessionLocal() as session:
            async with session.begin():
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

        if usage_id:
            await complete_usage(usage_id, report_id)

        log.info("report_persisted", report_id=report_id)
        clickup_task_id = payload.get("clickup_task_id", "")
        if clickup_task_id:
            await event_bus.publish(
                "report.generated",
                {
                    "report_id": report_id,
                    "project_name": project_name,
                    "clickup_task_id": clickup_task_id,
                    "content": content,
                    "summary": summary,
                    "commit_count": payload.get("commit_count", 0),
                    "trigger": trigger,
                },
            )
