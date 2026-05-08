"""
ArkLog - Report Schedule Registration

Registers cron jobs for all ProjectDestinations stored in the database.
"""

import structlog
from sqlalchemy import select

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
    Fetch project and destination from DB, pull full GitHub activity, trigger report.
    """
    from datetime import datetime, timedelta
    from app.core.events import event_bus
    from app.integrations.github.api_client import fetch_github_activity
    from app.repositories.report_repository import ReportRepository
    from app.models.tables import ProjectRecord, ReportDestinationRecord

    async with AsyncSessionLocal() as session:
        project = await session.get(ProjectRecord, project_id)
        result = await session.execute(
            select(ReportDestinationRecord).where(ReportDestinationRecord.id == dest_id)
        )
        dest = result.scalar_one_or_none()

        if not project or not dest:
            logger.warning("scheduled_report_missing_target", project_id=project_id, dest_id=dest_id)
            return

        logger.info("scheduled_report_fired", project=project.name, dest=dest.label, trigger=trigger)

        if dest.window_hours > 0:
            since = datetime.utcnow() - timedelta(hours=dest.window_hours)
        else:
            report_repo = ReportRepository(session)
            last_at = await report_repo.get_last_generated_at_for_trigger(project.id, trigger)
            since = last_at if last_at else datetime(2000, 1, 1)

        # Snapshot project info while session is still open
        proj_name = project.name
        proj_desc = project.description
        proj_stack = project.tech_stack
        proj_context = project.business_context
        repo_full_name = project.repo_full_name
        report_style = dest.report_style or project.report_style
        clickup_task_id = dest.clickup_task_id

    # Fetch live from GitHub API (always fresh, not dependent on webhook history)
    owner, repo = repo_full_name.split("/", 1)
    activity = await fetch_github_activity(owner, repo, since=since if since != datetime(2000, 1, 1) else None)

    from app.core.events import event_bus
    await event_bus.publish(
        "commit.batch_ready",
        {
            "project_name": proj_name,
            "description": proj_desc,
            "tech_stack": proj_stack,
            "business_context": proj_context,
            "report_style": report_style,
            "clickup_task_id": clickup_task_id,
            "trigger": trigger,
            "commits": activity["commits"],
            "pull_requests": activity["pull_requests"],
            "issues": activity["issues"],
            "workflow_runs": activity["workflow_runs"],
            "releases": activity["releases"],
            "commit_count": len(activity["commits"]),
        },
    )
