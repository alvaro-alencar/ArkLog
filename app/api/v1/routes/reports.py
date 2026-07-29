"""Report history scoped to the authenticated Ark user."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.tables import AutomationFlowRecord, ProjectRecord, ReportRecord, UserRecord
from app.schemas.report import ReportDetailResponse, ReportListResponse, ReportSummaryResponse

router = APIRouter()


def _to_summary(record: ReportRecord, owner_name: str) -> ReportSummaryResponse:
    return ReportSummaryResponse(
        id=record.id,
        project_id=record.project_id,
        flow_id=record.flow_id,
        project_name=owner_name,
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        commit_count=record.commit_count,
        generated_at=record.generated_at,
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: int | None = Query(default=None),
    flow_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserRecord = Depends(get_current_user),
) -> ReportListResponse:
    async with AsyncSessionLocal() as session:
        projects_result = await session.execute(
            select(ProjectRecord).where(ProjectRecord.user_id == current_user.id)
        )
        flows_result = await session.execute(
            select(AutomationFlowRecord).where(AutomationFlowRecord.user_id == current_user.id)
        )
        projects = {item.id: item.name for item in projects_result.scalars().all()}
        flows = {item.id: item.name for item in flows_result.scalars().all()}

        ownership = []
        if project_id is not None:
            if project_id not in projects:
                return ReportListResponse(total=0, limit=limit, offset=offset, reports=[])
            ownership.append(ReportRecord.project_id == project_id)
        elif flow_id is not None:
            if flow_id not in flows:
                return ReportListResponse(total=0, limit=limit, offset=offset, reports=[])
            ownership.append(ReportRecord.flow_id == flow_id)
        else:
            if projects:
                ownership.append(ReportRecord.project_id.in_(list(projects)))
            if flows:
                ownership.append(ReportRecord.flow_id.in_(list(flows)))

        if not ownership:
            return ReportListResponse(total=0, limit=limit, offset=offset, reports=[])

        predicate = or_(*ownership)
        records = list(
            (
                await session.execute(
                    select(ReportRecord)
                    .where(predicate)
                    .order_by(ReportRecord.generated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        total = int(
            await session.scalar(select(func.count(ReportRecord.id)).where(predicate)) or 0
        )

    def owner_name(record: ReportRecord) -> str:
        if record.flow_id is not None:
            return flows.get(record.flow_id, "Fluxo removido")
        return projects.get(record.project_id or -1, "Projeto removido")

    return ReportListResponse(
        total=total,
        limit=limit,
        offset=offset,
        reports=[_to_summary(record, owner_name(record)) for record in records],
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> ReportDetailResponse:
    async with AsyncSessionLocal() as session:
        record = await session.get(ReportRecord, report_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")

        owner_name: str | None = None
        if record.flow_id is not None:
            flow = await session.scalar(
                select(AutomationFlowRecord).where(
                    AutomationFlowRecord.id == record.flow_id,
                    AutomationFlowRecord.user_id == current_user.id,
                )
            )
            owner_name = flow.name if flow else None
        elif record.project_id is not None:
            project = await session.scalar(
                select(ProjectRecord).where(
                    ProjectRecord.id == record.project_id,
                    ProjectRecord.user_id == current_user.id,
                )
            )
            owner_name = project.name if project else None

        if owner_name is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return ReportDetailResponse(
        id=record.id,
        project_id=record.project_id,
        flow_id=record.flow_id,
        project_name=owner_name,
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        content=record.content,
        commit_count=record.commit_count,
        generated_at=record.generated_at,
    )
