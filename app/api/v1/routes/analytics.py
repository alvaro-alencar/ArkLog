"""Administrative analytics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import require_admin
from app.config.projects import projects_config
from app.schemas.analytics import AnalyticsSummaryResponse, HealthScore, ProjectStats
from app.security.ark_auth import ArkIdentity
from app.services.analytics_service import AnalyticsService

router = APIRouter()
_analytics = AnalyticsService()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    _: ArkIdentity = Depends(require_admin),
) -> AnalyticsSummaryResponse:
    return await _analytics.get_summary()


@router.get("/projects/{name}/stats", response_model=ProjectStats)
async def project_stats(
    name: str,
    _: ArkIdentity = Depends(require_admin),
) -> ProjectStats:
    if not projects_config.get_by_name(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{name}' not found",
        )
    result = await _analytics.get_project_stats(name)
    if not result:
        raise HTTPException(status_code=404, detail="No data yet for this project")
    return result


@router.get("/projects/{name}/health", response_model=HealthScore)
async def project_health(
    name: str,
    _: ArkIdentity = Depends(require_admin),
) -> HealthScore:
    if not projects_config.get_by_name(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{name}' not found",
        )
    result = await _analytics.get_health_score(name)
    if not result:
        raise HTTPException(status_code=404, detail="No data yet for this project")
    return result
