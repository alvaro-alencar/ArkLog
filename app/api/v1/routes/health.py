"""Safe liveness and readiness checks for ArkLog."""

import time
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()
_startup_time = time.time()
_CRITICAL_COMPONENTS = ("ark_auth", "openrouter", "credential_vault", "database")


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: str


class DetailedHealthResponse(HealthResponse):
    components: dict[str, str]


def _base(status: str) -> dict[str, object]:
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": round(time.time() - _startup_time, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _configured_components() -> dict[str, str]:
    """Describe configuration by state only, never by secret value."""
    return {
        "ark_auth": "configured"
        if settings.ark_auth_me_url.startswith("https://")
        else "missing",
        "openrouter": "configured" if bool(settings.ai_api_key) else "missing",
        "credential_vault": (
            "configured"
            if len(settings.connections_encryption_key.strip()) >= 32
            and len(settings.oauth_state_secret.strip()) >= 32
            else "missing"
        ),
        "github_app": "configured" if settings.github_app_configured else "pending",
        "slack_oauth": "configured" if settings.slack_oauth_configured else "pending",
        "notion_oauth": "configured" if settings.notion_oauth_configured else "pending",
        "clickup_oauth": "configured" if settings.clickup_oauth_configured else "pending",
        "trello_oauth": "configured" if settings.trello_oauth_configured else "pending",
    }


async def _readiness_snapshot() -> tuple[str, dict[str, str]]:
    components = _configured_components()
    try:
        from app.models.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception:
        logger.exception("health_database_check_failed")
        components["database"] = "unhealthy"

    overall = (
        "healthy"
        if all(components[name] in {"configured", "healthy"} for name in _CRITICAL_COMPONENTS)
        else "degraded"
    )
    return overall, components


def _readiness_payload(status: str, components: dict[str, str]) -> dict[str, Any]:
    configured_providers = [
        name.removesuffix("_oauth").removesuffix("_app")
        for name, state in components.items()
        if name not in _CRITICAL_COMPONENTS
        and name != "database"
        and state == "configured"
    ]
    pending_providers = [
        name.removesuffix("_oauth").removesuffix("_app")
        for name, state in components.items()
        if name not in _CRITICAL_COMPONENTS
        and name != "database"
        and state == "pending"
    ]
    return {
        **_base(status),
        "ready": status == "healthy",
        "components": components,
        "providers": {
            "configured": configured_providers,
            "pending": pending_providers,
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe that does not inspect or reveal secrets."""
    return HealthResponse(**_base("healthy"))


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Human-readable diagnostic with names and states only."""
    overall, components = await _readiness_snapshot()
    return DetailedHealthResponse(**_base(overall), components=components)


@router.get("/health/ready", response_class=JSONResponse)
async def readiness_check() -> JSONResponse:
    """Machine readiness probe: HTTP 200 when operable, HTTP 503 otherwise."""
    overall, components = await _readiness_snapshot()
    payload = _readiness_payload(overall, components)
    return JSONResponse(
        status_code=200 if payload["ready"] else 503,
        content=payload,
    )
