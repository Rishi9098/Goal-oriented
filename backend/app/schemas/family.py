import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

RelationshipType = Literal["spouse", "child", "parent", "other"]
Gender = Literal["female", "male", "other"]
InsuranceStatus = Literal["yes", "no", "not_sure"]

_MAX_AGE_YEARS = 130


def _validate_date_of_birth(value: date | None) -> date | None:
    if value is None:
        return value
    today = date.today()
    if value > today:
        raise ValueError("date_of_birth cannot be in the future")
    min_dob = date(today.year - _MAX_AGE_YEARS, today.month, today.day)
    if value < min_dob:
        raise ValueError(f"date_of_birth cannot be more than {_MAX_AGE_YEARS} years in the past")
    return value


class OnboardingSeedRequest(BaseModel):
    has_spouse: bool
    has_children: bool
    children_count: int | None = Field(default=None, ge=1, le=10)
    has_dependent_parents: bool

    @model_validator(mode="after")
    def _children_count_required_if_has_children(self) -> "OnboardingSeedRequest":
        if self.has_children and self.children_count is None:
            raise ValueError("children_count is required when has_children is true")
        return self


class FamilyMemberFieldsBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date_of_birth: date | None = None
    gender: Gender | None = None
    is_tax_dependent: bool = False
    # 'mother'|'father' for parent-type members; free text for other-type.
    relationship_detail: str | None = Field(default=None, max_length=100)
    has_own_insurance: InsuranceStatus | None = None

    @field_validator("date_of_birth")
    @classmethod
    def _dob_bounds(cls, v: date | None) -> date | None:
        return _validate_date_of_birth(v)


class FamilyMemberCreate(FamilyMemberFieldsBase):
    relationship_type: RelationshipType


class FamilyMemberUpdate(FamilyMemberFieldsBase):
    pass


class HouseholdSummary(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class FamilyMemberSummary(BaseModel):
    id: uuid.UUID
    relationship_type: str
    name: str | None
    is_complete: bool


class FamilyHomeResponse(BaseModel):
    household: HouseholdSummary
    members: list[FamilyMemberSummary]


class FamilyMemberResponse(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    relationship_type: str
    name: str | None
    date_of_birth: date | None = None
    gender: str | None = None
    is_tax_dependent: bool | None = None
    relationship_detail: str | None = None
    has_own_insurance: str | None = None
    # Milestone 2 Task 7: reuses family_service.is_complete() — the exact
    # same function the Family Home list (GET /family) already uses — so
    # the frontend never has to re-derive completeness from raw fields
    # itself, which would risk drifting from the one real definition.
    is_complete: bool = True
    # Populated as of Milestone 2 Task 3 via
    # scheme_eligibility_service.check_ssy_eligibility — reuses the same
    # evaluation path the Family Government Schemes screen (Task 11) will
    # use, never duplicated. Empty for any member who doesn't currently
    # match a seeded scheme's eligibility rules.
    eligible_schemes: list[dict[str, str]] = Field(default_factory=list)


class TaggedGoalSummary(BaseModel):
    id: uuid.UUID
    name: str


class CoverageSummary(BaseModel):
    health_policy_id: uuid.UUID
    policy_type: str


class FamilyMemberDetailResponse(BaseModel):
    member: FamilyMemberResponse
    # tagged_goals: the query (family_service.get_member_detail) was written
    # in Task 2/7 against goal_household_members directly — Task 8 is the
    # first thing that writes rows there, so this field starts populating
    # with zero changes to this response or its query.
    # coverage: still always empty until Task 10 (insurance) ships.
    tagged_goals: list[TaggedGoalSummary]
    coverage: list[CoverageSummary]


class TaggedMemberSummary(BaseModel):
    """A household member a goal has been tagged with — distinct from
    TaggedGoalSummary above (a goal tagged with a member)."""

    id: uuid.UUID
    name: str | None
    relationship_type: str


class FamilyTagsRequest(BaseModel):
    # Replaces the full tag set for a goal in one call (empty list is valid
    # — untags everyone). Each id is validated against the caller's own
    # household in family_service.set_goal_household_tags, never trusted
    # as-is.
    household_member_ids: list[uuid.UUID] = Field(default_factory=list)


class FamilyTagsResponse(BaseModel):
    goal_id: uuid.UUID
    tagged_members: list[TaggedMemberSummary]


class FamilyGoalSummary(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    target_amount: float
    current_amount: float
    target_date: date
    probability: float
    on_track: bool
    tagged_members: list[TaggedMemberSummary]
