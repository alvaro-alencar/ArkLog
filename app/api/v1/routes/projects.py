"""
ArkLog - Project & Timeline Endpoints

GET /projects              — list all monitored projects with DB stats
GET /projects/{name}/timeline?days=N  — daily activity over the last N days
"""

from datetime import timedelta

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, select

from app.config.projects import projects_config
from app.models.database import AsyncSessionLocal
from app.models.tables import CommitRecord, ProjectRecord, ReportRecord
from app.repositories.commit_repository import CommitRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.project import ProjectListResponse, ProjectSummary
from app.schemas.timeline import TimelineEntry, TimelineResponse
from app.utils.datetime_utils import naive_utcnow

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects() -> ProjectListResponse:
    """List all configured projects with commit and report counts from the DB."""
    project_names = [p.name for p in projects_config.projects]

    # Single query with correlated subqueries — replaces N×4 separate queries
    commit_count_sq = (
        select(func.count(CommitRecord.id))
        .where(CommitRecord.project_id == ProjectRecord.id)
        .correlate(ProjectRecord)
        .scalar_subquery()
    )
    report_count_sq = (
        select(func.count(ReportRecord.id))
        .where(ReportRecord.project_id == ProjectRecord.id)
        .correlate(ProjectRecord)
        .scalar_subquery()
    )
    last_commit_sq = (
        select(func.max(CommitRecord.committed_at))
        .where(CommitRecord.project_id == ProjectRecord.id)
        .correlate(ProjectRecord)
        .scalar_subquery()
    )
    last_report_sq = (
        select(func.max(ReportRecord.generated_at))
        .where(ReportRecord.project_id == ProjectRecord.id)
        .correlate(ProjectRecord)
        .scalar_subquery()
    )

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(
                ProjectRecord.name,
                commit_count_sq.label("total_commits"),
                report_count_sq.label("total_reports"),
                last_commit_sq.label("last_commit_at"),
                last_report_sq.label("last_report_at"),
            ).where(ProjectRecord.name.in_(project_names))
        )).all()

    db_stats = {row.name: row for row in rows}

    summaries: list[ProjectSummary] = []
    for project in projects_config.projects:
        row = db_stats.get(project.name)
        summaries.append(
            ProjectSummary(
                name=project.name,
                repo_full_name=project.repo_full_name,
                clickup_task_id=project.clickup_task_id,
                total_reports=row.total_reports if row else 0,
                total_commits=row.total_commits if row else 0,
                last_report_at=row.last_report_at if row else None,
                last_commit_at=row.last_commit_at if row else None,
            )
        )

    return ProjectListResponse(count=len(summaries), projects=summaries)


@router.post("/projects/{name}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def backfill_project(name: str, background_tasks: BackgroundTasks) -> dict:
    """
    Fetch all historical commits from GitHub for a project and generate
    a comprehensive report covering the entire history.
    Runs in background — returns immediately with 202.
    """
    from app.services.backfill_service import backfill_project as _backfill

    project = projects_config.get_by_name(name)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    background_tasks.add_task(_backfill, name)
    return {"status": "accepted", "project": name, "message": "Backfill started — report will be posted to ClickUp when ready."}


@router.get("/projects/{name}/timeline", response_model=TimelineResponse)
async def project_timeline(
    name: str,
    days: int = Query(default=30, ge=1, le=365),
) -> TimelineResponse:
    """Daily activity timeline for a project over the last N days."""
    project = projects_config.get_by_name(name)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    since = naive_utcnow() - timedelta(days=days)

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
        date = (naive_utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
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
