"""
ArkLog - Health Check Endpoints

Provides liveness (/health) and readiness (/health/detailed) probes
for container orchestration (Docker, Kubernetes, etc.).
"""

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


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — confirms the API process is alive."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=round(time.time() - _startup_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Readiness probe — checks all critical components are operational."""
    components: dict[str, str] = {}

    try:
        from app.models.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception as exc:
        components["database"] = f"unhealthy: {exc}"

    try:
        from app.config.projects import projects_config

        components["projects_config"] = f"healthy ({len(projects_config.projects)} projects)"
    except Exception as exc:
        components["projects_config"] = f"unhealthy: {exc}"

    overall = (
        "healthy"
        if all(v.startswith("healthy") for v in components.values())
        else "degraded"
    )

    return DetailedHealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.app_env,
        uptime_seconds=round(time.time() - _startup_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )
