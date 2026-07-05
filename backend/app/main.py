from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging, get_logger
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import (
    assumptions,
    auth,
    copilot,
    dashboard,
    financials,
    goals,
    profile,
    reports,
    simulate,
)

configure_logging()
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Schema is owned exclusively by Alembic migrations (see backend/alembic/).
    # This used to also call create_tables() (Base.metadata.create_all) on
    # every boot, which only creates missing tables and never applies
    # ALTER TABLEs from later migrations — running both meant two sources of
    # truth for schema, and create_all() winning the race on a fresh database
    # would leave `alembic upgrade head` failing with "already exists".
    logger.info("startup environment=%s version=%s", settings.environment, settings.app_version)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Middleware order: outermost first (request ID → rate limit → CORS)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(goals.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(simulate.router, prefix=prefix)
    app.include_router(copilot.router, prefix=prefix)
    app.include_router(profile.router, prefix=prefix)
    app.include_router(financials.router, prefix=prefix)
    app.include_router(assumptions.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness + readiness probe — checks DB connectivity."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            logger.error("health_check_db_failed error=%s", exc)
            db_status = "error"

        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": settings.app_version,
            "db": db_status,
        }

    return app


app = create_app()
