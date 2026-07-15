from pydantic import BaseModel

# Milestone 2.1-P1 — a direct passthrough of scheme_eligibility_service's
# EligibilityResult, no reshaping. Every field traces back to the seeded
# schemes/scheme_eligibility_rules tables via the already-certified
# evaluate_household_eligibility() (Task 3) — this schema adds no logic.


class SchemeEligibilityItem(BaseModel):
    scheme_code: str
    scheme_name: str
    member_name: str | None
    reason: str


class FamilySchemesResponse(BaseModel):
    eligible: list[SchemeEligibilityItem]
    potentially_eligible: list[SchemeEligibilityItem]
    not_eligible: list[SchemeEligibilityItem]
