"""REST API layer for the Life Event Engine (LifeEventAPI_ImplementationReport.md).

Covers every endpoint (`POST /life-events`, `GET /life-events`,
`GET /life-events/{id}`, `POST /life-events/{id}/undo`,
`POST /life-events/preview`) against the real, unmodified engine and real
handlers (Bonus/Salary Raise/House Purchase) — no mocking. Router tests
only: the engine's own generic-undo/rollback/notification behavior is
already exhaustively covered by `test_life_event_service.py` and each
event's own `test_<event>_handler.py` suite; these tests exist to prove
the HTTP layer wires into that already-correct engine properly, not to
re-prove the engine itself.
"""

import asyncio
import uuid
from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import Asset
from app.models.user import User

# ── POST /life-events ───────────────────────────────────────────────────────


class TestCreateLifeEvent:
    async def test_records_a_bonus_and_returns_the_event_effects_and_audit_reference(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/life-events",
            json={
                "event_type": "bonus",
                "occurred_on": "2026-06-01",
                "inputs": {"amount": 5000.0},
            },
            headers=auth_headers,
        )

        assert resp.status_code == 201
        body = resp.json()
        life_event = body["life_event"]
        assert life_event["event_type"] == "bonus"
        assert life_event["status"] == "applied"
        assert life_event["occurred_on"] == "2026-06-01"
        assert len(life_event["effects"]) == 1
        assert life_event["effects"][0]["entity_table"] == "assets"
        assert life_event["effects"][0]["change_type"] == "create"
        assert life_event["effects"][0]["after_state"]["current_value"] == 5000.0
        assert life_event["audit_action"] == "life_event_recorded"
        assert "id" in life_event
        # audit_reference is the AuditLog row's own id, distinct from the
        # life event's own id.
        assert body["audit_reference"] != life_event["id"]

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
        )
        assert resp.status_code == 403

    async def test_unsupported_event_type_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "not_a_real_event", "occurred_on": "2026-06-01", "inputs": {}},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "not_a_real_event" in resp.json()["detail"]

    async def test_invalid_payload_missing_required_field_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        # Bonus requires "amount" — omitting it raises KeyError inside the
        # handler, which the router translates to 422 rather than a 500.
        resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {}},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "bonus" in resp.json()["detail"]

    async def test_handler_owned_404_propagates_unchanged(
        self, client: AsyncClient, auth_headers: dict
    ):
        # House Purchase's optional down-payment step references an asset
        # id that must exist and be owned by the caller — a handler-raised
        # HTTPException(404), not a KeyError/ValueError, so it must pass
        # through the router's exception translation untouched.
        from uuid import uuid4

        resp = await client.post(
            "/api/v1/life-events",
            json={
                "event_type": "house_purchase",
                "occurred_on": "2026-06-01",
                "inputs": {
                    "property_value": 400000.0,
                    "mortgage_balance": 320000.0,
                    "down_payment_asset_id": str(uuid4()),
                    "down_payment_amount": 20000.0,
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
        # Atomicity itself (a failed compound event leaves nothing durable)
        # is already exhaustively proven per-handler (e.g.
        # test_house_purchase_handler.py::TestRollback) against the real
        # get_db() rollback-on-exception path; re-proving it here would
        # require the test client's dependency override to replicate that
        # rollback behavior, which it deliberately doesn't (see
        # conftest.py's override_get_db). What *is* new and worth
        # asserting here: this router adds zero db.commit()/db.rollback()
        # calls of its own — confirmed directly by inspection of
        # app/routers/life_events.py, not by a test that would only be
        # testing the test harness.


# ── GET /life-events ─────────────────────────────────────────────────────────


class TestListLifeEvents:
    async def test_returns_newest_first_with_pagination_metadata(
        self, client: AsyncClient, auth_headers: dict
    ):
        for amount in (1000.0, 2000.0, 3000.0):
            await client.post(
                "/api/v1/life-events",
                json={
                    "event_type": "bonus",
                    "occurred_on": "2026-06-01",
                    "inputs": {"amount": amount},
                },
                headers=auth_headers,
            )
            # SQLite's server_default=func.now() only has second-level
            # resolution in this test DB (unlike Postgres's microsecond
            # precision in production — test_life_event_service.py's own
            # ordering test documents and works around the same thing). A
            # real delay guarantees each event's recorded_at is distinct,
            # so "newest first" isn't a coin flip on tied timestamps.
            await asyncio.sleep(1.1)

        resp = await client.get("/api/v1/life-events", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["limit"] == 20
        assert body["offset"] == 0
        amounts = [item["effects"][0]["after_state"]["current_value"] for item in body["items"]]
        assert amounts == [3000.0, 2000.0, 1000.0]  # newest first

    async def test_limit_and_offset(self, client: AsyncClient, auth_headers: dict):
        for i in range(5):
            await client.post(
                "/api/v1/life-events",
                json={
                    "event_type": "bonus",
                    "occurred_on": "2026-06-01",
                    "inputs": {"amount": float(i)},
                },
                headers=auth_headers,
            )

        resp = await client.get(
            "/api/v1/life-events", params={"limit": 2, "offset": 2}, headers=auth_headers
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["limit"] == 2
        assert body["offset"] == 2

    async def test_filters_by_event_type(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/life-events",
            json={
                "event_type": "education_planning",
                "occurred_on": "2026-06-01",
                "inputs": {
                    "name": "College Fund",
                    "target_amount": 50000.0,
                    "target_date": (date.today() + timedelta(days=365 * 10)).isoformat(),
                },
            },
            headers=auth_headers,
        )

        resp = await client.get(
            "/api/v1/life-events", params={"event_type": "bonus"}, headers=auth_headers
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["event_type"] == "bonus"

    async def test_filters_by_date_range(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2020-01-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 2.0}},
            headers=auth_headers,
        )

        resp = await client.get(
            "/api/v1/life-events",
            params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
            headers=auth_headers,
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["occurred_on"] == "2026-06-01"

    async def test_only_returns_the_authenticated_users_own_events(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/life-events", headers=other_auth_headers)
        assert resp.json()["total"] == 0

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/api/v1/life-events")
        assert resp.status_code == 403


# ── GET /life-events/{id} ────────────────────────────────────────────────────


class TestGetLifeEvent:
    async def test_returns_the_event_with_effects_and_audit_metadata(
        self, client: AsyncClient, auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 42.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]

        resp = await client.get(f"/api/v1/life-events/{life_event_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == life_event_id
        assert body["audit_action"] == "life_event_recorded"
        assert len(body["effects"]) == 1

    async def test_nonexistent_id_returns_404(self, client: AsyncClient, auth_headers: dict):
        from uuid import uuid4

        resp = await client.get(f"/api/v1/life-events/{uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_another_users_event_returns_404_not_403(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]

        resp = await client.get(f"/api/v1/life-events/{life_event_id}", headers=other_auth_headers)
        assert resp.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient):
        from uuid import uuid4

        resp = await client.get(f"/api/v1/life-events/{uuid4()}")
        assert resp.status_code == 403


# ── POST /life-events/{id}/undo ──────────────────────────────────────────────


class TestUndoLifeEvent:
    async def test_clean_undo_returns_200_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]

        resp = await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"success": True, "blocked": False, "conflicts": []}

    async def test_blocked_undo_returns_409_with_conflicts(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1000.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]
        asset_id = uuid.UUID(create_resp.json()["life_event"]["effects"][0]["entity_id"])

        # Independently change the created asset after the event, via
        # ordinary Financials-shaped mutation — this is what should block
        # a clean undo.
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one()
        asset.current_value = 999999.0
        db.add(asset)
        await db.flush()

        resp = await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={}, headers=auth_headers
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["success"] is False
        assert body["blocked"] is True
        assert len(body["conflicts"]) == 1
        assert body["conflicts"][0]["entity_table"] == "assets"

    async def test_force_undo_overrides_a_conflict(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 500.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]
        asset_id = uuid.UUID(create_resp.json()["life_event"]["effects"][0]["entity_id"])

        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one()
        asset.current_value = 12345.0
        db.add(asset)
        await db.flush()

        resp = await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={"force": True}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_undoing_an_already_undone_event_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]

        await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={}, headers=auth_headers
        )
        resp = await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={}, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_nonexistent_event_returns_404(self, client: AsyncClient, auth_headers: dict):
        from uuid import uuid4

        resp = await client.post(
            f"/api/v1/life-events/{uuid4()}/undo", json={}, headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_another_users_event_returns_404_not_403(
        self, client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        create_resp = await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )
        life_event_id = create_resp.json()["life_event"]["id"]

        resp = await client.post(
            f"/api/v1/life-events/{life_event_id}/undo", json={}, headers=other_auth_headers
        )
        assert resp.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient):
        from uuid import uuid4

        resp = await client.post(f"/api/v1/life-events/{uuid4()}/undo", json={})
        assert resp.status_code == 403


# ── POST /life-events/preview ────────────────────────────────────────────────


class TestPreviewLifeEvent:
    async def test_preview_returns_predicted_effects_without_writing_anything(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        resp = await client.post(
            "/api/v1/life-events/preview",
            json={"event_type": "bonus", "inputs": {"amount": 7500.0}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_type"] == "bonus"
        assert len(body["effects"]) == 1
        assert body["effects"][0]["after_state"]["current_value"] == 7500.0
        assert body["affected_entities"] == ["assets"]
        assert body["validation_errors"] == []

        # Dry-run only — no Asset row actually exists afterward.
        result = await db.execute(select(Asset).where(Asset.user_id == user.id))
        assert result.scalars().all() == []

    async def test_preview_does_not_disturb_a_pending_life_events_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            "/api/v1/life-events",
            json={"event_type": "bonus", "occurred_on": "2026-06-01", "inputs": {"amount": 1.0}},
            headers=auth_headers,
        )

        await client.post(
            "/api/v1/life-events/preview",
            json={"event_type": "bonus", "inputs": {"amount": 999.0}},
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/life-events", headers=auth_headers)
        assert resp.json()["total"] == 1  # the preview never became a second event

    async def test_unsupported_event_type_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/life-events/preview",
            json={"event_type": "not_a_real_event", "inputs": {}},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_invalid_payload_returns_200_with_validation_errors_not_an_http_error(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/life-events/preview",
            json={"event_type": "bonus", "inputs": {}},  # missing required "amount"
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["effects"] == []
        assert body["affected_entities"] == []
        assert len(body["validation_errors"]) == 1

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/life-events/preview", json={"event_type": "bonus", "inputs": {}}
        )
        assert resp.status_code == 403
