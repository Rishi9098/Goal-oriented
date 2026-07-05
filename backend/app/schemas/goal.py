import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

GoalCategory = Literal["retirement", "education", "home", "travel", "wealth", "emergency"]
RiskProfile = Literal["conservative", "balanced", "aggressive"]


class GoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: GoalCategory
    target_amount: float = Field(gt=0)
    current_amount: float = Field(ge=0, default=0.0)
    target_date: date
    monthly_contribution: float = Field(ge=0, default=0.0)
    risk_profile: RiskProfile = "balanced"
    priority: int = Field(ge=1, le=10, default=1)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: GoalCategory | None = None
    target_amount: float | None = Field(default=None, gt=0)
    current_amount: float | None = Field(default=None, ge=0)
    target_date: date | None = None
    monthly_contribution: float | None = Field(default=None, ge=0)
    risk_profile: RiskProfile | None = None
    priority: int | None = Field(default=None, ge=1, le=10)


class GoalResponse(GoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    on_track: bool
    probability: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
