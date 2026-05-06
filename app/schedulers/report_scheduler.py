"""
ArkLog - Report Schedule Registration

Registers a cron job per project per schedule time from projects.yaml.
Scheduled jobs generate reports even when no commits have occurred.

This implements the core ArkLog insight:
  "Absence of commits is not absence of evolution."

When a scheduled job fires with zero commits, the AI receives full
project context (stack, goals, business context) and generates a
contextual status report — inferring phase (planning, debugging,
research, waiting on external dependencies) from the broader context.
"""

import structlog

from app.config.projects import projects_config
from app.domain.entities.project import Project
from app.schedulers.scheduler import scheduler

logger = structlog.get_logger(__name__)


def register_project_schedules() -> None:
    """
    Register cron jobs for all projects loaded from projects.yaml.
    Called once during application startup after projects are loaded.
    replace_existing=True makes this idempotent on restart.
    """
    job_count = 0
    for project in projects_config.projects:
        for time_str in project.schedule:
            hour, minute = map(int, time_str.split(":"))
            job_id = f"report__{project.name}__{time_str.replace(':', '')}"

            scheduler.add_job(
                _run_scheduled_report,
                trigger="cron",
                hour=hour,
                minute=minute,
                id=job_id,
                args=[project],
                replace_existing=True,
                misfire_grace_time=300,  # tolerate up to 5min clock drift or downtime
            )
            job_count += 1
            logger.debug("schedule_job_registered", project=project.name, time=time_str)

    logger.info(
        "schedules_registered",
        total_jobs=job_count,
        projects=len(projects_config.projects),
    )


async def _run_scheduled_report(project: Project) -> None:
    """
    Fire a report generation cycle for a project on schedule.
    Commits array is empty by design — the AI generates a contextual
    status report based on the project description and tech stack alone.
    """
    from app.core.events import event_bus

    logger.info("scheduled_report_fired", project=project.name)

    await event_bus.publish(
        "commit.batch_ready",
        {
            "project_name": project.name,
            "description": project.description,
            "tech_stack": list(project.tech_stack),
            "business_context": project.business_context,
            "report_style": project.report_style,
            "clickup_task_id": project.clickup_task_id,
            "commit_count": 0,
            "commits": [],
            "trigger": "scheduled",
        },
    )
