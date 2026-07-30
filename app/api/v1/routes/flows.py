"""Provider-agnostic flow configuration and manual execution."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.ai.report_generator import ReportGenerator
from app.api.v1.deps import get_identity
from app.core.config import settings
from app.integrations.catalog import provider_definition
from app.integrations.runtime import (
    IntegrationRuntimeError,
    collect_source,
    publish_destination,
    validate_connection_resource,
)
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    AutomationFlowRecord,
    IntegrationConnectionRecord,
    ReportPublicationRecord,
    ReportRecord,
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
    source_resource_id: str = Field(default="", max_length=255)
    source_resource_label: str = Field(default="", max_length=500)
    source_resource_type: str = Field(default="", max_length=80)
    destination_resource_id: str = Field(default="", max_length=255)
    destination_resource_label: str = Field(default="", max_length=500)
    destination_resource_type: str = Field(default="", max_length=80)
    source_options: dict[str, Any] = Field(default_factory=dict)
    destination_options: dict[str, Any] = Field(default_factory=dict)
    # Backward-compatible fields for clients created before the generic flow builder.
    repository: str = Field(default="", max_length=255)
    channel: str = Field(default="", max_length=255)
    channel_label: str = Field(default="", max_length=255)
    report_style: Literal["executivo", "tecnico", "misto"] = "misto"
    instructions: str = Field(default="", max_length=4000)
    window_hours: int = Field(default=168, ge=1, le=24 * 365)


class FlowExecute(BaseModel):
    window_hours: int | None = Field(default=None, ge=1, le=24 * 365)


def _require_access(identity: ArkIdentity) -> None:
    if identity.access.status not in _ALLOWED:
        raise HTTPException(status_code=403, detail="Acesso ao ArkLog não autorizado.")


def _normalized_config(
    config: dict[str, Any], provider: str, role: str
) -> dict[str, Any]:
    resource_id = str(config.get("resourceId") or "").strip()
    resource_label = str(config.get("resourceLabel") or "").strip()
    resource_type = str(config.get("resourceType") or "").strip()
    options = config.get("options") if isinstance(config.get("options"), dict) else {}

    if not resource_id and provider == "github" and role == "source":
        resource_id = str(config.get("repository") or "").strip()
        resource_label = resource_label or resource_id
        resource_type = resource_type or "repository"
    if not resource_id and provider == "slack":
        resource_id = str(config.get("channel") or "").strip()
        resource_label = resource_label or str(config.get("channelLabel") or resource_id)
        resource_type = resource_type or "channel"

    return {
        "resourceId": resource_id,
        "resourceLabel": resource_label or resource_id,
        "resourceType": resource_type,
        "options": options,
    }


def _serialize(flow: AutomationFlowRecord) -> dict[str, Any]:
    source_config = _normalized_config(
        flow.source_config, flow.source_connection.provider, "source"
    )
    destination_config = _normalized_config(
        flow.destination_config, flow.destination_connection.provider, "destination"
    )
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
        "sourceConfig": source_config,
        "destinationConfig": destination_config,
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


async def _create_pending_report(
    *,
    flow: AutomationFlowRecord,
    content: str,
    summary: str,
    item_count: int,
) -> tuple[int, int]:
    """Persist the generated artifact before any external side effect."""
    destination = _normalized_config(
        flow.destination_config, flow.destination_connection.provider, "destination"
    )
    target_id = str(destination.get("resourceId") or "")
    async with AsyncSessionLocal() as session, session.begin():
        report = ReportRecord(
            trigger="manual_flow",
            status="publication_pending",
            content=content,
            summary=summary,
            commit_count=item_count,
            flow_id=flow.id,
            project_id=None,
        )
        session.add(report)
        await session.flush()
        publication = ReportPublicationRecord(
            platform=flow.destination_connection.provider,
            target_id=target_id,
            external_id=None,
            status="pending",
            report_id=report.id,
        )
        session.add(publication)
        await session.flush()
        return report.id, publication.id


async def _mark_publication_success(
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


async def _mark_publication_failed(
    report_id: int | None,
    publication_id: int | None,
    error: str,
) -> None:
    if report_id is None or publication_id is None:
        return
    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            update(ReportRecord)
            .where(ReportRecord.id == report_id)
            .values(status="publication_failed")
        )
        await session.execute(
            update(ReportPublicationRecord)
            .where(ReportPublicationRecord.id == publication_id)
            .values(status="failed", error_message=error[:2000])
        )


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
    source_resource_id = (data.source_resource_id or data.repository).strip()
    destination_resource_id = (data.destination_resource_id or data.channel).strip()
    if not source_resource_id or not destination_resource_id:
        raise HTTPException(
            status_code=400,
            detail="Escolha um recurso para a fonte e outro para o destino.",
        )
    if (
        identity.access.status == "TRIAL"
        and data.window_hours > settings.arklog_trial_max_window_hours
    ):
        raise HTTPException(
            status_code=400,
            detail="O teste gratuito cobre no máximo sete dias por relatório.",
        )

    try:
        async with AsyncSessionLocal() as session:
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
            connections = {
                item.id: item for item in connections_result.scalars().all()
            }
            source = connections.get(data.source_connection_id)
            destination = connections.get(data.destination_connection_id)
            if source is None or destination is None:
                raise HTTPException(
                    status_code=400,
                    detail="As duas conexões precisam pertencer à sua conta Ark.",
                )
            if not provider_definition(source.provider).supports("source"):
                raise HTTPException(
                    status_code=400,
                    detail=f"{provider_definition(source.provider).name} não pode ser usado como fonte.",
                )
            if not provider_definition(destination.provider).supports("destination"):
                raise HTTPException(
                    status_code=400,
                    detail=f"{provider_definition(destination.provider).name} não pode ser usado como destino.",
                )

            source_resource = await validate_connection_resource(
                source, "source", source_resource_id
            )
            destination_resource = await validate_connection_resource(
                destination, "destination", destination_resource_id
            )

            async with session.begin():
                collision = await session.scalar(
                    select(AutomationFlowRecord).where(
                        AutomationFlowRecord.user_id == identity.user.id,
                        AutomationFlowRecord.name == data.name.strip(),
                        AutomationFlowRecord.status != "ARCHIVED",
                    )
                )
                if collision is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="Já existe um fluxo com este nome.",
                    )

                flow = AutomationFlowRecord(
                    user_id=identity.user.id,
                    organization_id=organization_id,
                    name=data.name.strip(),
                    source_connection_id=source.id,
                    destination_connection_id=destination.id,
                    source_config={
                        "resourceId": str(source_resource["id"]),
                        "resourceLabel": str(
                            source_resource.get("label")
                            or data.source_resource_label
                            or source_resource["id"]
                        ),
                        "resourceType": str(
                            source_resource.get("type")
                            or data.source_resource_type
                            or "resource"
                        ),
                        "options": data.source_options,
                    },
                    destination_config={
                        "resourceId": str(destination_resource["id"]),
                        "resourceLabel": str(
                            destination_resource.get("label")
                            or data.destination_resource_label
                            or data.channel_label
                            or destination_resource["id"]
                        ),
                        "resourceType": str(
                            destination_resource.get("type")
                            or data.destination_resource_type
                            or "resource"
                        ),
                        "options": data.destination_options,
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
    except IntegrationRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    if (
        identity.access.status == "TRIAL"
        and window_hours > settings.arklog_trial_max_window_hours
    ):
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
    report_id: int | None = None
    publication_id: int | None = None
    publication: dict[str, Any] | None = None
    try:
        source_config = _normalized_config(
            flow.source_config, flow.source_connection.provider, "source"
        )
        destination_config = _normalized_config(
            flow.destination_config,
            flow.destination_connection.provider,
            "destination",
        )
        await validate_connection_resource(
            flow.source_connection, "source", str(source_config["resourceId"])
        )
        await validate_connection_resource(
            flow.destination_connection,
            "destination",
            str(destination_config["resourceId"]),
        )
        activity = await collect_source(
            flow.source_connection,
            source_config,
            since=since,
            trial_limits=identity.access.status == "TRIAL",
        )
        instructions = str(flow.report_config.get("instructions") or "")
        event_count = int(
            activity.get("raw_item_count")
            or len(activity.get("normalized_events", []))
        )
        payload = {
            "project_name": flow.name,
            "description": (
                f"Fluxo ArkLog: {flow.source_connection.provider} → "
                f"{flow.destination_connection.provider}."
            ),
            "tech_stack": [],
            "business_context": instructions,
            "report_style": flow.report_config.get("style", "misto"),
            "trigger": "manual_flow",
            "access_status": identity.access.status,
            **activity,
            "commit_count": event_count,
        }
        content, summary = await ReportGenerator().generate(payload)
        report_id, publication_id = await _create_pending_report(
            flow=flow,
            content=content,
            summary=summary,
            item_count=event_count,
        )
        publication = await publish_destination(
            flow.destination_connection,
            destination_config,
            content,
            title=flow.name,
            idempotency_key=usage.id,
        )
        await _mark_publication_success(
            report_id,
            publication_id,
            publication,
        )
        await complete_usage(usage.id, report_id)
    except IntegrationRuntimeError as exc:
        await _mark_publication_failed(report_id, publication_id, str(exc))
        await fail_usage(usage.id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        await _mark_publication_failed(report_id, publication_id, str(exc))
        await fail_usage(usage.id, str(exc))
        raise HTTPException(
            status_code=502,
            detail="O fluxo falhou sem consumir sua cota. Tente novamente.",
        ) from exc

    assert report_id is not None
    assert publication is not None
    return {
        "status": "completed",
        "usageId": usage.id,
        "reportId": report_id,
        "publication": publication,
        "idempotentReplay": False,
    }
