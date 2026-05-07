"""
ArkLog - Report History Endpoints

GET /projects/{name}/reports           — paginated report list
GET /reports/{report_id}               — full report content
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.config.projects import projects_config
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportDetailResponse, ReportListResponse, ReportSummaryResponse

router = APIRouter()


@router.get("/projects/{name}/reports", response_model=ReportListResponse)
async def list_project_reports(
    name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReportListResponse:
    """Paginated report history for a project, newest first."""
    if not projects_config.get_by_name(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    async with AsyncSessionLocal() as session:
        proj_result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.name == name).limit(1)
        )
        db_project = proj_result.scalar_one_or_none()

        if db_project is None:
            return ReportListResponse(project_name=name, total=0, limit=limit, offset=offset, reports=[])

        repo = ReportRepository(session)
        records = await repo.get_by_project(db_project.id, limit=limit, offset=offset)
        total = await repo.count_by_project(db_project.id)

    return ReportListResponse(
        project_name=name,
        total=total,
        limit=limit,
        offset=offset,
        reports=[
            ReportSummaryResponse(
                id=r.id,
                project_name=name,
                trigger=r.trigger,
                status=r.status,
                summary=r.summary,
                commit_count=r.commit_count,
                generated_at=r.generated_at,
                published_at=r.published_at,
                clickup_comment_id=r.clickup_comment_id,
            )
            for r in records
        ],
    )


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report(report_id: int) -> ReportDetailResponse:
    """Retrieve the full content of a specific report by ID."""
    async with AsyncSessionLocal() as session:
        repo = ReportRepository(session)
        record = await repo.get_by_id(report_id)

        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        proj_result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.id == record.project_id).limit(1)
        )
        db_project = proj_result.scalar_one_or_none()

    return ReportDetailResponse(
        id=record.id,
        project_name=db_project.name if db_project else "unknown",
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        content=record.content,
        commit_count=record.commit_count,
        generated_at=record.generated_at,
        published_at=record.published_at,
        clickup_comment_id=record.clickup_comment_id,
    )
