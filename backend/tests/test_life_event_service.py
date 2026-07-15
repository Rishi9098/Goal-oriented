"""Life Event Engine, Phase A (Foundation) tests.

These exercise the generic orchestration/undo engine only. The two handlers
below (`_CreateGoalHandler`, `_FailingHandler`) are test-only scaffolding —
registered and unregistered per-test via a fixture — not shipped event
types. No concrete life event (salary raise, marriage, etc.) is implemented
or asserted here, per Phase A's scope.
"""

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.goal import Goal
from app.models.life_event import LifeEvent, LifeEventEffect
from app.models.user import User
from app.services import life_event_service
from app.services.life_event_service import EntityEffect, UndoResult

_TEST_CREATE_GOAL = "test_create_goal"
_TEST_FAILING = "test_failing"


class _CreateGoalHandler:
    """Minimal handler: creates one Goal, returns one create effect."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict
    ) -> list[EntityEffect]:
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
                after_state=life_event_service.snapshot(
                    goal, ["name", "target_amount", "current_amount"]
                ),
            )
        ]


class _UpdateGoalHandler:
    """Bumps an existing goal's target_amount and target_date, returning
    one "update" effect with a real before_state — exercises the
    before_state restoration path (as opposed to _CreateGoalHandler's
    before_state=None removal path)."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict
    ) -> list[EntityEffect]:
        # `inputs` is stored as JSON on LifeEvent.inputs, so callers (and
        # a real Phase B handler receiving a JSON request body) pass
        # JSON-safe primitives here, not native UUID/date objects.
        goal = await db.get(Goal, uuid.UUID(inputs["goal_id"]))
        assert goal is not None
        before = life_event_service.snapshot(goal, ["target_amount", "target_date"])
        goal.target_amount = inputs["new_target_amount"]
        goal.target_date = date.fromisoformat(inputs["new_target_date"])
        db.add(goal)
        await db.flush()
        return [
            EntityEffect(
                entity_table="goals",
                entity_id=goal.id,
                change_type="update",
                before_state=before,
                after_state=life_event_service.snapshot(
                    goal, ["target_amount", "target_date"]
                ),
            )
        ]


class _FailingHandler:
    """Creates one Goal, then raises — used to prove that a failure inside
    a handler leaves nothing durably committed, since record_life_event
    never calls db.commit() itself (TransactionConsistencyImplementationPlan.md)."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict
    ) -> list[EntityEffect]:
        goal = Goal(
            user_id=user.id,
            name="Should never survive",
            category="wealth",
            target_amount=1_000.0,
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()
        raise RuntimeError("simulated mid-event failure")


@pytest.fixture(autouse=True)
def _clean_handler_registry():
    """Every test registers its own scratch handler(s) and this fixture
    guarantees they never leak into another test, regardless of pass/fail."""
    before = life_event_service.registered_event_types()
    yield
    for event_type in life_event_service.registered_event_types():
        if event_type not in before:
            life_event_service.unregister_handler(event_type)


# ── Generic orchestration interface ────────────────────────────────────────


class TestOrchestrationInterface:
    async def test_scratch_event_type_is_not_registered_until_this_test_registers_it(self):
        # Phase A itself ships with zero registered types; as of Phase B.1
        # ("Loan Payoff") the real registry is no longer empty by the time
        # any test runs, since importing app.main (which every test does,
        # transitively via conftest.py) wires the one real handler that
        # now exists. This test only asserts the scratch type this file
        # owns isn't pre-registered — not that the whole registry is empty.
        assert _TEST_CREATE_GOAL not in life_event_service.registered_event_types()

    async def test_register_and_list_handler(self):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        assert _TEST_CREATE_GOAL in life_event_service.registered_event_types()

    async def test_unknown_event_type_raises_on_record(self, db: AsyncSession, user: User):
        with pytest.raises(ValueError, match="Unknown life event type"):
            await life_event_service.record_life_event(
                db, user, event_type="not_a_real_event", occurred_on=date.today(), inputs={}
            )

    async def test_unknown_event_type_raises_on_preview(self, db: AsyncSession, user: User):
        with pytest.raises(ValueError, match="Unknown life event type"):
            await life_event_service.preview_life_event(
                db, user, event_type="not_a_real_event", inputs={}
            )


# ── Record ──────────────────────────────────────────────────────────────────


class TestRecordLifeEvent:
    async def test_records_event_and_effect_and_applies_the_write(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date(2026, 1, 15),
            inputs={"name": "Retire at 60", "target_amount": 500_000.0},
        )

        assert life_event.event_type == _TEST_CREATE_GOAL
        assert life_event.status == "applied"
        assert life_event.occurred_on == date(2026, 1, 15)
        assert life_event.inputs == {"name": "Retire at 60", "target_amount": 500_000.0}

        assert len(life_event.effects) == 1
        effect = life_event.effects[0]
        assert effect.entity_table == "goals"
        assert effect.change_type == "create"
        assert effect.before_state is None
        assert effect.after_state["name"] == "Retire at 60"

        goal = await db.get(Goal, effect.entity_id)
        assert goal is not None
        assert goal.name == "Retire at 60"
        assert goal.user_id == user.id

    async def test_writes_a_generic_audit_log_row(self, db: AsyncSession, user: User):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id, AuditLog.action == "life_event_recorded"
            )
        )
        audit_rows = result.scalars().all()
        assert len(audit_rows) == 1
        assert audit_rows[0].after_state == {
            "life_event_id": str(life_event.id),
            "event_type": _TEST_CREATE_GOAL,
        }

    async def test_never_commits_a_handler_failure_partway_through(
        self, db: AsyncSession, user: User
    ):
        """The core proof this phase exists to deliver: if a handler fails
        after already writing one entity, nothing it wrote survives a
        rollback — because record_life_event itself never called commit."""
        life_event_service.register_handler(_TEST_FAILING, _FailingHandler())

        with pytest.raises(RuntimeError, match="simulated mid-event failure"):
            await life_event_service.record_life_event(
                db, user, event_type=_TEST_FAILING, occurred_on=date.today(), inputs={}
            )

        await db.rollback()

        result = await db.execute(select(Goal).where(Goal.user_id == user.id))
        assert result.scalars().all() == []

        result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user.id))
        assert result.scalars().all() == []


# ── Preview ─────────────────────────────────────────────────────────────────


class TestPreviewLifeEvent:
    async def test_preview_returns_effects_but_persists_nothing(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        effects = await life_event_service.preview_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, inputs={"name": "Preview Goal"}
        )

        assert len(effects) == 1
        assert effects[0].after_state["name"] == "Preview Goal"

        # The goal the handler flushed during preview must not be visible
        # after the savepoint rollback.
        result = await db.execute(select(Goal).where(Goal.user_id == user.id))
        assert result.scalars().all() == []

        result = await db.execute(select(LifeEvent).where(LifeEvent.user_id == user.id))
        assert result.scalars().all() == []

    async def test_preview_does_not_disturb_other_pending_work_on_the_session(
        self, db: AsyncSession, user: User
    ):
        """Preview runs inside a SAVEPOINT, not a full rollback of the
        session — anything else already pending on this request's session
        survives a preview call untouched."""
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        unrelated_goal = Goal(
            user_id=user.id,
            name="Unrelated, already pending",
            category="wealth",
            target_amount=1.0,
            current_amount=0.0,
            target_date=date(2050, 1, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(unrelated_goal)
        await db.flush()

        await life_event_service.preview_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, inputs={}
        )

        # Still present — preview's rollback must be scoped to its own
        # savepoint only.
        still_there = await db.get(Goal, unrelated_goal.id)
        assert still_there is not None


# ── Read ────────────────────────────────────────────────────────────────────


class TestReadLifeEvents:
    async def test_get_life_event_returns_none_for_another_users_event(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )

        assert await life_event_service.get_life_event(db, other_user, life_event.id) is None
        assert await life_event_service.get_life_event(db, user, life_event.id) is not None

    async def test_list_life_events_isolated_between_users_and_most_recent_first(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())

        first = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date(2026, 1, 1), inputs={}
        )
        # SQLite's server_default=func.now() only has second-level
        # resolution in this test DB (unlike Postgres's microsecond
        # precision in production — the same environment difference
        # notification_service.py's own `_aware()` helper is already
        # written around). A tiny real delay guarantees the two events'
        # recorded_at values are actually distinct, so the ordering this
        # test checks isn't a coin flip.
        await asyncio.sleep(1.1)
        second = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date(2026, 2, 1), inputs={}
        )
        await life_event_service.record_life_event(
            db, other_user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )

        items = await life_event_service.list_life_events(db, user)
        assert [i.id for i in items] == [second.id, first.id]


# ── Generic undo framework ──────────────────────────────────────────────────


class TestUndoLifeEvent:
    async def test_undo_reverses_a_create_effect_via_soft_delete(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        goal_id = life_event.effects[0].entity_id

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result == UndoResult(blocked=False, conflicts=[])
        goal = await db.get(Goal, goal_id)
        assert goal is not None
        assert goal.is_active is False

        await db.refresh(life_event)
        assert life_event.status == "undone"
        assert life_event.undone_at is not None

    async def test_undo_writes_a_generic_audit_log_row(self, db: AsyncSession, user: User):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        await life_event_service.undo_life_event(db, user, life_event.id)

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id, AuditLog.action == "life_event_undone"
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].after_state == {"life_event_id": str(life_event.id), "status": "undone"}

    async def test_undo_blocks_when_the_row_changed_since_recording(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type=_TEST_CREATE_GOAL,
            occurred_on=date.today(),
            inputs={"name": "Original Name"},
        )
        goal_id = life_event.effects[0].entity_id

        goal = await db.get(Goal, goal_id)
        assert goal is not None
        goal.name = "Independently renamed since the event"
        db.add(goal)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert len(result.conflicts) == 1
        assert result.conflicts[0].entity_table == "goals"
        assert result.conflicts[0].entity_id == goal_id

        # Untouched: neither the goal nor the event's status changed.
        unchanged_goal = await db.get(Goal, goal_id)
        assert unchanged_goal is not None
        assert unchanged_goal.name == "Independently renamed since the event"
        assert unchanged_goal.is_active is True
        await db.refresh(life_event)
        assert life_event.status == "applied"

    async def test_undo_with_force_overrides_a_state_conflict(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        goal_id = life_event.effects[0].entity_id

        goal = await db.get(Goal, goal_id)
        assert goal is not None
        goal.name = "Changed before a forced undo"
        db.add(goal)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id, force=True)

        assert result.blocked is False
        forced_goal = await db.get(Goal, goal_id)
        assert forced_goal is not None
        assert forced_goal.is_active is False

    async def test_undo_already_undone_event_raises(self, db: AsyncSession, user: User):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        await life_event_service.undo_life_event(db, user, life_event.id)

        with pytest.raises(ValueError, match="already been undone"):
            await life_event_service.undo_life_event(db, user, life_event.id)

    async def test_undo_nonexistent_event_raises_lookup_error(
        self, db: AsyncSession, user: User
    ):
        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, user, uuid.uuid4())

    async def test_cannot_undo_another_users_event(
        self, db: AsyncSession, user: User, other_user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )

        with pytest.raises(LookupError):
            await life_event_service.undo_life_event(db, other_user, life_event.id)


# ── Cascade / schema shape ───────────────────────────────────────────────────


class TestSchemaShape:
    async def test_deleting_a_life_event_cascades_its_effects(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        effect_id = life_event.effects[0].id

        await db.delete(life_event)
        await db.flush()

        assert await db.get(LifeEventEffect, effect_id) is None


# ── Undo: update effects, and unresolvable-row edge cases ──────────────────


class TestUndoAdditionalPaths:
    async def test_undo_restores_before_state_for_an_update_effect(
        self, db: AsyncSession, user: User
    ):
        """Exercises the before_state != None restoration path (as opposed
        to every other test's before_state=None removal path) and, via
        target_date, the date-typed value round trip through
        snapshot()/_restore_value()."""
        goal = Goal(
            user_id=user.id,
            name="Existing Goal",
            category="wealth",
            target_amount=100_000.0,
            current_amount=0.0,
            target_date=date(2040, 6, 1),
            monthly_contribution=0.0,
            risk_profile="balanced",
        )
        db.add(goal)
        await db.flush()

        life_event_service.register_handler("test_update_goal", _UpdateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db,
            user,
            event_type="test_update_goal",
            occurred_on=date.today(),
            inputs={
                "goal_id": str(goal.id),
                "new_target_amount": 250_000.0,
                "new_target_date": date(2045, 12, 31).isoformat(),
            },
        )
        await db.refresh(goal)
        assert goal.target_amount == 250_000.0
        assert goal.target_date == date(2045, 12, 31)

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result == UndoResult(blocked=False, conflicts=[])
        await db.refresh(goal)
        assert goal.target_amount == 100_000.0
        assert goal.target_date == date(2040, 6, 1)

    async def test_undo_conflict_when_row_no_longer_exists(
        self, db: AsyncSession, user: User
    ):
        life_event_service.register_handler(_TEST_CREATE_GOAL, _CreateGoalHandler())
        life_event = await life_event_service.record_life_event(
            db, user, event_type=_TEST_CREATE_GOAL, occurred_on=date.today(), inputs={}
        )
        goal_id = life_event.effects[0].entity_id

        goal = await db.get(Goal, goal_id)
        assert goal is not None
        await db.delete(goal)
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert result.conflicts[0].reason == "Row no longer exists"

    async def test_undo_conflict_for_unrecognized_entity_table(
        self, db: AsyncSession, user: User
    ):
        life_event = LifeEvent(
            user_id=user.id,
            event_type="test_unrecognized",
            occurred_on=date.today(),
            inputs={},
            status="applied",
        )
        db.add(life_event)
        await db.flush()
        db.add(
            LifeEventEffect(
                life_event_id=life_event.id,
                entity_table="not_a_real_table",
                entity_id=user.id,
                change_type="create",
                before_state=None,
                after_state=None,
            )
        )
        await db.flush()

        result = await life_event_service.undo_life_event(db, user, life_event.id)

        assert result.blocked is True
        assert result.conflicts[0].reason == (
            "Unrecognized entity table — cannot verify it is safe to undo"
        )
