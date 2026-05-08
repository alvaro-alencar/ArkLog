"""
ArkLog - Commit Service

Subscriber of "github.push". Orchestrates the commit ingestion pipeline:
  github.push → parse commits → match project → persist → publish commit.batch_ready

Now fully driven by DB configurations.
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.integrations.github.commit_parser import CommitParser
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord
from app.repositories.commit_repository import CommitRepository

logger = structlog.get_logger(__name__)


class CommitService:
    """Handles github.push events and drives commit ingestion."""

    def __init__(self) -> None:
        self._parser = CommitParser()

    async def handle_push_event(self, payload: dict[str, Any]) -> None:
        repo_full_name = payload.get("repository", {}).get("full_name", "unknown")
        log = logger.bind(repo=repo_full_name)

        commits = self._parser.parse(payload)
        if not commits:
            log.info("commit_service_no_commits")
            return

        project_new_commits: dict[int, list] = {}

        async with AsyncSessionLocal() as session:
            async with session.begin():
                commit_repo = CommitRepository(session)

                result = await session.execute(
                    select(ProjectRecord)
                    .where(ProjectRecord.repo_full_name == repo_full_name)
                    .options(selectinload(ProjectRecord.destinations))
                )
                projects = list(result.scalars().all())

                if not projects:
                    log.debug("commit_service_repo_not_monitored")
                    return

                for project in projects:
                    new_commits_for_project = []
                    for commit in commits:
                        if not await commit_repo.exists_for_project(commit.sha, project.id):
                            await commit_repo.save_commit(commit, project.id)
                            new_commits_for_project.append(commit)

                    if new_commits_for_project:
                        project_new_commits[project.id] = new_commits_for_project
                        log.info("commits_ingested", project=project.name, new=len(new_commits_for_project))

        for project in projects:
            if project.id in project_new_commits:
                await self._notify_destinations(project, project_new_commits[project.id])

    async def _notify_destinations(self, project: Any, new_commits: list[Any]) -> None:
        from app.core.events import event_bus

        commit_data = [
            {
                "sha": c.sha,
                "short_sha": c.short_sha,
                "subject": c.subject,
                "author": c.author_name,
                "files_changed": len(c.files),
                "directories": sorted(c.affected_directories),
                "extensions": sorted(c.affected_extensions),
            }
            for c in new_commits
        ]

        daily_dests = [d for d in project.destinations if d.schedule == "daily"]

        for dest in daily_dests:
            await event_bus.publish(
                "commit.batch_ready",
                {
                    "project_name": project.name,
                    "description": project.description,
                    "tech_stack": project.tech_stack,
                    "business_context": project.business_context,
                    "report_style": dest.report_style or project.report_style,
                    "clickup_task_id": dest.clickup_task_id,
                    "commit_count": len(new_commits),
                    "commits": commit_data,
                    "trigger": "webhook",
                },
            )
