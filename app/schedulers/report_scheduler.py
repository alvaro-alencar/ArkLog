"""
ArkLog - Report Schedule Registration

Registers one cron job per project per ReportDestination from projects.yaml.

  daily  → fires at each HH:MM in dest.times  (trigger: "daily_scheduled")
  weekly → fires at dest.time on dest.day      (trigger: "weekly_scheduled")

Continuidade: cada relatório começa do ponto onde o anterior terminou.
O scheduler consulta o generated_at do último relatório com o mesmo trigger
e busca apenas commits mais novos que esse timestamp — sem janelas fixas,
sem gaps, sem duplicatas entre relatórios consecutivos.
"""

import structlog

from app.config.projects import projects_config
from app.domain.entities.project import Project, ReportDestination
from app.schedulers.scheduler import scheduler

logger = structlog.get_logger(__name__)

TRIGGER_DAILY = "daily_scheduled"
TRIGGER_WEEKLY = "weekly_scheduled"


def register_project_schedules() -> None:
    """Register cron jobs for all destinations in all projects."""
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
                        args=[project, dest, TRIGGER_DAILY],
                        replace_existing=True,
                        misfire_grace_time=300,
                    )
                    job_count += 1
                    logger.debug("schedule_job_registered", project=project.name, dest=dest.label, time=time_str)

            elif dest.schedule == "weekly":
                hour, minute = map(int, dest.time.split(":"))
                job_id = f"report__{project.name}__{dest.label}__weekly"
                scheduler.add_job(
                    _run_scheduled_report,
                    trigger="cron",
                    day_of_week=dest.day[:3],
                    hour=hour,
                    minute=minute,
                    id=job_id,
                    args=[project, dest, TRIGGER_WEEKLY],
                    replace_existing=True,
                    misfire_grace_time=3600,
                )
                job_count += 1
                logger.debug("schedule_job_registered", project=project.name, dest=dest.label, day=dest.day, time=dest.time)

    logger.info("schedules_registered", total_jobs=job_count, projects=len(projects_config.projects))


async def _run_scheduled_report(project: Project, dest: ReportDestination, trigger: str) -> None:
    """
    Gera relatório para um destino.

    Continuidade: busca o generated_at do último relatório com o mesmo trigger.
    Commits desde esse ponto são incluídos no novo relatório.
    Se nunca houve relatório anterior, inclui todos os commits do DB.
    Se não há commits novos, a IA infere o estado atual pelo contexto do projeto.
    """
    from datetime import datetime, timezone

    from app.core.events import event_bus
    from app.models.database import AsyncSessionLocal
    from app.repositories.commit_repository import CommitRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.report_repository import ReportRepository

    logger.info("scheduled_report_fired", project=project.name, dest=dest.label, trigger=trigger)

    commits: list[dict] = []
    commit_count = 0

    async with AsyncSessionLocal() as session:
        proj_repo = ProjectRepository(session)
        proj_record = await proj_repo.get_by_name(project.name)

        if proj_record:
            report_repo = ReportRepository(session)
            commit_repo = CommitRepository(session)

            # Ponto de continuidade: último relatório com este mesmo trigger
            last_at = await report_repo.get_last_generated_at_for_trigger(proj_record.id, trigger)

            if last_at is not None:
                since = last_at
            else:
                # Primeiro relatório deste tipo — inclui tudo que está no DB
                since = datetime(2000, 1, 1)

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
                trigger=trigger,
                since=str(last_at),
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
            "trigger": trigger,
        },
    )
