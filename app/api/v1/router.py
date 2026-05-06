"""ArkLog - API v1 Router. Aggregates all v1 route modules."""

from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.webhooks import router as webhooks_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
