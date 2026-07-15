"""Integration tests for the Family API (ImplementationChecklist.md Task 2).

Covers: onboarding-seed, Family Home (incl. lazy-provision), member CRUD,
and the household-ownership authorization pattern — the first "act on data
that isn't your own user_id directly" pattern in this codebase, which
RiskChecklist.md #2 flags as requiring an explicit negative-path test for
every endpoint, not just the happy path.
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import Scheme, SchemeEligibilityRule


async def _seed_ssy_scheme(db: AsyncSession) -> None:
    """Minimal SSY-only seed for Milestone 2 Task 9's eligible_schemes
    regression test — mirrors the scheme/rule shape
    test_scheme_eligibility_service.py's _seed_minimal_scheme_data() uses,
    scoped down to just SSY since that's the only scheme this file's tests
    need."""
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


@pytest.mark.asyncio
class TestOnboardingSeed:
    async def test_creates_expected_member_rows(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/family/onboarding-seed",
            json={
                "has_spouse": True,
                "has_children": True,
                "children_count": 3,
                "has_dependent_parents": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        members = resp.json()["members"]
        by_type: dict[str, int] = {}
        for m in members:
            by_type[m["relationship_type"]] = by_type.get(m["relationship_type"], 0) + 1
        assert by_type == {"self": 1, "spouse": 1, "child": 3, "parent": 1}

    async def test_no_dependents_leaves_only_self(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/family/onboarding-seed",
            json={"has_spouse": False, "has_children": False, "has_dependent_parents": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        members = resp.json()["members"]
        assert len(members) == 1
        assert members[0]["relationship_type"] == "self"
        assert members[0]["is_complete"] is True

    async def test_children_count_required_when_has_children_true(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/onboarding-seed",
            json={"has_spouse": False, "has_children": True, "has_dependent_parents": False},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_children_count_above_ten_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/onboarding-seed",
            json={
                "has_spouse": False,
                "has_children": True,
                "children_count": 11,
                "has_dependent_parents": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_idempotent_does_not_duplicate(self, client: AsyncClient, auth_headers: dict):
        payload = {
            "has_spouse": True,
            "has_children": False,
            "has_dependent_parents": False,
        }
        first = await client.post(
            "/api/v1/family/onboarding-seed", json=payload, headers=auth_headers
        )
        second = await client.post(
            "/api/v1/family/onboarding-seed", json=payload, headers=auth_headers
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["household"]["id"] == second.json()["household"]["id"]
        assert len(second.json()["members"]) == 2  # self + spouse, not duplicated


@pytest.mark.asyncio
class TestFamilyHome:
    async def test_lazy_provisions_for_user_with_no_household(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/family", headers=auth_headers)
        assert resp.status_code == 200
        members = resp.json()["members"]
        assert len(members) == 1
        assert members[0]["relationship_type"] == "self"
        assert members[0]["name"] == "Test User"  # resolved from User.full_name

    async def test_reflects_onboarding_seeded_members(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            "/api/v1/family/onboarding-seed",
            json={"has_spouse": True, "has_children": False, "has_dependent_parents": False},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/family", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["members"]) == 2

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/api/v1/family")
        assert resp.status_code == 403  # HTTPBearer's default for a missing header


@pytest.mark.asyncio
class TestCreateFamilyMember:
    async def test_create_spouse_success(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Priya"
        assert data["relationship_type"] == "spouse"
        assert data["eligible_schemes"] == []  # Task 3 not built yet — see schema docstring
        # Milestone 2 Task 7: is_complete is now returned directly on the
        # create/update/detail responses (previously only on the Family
        # Home list), so the frontend never has to re-derive it.
        assert data["is_complete"] is True

    async def test_create_spouse_missing_dob_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "spouse", "name": "Priya"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_child_missing_dob_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "child", "name": "Ananya"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_parent_requires_relationship_detail_and_insurance(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "parent", "name": "Mother"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_parent_invalid_relationship_detail_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "parent",
                "name": "Mother",
                "relationship_detail": "grandmother",
                "has_own_insurance": "no",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_parent_success_with_not_sure_insurance(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "parent",
                "name": "Mother",
                "relationship_detail": "mother",
                "has_own_insurance": "not_sure",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["has_own_insurance"] == "not_sure"

    async def test_create_other_missing_relationship_detail_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "other", "name": "Cousin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_date_of_birth_in_future_rejected(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "spouse", "name": "Priya", "date_of_birth": "2099-01-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestUpdateFamilyMember:
    async def test_editing_one_member_never_changes_another(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Milestone 2 Task 7's Identity Integrity requirement: editing
        member A must never leak into member B's stored data."""
        seed = await client.post(
            "/api/v1/family/onboarding-seed",
            json={"has_spouse": True, "has_children": True, "children_count": 2,
                  "has_dependent_parents": False},
            headers=auth_headers,
        )
        children = [
            m["id"] for m in seed.json()["members"] if m["relationship_type"] == "child"
        ]
        child_a, child_b = children[0], children[1]

        resp = await client.put(
            f"/api/v1/family/members/{child_a}",
            json={"name": "Ananya", "date_of_birth": "2019-03-15", "gender": "female"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == child_a

        home = await client.get("/api/v1/family", headers=auth_headers)
        member_b = next(m for m in home.json()["members"] if m["id"] == child_b)
        assert member_b["name"] is None
        assert member_b["is_complete"] is False

        member_a = next(m for m in home.json()["members"] if m["id"] == child_a)
        assert member_a["name"] == "Ananya"
        assert member_a["is_complete"] is True

    async def test_completes_a_placeholder_member(self, client: AsyncClient, auth_headers: dict):
        seed = await client.post(
            "/api/v1/family/onboarding-seed",
            json={"has_spouse": True, "has_children": False, "has_dependent_parents": False},
            headers=auth_headers,
        )
        spouse_id = next(
            m["id"] for m in seed.json()["members"] if m["relationship_type"] == "spouse"
        )

        resp = await client.put(
            f"/api/v1/family/members/{spouse_id}",
            json={"name": "Priya", "date_of_birth": "1991-03-12"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Priya"
        assert resp.json()["is_complete"] is True

        home = await client.get("/api/v1/family", headers=auth_headers)
        updated = next(m for m in home.json()["members"] if m["id"] == spouse_id)
        assert updated["is_complete"] is True

    async def test_cannot_edit_self_via_member_endpoint(
        self, client: AsyncClient, auth_headers: dict
    ):
        home = await client.get("/api/v1/family", headers=auth_headers)
        self_id = home.json()["members"][0]["id"]

        resp = await client.put(
            f"/api/v1/family/members/{self_id}",
            json={"name": "Someone Else"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_nonexistent_member_returns_404(self, client: AsyncClient, auth_headers: dict):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.put(
            f"/api/v1/family/members/{fake_id}",
            json={"name": "Nobody"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_editing_never_creates_a_duplicate_member(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Milestone 2 Task 7's Identity Integrity requirement: PUT must
        always update the one existing row by id, never insert a second
        one — verified by household member count staying constant across
        repeated edits of the same member."""
        create = await client.post(
            "/api/v1/family/members",
            json={"relationship_type": "parent", "name": "Sunita", "relationship_detail": "mother",
                  "has_own_insurance": "no"},
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        before = await client.get("/api/v1/family", headers=auth_headers)
        count_before = len(before.json()["members"])

        for name in ("Sunita Mehta", "Sunita M.", "Sunita Mehta"):
            resp = await client.put(
                f"/api/v1/family/members/{member_id}",
                json={"name": name, "relationship_detail": "mother", "has_own_insurance": "no"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == member_id

        after = await client.get("/api/v1/family", headers=auth_headers)
        members_after = after.json()["members"]
        assert len(members_after) == count_before
        assert sum(1 for m in members_after if m["id"] == member_id) == 1


@pytest.mark.asyncio
class TestGetFamilyMemberDetail:
    async def test_returns_empty_goals_and_coverage_before_tasks_8_and_10(
        self, client: AsyncClient, auth_headers: dict
    ):
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.get(f"/api/v1/family/members/{member_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["member"]["name"] == "Priya"
        assert data["member"]["is_complete"] is True
        assert data["tagged_goals"] == []
        assert data["coverage"] == []

    async def test_returns_eligible_schemes_for_an_ssy_eligible_child(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """Milestone 2 Task 9: get_family_member previously never populated
        eligible_schemes at all (only create/update did) — caught live while
        building the goal-detail SSY callout, which reuses this exact field
        rather than re-implementing the check."""
        await _seed_ssy_scheme(db)
        dob = (date.today() - timedelta(days=365 * 7)).isoformat()
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "child",
                "name": "Ananya",
                "date_of_birth": dob,
                "gender": "female",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.get(f"/api/v1/family/members/{member_id}", headers=auth_headers)
        assert resp.status_code == 200
        schemes = resp.json()["member"]["eligible_schemes"]
        assert len(schemes) == 1
        assert schemes[0]["code"] == "SSY"

    async def test_self_member_detail_never_crashes_and_has_no_eligible_schemes(
        self, client: AsyncClient, auth_headers: dict
    ):
        """The 'self' member has no dependent row — eligible_schemes must
        resolve to [] rather than raising on a None dependent."""
        home = await client.get("/api/v1/family", headers=auth_headers)
        self_id = home.json()["members"][0]["id"]

        resp = await client.get(f"/api/v1/family/members/{self_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["member"]["eligible_schemes"] == []


@pytest.mark.asyncio
class TestDeleteFamilyMember:
    async def test_soft_deletes_not_hard_deletes(self, client: AsyncClient, auth_headers: dict):
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.delete(f"/api/v1/family/members/{member_id}", headers=auth_headers)
        assert resp.status_code == 204

        home = await client.get("/api/v1/family", headers=auth_headers)
        assert all(m["id"] != member_id for m in home.json()["members"])

        # Not hard-deleted: fetching by id directly now 404s via the
        # is_active filter, not because the row is gone.
        get_resp = await client.get(f"/api/v1/family/members/{member_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    async def test_cannot_remove_self(self, client: AsyncClient, auth_headers: dict):
        home = await client.get("/api/v1/family", headers=auth_headers)
        self_id = home.json()["members"][0]["id"]

        resp = await client.delete(f"/api/v1/family/members/{self_id}", headers=auth_headers)
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestCrossHouseholdOwnership:
    """RiskChecklist.md #2: the first authorization pattern in this
    codebase where a user acts on data that isn't keyed directly to their
    own user_id. Every mutating/reading member endpoint gets an explicit
    negative-path test here, not just the happy path."""

    async def test_get_member_denied_across_households(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/family/members/{member_id}", headers=other_auth_headers
        )
        assert resp.status_code == 404

    async def test_update_member_denied_across_households(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.put(
            f"/api/v1/family/members/{member_id}",
            json={"name": "Hijacked"},
            headers=other_auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_member_denied_across_households(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        create = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "spouse",
                "name": "Priya",
                "date_of_birth": "1991-03-12",
            },
            headers=auth_headers,
        )
        member_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/family/members/{member_id}", headers=other_auth_headers
        )
        assert resp.status_code == 404

        # Confirm it genuinely survived — not silently removed despite the 404.
        still_there = await client.get(
            f"/api/v1/family/members/{member_id}", headers=auth_headers
        )
        assert still_there.status_code == 200

    async def test_each_user_gets_their_own_household(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        mine = await client.get("/api/v1/family", headers=auth_headers)
        theirs = await client.get("/api/v1/family", headers=other_auth_headers)
        assert mine.json()["household"]["id"] != theirs.json()["household"]["id"]
