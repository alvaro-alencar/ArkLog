"""ArkLog - Report History Endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.tables import ProjectRecord, ReportRecord, UserRecord
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportDetailResponse, ReportListResponse, ReportSummaryResponse

router = APIRouter()


def _to_summary(record: ReportRecord, project_name: str) -> ReportSummaryResponse:
    return ReportSummaryResponse(
        id=record.id,
        project_id=record.project_id,
        project_name=project_name,
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        commit_count=record.commit_count,
        generated_at=record.generated_at,
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserRecord = Depends(get_current_user),
) -> ReportListResponse:
    """All reports for the current user, optionally filtered by project."""
    async with AsyncSessionLocal() as session:
        # Fetch user's projects to build a name map and scope by ownership
        proj_result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.user_id == current_user.id)
        )
        user_projects = {p.id: p.name for p in proj_result.scalars().all()}

        if not user_projects:
            return ReportListResponse(total=0, limit=limit, offset=offset, reports=[])

        project_ids = [project_id] if project_id and project_id in user_projects else list(user_projects.keys())

        stmt = (
            select(ReportRecord)
            .where(ReportRecord.project_id.in_(project_ids))
            .order_by(ReportRecord.generated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        records = list((await session.execute(stmt)).scalars().all())

        from sqlalchemy import func
        total_result = await session.execute(
            select(func.count(ReportRecord.id)).where(ReportRecord.project_id.in_(project_ids))
        )
        total = total_result.scalar_one()

    return ReportListResponse(
        total=total,
        limit=limit,
        offset=offset,
        reports=[_to_summary(r, user_projects.get(r.project_id, "unknown")) for r in records],
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> ReportDetailResponse:
    """Full content of a single report (scoped to current user)."""
    async with AsyncSessionLocal() as session:
        repo = ReportRepository(session)
        record = await repo.get_by_id(report_id)
        if not record:
            raise HTTPException(status_code=404, detail="Report not found")

        proj_result = await session.execute(
            select(ProjectRecord).where(
                ProjectRecord.id == record.project_id,
                ProjectRecord.user_id == current_user.id,
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Report not found")

    return ReportDetailResponse(
        id=record.id,
        project_id=record.project_id,
        project_name=project.name,
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        content=record.content,
        commit_count=record.commit_count,
        generated_at=record.generated_at,
    )
