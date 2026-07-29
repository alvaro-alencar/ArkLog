"""GitHub push ingestion with project-scoped report events."""

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
    def __init__(self) -> None:
        self._parser = CommitParser()

    async def handle_push_event(self, payload: dict[str, Any]) -> None:
        repo_full_name = payload.get("repository", {}).get("full_name", "unknown")
        log = logger.bind(repo=repo_full_name)
        commits = self._parser.parse(payload)
        if not commits:
            log.info("commit_service_no_commits")
            return

        project_new_commits: dict[int, list[Any]] = {}
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
                    return

                for project in projects:
                    new_commits = []
                    for commit in commits:
                        if not await commit_repo.exists_for_project(commit.sha, project.id):
                            await commit_repo.save_commit(commit, project.id)
                            new_commits.append(commit)
                    if new_commits:
                        project_new_commits[project.id] = new_commits

        for project in projects:
            if project.id in project_new_commits:
                await self._notify_destinations(project, project_new_commits[project.id])

    async def _notify_destinations(self, project: Any, new_commits: list[Any]) -> None:
        from app.core.events import event_bus

        commit_data = [
            {
                "sha": commit.sha,
                "short_sha": commit.short_sha,
                "subject": commit.subject,
                "author": commit.author_name,
                "files_changed": len(commit.files),
                "directories": sorted(commit.affected_directories),
                "extensions": sorted(commit.affected_extensions),
            }
            for commit in new_commits
        ]
        daily_destinations = [
            destination
            for destination in project.destinations
            if destination.schedule == "daily"
        ]
        for destination in daily_destinations:
            await event_bus.publish(
                "commit.batch_ready",
                {
                    "project_id": project.id,
                    "user_id": project.user_id,
                    "project_name": project.name,
                    "description": project.description,
                    "tech_stack": project.tech_stack,
                    "business_context": project.business_context,
                    "report_style": destination.report_style or project.report_style,
                    "clickup_task_id": destination.clickup_task_id,
                    "commit_count": len(new_commits),
                    "commits": commit_data,
                    "trigger": "webhook",
                },
            )
