"""Integration tests for Milestone 2 Task 12 (Family Dashboard):
GET /api/v1/family/dashboard.

Centered on IntegrationIntegrityReview_Task12.md: every card consumes the
same authoritative data its source screen shows (the feed-vs-endpoint and
card-vs-recommendation consistency tests are the heart of this file),
partial failures degrade to null cards rather than a 500, nothing is
persisted, and the Calculation Lifecycle stays untouched.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.policy import Scheme, SchemeEligibilityRule, TaxAct, TaxSection
from app.services import family_dashboard_service, planning_service


async def _seed_80d_tax_section(db) -> None:
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


async def _seed_ssy_scheme(db) -> None:
    ssy = Scheme(
        code="SSY",
        name="Sukanya Samriddhi Yojana",
        governing_authority="MoF",
        status="active",
        category="child",
    )
    db.add(ssy)
    await db.flush()
    db.add_all(
        [
            SchemeEligibilityRule(
                scheme_id=ssy.id,
                rule_type="max_age",
                operator="lt",
                value="10",
                effective_from=date(2015, 1, 1),
            ),
            SchemeEligibilityRule(
                scheme_id=ssy.id,
                rule_type="gender",
                operator="eq",
                value="female",
                effective_from=date(2015, 1, 1),
            ),
        ]
    )
    await db.flush()


async def _create_parent(
    client: AsyncClient, headers: dict, *, name: str = "Sunita Mehta", has_own_insurance: str = "no"
) -> str:
    resp = await client.post(
        "/api/v1/family/members",
        json={
            "relationship_type": "parent",
            "name": name,
            "relationship_detail": "mother",
            "has_own_insurance": has_own_insurance,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_daughter(client: AsyncClient, headers: dict) -> str:
    dob = (date.today() - timedelta(days=365 * 7)).isoformat()
    resp = await client.post(
        "/api/v1/family/members",
        json={
            "relationship_type": "child",
            "name": "Ananya Mehta",
            "date_of_birth": dob,
            "gender": "female",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_goal(
    client: AsyncClient, headers: dict, *, name: str, category: str, years_ahead: int = 10
) -> dict:
    resp = await client.post(
        "/api/v1/goals",
        json={
            "name": name,
            "category": category,
            "target_amount": 500_000,
            "current_amount": 50_000,
            "target_date": (date.today() + timedelta(days=365 * years_ahead)).isoformat(),
            "monthly_contribution": 2_000,
            "risk_profile": "balanced",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _tag_goal(client: AsyncClient, headers: dict, goal_id: str, member_ids: list[str]):
    resp = await client.put(
        f"/api/v1/goals/{goal_id}/family-tags",
        json={"household_member_ids": member_ids},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
class TestFamilyDashboard:
    async def test_empty_household_dashboard(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # A lazily-provisioned household contains only 'self' — a normal,
        # complete state, never an error.
        assert data["dependents"] == {
            "total_members": 1,
            "children": 0,
            "parents": 0,
            "spouse": 0,
            "others": 0,
        }
        assert data["education"] is None
        assert data["coverage"] == {"covered_members": 0, "total_members": 1}
        assert data["parents"] == {"uncovered_parent_names": []}
        assert data["retirement"] is None
        assert data["emergency"] is not None
        assert data["recommendations"] == []
        assert data["conflicts"] == []
        assert data["recommendations_unavailable"] is False

    async def test_dependents_card_counts_by_type(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _create_parent(client, auth_headers)
        await _create_daughter(client, auth_headers)
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        card = resp.json()["dependents"]
        assert card["total_members"] == 3
        assert card["children"] == 1
        assert card["parents"] == 1
        assert card["spouse"] == 0

    async def test_education_card_shows_nearest_future_goal_with_tagged_member(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        daughter_id = await _create_daughter(client, auth_headers)
        await _create_goal(
            client, auth_headers, name="College — far", category="education", years_ahead=15
        )
        near = await _create_goal(
            client, auth_headers, name="College — near", category="education", years_ahead=8
        )
        await _tag_goal(client, auth_headers, near["id"], [daughter_id])

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        card = resp.json()["education"]
        assert card["goal_name"] == "College — near"
        assert card["tagged_member_names"] == ["Ananya Mehta"]

    async def test_education_card_none_without_education_goals(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_goal(client, auth_headers, name="Retire", category="retirement")
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        assert resp.json()["education"] is None

    async def test_coverage_card_counts_covered_members(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        parent_id = await _create_parent(client, auth_headers)
        await _create_daughter(client, auth_headers)
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
        assert resp.status_code == 201

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        card = resp.json()["coverage"]
        assert card == {"covered_members": 1, "total_members": 3}

    async def test_parents_card_and_recommendation_move_together(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """The heart of DependencyValidation_Task12.md Finding 2: the
        Parents warning and the insurance recommendation share one
        authority — they appear together and disappear together."""
        await _seed_80d_tax_section(db)
        parent_id = await _create_parent(client, auth_headers, has_own_insurance="no")

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        data = resp.json()
        assert data["parents"]["uncovered_parent_names"] == ["Sunita Mehta"]
        assert any(r["source"] == "insurance" for r in data["recommendations"])

        # Recording a policy that covers the parent resolves BOTH at once.
        create = await client.post(
            "/api/v1/family/insurance/policies",
            json={
                "policy_type": "senior_citizen_standalone",
                "sum_insured": 500_000,
                "annual_premium": 20_000,
                "household_member_ids": [parent_id],
            },
            headers=auth_headers,
        )
        assert create.status_code == 201

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        data = resp.json()
        assert data["parents"]["uncovered_parent_names"] == []
        assert not any(r["source"] == "insurance" for r in data["recommendations"])

    async def test_retirement_card_uses_persisted_probability(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal = await _create_goal(client, auth_headers, name="Retire at 60", category="retirement")
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        card = resp.json()["retirement"]
        assert card["goal_name"] == "Retire at 60"
        # Byte-identical to the persisted value — never recomputed on read.
        assert card["probability"] == goal["probability"]
        assert card["on_track"] == goal["on_track"]

    async def test_emergency_card_passes_through_dashboard_figures(
        self, client: AsyncClient, auth_headers: dict
    ):
        dash = await client.get("/api/v1/dashboard", headers=auth_headers)
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        card = resp.json()["emergency"]
        assert card["liquid_assets"] == dash.json()["liquid_assets"]
        assert card["monthly_expenses"] == dash.json()["monthly_expenses"]

    async def test_feed_identical_to_recommendations_endpoint(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """The Contract's Acceptance Criterion: the feed never shows a
        recommendation its source screen wouldn't independently justify —
        guaranteed here by byte-identical output from the same service."""
        await _seed_80d_tax_section(db)
        await _seed_ssy_scheme(db)
        await _create_parent(client, auth_headers, has_own_insurance="no")
        await _create_daughter(client, auth_headers)

        feed = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        source = await client.get("/api/v1/family/recommendations", headers=auth_headers)
        assert feed.json()["recommendations"] == source.json()["recommendations"]
        assert feed.json()["conflicts"] == source.json()["conflicts"]

    async def test_nothing_is_persisted(self, client: AsyncClient, auth_headers: dict, db):
        from sqlalchemy import select

        from app.models.recommendation import Recommendation

        await _seed_80d_tax_section(db)
        await _create_parent(client, auth_headers)
        await client.get("/api/v1/family/dashboard", headers=auth_headers)

        result = await db.execute(select(Recommendation))
        assert result.scalars().all() == []

    async def test_calculation_lifecycle_untouched(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers, name="Emergency", category="emergency")
        for _ in range(3):
            await client.get("/api/v1/family/dashboard", headers=auth_headers)
        check = await client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
        assert check.json()["probability"] == goal["probability"]

    async def test_partial_failure_degrades_gracefully(
        self, client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        """One failed section returns a null card — never a 500, never a
        fabricated zero — while every other section still populates."""

        async def boom(*args, **kwargs):
            raise RuntimeError("simulated section failure")

        monkeypatch.setattr(planning_service, "get_dashboard", boom)

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["emergency"] is None
        assert data["dependents"] is not None
        assert data["coverage"] is not None
        assert data["recommendations_unavailable"] is False

    async def test_recommendations_unavailable_flag(
        self, client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        """A failed feed is flagged explicitly — distinguishable from the
        honest 'no recommendations' empty state."""

        async def boom(*args, **kwargs):
            raise RuntimeError("simulated feed failure")

        monkeypatch.setattr(
            family_dashboard_service.family_recommendations_service,
            "get_family_recommendations",
            boom,
        )

        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendations"] == []
        assert data["recommendations_unavailable"] is True
        assert data["dependents"] is not None

    async def test_dashboard_isolated_between_users(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict, db
    ):
        await _create_parent(client, other_auth_headers)
        resp = await client.get("/api/v1/family/dashboard", headers=auth_headers)
        assert resp.json()["dependents"]["parents"] == 0
