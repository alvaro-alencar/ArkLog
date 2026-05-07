"""
ArkLog - Backfill Service

Fetches all historical commits from the GitHub API for a project,
persists them to the DB, and triggers a full report covering the
entire history. Designed as a one-time operation per project.
"""

from typing import Any

import structlog

from app.config.projects import projects_config
from app.core.events import event_bus
from app.integrations.github.api_client import fetch_all_commits
from app.models.database import AsyncSessionLocal
from app.repositories.commit_repository import CommitRepository
from app.repositories.project_repository import ProjectRepository

logger = structlog.get_logger(__name__)


async def backfill_project(project_name: str) -> dict[str, Any]:
    """
    Fetch all GitHub commits for a project, save new ones, and generate
    a comprehensive report for each daily destination.

    Returns: {"total_fetched": N, "new_commits": M, "destinations_triggered": K}
    """
    project = projects_config.get_by_name(project_name)
    if project is None:
        raise ValueError(f"Project '{project_name}' not found in projects.yaml")

    logger.info("backfill_start", project=project_name)

    # 1. Fetch all commits from GitHub API
    raw_commits = await fetch_all_commits(project.repo_owner, project.repo_name)
    total_fetched = len(raw_commits)

    # 2. Persist new commits (idempotent — skips existing SHAs)
    new_count = 0
    async with AsyncSessionLocal() as session:
        async with session.begin():
            proj_repo = ProjectRepository(session)
            commit_repo = CommitRepository(session)
            proj_record = await proj_repo.get_or_create(project)

            for commit in raw_commits:
                if not await commit_repo.exists(commit.sha):
                    await commit_repo.save_commit(commit, proj_record.id)
                    new_count += 1

    logger.info(
        "backfill_commits_saved",
        project=project_name,
        total_fetched=total_fetched,
        new_commits=new_count,
    )

    # 3. Build commit payload (all historical commits, newest first from API)
    commit_data = [
        {
            "sha": c.sha,
            "short_sha": c.sha[:7],
            "subject": c.message.split("\n")[0],
            "author": c.author_name,
            "files_changed": 0,
            "directories": [],
            "extensions": [],
        }
        for c in raw_commits
    ]

    # 4. Trigger report for each daily destination
    daily_dests = project.daily_destinations
    for dest in daily_dests:
        await event_bus.publish(
            "commit.batch_ready",
            {
                "project_name": project.name,
                "description": project.description,
                "tech_stack": list(project.tech_stack),
                "business_context": project.business_context,
                "report_style": dest.report_style,
                "clickup_task_id": dest.clickup_task_id,
                "commit_count": total_fetched,
                "commits": commit_data,
                "trigger": "backfill",
            },
        )

    logger.info(
        "backfill_complete",
        project=project_name,
        destinations=len(daily_dests),
    )

    return {
        "total_fetched": total_fetched,
        "new_commits": new_count,
        "destinations_triggered": len(daily_dests),
    }
