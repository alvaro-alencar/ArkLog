"""
ArkLog - Analytics Endpoints

GET /analytics/summary                     — cross-project overview
GET /analytics/projects/{name}/stats       — project commit/report statistics
GET /analytics/projects/{name}/health      — computed health score (0–100)
"""

from fastapi import APIRouter, HTTPException, status

from app.config.projects import projects_config
from app.schemas.analytics import AnalyticsSummaryResponse, HealthScore, ProjectStats
from app.services.analytics_service import AnalyticsService

router = APIRouter()
_analytics = AnalyticsService()


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary() -> AnalyticsSummaryResponse:
    """Aggregated view across all configured projects."""
    return await _analytics.get_summary()


@router.get("/analytics/projects/{name}/stats", response_model=ProjectStats)
async def project_stats(name: str) -> ProjectStats:
    """Commit frequency, report counts, and activity recency for a project."""
    if not projects_config.get_by_name(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    stats = await _analytics.get_project_stats(name)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data yet for this project")
    return stats


@router.get("/analytics/projects/{name}/health", response_model=HealthScore)
async def project_health(name: str) -> HealthScore:
    """
    Computed health score (0–100) with grade and breakdown by factor.

    Factors:
      activity  (40pts) — recent commit frequency
      coverage  (30pts) — reports published to ClickUp vs generated
      recency   (30pts) — days since last commit
    """
    if not projects_config.get_by_name(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{name}' not found")

    health = await _analytics.get_health_score(name)
    if not health:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data yet for this project")
    return health
