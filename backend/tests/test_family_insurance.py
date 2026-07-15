"""Integration tests for Milestone 2 Task 10 (Family Insurance):
GET /api/v1/family/insurance, POST /api/v1/family/insurance/policies,
PUT /api/v1/family/insurance/policies/{id}/coverage.

Centered on RecommendationIntegrityReview_Task10.md's five guarantees:
verified-rules-only figures, every recommendation fully explained, missing
information never fabricated, the Calculation Lifecycle untouched, and
schemes/insurance kept separate.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import TaxAct, TaxSection


async def _seed_80d_tax_section(db: AsyncSession) -> None:
    """The test DB (fresh SQLite per test) has no seeded tax data by
    default — mirrors scripts/seed_policy_data.py's real 80D row so the
    recommendation has a verified figure to read, per RecommendationIntegrityReview_
    Task10.md #1 (never a hardcoded fallback)."""
    act = TaxAct(
        name="Income-tax Act, 1961",
        effective_from=date(1962, 4, 1),
        effective_to=date(2026, 3, 31),
    )
    db.add(act)
    await db.flush()
    db.add(
        TaxSection(
            tax_act_id=act.id,
            section_number="80D",
            purpose="health_insurance_premium_deduction",
            limit_amount=25_000.0,
            effective_from=date(1962, 4, 1),
            effective_to=date(2026, 3, 31),
        )
    )
    await db.flush()


def _senior_dob() -> str:
    return (date.today() - timedelta(days=365 * 65)).isoformat()


def _non_senior_dob() -> str:
    return (date.today() - timedelta(days=365 * 55)).isoformat()


async def _create_parent(
    client: AsyncClient,
    headers: dict,
    *,
    name: str = "Sunita",
    has_own_insurance: str = "no",
    date_of_birth: str | None = None,
    relationship_detail: str = "mother",
) -> str:
    body: dict[str, object] = {
        "relationship_type": "parent",
        "name": name,
        "relationship_detail": relationship_detail,
        "has_own_insurance": has_own_insurance,
    }
    if date_of_birth is not None:
        body["date_of_birth"] = date_of_birth
    resp = await client.post("/api/v1/family/members", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestInsuranceRecommendation:
    async def test_no_recommendation_with_no_parents(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["recommendation"] is None
        assert resp.json()["policies"] == []

    async def test_no_recommendation_when_parent_marked_yes(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="yes")
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.json()["recommendation"] is None

    async def test_recommendation_fires_for_no(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.json()["recommendation"] is not None

    async def test_recommendation_fires_for_not_sure(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="not_sure")
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.json()["recommendation"] is not None

    async def test_incomplete_parent_placeholder_never_triggers_recommendation(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Created with only relationship_type via onboarding-seed style
        # incompleteness is hard to reach through the member-create endpoint
        # directly (has_own_insurance is required for a parent at creation
        # time) — so this test targets the actual reachable incomplete
        # state instead: name entered, but the required has_own_insurance
        # answer intentionally omitted is rejected at creation (422), which
        # itself proves an incomplete parent can never reach the DB with a
        # has_own_insurance value the recommendation could misread.
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "parent", "name": "Placeholder"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_recommendation_always_fully_explained(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """No recommendation without why/why_now/used/missing populated —
        RecommendationIntegrityReview_Task10.md #2."""
        await _seed_80d_tax_section(db)
        await _create_parent(
            client, auth_headers, has_own_insurance="no", date_of_birth=_non_senior_dob()
        )
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        rec = resp.json()["recommendation"]
        assert rec["why"]
        assert rec["why_now"]
        assert len(rec["what_information_was_used"]) > 0
        assert isinstance(rec["what_information_is_missing"], list)

    async def test_figures_match_verified_source_exactly(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """RecommendationIntegrityReview_Task10.md #1 — base 25000, from
        the seeded tax_sections row, not a hardcoded literal."""
        await _seed_80d_tax_section(db)
        await _create_parent(
            client, auth_headers, has_own_insurance="no", date_of_birth=_non_senior_dob()
        )
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        rec = resp.json()["recommendation"]
        assert rec["floater_deduction_limit"] == 25_000.0
        assert rec["parent_deduction_limit"] == 25_000.0

    async def test_senior_parent_doubles_the_deduction_limit(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        await _seed_80d_tax_section(db)
        await _create_parent(
            client, auth_headers, has_own_insurance="no", date_of_birth=_senior_dob()
        )
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        rec = resp.json()["recommendation"]
        assert rec["parent_deduction_limit"] == 50_000.0
        assert rec["confidence_score"] == 1.0

    async def test_missing_date_of_birth_never_fabricates_senior_status(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """RecommendationIntegrityReview_Task10.md #3 — no DOB means the
        base figure only, lower confidence, and the gap is explicitly
        listed, never silently assumed either way."""
        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers, has_own_insurance="not_sure")
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        rec = resp.json()["recommendation"]
        assert rec["parent_deduction_limit"] == 25_000.0
        assert rec["confidence_score"] < 1.0
        assert any("date of birth" in m for m in rec["what_information_is_missing"])

    async def test_no_recommendation_when_parent_already_covered_by_a_policy(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """Data Integrity Review — avoiding a stale recommendation when the
        actual policy data contradicts the (possibly stale) onboarding
        answer."""
        await _seed_80d_tax_section(db)
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="not_sure")
        await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "senior_citizen_standalone",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.json()["recommendation"] is None

    async def test_calculation_lifecycle_untouched(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """Verifies this task never touches goal probability — creating a
        goal, then triggering the insurance recommendation, must not change
        it."""
        await _seed_80d_tax_section(db)
        goal_resp = await client.post(
            "/api/v1/goals",
            json={
                "name": "Emergency Fund",
                "category": "emergency",
                "target_amount": 50_000,
                "current_amount": 10_000,
                "target_date": "2030-01-01",
                "monthly_contribution": 500,
                "risk_profile": "balanced",
            },
            headers=auth_headers,
        )
        original_probability = goal_resp.json()["probability"]

        await _create_parent(client, auth_headers, has_own_insurance="no")
        await client.get("/api/v1/family/insurance", headers=auth_headers)

        get_goal = await client.get(f"/api/v1/goals/{goal_resp.json()['id']}", headers=auth_headers)
        assert get_goal.json()["probability"] == original_probability


@pytest.mark.asyncio
class TestPolicyCRUD:
    async def test_create_policy_success(self, client: AsyncClient, auth_headers: dict):
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "senior_citizen_standalone",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "insurer": "Star Health",
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["policy_type"] == "senior_citizen_standalone"
        assert len(data["covered_members"]) == 1
        assert data["covered_members"][0]["id"] == parent_id

    async def test_create_policy_with_zero_covered_members_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_policy_with_foreign_member_id_rejected(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        other_parent_id = await _create_parent(client, other_auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [other_parent_id],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_negative_sum_insured_rejected(self, client: AsyncClient, auth_headers: dict):
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": -1,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_negative_annual_premium_rejected(self, client: AsyncClient, auth_headers: dict):
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": -1,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_invalid_policy_type_rejected(self, client: AsyncClient, auth_headers: dict):
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "not_a_real_type",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_replace_coverage_success(self, client: AsyncClient, auth_headers: dict):
        parent_id = await _create_parent(
            client, auth_headers, name="Mother", has_own_insurance="no"
        )
        father_id = await _create_parent(
            client,
            auth_headers,
            name="Father",
            relationship_detail="father",
            has_own_insurance="no",
        )
        create = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        policy_id = create.json()["id"]

        resp = await client.put(
            f"/api/v1/family/insurance/policies/{policy_id}/coverage",
            json={"household_member_ids": [father_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        covered_ids = [m["id"] for m in resp.json()["covered_members"]]
        assert covered_ids == [father_id]

    async def test_replace_coverage_on_nonexistent_policy_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.put(
            f"/api/v1/family/insurance/policies/{fake_id}/coverage",
            json={"household_member_ids": [parent_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_replace_coverage_on_another_users_policy_returns_404(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        parent_id = await _create_parent(client, other_auth_headers, has_own_insurance="no")
        create = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=other_auth_headers,
        )
        policy_id = create.json()["id"]

        resp = await client.put(
            f"/api/v1/family/insurance/policies/{policy_id}/coverage",
            json={"household_member_ids": [parent_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_policies_isolated_between_users(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        other_parent_id = await _create_parent(client, other_auth_headers, has_own_insurance="no")
        await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [other_parent_id],
            },
            headers=other_auth_headers,
        )
        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        assert resp.json()["policies"] == []

    async def test_multiple_policies_have_correct_distinct_coverage(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Milestone 2.1-P4: list_policies_with_coverage batches the
        covered-member lookup across all policies in one query instead of
        one query per policy — this must not mix up which members belong
        to which policy."""
        mother_id = await _create_parent(
            client, auth_headers, name="Mother", has_own_insurance="no"
        )
        father_id = await _create_parent(
            client, auth_headers, name="Father", has_own_insurance="no"
        )
        await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [mother_id],
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "individual",
                "sum_insured": 300_000,
                "annual_premium": 8_000,
                "household_member_ids": [father_id],
            },
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/family/insurance", headers=auth_headers)
        policies = resp.json()["policies"]
        assert len(policies) == 2
        by_type = {p["policy_type"]: p for p in policies}
        assert [m["id"] for m in by_type["family_floater"]["covered_members"]] == [mother_id]
        assert [m["id"] for m in by_type["individual"]["covered_members"]] == [father_id]


@pytest.mark.asyncio
class TestInsuranceAuditLogging:
    """Milestone 2.1-P2 — every insurance create/coverage-update action
    must be audit logged, matching family_service.py's existing pattern,
    with no duplicate entries. See DependencyValidation_M2.1-P2.md."""

    async def test_create_policy_is_audit_logged(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        from sqlalchemy import select

        from app.models.audit import AuditLog

        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        resp = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        policy_id = resp.json()["id"]

        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "insurance_policy_created")
        )
        entries = result.scalars().all()
        assert len(entries) == 1
        assert entries[0].after_state["policy_id"] == policy_id
        assert entries[0].after_state["covered_member_ids"] == [parent_id]
        # No member name, DOB, or insurance-status text — PII stays out of
        # audit records (SecurityReview_M2.1-P2.md).
        assert "name" not in str(entries[0].after_state).lower()

    async def test_replace_coverage_is_audit_logged_with_before_and_after(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        from sqlalchemy import select

        from app.models.audit import AuditLog

        mother_id = await _create_parent(
            client, auth_headers, name="Mother", has_own_insurance="no"
        )
        father_id = await _create_parent(
            client, auth_headers, name="Father", has_own_insurance="no"
        )
        create = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [mother_id],
            },
            headers=auth_headers,
        )
        policy_id = create.json()["id"]

        await client.put(
            f"/api/v1/family/insurance/policies/{policy_id}/coverage",
            json={"household_member_ids": [father_id]},
            headers=auth_headers,
        )

        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "insurance_policy_coverage_updated")
        )
        entries = result.scalars().all()
        assert len(entries) == 1
        assert entries[0].before_state["covered_member_ids"] == [mother_id]
        assert entries[0].after_state["covered_member_ids"] == [father_id]

    async def test_no_duplicate_audit_entries_per_action(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        from sqlalchemy import select

        from app.models.audit import AuditLog

        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")
        await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "family_floater",
                "sum_insured": 500_000,
                "annual_premium": 12_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )

        result = await db.execute(select(AuditLog))
        all_entries = result.scalars().all()
        create_entries = [e for e in all_entries if e.action == "insurance_policy_created"]
        assert len(create_entries) == 1

    async def test_reading_insurance_produces_no_audit_entry(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """Reads must never be audit-logged — only real writes. The
        household lazy-provisions on first call (a pre-existing, correctly
        logged Task 2 action, unrelated to this finding), so the assertion
        isolates only this finding's two new insurance actions."""
        from sqlalchemy import select

        from app.models.audit import AuditLog

        await client.get("/api/v1/family/insurance", headers=auth_headers)
        await client.get("/api/v1/family/insurance", headers=auth_headers)

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action.in_(
                    ["insurance_policy_created", "insurance_policy_coverage_updated"]
                )
            )
        )
        assert result.scalars().all() == []
