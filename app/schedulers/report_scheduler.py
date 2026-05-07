"""
ArkLog - Report Schedule Registration

Registers one cron job per project per ReportDestination from projects.yaml.

  daily  → fires at each HH:MM in dest.times
  weekly → fires at dest.time on dest.day (e.g. friday 18:00)

For weekly destinations (window_days > 0), the job fetches commits from
the past N days out of the DB before generating the report, so the AI
has real data instead of an empty context.
"""

import structlog

from app.config.projects import projects_config
from app.domain.entities.project import Project, ReportDestination
from app.schedulers.scheduler import scheduler

logger = structlog.get_logger(__name__)


def register_project_schedules() -> None:
    """
    Register cron jobs for all destinations in all projects.
    replace_existing=True makes this idempotent on restart.
    """
    job_count = 0
    for project in projects_config.projects:
        for dest in project.reports:
            if dest.schedule == "daily":
                for time_str in dest.times:
                    hour, minute = map(int, time_str.split(":"))
                    job_id = f"report__{project.name}__{dest.label}__{time_str.replace(':', '')}"
                    scheduler.add_job(
                        _run_scheduled_report,
                        trigger="cron",
                        hour=hour,
                        minute=minute,
                        id=job_id,
                        args=[project, dest],
                        replace_existing=True,
                        misfire_grace_time=300,
                    )
                    job_count += 1
                    logger.debug(
                        "schedule_job_registered",
                        project=project.name,
                        dest=dest.label,
                        time=time_str,
                    )

            elif dest.schedule == "weekly":
                hour, minute = map(int, dest.time.split(":"))
                job_id = f"report__{project.name}__{dest.label}__weekly"
                scheduler.add_job(
                    _run_scheduled_report,
                    trigger="cron",
                    day_of_week=dest.day[:3],  # APScheduler: "mon", "fri", etc.
                    hour=hour,
                    minute=minute,
                    id=job_id,
                    args=[project, dest],
                    replace_existing=True,
                    misfire_grace_time=3600,   # 1h grace for weekly jobs
                )
                job_count += 1
                logger.debug(
                    "schedule_job_registered",
                    project=project.name,
                    dest=dest.label,
                    day=dest.day,
                    time=dest.time,
                )

    logger.info(
        "schedules_registered",
        total_jobs=job_count,
        projects=len(projects_config.projects),
    )


async def _run_scheduled_report(project: Project, dest: ReportDestination) -> None:
    """
    Fire a report for one destination.
    If dest.window_days > 0, fetches real commits from the DB for that period.
    If window_days == 0, sends an empty commit list so the AI generates a
    contextual status report from project description and tech stack alone.
    """
    from app.core.events import event_bus

    logger.info("scheduled_report_fired", project=project.name, dest=dest.label)

    commits: list[dict] = []
    commit_count = 0

    if dest.window_days > 0:
        from datetime import datetime, timedelta, timezone

        from app.models.database import AsyncSessionLocal
        from app.repositories.commit_repository import CommitRepository
        from app.repositories.project_repository import ProjectRepository

        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dest.window_days)

        async with AsyncSessionLocal() as session:
            proj_repo = ProjectRepository(session)
            commit_repo = CommitRepository(session)
            proj_record = await proj_repo.get_by_name(project.name)
            if proj_record:
                records = await commit_repo.get_since(proj_record.id, since)
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
                commit_count = len(commits)
                logger.info(
                    "scheduled_commits_fetched",
                    project=project.name,
                    dest=dest.label,
                    window_days=dest.window_days,
                    commits=commit_count,
                )

    await event_bus.publish(
        "commit.batch_ready",
        {
            "project_name": project.name,
            "description": project.description,
            "tech_stack": list(project.tech_stack),
            "business_context": project.business_context,
            "report_style": dest.report_style,
            "clickup_task_id": dest.clickup_task_id,
            "commit_count": commit_count,
            "commits": commits,
            "trigger": "scheduled",
        },
    )
