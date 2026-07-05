import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RiskProfile = Literal["conservative", "balanced", "aggressive"]


class SimulationRequest(BaseModel):
    goal_id: uuid.UUID | None = None
    initial_amount: float = Field(ge=0, description="Current savings toward this goal")
    monthly_contribution: float = Field(ge=0, description="Monthly savings added")
    years_to_goal: float = Field(gt=0, le=50, description="Investment horizon in years")
    risk_profile: RiskProfile = "balanced"
    num_simulations: int = Field(default=10_000, ge=1_000, le=100_000)


class PercentileOutcomes(BaseModel):
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class SimulationResponse(BaseModel):
    id: uuid.UUID
    success_rate: float = Field(description="Probability of reaching goal (0-100)")
    percentiles: PercentileOutcomes
    distribution: dict[str, float] = Field(
        description="Histogram bins: endpoint_value -> count fraction"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class OptimizationRequest(BaseModel):
    goal_id: uuid.UUID
    target_probability: float = Field(ge=50, le=99, default=80)
    max_monthly_increase: float = Field(default=1_000.0, ge=0, description="Max extra monthly contribution")
    allow_risk_adjustment: bool = True


class OptimizationSuggestion(BaseModel):
    description: str
    monthly_contribution_delta: float
    risk_profile_change: RiskProfile | None
    projected_probability: float
    impact_summary: str


class OptimizationResponse(BaseModel):
    goal_id: uuid.UUID
    current_probability: float
    suggestions: list[OptimizationSuggestion]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


class DashboardSuggestion(BaseModel):
    id: str
    title: str
    impact: str
    severity: Literal["warning", "info", "success"]


class DashboardResponse(BaseModel):
    net_worth: float
    net_worth_delta_pct: float
    liquid_assets: float
    invested: float
    liabilities: float
    monthly_income: float
    monthly_expenses: float
    monthly_savings_rate: float
    projected_retirement: float
    plan_health_score: int
    alerts: int
    goal_count: int
    goals_on_track: int
    suggestions: list[DashboardSuggestion] = []
