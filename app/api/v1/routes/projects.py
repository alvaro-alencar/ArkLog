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
            
            # Re-fetch with destinations for response
            await session.flush()
            
    # Refresh schedules (in-memory scheduler update)
    from app.schedulers.report_scheduler import register_project_schedules
    from app.core.events import on_startup # or a more surgical update
    # For now, just re-register everything (idempotent due to replace_existing=True)
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


@router.post("/{project_id}/instant-report", status_code=status.HTTP_202_ACCEPTED)
async def trigger_instant_report(
    project_id: int,
    data: InstantReportRequest,
    current_user: UserRecord = Depends(get_current_user),
) -> dict:
    """Trigger an immediate report for a project, bypassing the scheduler."""
    from datetime import datetime, timedelta
    from app.core.events import event_bus
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
            else datetime(2000, 1, 1)
        )

        commit_repo = CommitRepository(session)
        records = await commit_repo.get_since(project_id, since)
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
                "trigger": "instant",
            },
        )

    logger.info("instant_report_queued", project=project.name, commits=len(commits))
    return {"status": "queued", "commit_count": len(commits)}
