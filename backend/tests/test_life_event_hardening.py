"""Life Event Engine hardening (LifeEventEngine_BackendHardeningReport.md).

Proves the three HIGH findings `LifeEventEngine_FinalReleaseAudit.md` left
open are actually closed:

1. Idempotency — a duplicate `record_life_event`/`POST /life-events` call
   with the same `idempotency_key` is harmless (no re-run, no duplicate
   row), including the genuine flush-time race between two independent
   connections (`TestIdempotencyRace`).
2. Undo conflict detection — the exact gap the audit named in §1.3: an
   older event's own `after_state` never included a field a *later*,
   different event changed on the same row, so the pre-hardening
   field-scoped check alone would have missed it. `after_updated_at`'s
   row-level fingerprint now catches it (`TestUndoRowFingerprint`).
3. Concurrency protection — `.with_for_update()` is actually present (a
   structural, dialect-independent proof: SQLite's own compiler silently
   drops the `FOR UPDATE` clause at render time, so asserting on rendered
   SQL text would be a false negative on this test backend; the check
   instead inspects the SQLAlchemy Core construct itself,
   `_for_update_arg`, which is set identically regardless of dialect —
   `TestConcurrencyProtection`).

`TestIdempotencyRace` deliberately does not use the shared `db` fixture:
that fixture's engine binds every session to a single `StaticPool`
connection (verified directly against this project's own test setup), so
two sessions from it always share one physical connection and can never
have one committed independently of the other — there is no way to build
a genuine "two requests, one already durably committed" race on it. This
test opens its own temp-file SQLite database with two independent
sessions instead, which is the minimum needed to reproduce that race
honestly.
"""

import asyncio
import tempfile
import uuid
from datetime import date
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.financials import Asset
from app.models.goal import Goal
from app.models.user import User
from app.services import financials_service, life_event_service
from app.services.auth_service import hash_password
from app.services.life_event_service import EntityEffect

_TEST_CREATE_GOAL = "hardening_test_create_goal"
_TEST_UPDATE_GOAL_AMOUNT = "hardening_test_update_goal_amount"
_TEST_RENAME_GOAL = "hardening_test_rename_goal"


class _CreateGoalHandler:
    async def apply(self, db: AsyncSession, user: User, inputs: dict) -> list[EntityEffect]:
        goal = Goal(
            user_id=user.id,
            name=inputs.get("name", "Test Goal"),
            category="wealth",
            target_amount=inputs.get("target_amount", 50_000.0),
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()
        return [
            EntityEffect(
                entity_table="goals",
                entity_id=goal.id,
                change_type="create",
                before_state=None,
                after_state=life_event_service.snapshot(goal, ["name", "target_amount"]),
            )
        ]


class _UpdateGoalAmountHandler:
    """Touches only `target_amount` — its own `after_state` never mentions
    `name`, which is exactly the gap `TestUndoRowFingerprint` exploits."""

    async def apply(self, db: AsyncSession, user: User, inputs: dict) -> list[EntityEffect]:
        goal = await db.get(Goal, uuid.UUID(inputs["goal_id"]))
        assert goal is not None
        before = life_event_service.snapshot(goal, ["target_amount"])
        goal.target_amount = inputs["new_target_amount"]
        db.add(goal)
        await db.flush()
        return [
            EntityEffect(
                entity_table="goals",
                entity_id=goal.id,
                change_type="update",
                before_state=before,
                after_state=life_event_service.snapshot(goal, ["target_amount"]),
            )
        ]


class _RenameGoalHandler:
    """Touches only `name` — a second, later, unrelated event on the same
    row, modeling the audit's own scenario exactly."""

    async def apply(self, db: AsyncSession, user: User, inputs: dict) -> list[EntityEffect]:
        goal = await db.get(Goal, uuid.UUID(inputs["goal_id"]))
        assert goal is not None
        before = life_event_service.snapshot(goal, ["name"])
        goal.name = inputs["new_name"]
        db.add(goal)
        await db.flush()
        return [
            EntityEffect(
                entity_table="goals",
                entity_id=goal.id,
                change_type="update",
                before_state=before,
                after_state=life_event_service.snapshot(goal, ["name"]),
            )
        ]


@pytest.fixture(autouse=True)
def _clean_handler_registry():
    before = life_event_service.registered_event_types()
    yield
    for event_type in life_event_service.registered_event_types():
        if event_type not in before:
            life_event_service.unregister_handler(event_type)


# ── 1a. Idempotency — sequential duplicate (service layer) ─────────────────


class TestIdempotencySequential:
    async def test_duplicate_key_returns_the_same_event_and_never_reruns_the_handler(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        first = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date.today(),
            inputs={"name": "Original"},
            idempotency_key="retry-token-1",
        )
        second = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date.today(),
            inputs={"name": "Should never be created"},
            idempotency_key="retry-token-1",
        )

        assert second.id == first.id
        assert second.inputs == {"name": "Original"}  # the replay, not the resend

        goals = (await db.execute(select(Goal).where(Goal.user_id == user.id))).scalars().all()
        assert len(goals) == 1
        assert goals[0].name == "Original"

    async def test_different_keys_record_two_independent_events(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        first = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date.today(),
            inputs={"name": "A"},
            idempotency_key="token-a",
        )
        second = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date.today(),
            inputs={"name": "B"},
            idempotency_key="token-b",
        )

        assert first.id != second.id
        goals = (await db.execute(select(Goal).where(Goal.user_id == user.id))).scalars().all()
        assert {g.name for g in goals} == {"A", "B"}

    async def test_omitting_the_key_is_fully_backward_compatible(
        self, db: AsyncSession, user: User
    ):
        """No `idempotency_key` at all (every pre-hardening caller) still
        records two separate events for two separate calls — the new
        column is additive, never a behavior change for existing callers."""
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        first = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={"name": "A"}
        )
        second = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={"name": "B"}
        )
        assert first.id != second.id


# ── 1b. Idempotency — sequential duplicate (HTTP layer) ────────────────────


class TestIdempotencyRouter:
    async def test_duplicate_post_with_the_same_key_returns_the_same_event_id(
        self, client: AsyncClient, auth_headers: dict, db: AsyncSession, user: User
    ):
        payload = {
            "event_type": "bonus",
            "occurred_on": "2026-06-01",
            "inputs": {"amount": 5000.0},
            "idempotency_key": "double-click-guard",
        }

        first_resp = await client.post(
            "/api/v1/life-events", json=payload, headers=auth_headers
        )
        second_resp = await client.post(
            "/api/v1/life-events", json=payload, headers=auth_headers
        )

        assert first_resp.status_code == 201
        assert second_resp.status_code == 201
        first_id = first_resp.json()["life_event"]["id"]
        second_id = second_resp.json()["life_event"]["id"]
        assert first_id == second_id
        # Same audit_reference too — the replay reports the original
        # recording's own audit row, not a fresh one.
        assert first_resp.json()["audit_reference"] == second_resp.json()["audit_reference"]

        assets = (
            (await db.execute(select(Asset).where(Asset.user_id == user.id))).scalars().all()
        )
        assert len(assets) == 1


# ── 1c. Idempotency — genuine flush-time race (two independent connections) ─


async def _make_isolated_engine_and_users() -> tuple:
    """A dedicated temp-file SQLite database with its own engine/schema —
    see this module's own docstring for why the shared `db` fixture cannot
    host a genuine two-connection race."""
    tmp_path = Path(tempfile.mkstemp(suffix=".db")[1])
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}")
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as setup_session:
        racer = User(
            email="racer@example.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Racer",
            is_active=True,
        )
        setup_session.add(racer)
        await setup_session.commit()
        await setup_session.refresh(racer)

    return engine, session_factory, racer, tmp_path


class TestIdempotencyRace:
    async def test_a_flush_time_collision_recovers_the_already_committed_winner(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Reproduces the exact window `record_life_event`'s IntegrityError
        recovery targets: request A's pre-check (`_get_by_idempotency_key`)
        misses because request B's row is not yet committed, but by the
        time A flushes its own insert, B has already committed — A must
        discard its own attempt (including whatever its handler already
        wrote) and return B's event, not raise or create a duplicate."""
        engine, session_factory, racer, tmp_path = await _make_isolated_engine_and_users()
        try:
            life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

            async with session_factory() as session_b:
                winner = await life_event_service.record_life_event(
                    session_b,
                    racer,
                    event_type=_TEST_CREATE_GOAL,
                    occurred_on=date.today(),
                    inputs={"name": "Winner (already committed)"},
                    idempotency_key="race-key",
                )
                await session_b.commit()
                winner_id = winner.id

            # Session A's pre-check is forced to miss once — simulating a
            # request that started before B's commit was visible to it —
            # then falls through to the real lookup for every other call
            # (including the recovery lookup inside the except block).
            real_lookup = life_event_service._get_by_idempotency_key
            pre_check_done = False

            async def _miss_once_then_real(db_, user_, key_):
                nonlocal pre_check_done
                if not pre_check_done:
                    pre_check_done = True
                    return None
                return await real_lookup(db_, user_, key_)

            monkeypatch.setattr(
                life_event_service, "_get_by_idempotency_key", _miss_once_then_real
            )

            async with session_factory() as session_a:
                loser = await life_event_service.record_life_event(
                    session_a,
                    racer,
                    event_type=_TEST_CREATE_GOAL,
                    occurred_on=date.today(),
                    inputs={"name": "Loser (should never survive)"},
                    idempotency_key="race-key",
                )

            assert loser.id == winner_id

            async with session_factory() as verify:
                goals = (
                    (await verify.execute(select(Goal).where(Goal.user_id == racer.id)))
                    .scalars()
                    .all()
                )
                assert len(goals) == 1
                assert goals[0].name == "Winner (already committed)"

                events = (
                    (await verify.execute(select(life_event_service.LifeEvent)))
                    .scalars()
                    .all()
                )
                assert len(events) == 1
        finally:
            await engine.dispose()
            tmp_path.unlink(missing_ok=True)


# ── 2. Undo conflict detection — the row-fingerprint gap the audit found ───


class TestUndoRowFingerprint:
    async def test_undo_is_blocked_when_a_later_event_changes_a_different_field(
        self, db: AsyncSession, user: User
    ):
        """LifeEventEngine_FinalReleaseAudit.md §1.3's exact scenario: event
        A only ever recorded `target_amount` in its own after_state, so a
        purely field-scoped conflict check has nothing to compare against
        event B's change to `name` — it would report "no conflict" even
        though the row is no longer in the state event A left it in. The
        new `after_updated_at` row fingerprint (bumped by *any* column
        change) closes exactly this gap."""
        goal = Goal(
            user_id=user.id,
            name="Original Name",
            category="wealth",
            target_amount=100_000.0,
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()

        life_event_service.register_handler(_TEST_UPDATE_GOAL_AMOUNT, _UpdateGoalAmountHandler())
        life_event_service.register_handler(_TEST_RENAME_GOAL, _RenameGoalHandler())

        event_a = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_UPDATE_GOAL_AMOUNT,
            occurred_on=date(2026, 1, 1),
            inputs={"goal_id": str(goal.id), "new_target_amount": 150_000.0},
        )
        # event_a's own after_state is {"target_amount": 150000.0} only —
        # it says nothing about `name`.
        assert "name" not in event_a.effects[0].after_state

        await asyncio.sleep(1.1)  # SQLite's func.now() is second-resolution
        await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_RENAME_GOAL,
            occurred_on=date(2026, 2, 1),
            inputs={"goal_id": str(goal.id), "new_name": "Renamed by a later, unrelated event"},
        )

        result = await life_event_service.undo_life_event(db, user, event_a.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_id == goal.id
        assert result.conflicts[0].reason == "Row has changed since this event was recorded"

        # Untouched: the blocked undo did not revert target_amount.
        await db.refresh(goal)
        assert goal.target_amount == 150_000.0
        assert goal.name == "Renamed by a later, unrelated event"

    async def test_undo_still_succeeds_when_truly_nothing_changed(
        self, db: AsyncSession, user: User
    ):
        """Negative control: the new fingerprint must not over-block a
        clean undo when no interim change of any kind occurred."""
        goal = Goal(
            user_id=user.id,
            name="Untouched Goal",
            category="wealth",
            target_amount=100_000.0,
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()

        life_event_service.register_handler(_TEST_UPDATE_GOAL_AMOUNT, _UpdateGoalAmountHandler())
        event_a = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_UPDATE_GOAL_AMOUNT,
            occurred_on=date.today(),
            inputs={"goal_id": str(goal.id), "new_target_amount": 150_000.0},
        )

        result = await life_event_service.undo_life_event(db, user, event_a.id)

        assert result.blocked is False
        await db.refresh(goal)
        assert goal.target_amount == 100_000.0


# ── 3. Concurrency protection — with_for_update() is actually requested ────


class TestConcurrencyProtection:
    async def test_adjust_asset_value_requests_a_row_lock(
        self, db: AsyncSession, user: User
    ):
        """Structural proof, not a rendered-SQL-text check: SQLite's own
        compiler silently drops `FOR UPDATE` when rendering (confirmed
        separately — it is not an error, just a no-op on this backend), so
        asserting on compiled SQL would falsely report "no lock" on the
        very backend this whole test suite runs against. Inspecting
        `_for_update_arg` on the actual `Select` construct SQLAlchemy
        builds is dialect-independent: it is set identically whether the
        underlying database honors it (Postgres, production) or silently
        ignores it (SQLite, here)."""
        asset = Asset(user_id=user.id, asset_type="savings", current_value=1_000.0)
        db.add(asset)
        await db.flush()

        locked_selects = []

        def _capture(conn, clauseelement, *args, **kwargs):
            if getattr(clauseelement, "_for_update_arg", None) is not None:
                locked_selects.append(clauseelement)

        sync_engine = db.bind.sync_engine  # type: ignore[union-attr]
        event.listen(sync_engine, "before_execute", _capture)
        try:
            await financials_service.adjust_asset_value(db, user, asset.id, 500.0)
        finally:
            event.remove(sync_engine, "before_execute", _capture)

        assert len(locked_selects) == 1

    async def test_undo_loads_each_touched_row_with_a_row_lock(
        self, db: AsyncSession, user: User
    ):
        goal = Goal(
            user_id=user.id,
            name="Locked on undo",
            category="wealth",
            target_amount=1.0,
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()

        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )

        locked_selects = []

        def _capture(conn, clauseelement, *args, **kwargs):
            if getattr(clauseelement, "_for_update_arg", None) is not None:
                locked_selects.append(clauseelement)

        sync_engine = db.bind.sync_engine  # type: ignore[union-attr]
        event.listen(sync_engine, "before_execute", _capture)
        try:
            await life_event_service.undo_life_event(db, user, life_event.id)
        finally:
            event.remove(sync_engine, "before_execute", _capture)

        assert len(locked_selects) >= 1

    async def test_sequential_adjustments_never_lose_a_delta(
        self, db: AsyncSession, user: User
    ):
        """Not a race test (see this module's docstring for why a true
        interleaved-transaction race cannot be built on this project's
        shared-connection SQLite test fixture) — this proves the
        read-modify-write arithmetic `.with_for_update()` protects is
        itself correct, so the lock is guarding a genuinely correct
        critical section rather than papering over a broken one."""
        asset = Asset(user_id=user.id, asset_type="savings", current_value=1_000.0)
        db.add(asset)
        await db.flush()

        await financials_service.adjust_asset_value(db, user, asset.id, 500.0)
        await financials_service.adjust_asset_value(db, user, asset.id, -200.0)
        await financials_service.adjust_asset_value(db, user, asset.id, 300.0)

        await db.refresh(asset)
        assert asset.current_value == 1_600.0
