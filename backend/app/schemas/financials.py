import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IncomeSourceCreate(BaseModel):
    source_type: str = Field(max_length=50)
    description: str | None = Field(default=None, max_length=255)
    annual_amount: float = Field(gt=0)


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
    monthly_amount: float = Field(ge=0)


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
    current_value: float = Field(ge=0)


class AssetUpdate(BaseModel):
    current_value: float | None = Field(default=None, ge=0)
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
    balance: float = Field(ge=0)
    interest_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_payment: float = Field(ge=0, default=0.0)


class LiabilityUpdate(BaseModel):
    balance: float | None = Field(default=None, ge=0)
    interest_rate: float | None = Field(default=None, ge=0, le=1)
    monthly_payment: float | None = Field(default=None, ge=0)
    institution: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class LiabilityResponse(LiabilityCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
