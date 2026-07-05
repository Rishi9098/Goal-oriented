import uuid
from datetime import date, datetime

from pydantic import BaseModel


class GoalReportItem(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    target_amount: float
    current_amount: float
    monthly_contribution: float
    probability: float
    on_track: bool
    target_date: date


class ReportSummaryResponse(BaseModel):
    generated_at: datetime
    plan_health_score: int
    net_worth: float
    liquid_assets: float
    invested: float
    liabilities: float
    monthly_income: float
    monthly_expenses: float
    monthly_savings_rate: float
    goal_count: int
    goals_on_track: int
    goals: list[GoalReportItem]
