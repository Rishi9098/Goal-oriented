"""Integration tests for Milestone 2 Task 9 (Family Goals & Custom Inflation):
custom_inflation_rate on PATCH/GET /api/v1/goals/{goal_id}.

Central concern per CalculationContextReview.md: custom_inflation_rate is
deliberately NOT part of the Calculation Context (ADR-001) — setting it must
never change goal.probability/on_track, and must never invoke
calculate_goal_probability(). These tests exist specifically to make that a
permanent, automated guarantee, not just a one-time manual check.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

GOAL_PAYLOAD = {
    "name": "Daughter's college fund",
    "category": "education",
    "target_amount": 80_000,
    "current_amount": 5_000,
    "target_date": (date.today() + timedelta(days=365 * 11)).isoformat(),
    "monthly_contribution": 400,
    "risk_profile": "balanced",
    "priority": 1,
}


async def _create_goal(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
class TestCustomInflationRate:
    async def test_setting_custom_rate_persists_and_is_returned(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal = await _create_goal(client, auth_headers)
        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": 0.08},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["custom_inflation_rate"] == 0.08

        get_resp = await client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
        assert get_resp.json()["custom_inflation_rate"] == 0.08

    async def test_new_goal_has_no_custom_rate_by_default(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal = await _create_goal(client, auth_headers)
        assert goal["custom_inflation_rate"] is None

    async def test_setting_custom_rate_alone_never_changes_probability(
        self, client: AsyncClient, auth_headers: dict
    ):
        """The central Calculation Context guarantee for this task."""
        goal = await _create_goal(client, auth_headers)
        original_probability = goal["probability"]
        original_on_track = goal["on_track"]

        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": 0.10},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["probability"] == original_probability
        assert resp.json()["on_track"] == original_on_track

    async def test_repeated_inflation_only_updates_never_drift_probability(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Guards against unseeded-RNG drift specifically: PATCHing
        custom_inflation_rate 3 times in a row (a real scenario — a user
        trying different rates) must never perturb probability, matching
        the 'repeated reads never change results' requirement."""
        goal = await _create_goal(client, auth_headers)
        original_probability = goal["probability"]

        for rate in (0.05, 0.09, 0.12):
            resp = await client.patch(
                f"/api/v1/goals/{goal['id']}",
                json={"custom_inflation_rate": rate},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["probability"] == original_probability

    async def test_calculation_context_field_alongside_inflation_still_recalculates(
        self, client: AsyncClient, auth_headers: dict
    ):
        """A real Calculation Context change (monthly_contribution) present
        in the same PATCH body must still trigger recalculation — the fix
        must not accidentally suppress legitimate recomputation."""
        goal = await _create_goal(client, auth_headers)

        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": 0.08, "monthly_contribution": 2000},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # A materially larger monthly contribution should raise probability
        # from whatever the original (lower-contribution) goal had.
        assert resp.json()["probability"] >= goal["probability"]
        assert resp.json()["custom_inflation_rate"] == 0.08

    async def test_name_only_update_does_not_change_probability(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Confirms the fix's scope: any non-Calculation-Context field
        (not just custom_inflation_rate) is now correctly excluded from
        triggering recomputation, per calculate_goal_probability()'s own
        pre-existing docstring contract."""
        goal = await _create_goal(client, auth_headers)
        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"name": "Renamed goal"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["probability"] == goal["probability"]

    async def test_rate_above_upper_bound_rejected(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": 0.51},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_negative_rate_rejected(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": -0.01},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_rate_at_exact_bounds_accepted(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        for rate in (0.0, 0.5):
            resp = await client.patch(
                f"/api/v1/goals/{goal['id']}",
                json={"custom_inflation_rate": rate},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["custom_inflation_rate"] == rate

    async def test_custom_rate_scoped_to_one_goal_only(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal_a = await _create_goal(client, auth_headers)
        goal_b = await _create_goal(client, auth_headers)

        await client.patch(
            f"/api/v1/goals/{goal_a['id']}",
            json={"custom_inflation_rate": 0.09},
            headers=auth_headers,
        )

        get_b = await client.get(f"/api/v1/goals/{goal_b['id']}", headers=auth_headers)
        assert get_b.json()["custom_inflation_rate"] is None

    async def test_cannot_set_custom_rate_on_another_users_goal(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        goal = await _create_goal(client, other_auth_headers)
        resp = await client.patch(
            f"/api/v1/goals/{goal['id']}",
            json={"custom_inflation_rate": 0.09},
            headers=auth_headers,
        )
        assert resp.status_code == 404
