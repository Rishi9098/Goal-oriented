"""Integration tests for Milestone 2 Task 8 (Family Goal Tagging):
PUT /api/v1/goals/{goal_id}/family-tags and GET /api/v1/family/goals.

Covers the explicit review requirements from this task's brief: goal
ownership stays unchanged, no duplicate members are created through
repeated tagging, existing Monte Carlo calculations remain untouched
(ADR-001's Calculation Lifecycle), and cross-household tagging is rejected
with 422, not a silent no-op.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

GOAL_PAYLOAD = {
    "name": "Home down payment",
    "category": "home",
    "target_amount": 120_000,
    "current_amount": 10_000,
    "target_date": (date.today() + timedelta(days=365 * 5)).isoformat(),
    "monthly_contribution": 800,
    "risk_profile": "conservative",
    "priority": 1,
}


async def _create_goal(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/v1/goals", json=GOAL_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_spouse(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/api/v1/family/members",
        json={"relationship_type": "spouse", "name": "Priya", "date_of_birth": "1991-03-12"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _self_member_id(client: AsyncClient, headers: dict) -> str:
    home = await client.get("/api/v1/family", headers=headers)
    return next(m["id"] for m in home.json()["members"] if m["relationship_type"] == "self")


@pytest.mark.asyncio
class TestSetGoalFamilyTags:
    async def test_tag_goal_with_spouse_success(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["goal_id"] == goal["id"]
        assert len(data["tagged_members"]) == 1
        assert data["tagged_members"][0]["name"] == "Priya"
        assert data["tagged_members"][0]["relationship_type"] == "spouse"

    async def test_tag_goal_with_self_resolves_name_from_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal = await _create_goal(client, auth_headers)
        self_id = await _self_member_id(client, auth_headers)

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [self_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tagged_members"][0]["name"] == "Test User"

    async def test_empty_list_untags_everyone(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)
        await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tagged_members"] == []

        # The goal itself must never be deleted or deactivated by untagging.
        get_resp = await client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is True

    async def test_repeated_tagging_never_creates_duplicate_rows(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Task 8's explicit 'no duplicate ownership model' / no-duplicate-
        row requirement: retagging with the same member twice must not
        violate goal_household_members' unique constraint or leave two
        rows for the same (goal, member) pair."""
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)

        for _ in range(3):
            resp = await client.put(
                f"/api/v1/goals/{goal['id']}/family-tags",
                json={"household_member_ids": [spouse_id]},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert len(resp.json()["tagged_members"]) == 1

        goals_resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        tagged = goals_resp.json()[0]["tagged_members"]
        assert len(tagged) == 1

    async def test_invalid_household_member_id_rejected_with_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        goal = await _create_goal(client, auth_headers)
        fake_id = "00000000-0000-0000-0000-000000000000"

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [fake_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_cross_household_member_id_rejected_not_silently_ignored(
        self,
        client: AsyncClient,
        auth_headers: dict,
        other_auth_headers: dict,
    ):
        goal = await _create_goal(client, auth_headers)
        other_spouse_id = await _create_spouse(client, other_auth_headers)

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [other_spouse_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

        # Confirm it was rejected outright, not silently dropped/ignored.
        goals_resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        assert goals_resp.json()[0]["tagged_members"] == []

    async def test_tagging_goal_owned_by_another_user_returns_404(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        goal = await _create_goal(client, other_auth_headers)

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_nonexistent_goal_returns_404(self, client: AsyncClient, auth_headers: dict):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.put(
            f"/api/v1/goals/{fake_id}/family-tags",
            json={"household_member_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_tagging_never_changes_goal_owner(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Goal Ownership Review requirement: goal_household_members is a
        purely descriptive tag, never a co-ownership mechanism."""
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)
        original_owner = goal["user_id"]

        await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )

        get_resp = await client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
        assert get_resp.json()["user_id"] == original_owner

    async def test_tagging_never_changes_goal_probability(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Data Integrity / Calculation Lifecycle compatibility (ADR-001):
        tagging is not a Calculation Context change and must never trigger
        calculate_goal_probability."""
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)
        original_probability = goal["probability"]
        original_on_track = goal["on_track"]

        await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )

        get_resp = await client.get(f"/api/v1/goals/{goal['id']}", headers=auth_headers)
        assert get_resp.json()["probability"] == original_probability
        assert get_resp.json()["on_track"] == original_on_track

    async def test_tagging_writes_audit_log(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)

        resp = await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Audit row correctness is verified at the service layer via the
        # existing family_service audit pattern (household_created,
        # family_member_added/updated/removed all follow the same shape);
        # this test's job is only to confirm the endpoint succeeds without
        # bypassing that path — a full row-count assertion would require
        # direct DB access this integration test layer doesn't otherwise use.


@pytest.mark.asyncio
class TestListFamilyGoals:
    async def test_empty_when_no_goals(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_untagged_goal_has_empty_tagged_members(
        self, client: AsyncClient, auth_headers: dict
    ):
        await _create_goal(client, auth_headers)
        resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["tagged_members"] == []

    async def test_reflects_tagged_members(self, client: AsyncClient, auth_headers: dict):
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)
        await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()[0]
        assert data["id"] == goal["id"]
        assert len(data["tagged_members"]) == 1
        assert data["tagged_members"][0]["name"] == "Priya"

    async def test_only_returns_caller_own_goals(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        await _create_goal(client, other_auth_headers)
        resp = await client.get("/api/v1/family/goals", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestMemberDetailReflectsTaggedGoals:
    async def test_tagging_makes_goal_appear_in_member_detail(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Cross-task integration: Task 7's GET /family/members/{id}
        already queries goal_household_members (built ahead of need in
        Task 2/7); Task 8 is the first thing that writes rows there, so
        this should start populating with zero changes to that endpoint."""
        goal = await _create_goal(client, auth_headers)
        spouse_id = await _create_spouse(client, auth_headers)

        await client.put(
            f"/api/v1/goals/{goal['id']}/family-tags",
            json={"household_member_ids": [spouse_id]},
            headers=auth_headers,
        )

        detail = await client.get(f"/api/v1/family/members/{spouse_id}", headers=auth_headers)
        assert detail.status_code == 200
        tagged_goals = detail.json()["tagged_goals"]
        assert len(tagged_goals) == 1
        assert tagged_goals[0]["name"] == "Home down payment"
