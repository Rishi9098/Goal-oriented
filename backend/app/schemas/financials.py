import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# Upper bounds keep user-supplied amounts within a plausible financial-planning
# range and out of the territory where the Monte Carlo engine's compounding
# loop (backend/app/services/monte_carlo.py) can produce inf/NaN terminal
# values (AUDIT.md #10). None of these are meant to be tight — they're a
# backstop against typos and abuse, not a real constraint on legitimate use.
_MAX_BALANCE = 1_000_000_000.0
_MAX_ANNUAL_AMOUNT = 100_000_000.0
_MAX_MONTHLY_AMOUNT = 10_000_000.0


class IncomeSourceCreate(BaseModel):
    source_type: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)
    annual_amount: float = Field(gt=0, le=_MAX_ANNUAL_AMOUNT)


class IncomeSourceResponse(IncomeSourceCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    category: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)
    monthly_amount: float = Field(ge=0, le=_MAX_MONTHLY_AMOUNT)


class ExpenseResponse(ExpenseCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    asset_type: str = Field(max_length=50)
    institution: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    current_value: float = Field(ge=0, le=_MAX_BALANCE)


class AssetUpdate(BaseModel):
    current_value: float | None = Field(default=None, ge=0, le=_MAX_BALANCE)
    institution: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class AssetResponse(AssetCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiabilityCreate(BaseModel):
    liability_type: str = Field(max_length=50)
    institution: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    balance: float = Field(ge=0, le=_MAX_BALANCE)
    interest_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_payment: float = Field(ge=0, le=_MAX_MONTHLY_AMOUNT, default=0.0)


class LiabilityUpdate(BaseModel):
    balance: float | None = Field(default=None, ge=0, le=_MAX_BALANCE)
    interest_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_payment: float | None = Field(default=None, ge=0, le=_MAX_MONTHLY_AMOUNT)
    institution: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class LiabilityResponse(LiabilityCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
