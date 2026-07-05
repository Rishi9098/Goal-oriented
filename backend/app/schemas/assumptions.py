import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FinancialAssumptionsBase(BaseModel):
    inflation_rate: float = Field(ge=0, le=0.5, default=0.03)
    expected_return_conservative: float = Field(ge=0, le=0.5, default=0.05)
    expected_return_balanced: float = Field(ge=0, le=0.5, default=0.07)
    expected_return_aggressive: float = Field(ge=0, le=0.5, default=0.09)
    tax_rate: float = Field(ge=0, le=1, default=0.22)
    retirement_age: int = Field(ge=40, le=80, default=65)
    social_security_monthly: float = Field(ge=0, default=0.0)


class FinancialAssumptionsUpdate(FinancialAssumptionsBase):
    pass


class FinancialAssumptionsResponse(FinancialAssumptionsBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
