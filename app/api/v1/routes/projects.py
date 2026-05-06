"""
ArkLog - Project & Timeline Endpoints

GET /projects              — list all monitored projects with DB stats
GET /projects/{name}/timeline?days=N  — daily activity over the last N days
"""

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.config.projects import projects_config
from app.models.database import AsyncSessionLocal
from app.models.tables import CommitRecord, ProjectRecord, ReportRecord
from app.repositories.commit_repository import CommitRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.project import ProjectListResponse, ProjectSummary
from app.schemas.timeline import TimelineEntry, TimelineResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects() -> ProjectListResponse:
    """List all configured projects with commit and report counts from the DB."""
    summaries: list[ProjectSummary] = []

    async with AsyncSessionLocal() as session:
        for project in projects_config.projects:
            db_result = await session.execute(
                select(ProjectRecord).where(ProjectRecord.name == project.name).limit(1)
            )
            db_project = db_result.scalar_one_or_none()

            if db_project is None:
                summaries.append(
                    ProjectSummary(
                        name=project.name,
                        repo_full_name=project.repo_full_name,
                        clickup_task_id=project.clickup_task_id,
                        total_reports=0,
                        total_commits=0,
                        last_report_at=None,
                        last_commit_at=None,
                    )
                )
                continue

            total_commits = (await session.execute(
                select(func.count(CommitRecord.id)).where(CommitRecord.project_id == db_project.id)
            )).scalar_one() or 0

            total_reports = (await session.execute(
                select(func.count(ReportRecord.id)).where(ReportRecord.project_id == db_project.id)
            )).scalar_one() or 0

            last_commit_at = (await session.execute(
                select(func.max(CommitRecord.committed_at)).where(CommitRecord.project_id == db_project.id)
            )).scalar_one()

            last_report_at = (await session.execute(
                select(func.max(ReportRecord.generated_at)).where(ReportRecord.project_id == db_project.id)
            )).scalar_one()

            summaries.append(
                ProjectSummary(
                    name=project.name,
                    repo_full_name=project.repo_full_name,
                    clickup_task_id=project.clickup_task_id,
                    total_reports=total_reports,
                    total_commits=total_commits,
                    last_report_at=last_report_at,
                    last_commit_at=last_commit_at,
                )
            )

    return ProjectListResponse(count=len(summaries), projects=summaries)


@router.get("/projects/{name}/timeline", response_model=TimelineResponse)
async def project_timeline(
    name: str,
    days: int = Query(default=30, ge=1, le=365),
) -> TimelineResponse:
    """Daily activity timeline for a project over the last N days."""
    project = projects_config.get_by_name(name)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    since = datetime.utcnow() - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        db_result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.name == name).limit(1)
        )
        db_project = db_result.scalar_one_or_none()

        if db_project is None:
            return TimelineResponse(
                project_name=name, period_days=days, total_commits=0, total_reports=0, entries=[]
            )

        commit_repo = CommitRepository(session)
        report_repo = ReportRepository(session)

        commits = await commit_repo.get_since(db_project.id, since)
        reports = await report_repo.get_since(db_project.id, since)

    # Group by date (Python-side for portability across SQLite/PostgreSQL)
    commit_map: dict[str, int] = {}
    for c in commits:
        d = c.committed_at.strftime("%Y-%m-%d")
        commit_map[d] = commit_map.get(d, 0) + 1

    report_map: dict[str, tuple[int, str]] = {}
    for r in reports:
        d = r.generated_at.strftime("%Y-%m-%d")
        count, _ = report_map.get(d, (0, ""))
        report_map[d] = (count + 1, r.summary or "")

    # Build dense date range (all days, including zeros)
    entries: list[TimelineEntry] = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        report_count, summary = report_map.get(date, (0, None))
        entries.append(
            TimelineEntry(
                date=date,
                commits=commit_map.get(date, 0),
                reports=report_count,
                summary=summary or None,
            )
        )

    return TimelineResponse(
        project_name=name,
        period_days=days,
        total_commits=len(commits),
        total_reports=len(reports),
        entries=entries,
    )
