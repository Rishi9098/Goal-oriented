import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

GoalCategory = Literal["retirement", "education", "home", "travel", "wealth", "emergency"]
RiskProfile = Literal["conservative", "balanced", "aggressive"]



# Upper bounds keep user-supplied amounts within a plausible financial-planning
# range and out of the territory where the Monte Carlo engine's compounding
# loop (backend/app/services/monte_carlo.py) can produce inf/NaN terminal
# values (AUDIT.md #10). None of these are meant to be tight — they're a
# backstop against typos and abuse, not a real constraint on legitimate use.
_MAX_AMOUNT = 1_000_000_000.0
_MAX_MONTHLY_AMOUNT = 10_000_000.0


class GoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: GoalCategory
    target_amount: float = Field(gt=0, le=_MAX_AMOUNT)
    current_amount: float = Field(ge=0, le=_MAX_AMOUNT, default=0.0)
    target_date: date
    monthly_contribution: float = Field(ge=0, le=_MAX_MONTHLY_AMOUNT, default=0.0)
    risk_profile: RiskProfile = "balanced"
    priority: int = Field(ge=1, le=10, default=1)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: GoalCategory | None = None
    target_amount: float | None = Field(default=None, gt=0, le=_MAX_AMOUNT)
    current_amount: float | None = Field(default=None, ge=0, le=_MAX_AMOUNT)
    target_date: date | None = None
    monthly_contribution: float | None = Field(default=None, ge=0, le=_MAX_MONTHLY_AMOUNT)
    risk_profile: RiskProfile | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    # Milestone 2 Task 9: nullable per-goal override of
    # financial_assumptions.inflation_rate, for education-category goals.
    # Bound matches FinancialAssumptions.inflation_rate's own [0, 0.5] range
    # (Milestone2ImplementationContract.md §9). Deliberately NOT part of
    # planning_service.CALCULATION_CONTEXT_FIELDS — see routers/goals.py.
    custom_inflation_rate: float | None = Field(default=None, ge=0, le=0.5)


class GoalResponse(GoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    on_track: bool
    probability: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    custom_inflation_rate: float | None = None

    model_config = {"from_attributes": True}
