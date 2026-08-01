"""Human review endpoints for Ark Memory Protocol v1."""

from collections import defaultdict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select

from app.api.v1.deps import get_current_user
from app.models.database import AsyncSessionLocal
from app.models.memory import ReportReviewRecord
from app.models.tables import AutomationFlowRecord, ProjectRecord, ReportRecord, UserRecord
from app.schemas.memory import (
    MemoryProfileResponse,
    MemoryRule,
    ReportReviewRequest,
    ReportReviewResponse,
)
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()


async def _owned_report(session: object, report_id: int, user_id: int) -> ReportRecord | None:
    project_ids = select(ProjectRecord.id).where(ProjectRecord.user_id == user_id)
    flow_ids = select(AutomationFlowRecord.id).where(AutomationFlowRecord.user_id == user_id)
    return await session.scalar(
        select(ReportRecord).where(
            ReportRecord.id == report_id,
            or_(
                ReportRecord.project_id.in_(project_ids),
                ReportRecord.flow_id.in_(flow_ids),
            ),
        )
    )


def _response(record: ReportReviewRecord) -> ReportReviewResponse:
    return ReportReviewResponse(
        event_id=record.event_id,
        occurred_at=record.occurred_at,
        report_id=record.report_id,
        verdict=record.verdict,
        original_content=record.original_content,
        approved_content=record.approved_content,
        reason=record.reason,
        labels=list(record.labels or []),
    )


@router.post("/reports/{report_id}/reviews", response_model=ReportReviewResponse, status_code=201)
async def review_report(
    report_id: int,
    payload: ReportReviewRequest,
    current_user: UserRecord = Depends(get_current_user),
) -> ReportReviewResponse:
    async with AsyncSessionLocal() as session:
        report = await _owned_report(session, report_id, current_user.id)
        if report is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")

        approved_content = payload.approved_content
        if payload.verdict == "approved":
            approved_content = report.content

        record = ReportReviewRecord(
            event_id=str(uuid4()),
            verdict=payload.verdict,
            original_content=report.content,
            approved_content=approved_content,
            reason=payload.reason.strip(),
            labels=sorted({item.strip().lower() for item in payload.labels if item.strip()}),
            occurred_at=naive_utcnow(),
            report_id=report.id,
            user_id=current_user.id,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return _response(record)


@router.get("/memory/profile", response_model=MemoryProfileResponse)
async def get_memory_profile(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserRecord = Depends(get_current_user),
) -> MemoryProfileResponse:
    async with AsyncSessionLocal() as session:
        reviews = list(
            (
                await session.execute(
                    select(ReportReviewRecord)
                    .where(ReportReviewRecord.user_id == current_user.id)
                    .order_by(ReportReviewRecord.occurred_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    counts = defaultdict(int)
    label_evidence: dict[str, list[ReportReviewRecord]] = defaultdict(list)
    for review in reviews:
        counts[review.verdict] += 1
        for label in review.labels or []:
            label_evidence[label].append(review)

    rules = [
        MemoryRule(
            key=f"label:{label}",
            statement=f"Aplicar a preferência marcada como '{label}' ao gerar novos relatórios.",
            evidence_count=len(items),
            last_seen_at=max(item.occurred_at for item in items),
        )
        for label, items in sorted(
            label_evidence.items(), key=lambda pair: (-len(pair[1]), pair[0])
        )
    ]

    return MemoryProfileResponse(
        user_id=current_user.id,
        review_count=len(reviews),
        approved_count=counts["approved"],
        edited_count=counts["edited"],
        rejected_count=counts["rejected"],
        rules=rules,
        examples=[_response(item) for item in reviews[:10]],
    )
