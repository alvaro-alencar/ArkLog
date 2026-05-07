"""
ArkLog - Report Schedule Registration

Registers cron jobs for all ProjectDestinations stored in the database.
"""

import structlog

from app.models.database import AsyncSessionLocal
from app.repositories.project_repository import ProjectRepository
from app.schedulers.scheduler import scheduler

logger = structlog.get_logger(__name__)

TRIGGER_DAILY = "daily_scheduled"
TRIGGER_WEEKLY = "weekly_scheduled"


async def register_project_schedules() -> None:
    """Fetch all projects from DB and register their reporting schedules."""
    job_count = 0
    
    async with AsyncSessionLocal() as session:
        proj_repo = ProjectRepository(session)
        projects = await proj_repo.get_all_active()

        for project in projects:
            for dest in project.destinations:
                if dest.schedule == "daily":
                    for time_str in dest.times:
                        hour, minute = map(int, time_str.split(":"))
                        job_id = f"report__{project.id}__{dest.id}__{time_str.replace(':', '')}"
                        scheduler.add_job(
                            _run_scheduled_report,
                            trigger="cron",
                            hour=hour,
                            minute=minute,
                            id=job_id,
                            args=[project.id, dest.id, TRIGGER_DAILY],
                            replace_existing=True,
                            misfire_grace_time=300,
                        )
                        job_count += 1

                elif dest.schedule == "weekly":
                    hour, minute = map(int, dest.time.split(":"))
                    job_id = f"report__{project.id}__{dest.id}__weekly"
                    scheduler.add_job(
                        _run_scheduled_report,
                        trigger="cron",
                        day_of_week=dest.day[:3],
                        hour=hour,
                        minute=minute,
                        id=job_id,
                        args=[project.id, dest.id, TRIGGER_WEEKLY],
                        replace_existing=True,
                        misfire_grace_time=3600,
                    )
                    job_count += 1

    logger.info("schedules_registered", total_jobs=job_count, projects=len(projects))


async def _run_scheduled_report(project_id: int, dest_id: int, trigger: str) -> None:
    """
    Fetch project and destination from DB and trigger report generation.
    """
    from datetime import datetime
    from app.core.events import event_bus
    from app.repositories.commit_repository import CommitRepository
    from app.repositories.report_repository import ReportRepository
    from app.models.tables import ProjectRecord, ReportDestinationRecord

    async with AsyncSessionLocal() as session:
        project = await session.get(ProjectRecord, project_id)
        # Manually fetch destination to avoid lazy loading issues in background job
        result = await session.execute(
            ProjectRepository(session).select(ReportDestinationRecord).where(ReportDestinationRecord.id == dest_id)
        )
        dest = result.scalar_one_or_none()

        if not project or not dest:
            logger.warning("scheduled_report_missing_target", project_id=project_id, dest_id=dest_id)
            return

        logger.info("scheduled_report_fired", project=project.name, dest=dest.label, trigger=trigger)

        report_repo = ReportRepository(session)
        commit_repo = CommitRepository(session)

        if dest.window_hours > 0:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=dest.window_hours)
        else:
            # Continuity: use last report timestamp so we don't repeat commits
            last_at = await report_repo.get_last_generated_at_for_trigger(project.id, trigger)
            since = last_at if last_at else datetime(2000, 1, 1)

        records = await commit_repo.get_since(project.id, since)
        commits = [
            {
                "sha": r.sha,
                "short_sha": r.sha[:7],
                "subject": r.message.split("\n")[0],
                "author": r.author_name,
                "files_changed": r.files_changed,
                "directories": [],
                "extensions": [],
            }
            for r in records
        ]

        await event_bus.publish(
            "commit.batch_ready",
            {
                "project_name": project.name,
                "description": project.description,
                "tech_stack": project.tech_stack,
                "business_context": project.business_context,
                "report_style": dest.report_style or project.report_style,
                "clickup_task_id": dest.clickup_task_id,
                "commit_count": len(commits),
                "commits": commits,
                "trigger": trigger,
            },
        )
