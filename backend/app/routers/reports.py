from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.schemas.reports import GoalReportItem, ReportSummaryResponse
from app.services.planning_service import get_dashboard

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=ReportSummaryResponse)
async def report_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSummaryResponse:
    # `get_dashboard` is read-only (ADR-001): it aggregates financials and reads
    # each goal's already-persisted probability, never recomputes it. The SELECT
    # below reads the same identity-mapped Goal objects, so both always agree.
    dashboard = await get_dashboard(db, current_user)

    result = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
    )
    active_goals = list(result.scalars().all())

    return ReportSummaryResponse(
        generated_at=datetime.now(UTC),
        plan_health_score=dashboard.plan_health_score,
        net_worth=dashboard.net_worth,
        liquid_assets=dashboard.liquid_assets,
        invested=dashboard.invested,
        liabilities=dashboard.liabilities,
        monthly_income=dashboard.monthly_income,
        monthly_expenses=dashboard.monthly_expenses,
        monthly_savings_rate=dashboard.monthly_savings_rate,
        goal_count=dashboard.goal_count,
        goals_on_track=dashboard.goals_on_track,
        goals=[
            GoalReportItem(
                id=g.id,
                name=g.name,
                category=g.category,
                target_amount=g.target_amount,
                current_amount=g.current_amount,
                monthly_contribution=g.monthly_contribution,
                probability=g.probability,
                on_track=g.on_track,
                target_date=g.target_date,
            )
            for g in active_goals
        ],
    )
