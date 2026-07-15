"""Integration tests for Phase 3 (Notification Center):
GET /api/v1/notifications, POST /api/v1/notifications/{source}/{key}/read,
POST /api/v1/notifications/{source}/{key}/dismiss.

Centered on ArchitectureReview_Phase3.md's two guarantees: notifications are
never a second recommendation engine (content always read live), and no GET
request ever mutates state (NotificationMarker rows are created only by the
explicit read/dismiss endpoints).
"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import Liability
from app.models.notification import NotificationMarker
from app.models.policy import TaxAct, TaxSection
from app.models.user import User
from app.services import life_event_service

AT_RISK_GOAL = {
    "name": "Impossible Goal",
    "category": "retirement",
    "target_amount": 100_000_000,
    "current_amount": 0,
    "target_date": (date.today() + timedelta(days=365)).isoformat(),
    "monthly_contribution": 1,
    "risk_profile": "conservative",
    "priority": 1,
}

COMPLETED_GOAL = {
    "name": "Already There",
    "category": "emergency",
    "target_amount": 10_000,
    "current_amount": 10_000,
    "target_date": (date.today() + timedelta(days=365 * 5)).isoformat(),
    "monthly_contribution": 100,
    "risk_profile": "balanced",
    "priority": 1,
}


async def _seed_80d_tax_section(db: AsyncSession) -> None:
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


@pytest.mark.asyncio
class TestNotificationSources:
    async def test_empty_household_has_no_notifications(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["unread_count"] == 0

    async def test_family_member_added_appears_as_notification(
        self, client: AsyncClient, auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "child",
                "name": "Aarav",
                "date_of_birth": (date.today() - timedelta(days=365 * 8)).isoformat(),
                "is_tax_dependent": True,
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        assert any(i["source"] == "family_member_added" and "Aarav" in i["title"] for i in items)

    async def test_goal_at_risk_appears_as_notification(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        at_risk = [i for i in items if i["source"] == "goal_at_risk"]
        assert len(at_risk) == 1
        assert "Impossible Goal" in at_risk[0]["title"]

    async def test_goal_completed_appears_as_notification_not_at_risk(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/v1/goals", json=COMPLETED_GOAL, headers=auth_headers)
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        assert any(i["source"] == "goal_completed" and "Already There" in i["title"] for i in items)
        assert not any(i["source"] == "goal_at_risk" for i in items)

    async def test_insurance_recommendation_appears_as_notification(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        await _seed_80d_tax_section(db)
        create_resp = await client.post(
            "/api/v1/family/members",
            json={
                "relationship_type": "parent",
                "name": "Sunita",
                "relationship_detail": "mother",
                "has_own_insurance": "no",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        assert any(i["source"] == "insurance" for i in items)

    async def test_life_event_appears_as_notification(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        """The generic Life Event Engine collector (notification_service.
        _collect_life_event_facts, LifeEventEngineArchitecture.md §6) —
        no router exists yet to record an event over HTTP, so the event is
        recorded directly through the same engine a future endpoint would
        call; the notification read itself goes through the real HTTP
        endpoint like every other test in this file."""
        liability = Liability(
            user_id=user.id,
            liability_type="credit_card",
            balance=500.0,
            interest_rate=0.19,
        )
        db.add(liability)
        await db.flush()
        await life_event_service.record_life_event(
            db,
            user,
            event_type="loan_payoff",
            occurred_on=date.today(),
            inputs={"liability_id": str(liability.id)},
        )

        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        items = resp.json()["items"]
        life_event_items = [i for i in items if i["source"] == "life_event"]
        assert len(life_event_items) == 1
        assert life_event_items[0]["title"] == "✓ Debt paid off"
        assert life_event_items[0]["action_path"] == "/app/life-events"

    async def test_all_new_notifications_start_unread(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        resp = await client.get("/api/v1/notifications", headers=auth_headers)
        body = resp.json()
        assert body["unread_count"] == len(body["items"])
        assert all(i["state"] == "unread" for i in body["items"])


@pytest.mark.asyncio
class TestReadDismissAndPurity:
    async def test_get_notifications_never_creates_a_marker_row(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        """ArchitectureReview_Phase3.md's read/write discipline: GET must
        never write, even to record 'first seen'."""
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        for _ in range(3):
            await client.get("/api/v1/notifications", headers=auth_headers)
        result = await db.execute(select(NotificationMarker))
        assert result.scalars().all() == []

    async def test_mark_read_updates_state_and_unread_count(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        first = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
        item = first["items"][0]

        mark_resp = await client.post(
            f"/api/v1/notifications/{item['source']}/{item['id']}/read", headers=auth_headers
        )
        assert mark_resp.status_code == 204

        second = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
        updated = next(i for i in second["items"] if i["id"] == item["id"])
        assert updated["state"] == "read"
        assert second["unread_count"] == first["unread_count"] - 1

    async def test_dismiss_removes_notification_from_default_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        first = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
        item = first["items"][0]

        dismiss_resp = await client.post(
            f"/api/v1/notifications/{item['source']}/{item['id']}/dismiss", headers=auth_headers
        )
        assert dismiss_resp.status_code == 204

        second = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
        assert all(i["id"] != item["id"] for i in second["items"])

    async def test_dismissing_a_fact_that_still_exists_does_not_bring_it_back(
        self, client: AsyncClient, auth_headers: dict
    ):
        """A dismissed, still-true fact must not reappear just because the
        household state that produced it hasn't changed."""
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        first = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
        item = next(i for i in first["items"] if i["source"] == "goal_at_risk")
        await client.post(
            f"/api/v1/notifications/{item['source']}/{item['id']}/dismiss", headers=auth_headers
        )
        for _ in range(3):
            again = (await client.get("/api/v1/notifications", headers=auth_headers)).json()
            assert not any(i["source"] == "goal_at_risk" for i in again["items"])

    async def test_notifications_are_scoped_to_the_requesting_user(
        self,
        client: AsyncClient,
        auth_headers: dict,
        other_auth_headers: dict,
    ):
        await client.post("/api/v1/goals", json=AT_RISK_GOAL, headers=auth_headers)
        other_resp = await client.get("/api/v1/notifications", headers=other_auth_headers)
        assert other_resp.json()["items"] == []
