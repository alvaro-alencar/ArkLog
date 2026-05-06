"""
ArkLog - Commit Service

Subscriber of "github.push". Orchestrates the commit ingestion pipeline:
  github.push → parse commits → match project → persist → publish commit.batch_ready

Only new (unseen) commits are persisted and forwarded — duplicate push
events from GitHub are idempotent thanks to the SHA existence check.
"""

from typing import Any

import structlog

from app.config.projects import projects_config
from app.domain.entities.commit import Commit
from app.integrations.github.commit_parser import CommitParser
from app.models.database import AsyncSessionLocal
from app.repositories.commit_repository import CommitRepository
from app.repositories.project_repository import ProjectRepository

logger = structlog.get_logger(__name__)


class CommitService:
    """Handles github.push events and drives commit ingestion."""

    def __init__(self) -> None:
        self._parser = CommitParser()

    async def handle_push_event(self, payload: dict[str, Any]) -> None:
        repo_full_name = payload.get("repository", {}).get("full_name", "unknown")
        log = logger.bind(repo=repo_full_name)

        # 1. Match the incoming repo to a configured project
        project = projects_config.get_by_repo(repo_full_name)
        if project is None:
            log.debug("commit_service_project_not_configured")
            return

        # 2. Parse commits from the webhook payload
        commits = self._parser.parse(payload)
        if not commits:
            log.info("commit_service_no_commits")
            return

        # 3. Persist new commits, skip duplicates
        new_commits: list[Commit] = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                project_repo = ProjectRepository(session)
                commit_repo = CommitRepository(session)

                project_record = await project_repo.get_or_create(project)

                for commit in commits:
                    if await commit_repo.exists(commit.sha):
                        log.debug("commit_already_processed", sha=commit.short_sha)
                        continue
                    await commit_repo.save_commit(commit, project_record.id)
                    new_commits.append(commit)

        log.info("commits_ingested", new=len(new_commits), skipped=len(commits) - len(new_commits))

        if not new_commits:
            return

        # 4. Publish enriched payload for the AI engine (Phase 3)
        from app.core.events import event_bus

        await event_bus.publish(
            "commit.batch_ready",
            {
                "project_name": project.name,
                "description": project.description,
                "tech_stack": list(project.tech_stack),
                "business_context": project.business_context,
                "report_style": project.report_style,
                "clickup_task_id": project.clickup_task_id,
                "commit_count": len(new_commits),
                "commits": [
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
                ],
            },
        )
