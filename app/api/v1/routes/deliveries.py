"""Retry external report delivery without another AI generation or quota charge."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_identity
from app.api.v1.routes.flows import _normalized_config, _require_access
from app.integrations.runtime import (
    IntegrationRuntimeError,
    publish_destination,
    validate_connection_resource,
)
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    AutomationFlowRecord,
    ReportPublicationRecord,
    ReportRecord,
)
from app.security.ark_auth import ArkIdentity
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()
_RETRY_IN_PROGRESS_MINUTES = 5


def _delivery_idempotency_key(report_id: int, target_id: str) -> str:
    """Return a stable UUID so providers can deduplicate ambiguous retries."""
    return str(uuid5(NAMESPACE_URL, f"arklog:report:{report_id}:target:{target_id}"))


def _latest_publication(
    publications: list[ReportPublicationRecord],
) -> ReportPublicationRecord | None:
    return max(publications, key=lambda item: item.id or 0, default=None)


def _pending_is_fresh(publication: ReportPublicationRecord | None) -> bool:
    if publication is None or publication.status != "pending":
        return False
    started_at = publication.published_at
    if started_at is None:
        return False
    return started_at > naive_utcnow() - timedelta(minutes=_RETRY_IN_PROGRESS_MINUTES)


async def _load_owned_report(
    report_id: int,
    identity: ArkIdentity,
) -> ReportRecord:
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        report = await session.scalar(
            select(ReportRecord)
            .where(ReportRecord.id == report_id)
            .options(
                selectinload(ReportRecord.publications),
                selectinload(ReportRecord.flow).selectinload(
                    AutomationFlowRecord.destination_connection
                ),
            )
        )
    if report is None or report.flow is None:
        raise HTTPException(
            status_code=404,
            detail="Relatório de fluxo não encontrado.",
        )
    if (
        report.flow.user_id != identity.user.id
        or report.flow.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Relatório de fluxo não encontrado.",
        )
    if report.flow.status == "ARCHIVED":
        raise HTTPException(
            status_code=409,
            detail="Reative ou recrie o fluxo antes de republicar este relatório.",
        )
    return report


async def _create_retry_attempt(
    report: ReportRecord,
    target_id: str,
    platform: str,
) -> int:
    """Create a distinct audit row and prevent concurrent retry clicks."""
    async with AsyncSessionLocal() as session, session.begin():
        locked = await session.scalar(
            select(ReportRecord)
            .where(ReportRecord.id == report.id)
            .with_for_update()
            .options(selectinload(ReportRecord.publications))
        )
        if locked is None:
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        latest = _latest_publication(list(locked.publications))
        if locked.status == "published" or (latest and latest.status == "success"):
            raise HTTPException(
                status_code=409,
                detail="Este relatório já foi publicado com sucesso.",
            )
        if _pending_is_fresh(latest):
            raise HTTPException(
                status_code=409,
                detail="Já existe uma tentativa de publicação em andamento.",
            )
        attempt = ReportPublicationRecord(
            platform=platform,
            target_id=target_id,
            external_id=None,
            status="pending",
            error_message=None,
            published_at=naive_utcnow(),
            report_id=locked.id,
        )
        session.add(attempt)
        locked.status = "publication_pending"
        await session.flush()
        return attempt.id


async def _mark_success(
    report_id: int,
    publication_id: int,
    publication: dict[str, Any],
) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            update(ReportRecord)
            .where(ReportRecord.id == report_id)
            .values(status="published")
        )
        await session.execute(
            update(ReportPublicationRecord)
            .where(ReportPublicationRecord.id == publication_id)
            .values(
                status="success",
                platform=publication["provider"],
                target_id=publication["target_id"],
                external_id=publication["external_id"],
                error_message=None,
                published_at=naive_utcnow(),
            )
        )


async def _mark_failure(
    report_id: int,
    publication_id: int,
    error: str,
) -> None:
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            update(ReportRecord)
            .where(ReportRecord.id == report_id)
            .values(status="publication_failed")
        )
        await session.execute(
            update(ReportPublicationRecord)
            .where(ReportPublicationRecord.id == publication_id)
            .values(
                status="failed",
                error_message=error[:2000],
                published_at=naive_utcnow(),
            )
        )


@router.post("/reports/{report_id}/retry")
async def retry_report_delivery(
    report_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    """Republish saved content without calling the model or reserving quota."""
    _require_access(identity)
    report = await _load_owned_report(report_id, identity)
    flow = report.flow
    assert flow is not None
    connection = flow.destination_connection
    if connection.status != "ACTIVE":
        raise HTTPException(
            status_code=409,
            detail="Reconecte o destino antes de tentar publicar novamente.",
        )

    destination = _normalized_config(
        flow.destination_config,
        connection.provider,
        "destination",
    )
    target_id = str(destination.get("resourceId") or "").strip()
    try:
        await validate_connection_resource(
            connection,
            "destination",
            target_id,
        )
    except IntegrationRuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    publication_id = await _create_retry_attempt(
        report,
        target_id,
        connection.provider,
    )
    idempotency_key = _delivery_idempotency_key(report.id, target_id)
    try:
        publication = await publish_destination(
            connection,
            destination,
            report.content,
            title=flow.name,
            idempotency_key=idempotency_key,
        )
        await _mark_success(report.id, publication_id, publication)
    except IntegrationRuntimeError as exc:
        await _mark_failure(report.id, publication_id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        safe_error = "A republicação falhou. O relatório continua salvo e nenhuma cota foi consumida."
        await _mark_failure(report.id, publication_id, safe_error)
        raise HTTPException(status_code=502, detail=safe_error) from exc

    return {
        "status": "published",
        "reportId": report.id,
        "publicationId": publication_id,
        "publication": publication,
        "modelCalled": False,
        "quotaConsumed": False,
    }
