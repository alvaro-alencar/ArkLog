"""ArkLog - API v1 Router. Aggregates all v1 route modules."""

from fastapi import APIRouter

from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.github import router as github_router
from app.api.v1.routes.clickup import router as clickup_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.webhooks import router as webhooks_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(github_router, prefix="/github", tags=["github"])
router.include_router(clickup_router, prefix="/clickup", tags=["clickup"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(reports_router, prefix="/reports", tags=["reports"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
