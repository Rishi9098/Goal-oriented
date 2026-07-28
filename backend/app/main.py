from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal, engine
from app.logging_config import configure_logging, get_logger
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import (
    assumptions,
    auth,
    copilot,
    dashboard,
    family,
    financials,
    goals,
    life_events,
    notifications,
    profile,
    reports,
    simulate,
)
from app.services import life_event_service
from app.services.birth_of_child_handler import BirthOfChildHandler
from app.services.bonus_handler import BonusHandler
from app.services.business_sale_handler import BusinessSaleHandler
from app.services.business_start_handler import BusinessStartHandler
from app.services.dependent_parent_handler import DependentParentHandler
from app.services.divorce_handler import DivorceHandler
from app.services.education_planning_handler import EducationPlanningHandler
from app.services.home_sale_handler import HomeSaleHandler
from app.services.house_purchase_handler import HousePurchaseHandler
from app.services.inheritance_handler import InheritanceHandler
from app.services.job_change_handler import JobChangeHandler
from app.services.loan_payoff_handler import LoanPayoffHandler
from app.services.major_medical_event_handler import MajorMedicalEventHandler
from app.services.marriage_handler import MarriageHandler
from app.services.new_loan_handler import NewLoanHandler
from app.services.retirement_handler import RetirementHandler
from app.services.salary_raise_handler import SalaryRaiseHandler

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
    await engine.dispose()


def _register_life_event_handlers() -> None:
    """Wires the Life Event Engine's concrete handlers into the generic
    registry built in Phase A. Idempotent to call more than once
    (register_handler is a plain dict assignment)."""
    life_event_service.register_handler("loan_payoff", LoanPayoffHandler())
    life_event_service.register_handler("salary_raise", SalaryRaiseHandler())
    life_event_service.register_handler("job_change", JobChangeHandler())
    life_event_service.register_handler("bonus", BonusHandler())
    life_event_service.register_handler("new_loan", NewLoanHandler())
    life_event_service.register_handler("house_purchase", HousePurchaseHandler())
    life_event_service.register_handler("home_sale", HomeSaleHandler())
    life_event_service.register_handler("marriage", MarriageHandler())
    life_event_service.register_handler("birth_of_child", BirthOfChildHandler())
    # Adoption is "identical to Birth of Child in every respect" per
    # LifeEventEngineArchitecture.md §5.6 — same handler class, registered
    # under a second event_type key, not a duplicate handler file.
    life_event_service.register_handler("adoption", BirthOfChildHandler())
    life_event_service.register_handler("divorce", DivorceHandler())
    life_event_service.register_handler("dependent_parent", DependentParentHandler())
    life_event_service.register_handler("retirement", RetirementHandler())
    life_event_service.register_handler("education_planning", EducationPlanningHandler())
    life_event_service.register_handler("inheritance", InheritanceHandler())
    life_event_service.register_handler("major_medical_event", MajorMedicalEventHandler())
    life_event_service.register_handler("business_start", BusinessStartHandler())
    life_event_service.register_handler("business_sale", BusinessSaleHandler())


def create_app() -> FastAPI:
    _register_life_event_handlers()

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
    app.include_router(family.router, prefix=prefix)
    app.include_router(notifications.router, prefix=prefix)
    app.include_router(life_events.router, prefix=prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        """Root status probe for load balancers and platform monitors."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "ok",
        }

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
