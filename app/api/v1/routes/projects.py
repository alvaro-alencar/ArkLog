"""
ArkLog - Project Management APIs

CRUD operations for projects and report destinations.
All routes are protected by JWT and scoped to the current user.
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord, ReportDestinationRecord, UserRecord
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse, InstantReportRequest

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ProjectListResponse)
async def list_user_projects(
    current_user: UserRecord = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects owned by the authenticated user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.user_id == current_user.id)
            .options(selectinload(ProjectRecord.destinations))
        )
        projects = result.scalars().all()
    
    # Map to schemas (simplified for now, reusing existing ProjectSummary or similar)
    from app.schemas.project import ProjectSummary
    summaries = [
        ProjectSummary(
            id=p.id,
            name=p.name,
            repo_full_name=p.repo_full_name,
            description=p.description,
            created_at=p.created_at,
        )
        for p in projects
    ]
    return ProjectListResponse(count=len(summaries), projects=summaries)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: UserRecord = Depends(get_current_user),
) -> Any:
    """Create a new project and its reporting destinations."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Check for name collision
            collision = await session.execute(
                select(ProjectRecord).where(ProjectRecord.name == data.name).limit(1)
            )
            if collision.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"Project name '{data.name}' already exists")

            project = ProjectRecord(
                name=data.name,
                repo_full_name=data.repo_full_name,
                description=data.description,
                report_style=data.report_style,
                tech_stack=data.tech_stack,
                business_context=data.business_context,
                user_id=current_user.id,
            )
            session.add(project)
            await session.flush()

            for dest_in in data.reports:
                dest = ReportDestinationRecord(
                    label=dest_in.label,
                    clickup_task_id=dest_in.clickup_task_id,
                    schedule=dest_in.schedule,
                    times=dest_in.times,
                    day=dest_in.day,
                    time=dest_in.time,
                    report_style=dest_in.report_style,
                    window_hours=dest_in.window_hours,
                    project_id=project.id,
                )
                session.add(dest)

            await session.flush()
            project_id = project.id

        # Re-fetch with destinations eagerly loaded while session is still open
        result = await session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id)
            .options(selectinload(ProjectRecord.destinations))
        )
        project = result.scalar_one()

    from app.schedulers.report_scheduler import register_project_schedules
    await register_project_schedules()

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> Any:
    """Get detailed project configuration."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id, ProjectRecord.user_id == current_user.id)
            .options(selectinload(ProjectRecord.destinations))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> None:
    """Delete a project and all its associated data."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(ProjectRecord).where(ProjectRecord.id == project_id, ProjectRecord.user_id == current_user.id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Delete cascades (if configured in DB) or manually
            # Commits and Reports have ForeignKey to ProjectRecord
            # We should probably have onDelete="CASCADE" in DB.
            # Our Alembic migration didn't specify it, so let's check.
            await session.delete(project)
    
    # Re-register schedules to remove deleted project jobs
    from app.schedulers.report_scheduler import register_project_schedules
    await register_project_schedules()


@router.post("/{project_id}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def backfill_commits(
    project_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> dict:
    """Fetch all commits from GitHub API and persist them for the project."""
    from app.integrations.github.api_client import fetch_all_commits
    from app.repositories.commit_repository import CommitRepository

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.id == project_id, ProjectRecord.user_id == current_user.id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    owner, repo = project.repo_full_name.split("/", 1)
    commits = await fetch_all_commits(owner, repo)

    saved = 0
    async with AsyncSessionLocal() as session:
        async with session.begin():
            commit_repo = CommitRepository(session)
            for commit in commits:
                if not await commit_repo.exists_for_project(commit.sha, project_id):
                    await commit_repo.save_commit(commit, project_id)
                    saved += 1

    logger.info("backfill_complete", project=project.repo_full_name, saved=saved, total=len(commits))
    return {"status": "ok", "saved": saved, "total": len(commits)}


@router.post("/{project_id}/instant-report", status_code=status.HTTP_202_ACCEPTED)
async def trigger_instant_report(
    project_id: int,
    data: InstantReportRequest,
    current_user: UserRecord = Depends(get_current_user),
) -> dict:
    """Trigger an immediate report for a project, bypassing the scheduler."""
    from datetime import datetime, timedelta
    from app.core.events import event_bus
    from app.integrations.github.api_client import fetch_github_activity
    from app.repositories.commit_repository import CommitRepository

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id, ProjectRecord.user_id == current_user.id)
            .options(selectinload(ProjectRecord.destinations))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.destinations:
            raise HTTPException(status_code=400, detail="Project has no report destinations configured")

        if data.destination_id:
            dest = next((d for d in project.destinations if d.id == data.destination_id), None)
            if not dest:
                raise HTTPException(status_code=404, detail="Destination not found")
        else:
            dest = project.destinations[0]

        since = (
            datetime.utcnow() - timedelta(hours=data.window_hours)
            if data.window_hours > 0
            else None
        )

        repo_full_name = project.repo_full_name
        dest_id = dest.id

    # Fetch all GitHub activity (commits, PRs, issues, CI, releases)
    owner, repo = repo_full_name.split("/", 1)
    activity = await fetch_github_activity(owner, repo, since=since)

    # Persist new commits to DB as a side effect (keeps history for scheduled reports)
    from app.domain.entities.commit import Commit
    from app.utils.datetime_utils import parse_github_timestamp
    async with AsyncSessionLocal() as session:
        async with session.begin():
            commit_repo = CommitRepository(session)
            for c in activity["commits"]:
                if not await commit_repo.exists_for_project(c["sha"], project_id):
                    entity = Commit(
                        sha=c["sha"],
                        message=c["subject"] + ("\n\n" + c["body"] if c.get("body") else ""),
                        author_name=c["author"],
                        author_email="",
                        timestamp=parse_github_timestamp(c.get("committed_at", "")),
                        url="",
                        repo_full_name=repo_full_name,
                        branch="",
                        files=(),
                    )
                    await commit_repo.save_commit(entity, project_id)

    # Re-fetch dest details (session closed above)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProjectRecord)
            .where(ProjectRecord.id == project_id)
            .options(selectinload(ProjectRecord.destinations))
        )
        project = result.scalar_one()
        dest = next(d for d in project.destinations if d.id == dest_id)

        await event_bus.publish(
            "commit.batch_ready",
            {
                "project_name": project.name,
                "description": project.description,
                "tech_stack": project.tech_stack,
                "business_context": project.business_context,
                "report_style": dest.report_style or project.report_style,
                "clickup_task_id": dest.clickup_task_id,
                "trigger": "instant",
                # Full activity payload
                "commits": activity["commits"],
                "pull_requests": activity["pull_requests"],
                "issues": activity["issues"],
                "workflow_runs": activity["workflow_runs"],
                "releases": activity["releases"],
                "commit_count": len(activity["commits"]),
            },
        )

    total_activity = sum(len(v) for v in activity.values())
    logger.info("instant_report_queued", project=project.name, **{k: len(v) for k, v in activity.items()})
    return {"status": "queued", "commit_count": len(activity["commits"]), "total_activity": total_activity}
