"""Trusted scheduled reports. Non-admin accounts never consume the owner AI key."""

from datetime import datetime, timedelta

import structlog
from sqlalchemy import select

from app.core.config import settings
from app.models.database import AsyncSessionLocal
from app.models.tables import ArkLogAccessRecord, ProjectRecord, ReportDestinationRecord
from app.repositories.project_repository import ProjectRepository
from app.schedulers.scheduler import scheduler

logger = structlog.get_logger(__name__)
TRIGGER_DAILY = "daily_scheduled"
TRIGGER_WEEKLY = "weekly_scheduled"


async def register_project_schedules() -> None:
    job_count = 0
    async with AsyncSessionLocal() as session:
        project_repository = ProjectRepository(session)
        projects = await project_repository.get_all_active()
        for project in projects:
            access = await session.scalar(
                select(ArkLogAccessRecord).where(
                    ArkLogAccessRecord.user_id == project.user_id,
                    ArkLogAccessRecord.is_admin.is_(True),
                    ArkLogAccessRecord.status == "ACTIVE",
                )
            )
            if access is None:
                continue
            for destination in project.destinations:
                if destination.schedule == "daily":
                    for time_string in destination.times:
                        hour, minute = map(int, time_string.split(":"))
                        scheduler.add_job(
                            _run_scheduled_report,
                            trigger="cron",
                            hour=hour,
                            minute=minute,
                            id=(
                                f"report__{project.id}__{destination.id}__"
                                f"{time_string.replace(':', '')}"
                            ),
                            args=[project.id, destination.id, TRIGGER_DAILY],
                            replace_existing=True,
                            misfire_grace_time=300,
                        )
                        job_count += 1
                elif destination.schedule == "weekly":
                    hour, minute = map(int, destination.time.split(":"))
                    scheduler.add_job(
                        _run_scheduled_report,
                        trigger="cron",
                        day_of_week=destination.day[:3],
                        hour=hour,
                        minute=minute,
                        id=f"report__{project.id}__{destination.id}__weekly",
                        args=[project.id, destination.id, TRIGGER_WEEKLY],
                        replace_existing=True,
                        misfire_grace_time=3600,
                    )
                    job_count += 1
    logger.info("schedules_registered", total_jobs=job_count)


async def _run_scheduled_report(project_id: int, destination_id: int, trigger: str) -> None:
    from app.core.events import event_bus
    from app.integrations.github.api_client import fetch_github_activity
    from app.repositories.report_repository import ReportRepository

    async with AsyncSessionLocal() as session:
        project = await session.get(ProjectRecord, project_id)
        destination = await session.scalar(
            select(ReportDestinationRecord).where(
                ReportDestinationRecord.id == destination_id,
                ReportDestinationRecord.project_id == project_id,
            )
        )
        if not project or not destination:
            return
        access = await session.scalar(
            select(ArkLogAccessRecord).where(
                ArkLogAccessRecord.user_id == project.user_id,
                ArkLogAccessRecord.is_admin.is_(True),
                ArkLogAccessRecord.status == "ACTIVE",
            )
        )
        if access is None:
            logger.warning("scheduled_report_blocked", project_id=project_id)
            return

        if destination.window_hours > 0:
            since = datetime.utcnow() - timedelta(hours=destination.window_hours)
        else:
            report_repository = ReportRepository(session)
            previous = await report_repository.get_last_generated_at_for_trigger(
                project.id, trigger
            )
            since = previous if previous else None

        snapshot = {
            "project_id": project.id,
            "user_id": project.user_id,
            "project_name": project.name,
            "description": project.description,
            "tech_stack": project.tech_stack,
            "business_context": project.business_context,
            "report_style": destination.report_style or project.report_style,
            "clickup_task_id": destination.clickup_task_id,
            "repo_full_name": project.repo_full_name,
        }

    owner, repo = snapshot.pop("repo_full_name").split("/", 1)
    activity = await fetch_github_activity(
        owner,
        repo,
        since=since,
        token=settings.github_token or None,
        use_global_token=True,
    )
    await event_bus.publish(
        "commit.batch_ready",
        {
            **snapshot,
            "access_status": "ACTIVE",
            "trigger": trigger,
            **activity,
            "commit_count": len(activity["commits"]),
        },
    )
