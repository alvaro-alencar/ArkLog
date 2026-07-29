"""ArkLog FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.events import on_shutdown, on_startup
from app.core.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await on_startup()
    logger.info(
        "arklog_started",
        version=settings.app_version,
        env=settings.app_env,
        port=settings.api_port,
    )
    yield
    await on_shutdown()
    logger.info("arklog_stopped")


def create_application() -> FastAPI:
    application = FastAPI(
        title="ArkLog",
        description="Provider-agnostic AI reporting flows with user-owned connections.",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(v1_router, prefix=settings.api_prefix)
    if settings.public_api_prefix != settings.api_prefix:
        application.include_router(v1_router, prefix=settings.public_api_prefix)

    @application.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            {"name": "ArkLog", "version": settings.app_version, "status": "operational"}
        )

    return application


app = create_application()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_config=None,
    )


if __name__ == "__main__":
    main()
