"""Safe liveness and readiness checks for ArkLog."""

import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()
_startup_time = time.time()


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


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe that does not inspect or reveal secrets."""
    return HealthResponse(**_base("healthy"))


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Readiness probe with names and states only, never raw exception details."""
    components: dict[str, str] = {
        "ark_auth": "configured" if settings.ark_auth_me_url.startswith("https://") else "missing",
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

    try:
        from app.models.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception:
        logger.exception("health_database_check_failed")
        components["database"] = "unhealthy"

    critical = ("ark_auth", "openrouter", "credential_vault", "database")
    overall = (
        "healthy"
        if all(components[name] in {"configured", "healthy"} for name in critical)
        else "degraded"
    )
    return DetailedHealthResponse(**_base(overall), components=components)
