"""Authorization, atomic quota reservation and idempotency."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.models.database import AsyncSessionLocal
from app.models.tables import ArkLogAccessRecord, ReportUsageRecord
from app.security.ark_auth import ArkIdentity
from app.utils.datetime_utils import naive_utcnow

APPROVED_STATUSES = {"TRIAL", "ACTIVE"}


def public_access(access: ArkLogAccessRecord) -> dict:
    remaining = None if access.report_limit < 0 else max(access.report_limit - access.reports_used, 0)
    return {
        "status": access.status,
        "reportLimit": access.report_limit,
        "reportsUsed": access.reports_used,
        "remainingReports": remaining,
        "isAdmin": access.is_admin,
        "approvedAt": access.approved_at.isoformat() if access.approved_at else None,
        "blockedReason": access.blocked_reason,
    }


async def _find_usage(user_id: int, idempotency_key: str) -> ReportUsageRecord | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ReportUsageRecord).where(
                ReportUsageRecord.user_id == user_id,
                ReportUsageRecord.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()


async def reserve_report(
    identity: ArkIdentity,
    idempotency_key: str,
    trigger: str = "instant",
    *,
    project_id: int | None = None,
    flow_id: int | None = None,
) -> tuple[ReportUsageRecord, bool]:
    """Atomically reserve one report slot for exactly one project or flow."""
    if (project_id is None) == (flow_id is None):
        raise HTTPException(
            status_code=400,
            detail="A geração deve pertencer a exatamente um projeto ou fluxo.",
        )
    if len(idempotency_key) < 16 or len(idempotency_key) > 100:
        raise HTTPException(status_code=400, detail="Chave de idempotência inválida.")

    usage = ReportUsageRecord(
        id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        trigger=trigger,
        status="RESERVED",
        user_id=identity.user.id,
        project_id=project_id,
        flow_id=flow_id,
    )

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                existing_result = await session.execute(
                    select(ReportUsageRecord).where(
                        ReportUsageRecord.user_id == identity.user.id,
                        ReportUsageRecord.idempotency_key == idempotency_key,
                    )
                )
                existing = existing_result.scalar_one_or_none()
                if existing:
                    return existing, False

                updated = await session.execute(
                    update(ArkLogAccessRecord)
                    .where(
                        ArkLogAccessRecord.id == identity.access.id,
                        ArkLogAccessRecord.status.in_(APPROVED_STATUSES),
                        or_(
                            ArkLogAccessRecord.report_limit < 0,
                            ArkLogAccessRecord.reports_used < ArkLogAccessRecord.report_limit,
                        ),
                    )
                    .values(reports_used=ArkLogAccessRecord.reports_used + 1)
                    .returning(ArkLogAccessRecord.id)
                )
                if updated.scalar_one_or_none() is None:
                    if identity.access.status == "PENDING":
                        raise HTTPException(
                            status_code=403,
                            detail="Acesso ao ArkLog ainda não foi liberado.",
                        )
                    if identity.access.status == "BLOCKED":
                        raise HTTPException(status_code=403, detail="Acesso ao ArkLog bloqueado.")
                    raise HTTPException(
                        status_code=403,
                        detail="A cota de relatórios desta conta terminou.",
                    )

                session.add(usage)
                await session.flush()
            await session.refresh(usage)
            return usage, True
    except IntegrityError:
        existing = await _find_usage(identity.user.id, idempotency_key)
        if existing is not None:
            return existing, False
        raise


async def complete_usage(usage_id: str, report_id: int) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            update(ReportUsageRecord)
            .where(
                ReportUsageRecord.id == usage_id,
                ReportUsageRecord.status == "RESERVED",
            )
            .values(status="COMPLETED", report_id=report_id, completed_at=naive_utcnow())
        )


async def fail_usage(usage_id: str | None, error: str) -> None:
    """Mark a reservation failed and return its quota slot exactly once."""
    if not usage_id:
        return

    async with AsyncSessionLocal() as session, session.begin():
        failed = await session.execute(
            update(ReportUsageRecord)
            .where(
                ReportUsageRecord.id == usage_id,
                ReportUsageRecord.status == "RESERVED",
            )
            .values(status="FAILED", error_message=error[:2000], completed_at=naive_utcnow())
            .returning(ReportUsageRecord.user_id)
        )
        user_id = failed.scalar_one_or_none()
        if user_id is None:
            return

        await session.execute(
            update(ArkLogAccessRecord)
            .where(
                ArkLogAccessRecord.user_id == user_id,
                ArkLogAccessRecord.reports_used > 0,
            )
            .values(reports_used=ArkLogAccessRecord.reports_used - 1)
        )
