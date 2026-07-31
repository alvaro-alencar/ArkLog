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
