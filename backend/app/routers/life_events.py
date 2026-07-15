"""REST API layer for the Life Event Engine.

`LifeEventEngine_FinalReleaseAudit.md`'s one release-blocking finding was
that no router exists for any of `life_event_service.py`'s 17 handlers or
its generic record/preview/undo/list surface. This router adds exactly
the HTTP layer LifeEventEngineArchitecture.md §10 already specified —
no business logic lives here. Every endpoint below does only three
things: validate the request shape, call the existing service function,
and translate its result (or exception) into an HTTP response. The
engine itself (`life_event_service.py`) and all 17 event handlers are
untouched except for one additive, backward-compatible function
(`list_life_events_paginated`) needed for pagination/filtering.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.audit import AuditLog
from app.models.life_event import LifeEvent, LifeEventEffect
from app.models.user import User
from app.schemas.life_event import (
    EntityEffectResponse,
    LifeEventCreateRequest,
    LifeEventCreateResponse,
    LifeEventListResponse,
    LifeEventPreviewRequest,
    LifeEventPreviewResponse,
    LifeEventResponse,
    UndoConflictResponse,
    UndoRequest,
    UndoResponse,
)
from app.services import life_event_service
from app.services.life_event_service import EntityEffect

router = APIRouter(prefix="/life-events", tags=["life-events"])


def _to_effect_response(effect: EntityEffect | LifeEventEffect) -> EntityEffectResponse:
    """Builds a response model from either a `life_event_service.EntityEffect`
    (preview path) or a persisted `LifeEventEffect` row (record/list/get
    path) — both expose the same four attributes, so one helper covers
    both without either ever being returned as a response itself."""
    return EntityEffectResponse(
        entity_table=effect.entity_table,
        entity_id=effect.entity_id,
        change_type=effect.change_type,
        before_state=effect.before_state,
        after_state=effect.after_state,
    )


def _to_life_event_response(life_event: LifeEvent) -> LifeEventResponse:
    # Derived, not queried: this is exactly the `action` string
    # record_life_event/undo_life_event always writes for a life event in
    # this status — reporting it this way avoids an extra AuditLog query
    # per row (no N+1 on the list endpoint).
    audit_action = "life_event_undone" if life_event.status == "undone" else "life_event_recorded"
    return LifeEventResponse(
        id=life_event.id,
        event_type=life_event.event_type,
        occurred_on=life_event.occurred_on,
        recorded_at=life_event.recorded_at,
        inputs=life_event.inputs,
        status=life_event.status,
        undone_at=life_event.undone_at,
        notes=life_event.notes,
        effects=[_to_effect_response(e) for e in life_event.effects],
        audit_action=audit_action,
    )


def _require_supported_event_type(event_type: str) -> None:
    if event_type not in life_event_service.registered_event_types():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported event_type: {event_type!r}",
        )


@router.post("/preview", response_model=LifeEventPreviewResponse)
async def preview_life_event(
    body: LifeEventPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LifeEventPreviewResponse:
    """Dry-run only — `life_event_service.preview_life_event` runs the real
    handler inside a SAVEPOINT that is always rolled back, so nothing this
    endpoint does is ever written. A payload-shape problem the handler
    itself catches (a missing required input, a malformed id) is reported
    as a `validation_errors` entry with an otherwise-empty result, not an
    HTTP error — this *is* the dry run's job: show the user what's wrong
    without a hard failure. An unsupported `event_type` is a different,
    structural problem and is rejected up front instead."""
    _require_supported_event_type(body.event_type)

    try:
        effects = await life_event_service.preview_life_event(
            db, current_user, event_type=body.event_type, inputs=body.inputs
        )
    except (KeyError, ValueError, TypeError) as exc:
        return LifeEventPreviewResponse(
            event_type=body.event_type,
            effects=[],
            affected_entities=[],
            validation_errors=[str(exc)],
        )

    return LifeEventPreviewResponse(
        event_type=body.event_type,
        effects=[_to_effect_response(e) for e in effects],
        affected_entities=sorted({e.entity_table for e in effects}),
    )


@router.post("", response_model=LifeEventCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_life_event(
    body: LifeEventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LifeEventCreateResponse:
    """Records a life event via the existing, unmodified
    `life_event_service.record_life_event` — ownership is implicit
    (`current_user` is always the JWT-derived user, never a client-supplied
    id) and the transaction boundary is the request-scoped session
    `get_db()` already owns, exactly as every other write endpoint in this
    codebase already works."""
    _require_supported_event_type(body.event_type)

    try:
        life_event = await life_event_service.record_life_event(
            db,
            current_user,
            event_type=body.event_type,
            occurred_on=body.occurred_on,
            inputs=body.inputs,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid inputs for {body.event_type!r}: {exc}",
        ) from exc

    # The AuditLog row this specific life event's own recording wrote — a
    # plain read of the existing generic ledger, not a new write.
    # Deliberately scoped by this life_event's own id (not just "most
    # recent for this user+action") so a replayed idempotent request
    # still returns *that* event's original audit reference, not
    # whichever life_event_recorded row happens to be newest for this
    # user at read time.
    audit_result = await db.execute(
        select(AuditLog.id)
        .where(
            AuditLog.user_id == current_user.id,
            AuditLog.action == "life_event_recorded",
            AuditLog.after_state["life_event_id"].as_string() == str(life_event.id),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    audit_reference = audit_result.scalar_one()

    return LifeEventCreateResponse(
        life_event=_to_life_event_response(life_event),
        audit_reference=audit_reference,
    )


@router.get("", response_model=LifeEventListResponse)
async def list_life_events(
    event_type: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LifeEventListResponse:
    """Paginated, newest-first history — calls the additive
    `list_life_events_paginated` (existing `list_life_events` is
    untouched)."""
    events, total = await life_event_service.list_life_events_paginated(
        db,
        current_user,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return LifeEventListResponse(
        items=[_to_life_event_response(e) for e in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{life_event_id}", response_model=LifeEventResponse)
async def get_life_event(
    life_event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LifeEventResponse:
    """Ownership is enforced by `get_life_event` itself (filters on
    `user_id`), so another user's event id 404s exactly like a nonexistent
    one — never a distinguishable 403 that would leak existence."""
    life_event = await life_event_service.get_life_event(db, current_user, life_event_id)
    if life_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Life event not found")
    return _to_life_event_response(life_event)


@router.post("/{life_event_id}/undo", response_model=UndoResponse)
async def undo_life_event(
    life_event_id: uuid.UUID,
    body: UndoRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UndoResponse:
    """Calls the generic undo framework directly — no event-specific undo
    logic exists anywhere in this codebase, and none is added here. Three
    distinct outcomes, matching the brief: success (200), conflict (409,
    the guarded-undo case LifeEventEngineArchitecture.md §7 describes —
    something the event touched changed independently since), and
    validation error (422 — the event doesn't exist for this user, or was
    already undone)."""
    try:
        result = await life_event_service.undo_life_event(
            db, current_user, life_event_id, force=body.force
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if result.blocked:
        response.status_code = status.HTTP_409_CONFLICT
        return UndoResponse(
            success=False,
            blocked=True,
            conflicts=[
                UndoConflictResponse(
                    effect_id=c.effect_id,
                    entity_table=c.entity_table,
                    entity_id=c.entity_id,
                    reason=c.reason,
                )
                for c in result.conflicts
            ],
        )

    return UndoResponse(success=True, blocked=False, conflicts=[])
