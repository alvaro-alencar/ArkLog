"""Report history scoped to the authenticated Ark user."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    AutomationFlowRecord,
    ProjectRecord,
    ReportPublicationRecord,
    ReportRecord,
    UserRecord,
)
from app.schemas.report import (
    ReportDetailResponse,
    ReportListResponse,
    ReportPublicationResponse,
    ReportSummaryResponse,
)

router = APIRouter()


def _owner_metadata(
    record: ReportRecord,
    projects: dict[int, str],
    flows: dict[int, dict[str, str]],
) -> dict[str, Any]:
    if record.flow_id is not None:
        flow = flows.get(record.flow_id)
        if flow is None:
            return {
                "name": "Fluxo removido",
                "kind": "flow",
                "source": None,
                "destination": None,
            }
        return {
            "name": flow["name"],
            "kind": "flow",
            "source": flow["source"],
            "destination": flow["destination"],
        }
    return {
        "name": projects.get(record.project_id or -1, "Projeto removido"),
        "kind": "project",
        "source": "github" if record.project_id is not None else None,
        "destination": None,
    }


def _to_summary(record: ReportRecord, owner: dict[str, Any]) -> ReportSummaryResponse:
    item_count = max(0, int(record.commit_count or 0))
    return ReportSummaryResponse(
        id=record.id,
        project_id=record.project_id,
        flow_id=record.flow_id,
        project_name=str(owner["name"]),
        owner_kind=str(owner["kind"]),
        source_provider=owner.get("source"),
        destination_provider=owner.get("destination"),
        trigger=record.trigger,
        status=record.status,
        summary=record.summary,
        item_count=item_count,
        commit_count=item_count,
        generated_at=record.generated_at,
    )


def _to_publication(record: ReportPublicationRecord) -> ReportPublicationResponse:
    return ReportPublicationResponse(
        platform=record.platform,
        target_id=record.target_id,
        external_id=record.external_id,
        status=record.status,
        error_message=record.error_message,
        published_at=record.published_at,
    )


async def _owned_catalogs(
    session: Any,
    current_user: UserRecord,
) -> tuple[dict[int, str], dict[int, dict[str, str]]]:
    projects_result = await session.execute(
        select(ProjectRecord).where(ProjectRecord.user_id == current_user.id)
    )
    flows_result = await session.execute(
        select(AutomationFlowRecord)
        .where(AutomationFlowRecord.user_id == current_user.id)
        .options(
            selectinload(AutomationFlowRecord.source_connection),
            selectinload(AutomationFlowRecord.destination_connection),
        )
    )
    projects = {item.id: item.name for item in projects_result.scalars().all()}
    flows = {
        item.id: {
            "name": item.name,
            "source": item.source_connection.provider,
            "destination": item.destination_connection.provider,
        }
        for item in flows_result.scalars().all()
    }
    return projects, flows


@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: int | None = Query(default=None),
    flow_id: int | None = Query(default=None),
    status: str | None = Query(default=None, max_length=50),
    trigger: str | None = Query(default=None, max_length=50),
    query: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserRecord = Depends(get_current_user),
) -> ReportListResponse:
    if project_id is not None and flow_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Filtre por projeto ou por fluxo, não pelos dois ao mesmo tempo.",
        )

    async with AsyncSessionLocal() as session:
        projects, flows = await _owned_catalogs(session, current_user)
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

        predicates = [or_(*ownership)]
        normalized_status = (status or "").strip()
        normalized_trigger = (trigger or "").strip()
        normalized_query = (query or "").strip()
        if normalized_status:
            predicates.append(ReportRecord.status == normalized_status)
        if normalized_trigger:
            predicates.append(ReportRecord.trigger == normalized_trigger)
        if normalized_query:
            pattern = f"%{normalized_query}%"
            predicates.append(
                or_(
                    ReportRecord.summary.ilike(pattern),
                    ReportRecord.content.ilike(pattern),
                )
            )

        records = list(
            (
                await session.execute(
                    select(ReportRecord)
                    .where(*predicates)
                    .order_by(ReportRecord.generated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        total = int(
            await session.scalar(
                select(func.count(ReportRecord.id)).where(*predicates)
            )
            or 0
        )

    return ReportListResponse(
        total=total,
        limit=limit,
        offset=offset,
        reports=[
            _to_summary(record, _owner_metadata(record, projects, flows))
            for record in records
        ],
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    current_user: UserRecord = Depends(get_current_user),
) -> ReportDetailResponse:
    async with AsyncSessionLocal() as session:
        projects, flows = await _owned_catalogs(session, current_user)
        record = await session.scalar(
            select(ReportRecord)
            .where(ReportRecord.id == report_id)
            .options(selectinload(ReportRecord.publications))
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        if record.flow_id is not None and record.flow_id not in flows:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        if record.project_id is not None and record.project_id not in projects:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        if record.flow_id is None and record.project_id is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")

        owner = _owner_metadata(record, projects, flows)
        summary = _to_summary(record, owner)
        publications = [_to_publication(item) for item in record.publications]

    return ReportDetailResponse(
        **summary.model_dump(),
        content=record.content,
        publications=publications,
    )
