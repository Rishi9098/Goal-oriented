import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class UserProfileBase(BaseModel):
    date_of_birth: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    dependents: int = Field(ge=0, default=0)
    country: str | None = None
    state_province: str | None = None
    employment_status: str | None = None
    employer: str | None = Field(default=None, max_length=255)
    occupation: str | None = Field(default=None, max_length=255)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    onboarding_complete: bool | None = None
    current_step: int | None = Field(ge=0, default=None)


class UserProfileResponse(UserProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    onboarding_complete: bool
    current_step: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
