"""Provider-agnostic flow configuration and manual execution."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.report_generator import ReportGenerator
from app.api.v1.deps import get_identity
from app.core.config import settings
from app.integrations.runtime import (
    IntegrationRuntimeError,
    collect_source,
    publish_destination,
)
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    AutomationFlowRecord,
    IntegrationConnectionRecord,
    ReportPublicationRecord,
    ReportRecord,
    ReportUsageRecord,
)
from app.security.access import complete_usage, fail_usage, reserve_report
from app.security.ark_auth import ArkIdentity
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()
_ALLOWED = {"TRIAL", "ACTIVE"}


class FlowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    source_connection_id: int
    destination_connection_id: int
    repository: str = Field(min_length=3, max_length=255)
    channel: str = Field(min_length=1, max_length=255)
    channel_label: str = Field(default="", max_length=255)
    report_style: Literal["executivo", "tecnico", "misto"] = "misto"
    instructions: str = Field(default="", max_length=4000)
    window_hours: int = Field(default=168, ge=1, le=24 * 365)


class FlowExecute(BaseModel):
    window_hours: int | None = Field(default=None, ge=1, le=24 * 365)


def _require_access(identity: ArkIdentity) -> None:
    if identity.access.status not in _ALLOWED:
        raise HTTPException(status_code=403, detail="Acesso ao ArkLog não autorizado.")


def _serialize(flow: AutomationFlowRecord) -> dict[str, Any]:
    return {
        "id": flow.id,
        "name": flow.name,
        "status": flow.status,
        "sourceConnectionId": flow.source_connection_id,
        "destinationConnectionId": flow.destination_connection_id,
        "sourceProvider": flow.source_connection.provider,
        "sourceLabel": flow.source_connection.label,
        "destinationProvider": flow.destination_connection.provider,
        "destinationLabel": flow.destination_connection.label,
        "sourceConfig": flow.source_config,
        "destinationConfig": flow.destination_config,
        "reportConfig": flow.report_config,
        "createdAt": flow.created_at.isoformat(),
        "updatedAt": flow.updated_at.isoformat(),
    }


async def _flow_query(flow_id: int, identity: ArkIdentity) -> AutomationFlowRecord:
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        flow = await session.scalar(
            select(AutomationFlowRecord)
            .where(
                AutomationFlowRecord.id == flow_id,
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
            )
            .options(
                selectinload(AutomationFlowRecord.source_connection),
                selectinload(AutomationFlowRecord.destination_connection),
            )
        )
    if flow is None:
        raise HTTPException(status_code=404, detail="Fluxo não encontrado.")
    return flow


@router.get("")
async def list_flows(identity: ArkIdentity = Depends(get_identity)) -> dict[str, Any]:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AutomationFlowRecord)
            .where(
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
                AutomationFlowRecord.status != "ARCHIVED",
            )
            .options(
                selectinload(AutomationFlowRecord.source_connection),
                selectinload(AutomationFlowRecord.destination_connection),
            )
            .order_by(AutomationFlowRecord.created_at.desc())
        )
        flows = result.scalars().all()
    return {"flows": [_serialize(flow) for flow in flows]}


@router.post("")
async def create_flow(
    data: FlowCreate,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    repository = data.repository.strip()
    if repository.count("/") != 1:
        raise HTTPException(status_code=400, detail="Escolha um repositório GitHub válido.")
    if identity.access.status == "TRIAL" and data.window_hours > settings.arklog_trial_max_window_hours:
        raise HTTPException(
            status_code=400,
            detail="O teste gratuito cobre no máximo sete dias por relatório.",
        )

    async with AsyncSessionLocal() as session:
        async with session.begin():
            connections_result = await session.execute(
                select(IntegrationConnectionRecord).where(
                    IntegrationConnectionRecord.id.in_(
                        [data.source_connection_id, data.destination_connection_id]
                    ),
                    IntegrationConnectionRecord.user_id == identity.user.id,
                    IntegrationConnectionRecord.organization_id == organization_id,
                    IntegrationConnectionRecord.status == "ACTIVE",
                )
            )
            connections = {item.id: item for item in connections_result.scalars().all()}
            source = connections.get(data.source_connection_id)
            destination = connections.get(data.destination_connection_id)
            if source is None or destination is None:
                raise HTTPException(
                    status_code=400,
                    detail="As duas conexões precisam pertencer à sua conta Ark.",
                )
            if source.provider != "github":
                raise HTTPException(status_code=400, detail="A primeira fonte disponível é o GitHub.")
            if destination.provider != "slack":
                raise HTTPException(status_code=400, detail="O primeiro destino disponível é o Slack.")

            collision = await session.scalar(
                select(AutomationFlowRecord).where(
                    AutomationFlowRecord.user_id == identity.user.id,
                    AutomationFlowRecord.name == data.name.strip(),
                    AutomationFlowRecord.status != "ARCHIVED",
                )
            )
            if collision is not None:
                raise HTTPException(status_code=409, detail="Já existe um fluxo com este nome.")

            flow = AutomationFlowRecord(
                user_id=identity.user.id,
                organization_id=organization_id,
                name=data.name.strip(),
                source_connection_id=source.id,
                destination_connection_id=destination.id,
                source_config={"repository": repository},
                destination_config={
                    "channel": data.channel.strip(),
                    "channelLabel": data.channel_label.strip(),
                },
                report_config={
                    "style": data.report_style,
                    "instructions": data.instructions.strip(),
                    "windowHours": data.window_hours,
                },
                status="ACTIVE",
            )
            session.add(flow)
            await session.flush()
            flow_id = flow.id

        flow = await session.scalar(
            select(AutomationFlowRecord)
            .where(AutomationFlowRecord.id == flow_id)
            .options(
                selectinload(AutomationFlowRecord.source_connection),
                selectinload(AutomationFlowRecord.destination_connection),
            )
        )
    assert flow is not None
    return {"flow": _serialize(flow)}


@router.get("/{flow_id}")
async def get_flow(
    flow_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    return {"flow": _serialize(await _flow_query(flow_id, identity))}


@router.delete("/{flow_id}")
async def archive_flow(
    flow_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, str]:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session, session.begin():
        flow = await session.scalar(
            select(AutomationFlowRecord).where(
                AutomationFlowRecord.id == flow_id,
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
            )
        )
        if flow is None:
            raise HTTPException(status_code=404, detail="Fluxo não encontrado.")
        flow.status = "ARCHIVED"
        flow.updated_at = naive_utcnow()
    return {"status": "archived"}


@router.post("/{flow_id}/execute")
async def execute_flow(
    flow_id: int,
    data: FlowExecute,
    identity: ArkIdentity = Depends(get_identity),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_access(identity)
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key é obrigatório.")
    flow = await _flow_query(flow_id, identity)
    if flow.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Este fluxo não está ativo.")

    configured_window = int(flow.report_config.get("windowHours") or 168)
    window_hours = data.window_hours or configured_window
    if identity.access.status == "TRIAL" and window_hours > settings.arklog_trial_max_window_hours:
        raise HTTPException(
            status_code=400,
            detail="O teste gratuito cobre no máximo sete dias por relatório.",
        )

    usage, is_new = await reserve_report(
        identity,
        idempotency_key,
        trigger="manual_flow",
        flow_id=flow.id,
    )
    if not is_new:
        return {
            "status": usage.status.lower(),
            "usageId": usage.id,
            "reportId": usage.report_id,
            "idempotentReplay": True,
        }

    since = naive_utcnow() - timedelta(hours=window_hours)
    try:
        activity = await collect_source(
            flow.source_connection,
            flow.source_config,
            since=since,
            trial_limits=identity.access.status == "TRIAL",
        )
        repository = str(flow.source_config.get("repository") or "")
        instructions = str(flow.report_config.get("instructions") or "")
        payload = {
            "project_name": flow.name,
            "description": f"Fluxo ArkLog alimentado por {repository}.",
            "tech_stack": [],
            "business_context": instructions,
            "report_style": flow.report_config.get("style", "misto"),
            "trigger": "instant",
            "access_status": identity.access.status,
            **activity,
            "commit_count": len(activity.get("commits", [])),
        }
        content, summary = await ReportGenerator().generate(payload)
        publication = await publish_destination(
            flow.destination_connection,
            flow.destination_config,
            content,
        )

        async with AsyncSessionLocal() as session:
            async with session.begin():
                report = ReportRecord(
                    trigger="manual_flow",
                    status="generated",
                    content=content,
                    summary=summary,
                    commit_count=len(activity.get("commits", [])),
                    flow_id=flow.id,
                    project_id=None,
                )
                session.add(report)
                await session.flush()
                session.add(
                    ReportPublicationRecord(
                        platform=publication["provider"],
                        target_id=publication["target_id"],
                        external_id=publication["external_id"],
                        status="success",
                        report_id=report.id,
                    )
                )
                report_id = report.id
        await complete_usage(usage.id, report_id)
    except IntegrationRuntimeError as exc:
        await fail_usage(usage.id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        await fail_usage(usage.id, str(exc))
        raise HTTPException(
            status_code=502,
            detail="O fluxo falhou sem consumir sua cota. Tente novamente.",
        ) from exc

    async with AsyncSessionLocal() as session:
        final_usage = await session.scalar(
            select(ReportUsageRecord).where(ReportUsageRecord.id == usage.id)
        )
    return {
        "status": "completed",
        "usageId": usage.id,
        "reportId": report_id,
        "publication": publication,
        "reportsUsed": final_usage.status if final_usage else "COMPLETED",
        "idempotentReplay": False,
    }
