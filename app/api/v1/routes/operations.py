"""Operational diagnostics and lifecycle controls for ArkLog flows."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.v1.deps import get_identity
from app.api.v1.routes.flows import (
    _flow_query,
    _normalized_config,
    _require_access,
    _serialize,
)
from app.core.config import settings
from app.integrations.catalog import provider_definition
from app.integrations.runtime import (
    IntegrationRuntimeError,
    list_connection_resources,
    validate_connection_resource,
)
from app.models.database import AsyncSessionLocal
from app.models.tables import (
    AutomationFlowRecord,
    IntegrationConnectionRecord,
    ReportUsageRecord,
)
from app.security.ark_auth import ArkIdentity
from app.utils.datetime_utils import naive_utcnow

router = APIRouter()


class FlowPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    report_style: Literal["executivo", "tecnico", "misto"] | None = None
    instructions: str | None = Field(default=None, max_length=4000)
    window_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    status: Literal["ACTIVE", "PAUSED"] | None = None


class FlowConfigurationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    source_connection_id: int
    destination_connection_id: int
    source_resource_id: str = Field(min_length=1, max_length=500)
    source_resource_label: str = Field(default="", max_length=500)
    source_resource_type: str = Field(default="", max_length=100)
    destination_resource_id: str = Field(min_length=1, max_length=500)
    destination_resource_label: str = Field(default="", max_length=500)
    destination_resource_type: str = Field(default="", max_length=100)
    report_style: Literal["executivo", "tecnico", "misto"] = "misto"
    instructions: str = Field(default="", max_length=4000)
    window_hours: int = Field(default=168, ge=1, le=24 * 365)


def _resource_check(
    role: str,
    provider: str,
    resource: dict[str, Any] | None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "provider": provider,
        "ready": error is None,
        "resourceId": str((resource or {}).get("id") or ""),
        "resourceLabel": str((resource or {}).get("label") or ""),
        "message": error or "Recurso acessível e pronto para uso.",
    }


def _connection_check(role: str, resources: list[dict[str, Any]]) -> dict[str, Any]:
    available = sum(1 for item in resources if item.get("available", True))
    unavailable = len(resources) - available
    return {
        "role": role,
        "ready": True,
        "resourceCount": len(resources),
        "availableCount": available,
        "unavailableCount": unavailable,
        "message": (
            f"{available} recurso(s) pronto(s)."
            if resources
            else "Conexão válida, mas nenhum recurso foi compartilhado com o ArkLog."
        ),
    }


def _resource_config(resource: dict[str, Any], fallback_type: str) -> dict[str, Any]:
    return {
        "resourceId": str(resource.get("id") or ""),
        "resourceLabel": str(resource.get("label") or resource.get("name") or ""),
        "resourceType": str(resource.get("type") or fallback_type or ""),
    }


def _clone_name(base_name: str, existing_names: set[str]) -> str:
    candidate = f"{base_name} · cópia"
    if candidate not in existing_names:
        return candidate
    suffix = 2
    while f"{candidate} {suffix}" in existing_names:
        suffix += 1
    return f"{candidate} {suffix}"


async def _owned_connection(
    connection_id: int,
    identity: ArkIdentity,
) -> IntegrationConnectionRecord:
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session:
        connection = await session.scalar(
            select(IntegrationConnectionRecord).where(
                IntegrationConnectionRecord.id == connection_id,
                IntegrationConnectionRecord.user_id == identity.user.id,
                IntegrationConnectionRecord.organization_id == organization_id,
            )
        )
    if connection is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return connection


async def _validated_endpoint(
    connection_id: int,
    resource_id: str,
    role: Literal["source", "destination"],
    identity: ArkIdentity,
) -> tuple[IntegrationConnectionRecord, dict[str, Any]]:
    connection = await _owned_connection(connection_id, identity)
    if connection.status != "ACTIVE":
        raise HTTPException(
            status_code=409,
            detail=f"Reconecte a conta usada como {role} antes de salvar o fluxo.",
        )
    definition = provider_definition(connection.provider)
    if not definition.supports(role):
        raise HTTPException(
            status_code=400,
            detail=f"{definition.name} não pode atuar como {role}.",
        )
    try:
        resource = await validate_connection_resource(connection, role, resource_id)
    except IntegrationRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return connection, resource


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: int,
    role: Literal["source", "destination"] | None = Query(default=None),
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    connection = await _owned_connection(connection_id, identity)
    if connection.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Reconecte esta conta antes de testá-la.")

    definition = provider_definition(connection.provider)
    roles = [role] if role else list(definition.capabilities)
    checks: list[dict[str, Any]] = []
    for current_role in roles:
        if current_role is None or not definition.supports(current_role):
            continue
        try:
            resources = await list_connection_resources(connection, current_role)
            checks.append(_connection_check(current_role, resources))
        except IntegrationRuntimeError as exc:
            checks.append(
                {
                    "role": current_role,
                    "ready": False,
                    "resourceCount": 0,
                    "availableCount": 0,
                    "unavailableCount": 0,
                    "message": str(exc),
                }
            )

    healthy = bool(checks) and all(item["ready"] for item in checks)
    return {
        "connectionId": connection.id,
        "provider": connection.provider,
        "healthy": healthy,
        "status": "healthy" if healthy else "attention",
        "checks": checks,
    }


@router.post("/flows/{flow_id}/preflight")
async def preflight_flow(
    flow_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    flow = await _flow_query(flow_id, identity)
    source_config = _normalized_config(
        flow.source_config, flow.source_connection.provider, "source"
    )
    destination_config = _normalized_config(
        flow.destination_config,
        flow.destination_connection.provider,
        "destination",
    )

    checks: list[dict[str, Any]] = []
    for role, connection, config in (
        ("source", flow.source_connection, source_config),
        ("destination", flow.destination_connection, destination_config),
    ):
        try:
            resource = await validate_connection_resource(
                connection,
                role,
                str(config.get("resourceId") or ""),
            )
            checks.append(_resource_check(role, connection.provider, resource))
        except IntegrationRuntimeError as exc:
            checks.append(
                _resource_check(role, connection.provider, None, str(exc))
            )

    ready = all(item["ready"] for item in checks)
    return {
        "flowId": flow.id,
        "ready": ready,
        "status": flow.status,
        "checks": checks,
        "message": (
            "As duas pontas estão prontas para executar."
            if ready
            else "Uma das pontas precisa de atenção antes da próxima execução."
        ),
    }


@router.patch("/flows/{flow_id}")
async def update_flow(
    flow_id: int,
    data: FlowPatch,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    if (
        data.window_hours is not None
        and identity.access.status == "TRIAL"
        and data.window_hours > settings.arklog_trial_max_window_hours
    ):
        raise HTTPException(
            status_code=400,
            detail="O teste gratuito cobre no máximo sete dias por relatório.",
        )

    async with AsyncSessionLocal() as session, session.begin():
        flow = await session.scalar(
            select(AutomationFlowRecord).where(
                AutomationFlowRecord.id == flow_id,
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
                AutomationFlowRecord.status != "ARCHIVED",
            )
        )
        if flow is None:
            raise HTTPException(status_code=404, detail="Fluxo não encontrado.")

        if data.name is not None:
            normalized_name = data.name.strip()
            collision = await session.scalar(
                select(AutomationFlowRecord.id).where(
                    AutomationFlowRecord.id != flow.id,
                    AutomationFlowRecord.user_id == identity.user.id,
                    AutomationFlowRecord.organization_id == organization_id,
                    AutomationFlowRecord.name == normalized_name,
                    AutomationFlowRecord.status != "ARCHIVED",
                )
            )
            if collision is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Já existe um fluxo com este nome.",
                )
            flow.name = normalized_name

        report_config = dict(flow.report_config or {})
        if data.report_style is not None:
            report_config["style"] = data.report_style
        if data.instructions is not None:
            report_config["instructions"] = data.instructions.strip()
        if data.window_hours is not None:
            report_config["windowHours"] = data.window_hours
        flow.report_config = report_config
        if data.status is not None:
            flow.status = data.status
        flow.updated_at = naive_utcnow()

    updated = await _flow_query(flow_id, identity)
    return {"flow": _serialize(updated)}


@router.put("/flows/{flow_id}/configuration")
async def replace_flow_configuration(
    flow_id: int,
    data: FlowConfigurationUpdate,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    """Validate both endpoints outside the transaction, then atomically replace the flow."""
    _require_access(identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    if (
        identity.access.status == "TRIAL"
        and data.window_hours > settings.arklog_trial_max_window_hours
    ):
        raise HTTPException(
            status_code=400,
            detail="O teste gratuito cobre no máximo sete dias por relatório.",
        )

    source, source_resource = await _validated_endpoint(
        data.source_connection_id,
        data.source_resource_id,
        "source",
        identity,
    )
    destination, destination_resource = await _validated_endpoint(
        data.destination_connection_id,
        data.destination_resource_id,
        "destination",
        identity,
    )
    source_config = _resource_config(source_resource, data.source_resource_type)
    destination_config = _resource_config(
        destination_resource,
        data.destination_resource_type,
    )
    normalized_name = data.name.strip()

    async with AsyncSessionLocal() as session, session.begin():
        flow = await session.scalar(
            select(AutomationFlowRecord)
            .where(
                AutomationFlowRecord.id == flow_id,
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
                AutomationFlowRecord.status != "ARCHIVED",
            )
            .with_for_update()
        )
        if flow is None:
            raise HTTPException(status_code=404, detail="Fluxo não encontrado.")
        collision = await session.scalar(
            select(AutomationFlowRecord.id).where(
                AutomationFlowRecord.id != flow.id,
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
                AutomationFlowRecord.name == normalized_name,
                AutomationFlowRecord.status != "ARCHIVED",
            )
        )
        if collision is not None:
            raise HTTPException(
                status_code=409,
                detail="Já existe um fluxo com este nome.",
            )

        flow.name = normalized_name
        flow.source_connection_id = source.id
        flow.destination_connection_id = destination.id
        flow.source_config = source_config
        flow.destination_config = destination_config
        flow.report_config = {
            "style": data.report_style,
            "instructions": data.instructions.strip(),
            "windowHours": data.window_hours,
        }
        flow.updated_at = naive_utcnow()

    updated = await _flow_query(flow_id, identity)
    return {"flow": _serialize(updated)}


@router.post("/flows/{flow_id}/clone")
async def clone_flow(
    flow_id: int,
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    """Duplicate a flow as PAUSED so the copy cannot execute accidentally."""
    _require_access(identity)
    original = await _flow_query(flow_id, identity)
    organization_id = str(identity.ark_session["organization"]["id"])
    async with AsyncSessionLocal() as session, session.begin():
        names_result = await session.execute(
            select(AutomationFlowRecord.name).where(
                AutomationFlowRecord.user_id == identity.user.id,
                AutomationFlowRecord.organization_id == organization_id,
                AutomationFlowRecord.status != "ARCHIVED",
            )
        )
        clone = AutomationFlowRecord(
            user_id=identity.user.id,
            organization_id=organization_id,
            name=_clone_name(original.name, set(names_result.scalars().all())),
            source_connection_id=original.source_connection_id,
            destination_connection_id=original.destination_connection_id,
            source_config=dict(original.source_config or {}),
            destination_config=dict(original.destination_config or {}),
            report_config=dict(original.report_config or {}),
            status="PAUSED",
        )
        session.add(clone)
        await session.flush()
        clone_id = clone.id

    created = await _flow_query(clone_id, identity)
    return {"flow": _serialize(created)}


@router.get("/flows/{flow_id}/runs")
async def list_flow_runs(
    flow_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    identity: ArkIdentity = Depends(get_identity),
) -> dict[str, Any]:
    _require_access(identity)
    await _flow_query(flow_id, identity)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ReportUsageRecord)
            .where(
                ReportUsageRecord.user_id == identity.user.id,
                ReportUsageRecord.flow_id == flow_id,
            )
            .order_by(ReportUsageRecord.created_at.desc())
            .limit(limit)
        )
        usages = result.scalars().all()

    return {
        "flowId": flow_id,
        "runs": [
            {
                "id": item.id,
                "status": item.status,
                "trigger": item.trigger,
                "reportId": item.report_id,
                "error": item.error_message,
                "createdAt": item.created_at.isoformat(),
                "completedAt": item.completed_at.isoformat()
                if item.completed_at
                else None,
            }
            for item in usages
        ],
    }
