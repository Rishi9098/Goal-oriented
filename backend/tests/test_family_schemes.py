"""Integration tests for Milestone 2.1-P1 (Government Schemes Screen):
GET /api/v1/family/schemes.

Centered on DesignReview_M2.1-P1.md: this endpoint is a direct passthrough
of scheme_eligibility_service.evaluate_household_eligibility() — these
tests verify the passthrough is faithful and that nothing is persisted,
not the eligibility logic itself (already covered by Task 3's own tests).
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.policy import Scheme, SchemeEligibilityRule


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


async def _seed_unconfigured_scheme(db) -> None:
    db.add(
        Scheme(
            code="PPF",
            name="Public Provident Fund",
            governing_authority="MoF/RBI",
            status="active",
            category="general_savings",
        )
    )
    await db.flush()


async def _create_daughter(client: AsyncClient, headers: dict, *, years_old: int = 7) -> str:
    dob = (date.today() - timedelta(days=365 * years_old)).isoformat()
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


async def _create_son(client: AsyncClient, headers: dict, *, years_old: int = 7) -> str:
    dob = (date.today() - timedelta(days=365 * years_old)).isoformat()
    resp = await client.post(
        "/api/v1/family/members",
        json={
            "relationship_type": "child",
            "name": "Ravi Mehta",
            "date_of_birth": dob,
            "gender": "male",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestFamilySchemes:
    async def test_empty_household_all_buckets_empty_or_unconfigured(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/family/schemes", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] == []
        assert data["potentially_eligible"] == []
        # No family members and no seeded schemes at all in a fresh test DB.
        assert data["not_eligible"] == []

    async def test_eligible_child_appears_in_eligible_bucket(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        await _seed_ssy_scheme(db)
        await _create_daughter(client, auth_headers, years_old=7)

        resp = await client.get("/api/v1/family/schemes", headers=auth_headers)
        data = resp.json()
        assert len(data["eligible"]) == 1
        assert data["eligible"][0]["scheme_code"] == "SSY"
        assert data["eligible"][0]["member_name"] == "Ananya Mehta"
        assert "Ananya Mehta" in data["eligible"][0]["reason"]

    async def test_ineligible_son_appears_in_not_eligible_bucket_not_hidden(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """A boy fails SSY's gender rule — must appear honestly in
        not_eligible, never silently omitted or miscategorized."""
        await _seed_ssy_scheme(db)
        await _create_son(client, auth_headers, years_old=7)

        resp = await client.get("/api/v1/family/schemes", headers=auth_headers)
        data = resp.json()
        assert data["eligible"] == []
        not_eligible_names = [item["member_name"] for item in data["not_eligible"]]
        assert "Ravi Mehta" in not_eligible_names

    async def test_unconfigured_scheme_is_honest_not_fabricated(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """A scheme with zero seeded rules must read as honestly
        unconfigured, never fabricated into eligible or not_eligible-with-
        a-made-up-reason."""
        await _seed_unconfigured_scheme(db)
        resp = await client.get("/api/v1/family/schemes", headers=auth_headers)
        data = resp.json()
        assert len(data["not_eligible"]) == 1
        assert data["not_eligible"][0]["scheme_code"] == "PPF"
        assert "not yet configured" in data["not_eligible"][0]["reason"]

    async def test_nothing_is_persisted(self, client: AsyncClient, auth_headers: dict, db):
        from sqlalchemy import select

        from app.models.recommendation import Recommendation

        await _seed_ssy_scheme(db)
        await _create_daughter(client, auth_headers)
        await client.get("/api/v1/family/schemes", headers=auth_headers)

        result = await db.execute(select(Recommendation))
        assert result.scalars().all() == []

    async def test_identical_to_recommendations_feed_for_eligible_bucket(
        self, client: AsyncClient, auth_headers: dict, db
    ):
        """DesignReview_M2.1-P1.md: the Schemes screen and the
        Recommendations feed/Dashboard cannot disagree, because both call
        the same evaluate_household_eligibility() with no caching between
        them. Verify the eligible scheme's reason text matches exactly."""
        await _seed_ssy_scheme(db)
        await _create_daughter(client, auth_headers)

        schemes = await client.get("/api/v1/family/schemes", headers=auth_headers)
        recs = await client.get("/api/v1/family/recommendations", headers=auth_headers)

        scheme_reason = schemes.json()["eligible"][0]["reason"]
        rec_reason = next(
            r["why"] for r in recs.json()["recommendations"] if r["source"] == "schemes"
        )
        assert scheme_reason == rec_reason

    async def test_calculation_lifecycle_untouched(self, client: AsyncClient, auth_headers: dict):
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

        await client.get("/api/v1/family/schemes", headers=auth_headers)

        check = await client.get(f"/api/v1/goals/{goal_resp.json()['id']}", headers=auth_headers)
        assert check.json()["probability"] == original_probability

    async def test_schemes_isolated_between_users(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict, db
    ):
        await _seed_ssy_scheme(db)
        await _create_daughter(client, other_auth_headers)

        resp = await client.get("/api/v1/family/schemes", headers=auth_headers)
        assert resp.json()["eligible"] == []
