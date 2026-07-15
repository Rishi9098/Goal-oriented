"""Life Event Engine, Phase A — foundation only.

This module is the generic orchestration and undo engine described in
LifeEventEngineArchitecture.md §4/§7. It contains zero event-specific logic:
`_HANDLERS` starts empty in this phase and stays empty until a later phase
registers a concrete event type (e.g. "salary_raise", "marriage"). Nothing
here computes a financial figure, a recommendation, or a Monte Carlo
probability — every write a future handler performs goes through the same
entity models and, where a goal field is touched, the same
`calculate_goal_probability`/`CALCULATION_CONTEXT_FIELDS` trigger
`routers/goals.py` already uses (ADR-001). This module orchestrates and
records; it never duplicates that machinery.

Transaction discipline (TransactionConsistencyImplementationPlan.md): every
function below calls `db.flush()` where a generated id is needed, and never
`db.commit()`. Callers (a router via `get_db()`, or a test using the
request-scoped session directly) own the commit/rollback boundary — this is
what makes a compound life event atomic once a real handler is registered.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.database import Base
from app.models.assumptions import FinancialAssumptions
from app.models.audit import AuditLog
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.goal import Goal
from app.models.household import Dependent, HouseholdMember
from app.models.life_event import LifeEvent, LifeEventEffect
from app.models.profile import UserProfile
from app.models.user import User

# ── Generic entity registry ───────────────────────────────────────────────
#
# A table-name -> ORM-class lookup for the generic undo engine. This encodes
# no business rule about *when* or *why* any of these tables is written —
# it only lets undo resolve "entity_table='assets'" back to the Asset class
# to load and restore a row. The set of tables is exactly
# LifeEventEngineArchitecture.md §3's list; adding a tenth table later is a
# one-line addition here, not a new mechanism.

_ENTITY_MODELS: dict[str, type[Base]] = {
    "income_sources": IncomeSource,
    "expenses": Expense,
    "assets": Asset,
    "liabilities": Liability,
    "goals": Goal,
    "household_members": HouseholdMember,
    "dependents": Dependent,
    "user_profiles": UserProfile,
    "financial_assumptions": FinancialAssumptions,
}


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def snapshot(row: Any, fields: Iterable[str]) -> dict[str, Any]:
    """Generic before/after state capture used by handlers (a later phase)
    to build an `EntityEffect`'s `before_state`/`after_state`. JSON-safe by
    construction, so undo's conflict comparison (`_current_state_matches`)
    is always comparing like-for-like. Not event-specific — it only knows
    how to read attributes off any row."""
    return {f: _to_json_safe(getattr(row, f)) for f in fields}


def _aware(value: datetime) -> datetime:
    """SQLite (test DB) returns naive datetimes even for TIMESTAMPTZ
    columns, unlike Postgres's aware datetimes in production — the same
    cross-backend difference `notification_service.py`'s own `_aware()`
    already normalizes for an unrelated reason. Normalizing here means an
    `after_updated_at` comparison never spuriously conflicts (or
    spuriously matches) purely because of which backend is running."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _restore_value(model_cls: type[Base], field_name: str, value: Any) -> Any:
    """The inverse of `snapshot()` for one field: converts a JSON-safe
    stored value back to the Python type the column expects, using only
    the column's own declared type (schema metadata) — never a per-field
    or per-event special case."""
    if value is None:
        return None
    column = model_cls.__table__.columns.get(field_name)
    if column is None:
        return value
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return value  # JSON-typed columns already hold native values
    if python_type is uuid.UUID and isinstance(value, str):
        return uuid.UUID(value)
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if python_type is date and isinstance(value, str):
        return date.fromisoformat(value)
    return value


# ── Generic event orchestration interface ─────────────────────────────────


@dataclass(frozen=True)
class EntityEffect:
    """One entity mutation a handler performed, in the shape
    `life_event_effects` stores it. `before_state`/`after_state` must be
    built via `snapshot()` above, not by hand, so a later undo's conflict
    check compares consistent representations."""

    entity_table: str
    entity_id: uuid.UUID
    change_type: str  # "create" | "update" | "soft_delete" | "reactivate"
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None


class LifeEventHandler(Protocol):
    """The interface a concrete life event (a later phase) implements.
    `apply` performs whatever entity writes the event requires — reusing
    existing service functions/model mutations exactly as
    LifeEventEngineArchitecture.md §2 requires — and returns the list of
    effects that were applied, in write order. It must never call
    `db.commit()`; the caller owns the transaction boundary."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]: ...


_HANDLERS: dict[str, LifeEventHandler] = {}


def register_handler(event_type: str, handler: LifeEventHandler) -> None:
    """Registers a concrete event type. Phase A registers none — this
    function exists so a later phase (or a test exercising this generic
    engine) has exactly one place to plug in, rather than this module
    growing an if/elif per event type."""
    _HANDLERS[event_type] = handler


def unregister_handler(event_type: str) -> None:
    _HANDLERS.pop(event_type, None)


def registered_event_types() -> list[str]:
    return sorted(_HANDLERS)


def _require_handler(event_type: str) -> LifeEventHandler:
    handler = _HANDLERS.get(event_type)
    if handler is None:
        raise ValueError(
            f"Unknown life event type: {event_type!r}. No handler is registered — "
            "this is expected in Phase A, which ships the engine with zero "
            "concrete event types (LifeEventEngineArchitecture.md, Phase B+)."
        )
    return handler


# ── Record ─────────────────────────────────────────────────────────────────


async def preview_life_event(
    db: AsyncSession, user: User, *, event_type: str, inputs: dict[str, Any]
) -> list[EntityEffect]:
    """Runs the exact same handler `record_life_event` would, inside a
    SAVEPOINT that is always rolled back — the preview a caller sees is
    never a lie, because it is produced by the same code that would
    actually run (LifeEventEngineArchitecture.md §4.1). Scoped to a nested
    transaction specifically so it never disturbs whatever else is pending
    on the caller's request-scoped session."""
    handler = _require_handler(event_type)
    savepoint = await db.begin_nested()
    try:
        return await handler.apply(db, user, inputs)
    finally:
        await savepoint.rollback()


async def _get_by_idempotency_key(
    db: AsyncSession, user: User, idempotency_key: str
) -> LifeEvent | None:
    result = await db.execute(
        select(LifeEvent)
        .options(selectinload(LifeEvent.effects))
        .where(
            LifeEvent.user_id == user.id,
            LifeEvent.idempotency_key == idempotency_key,
            LifeEvent.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _row_updated_at(
    db: AsyncSession, entity_table: str, entity_id: uuid.UUID
) -> datetime | None:
    """Reads the just-touched row's own `updated_at`, for
    `LifeEventEffect.after_updated_at` — a row-level fingerprint captured
    alongside (not instead of) the existing field-level `after_state`
    snapshot (LifeEventEngine_FinalReleaseAudit.md §1.3). Queried as a
    plain Core column read rather than `db.get()` + attribute access:
    the handler that just wrote this row typically already flushed it in
    this same transaction, and SQLAlchemy always expires an
    `onupdate=func.now()` column after a flush (only the DB knows the
    value it computed) — a bare `getattr` on that expired attribute
    triggers an implicit, un-awaited lazy-reload that raises
    `MissingGreenlet` under the async driver. A direct `select()` reads
    the true just-committed value without ever touching ORM attribute
    state. Returns None gracefully — never raises — for an unrecognized
    table or an entity type with no `updated_at` column."""
    model_cls = _ENTITY_MODELS.get(entity_table)
    if model_cls is None:
        return None
    table = model_cls.__table__
    updated_at_column = table.columns.get("updated_at")
    if updated_at_column is None:
        return None
    result = await db.execute(select(updated_at_column).where(table.c.id == entity_id))
    updated_at = result.scalar_one_or_none()
    return _aware(updated_at) if updated_at is not None else None


async def record_life_event(
    db: AsyncSession,
    user: User,
    *,
    event_type: str,
    occurred_on: date,
    inputs: dict[str, Any],
    notes: str | None = None,
    idempotency_key: str | None = None,
) -> LifeEvent:
    """Applies one life event atomically: runs its handler, records the
    event and every effect it produced, and writes one AuditLog row. Never
    commits — see this module's docstring.

    `idempotency_key` is optional and additive
    (LifeEventEngine_FinalReleaseAudit.md §4.2): a caller that never
    passes one gets byte-for-byte the same behavior this function always
    had. When given, a prior life event recorded with the same key (for
    this user) is returned unchanged — the handler is never re-invoked, no
    new row of any kind is written. A genuinely concurrent duplicate (two
    requests racing before either commits) is caught by the
    UNIQUE(user_id, idempotency_key) constraint at flush time and
    recovered the same way `routers/assumptions.py`'s own
    `get_assumptions` already recovers from an analogous first-access
    race: discard this attempt, re-read the winner."""
    if idempotency_key is not None:
        existing = await _get_by_idempotency_key(db, user, idempotency_key)
        if existing is not None:
            return existing

    handler = _require_handler(event_type)
    effects = await handler.apply(db, user, inputs)

    life_event = LifeEvent(
        user_id=user.id,
        event_type=event_type,
        occurred_on=occurred_on,
        inputs=inputs,
        status="applied",
        notes=notes,
        idempotency_key=idempotency_key,
    )
    db.add(life_event)

    if idempotency_key is None:
        await db.flush()
    else:
        try:
            await db.flush()
        except IntegrityError:
            # Lost a genuine race to a concurrent identical request that
            # already committed its own row with this key. This attempt's
            # own writes (including whatever the handler already flushed)
            # are discarded by the rollback — that is correct, not
            # incidental: this request accomplishes nothing new, which is
            # exactly the idempotency guarantee.
            await db.rollback()
            existing = await _get_by_idempotency_key(db, user, idempotency_key)
            if existing is None:
                # The constraint violation implies a row exists — never
                # silently swallow the unexplained case otherwise.
                raise
            return existing

    effect_rows = [
        LifeEventEffect(
            life_event_id=life_event.id,
            entity_table=effect.entity_table,
            entity_id=effect.entity_id,
            change_type=effect.change_type,
            before_state=effect.before_state,
            after_state=effect.after_state,
            after_updated_at=await _row_updated_at(db, effect.entity_table, effect.entity_id),
        )
        for effect in effects
    ]
    for row in effect_rows:
        db.add(row)
    await db.flush()

    # Explicitly marks `.effects` as already loaded with exactly these rows
    # — a persisted parent's collection is otherwise considered "unloaded"
    # until queried, and a caller reading `life_event.effects` right after
    # this call returns (with no `await` in between) cannot trigger that
    # query: AsyncSession's lazy-load requires an awaited context. This is
    # the SQLAlchemy-supported way to avoid it, not a workaround.
    set_committed_value(life_event, "effects", effect_rows)  # type: ignore[no-untyped-call]

    db.add(
        AuditLog(
            user_id=user.id,
            action="life_event_recorded",
            after_state={"life_event_id": str(life_event.id), "event_type": event_type},
        )
    )
    return life_event


# ── Read ───────────────────────────────────────────────────────────────────


async def get_life_event(
    db: AsyncSession, user: User, life_event_id: uuid.UUID
) -> LifeEvent | None:
    result = await db.execute(
        select(LifeEvent)
        .options(selectinload(LifeEvent.effects))
        .where(
            LifeEvent.id == life_event_id,
            LifeEvent.user_id == user.id,
            LifeEvent.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_life_events(db: AsyncSession, user: User) -> list[LifeEvent]:
    result = await db.execute(
        select(LifeEvent)
        .where(LifeEvent.user_id == user.id, LifeEvent.is_active.is_(True))
        .order_by(LifeEvent.recorded_at.desc())
    )
    return list(result.scalars().all())


async def list_life_events_paginated(
    db: AsyncSession,
    user: User,
    *,
    event_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[LifeEvent], int]:
    """Additive sibling of `list_life_events` for the REST API's paginated
    history view (LifeEventEngineArchitecture.md §10) — `list_life_events`
    itself is untouched (existing callers/tests keep their exact contract).
    Newest-first, optionally filtered by `event_type` and an
    `occurred_on` date range. Returns `(page, total_matching_count)` so a
    caller can render "page 2 of N" without a second round trip building
    its own count query. Eager-loads `effects` via the same
    `selectinload` `get_life_event` already uses, so rendering a page of
    events never N+1s into one effects-query per event."""
    filters = [LifeEvent.user_id == user.id, LifeEvent.is_active.is_(True)]
    if event_type is not None:
        filters.append(LifeEvent.event_type == event_type)
    if start_date is not None:
        filters.append(LifeEvent.occurred_on >= start_date)
    if end_date is not None:
        filters.append(LifeEvent.occurred_on <= end_date)

    count_result = await db.execute(select(func.count()).select_from(LifeEvent).where(*filters))
    total = count_result.scalar_one()

    page_result = await db.execute(
        select(LifeEvent)
        .options(selectinload(LifeEvent.effects))
        .where(*filters)
        .order_by(LifeEvent.recorded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(page_result.scalars().all()), total


# ── Generic undo framework (no event-specific logic) ──────────────────────


@dataclass(frozen=True)
class UndoConflict:
    effect_id: uuid.UUID
    entity_table: str
    entity_id: uuid.UUID
    reason: str


@dataclass(frozen=True)
class UndoResult:
    blocked: bool
    conflicts: list[UndoConflict] = field(default_factory=list)


def _current_state_matches(row: Any, after_state: dict[str, Any]) -> bool:
    return snapshot(row, after_state.keys()) == after_state


def _updated_at_matches(row: Any, after_updated_at: datetime) -> bool:
    """Row-level fingerprint check, layered alongside (never instead of)
    `_current_state_matches`'s field-level check
    (LifeEventEngine_FinalReleaseAudit.md §1.3): catches a row that
    changed on a field this specific effect never touched at all — e.g. a
    later, unrelated event soft-deleting the same row a field-only effect
    updated. `updated_at` bumps via `onupdate=func.now()` on *any* column
    change, on all nine entity tables this engine touches (verified
    against every model file), so this needs no per-table special case.
    An entity with no `updated_at` at all degrades to True (nothing to
    compare — the field-level check remains the only guard for it)."""
    current = getattr(row, "updated_at", None)
    if current is None:
        return True
    return _aware(current) == _aware(after_updated_at)


async def undo_life_event(
    db: AsyncSession, user: User, life_event_id: uuid.UUID, *, force: bool = False
) -> UndoResult:
    """Reverses every effect of one life event, in reverse order, guarded:
    an effect is only reversed if the row it touched still matches both
    the `after_state` captured when the event was recorded *and* the
    row's own `updated_at` at that time (`after_updated_at` — see
    `_updated_at_matches`'s own docstring for why both checks matter), or
    `force=True` is passed. This function contains no knowledge of what
    any particular event_type means — it operates purely on
    `entity_table`/`entity_id`/`before_state`/`after_state`/
    `after_updated_at`, exactly as LifeEventEngineArchitecture.md §7
    specifies. Never commits.

    Each touched row is loaded with `with_for_update=True`
    (LifeEventEngine_FinalReleaseAudit.md §4.3): silently ignored by
    SQLite (this test suite's backend, which has no row-level locking),
    a real row lock under Postgres (production), so a concurrent write to
    the same row can't interleave between this conflict check and the
    reversal write below."""
    life_event = await _get_owned_life_event(db, user, life_event_id)
    if life_event.status == "undone":
        raise ValueError(f"Life event {life_event_id} has already been undone")

    conflicts: list[UndoConflict] = []
    rows_by_effect_id: dict[uuid.UUID, Any] = {}

    for effect in life_event.effects:
        model_cls = _ENTITY_MODELS.get(effect.entity_table)
        if model_cls is None:
            conflicts.append(
                UndoConflict(
                    effect.id,
                    effect.entity_table,
                    effect.entity_id,
                    "Unrecognized entity table — cannot verify it is safe to undo",
                )
            )
            continue
        row = await db.get(model_cls, effect.entity_id, with_for_update=True)
        if row is None:
            conflicts.append(
                UndoConflict(
                    effect.id, effect.entity_table, effect.entity_id, "Row no longer exists"
                )
            )
            continue
        state_changed = effect.after_state is not None and not _current_state_matches(
            row, effect.after_state
        )
        timestamp_changed = effect.after_updated_at is not None and not _updated_at_matches(
            row, effect.after_updated_at
        )
        if state_changed or timestamp_changed:
            conflicts.append(
                UndoConflict(
                    effect.id,
                    effect.entity_table,
                    effect.entity_id,
                    "Row has changed since this event was recorded",
                )
            )
            # Still tracked below: a state mismatch is exactly what
            # force=True is for (LifeEventEngineArchitecture.md §7 — "a
            # user who explicitly wants to discard the intervening change
            # too"). Only a missing row or an unrecognized table (above)
            # is unresolvable regardless of force.
        rows_by_effect_id[effect.id] = row

    if conflicts and not force:
        return UndoResult(blocked=True, conflicts=conflicts)

    for effect in reversed(life_event.effects):
        row = rows_by_effect_id.get(effect.id)
        if row is None:
            continue  # forced undo: skip whatever could not be verified/loaded
        model_cls = _ENTITY_MODELS[effect.entity_table]
        if effect.before_state is None:
            # This effect was a "create" — undoing it means removing the
            # row. The generic rule this engine applies: soft-delete if the
            # entity has the schema-wide `is_active` convention, otherwise
            # there is nothing generically safe to do (a known limitation,
            # not resolved here — see LifeEventArchitectureValidation.md).
            if hasattr(row, "is_active"):
                row.is_active = False
        else:
            for field_name, value in effect.before_state.items():
                setattr(row, field_name, _restore_value(model_cls, field_name, value))
        db.add(row)

    life_event.status = "undone"
    life_event.undone_at = datetime.now(UTC)
    db.add(life_event)

    db.add(
        AuditLog(
            user_id=user.id,
            action="life_event_undone",
            before_state={"life_event_id": str(life_event.id), "status": "applied"},
            after_state={"life_event_id": str(life_event.id), "status": "undone"},
        )
    )
    await db.flush()
    return UndoResult(blocked=False, conflicts=[])


async def _get_owned_life_event(
    db: AsyncSession, user: User, life_event_id: uuid.UUID
) -> LifeEvent:
    life_event = await get_life_event(db, user, life_event_id)
    if life_event is None:
        raise LookupError(f"Life event {life_event_id} not found")
    return life_event
