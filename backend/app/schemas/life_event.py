"""Request/response schemas for the Life Event Engine's REST API layer.

This is the one piece `LifeEventEngine_FinalReleaseAudit.md` found missing:
every one of these schemas is a thin, additive view over
`life_event_service.py`'s existing `EntityEffect`/`LifeEvent`/`UndoResult`
shapes (LifeEventEngineArchitecture.md §3/§10) — no new field is invented
here that the engine doesn't already produce. `inputs`/`payload` stays a
free-form JSON object (not 17 separate typed schemas, one per event) for
the same reason `life_events.inputs` itself is a JSON column: each
handler's own required/optional fields are already documented per-event
in the architecture and enforced by the handler itself (reused, not
re-validated here) — see `LifeEventAPI_ImplementationReport.md` §4 for why
deep, per-event-type request validation is deliberately not built here.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Requests ─────────────────────────────────────────────────────────────


class LifeEventCreateRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    occurred_on: date
    inputs: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2000)
    # Optional. A client-generated token (e.g. a UUID minted once per form
    # submission) that makes a retried/duplicated POST harmless: replaying
    # the same key returns the original life event instead of recording a
    # second one (LifeEventEngine_FinalReleaseAudit.md §4.2). Omitting it
    # is fully backward compatible — behavior is byte-for-byte the same as
    # before this field existed.
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=100)


class LifeEventPreviewRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    inputs: dict[str, Any] = Field(default_factory=dict)


class UndoRequest(BaseModel):
    force: bool = False


# ── Shared building blocks ───────────────────────────────────────────────


class EntityEffectResponse(BaseModel):
    """Mirrors `life_event_service.EntityEffect`/`LifeEventEffect` exactly
    — never the ORM row itself (no relationship, no session-bound state)."""

    entity_table: str
    entity_id: uuid.UUID
    change_type: str
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None


class LifeEventResponse(BaseModel):
    """Mirrors `LifeEvent` plus its `effects`, built field-by-field by the
    router (never `LifeEvent` itself as `response_model`) — see
    `life_events.py`'s `_to_life_event_response`. `audit_action` is derived,
    not queried: it is exactly the `action` string
    `life_event_service.record_life_event`/`undo_life_event` always writes
    to `AuditLog` for the row's current `status`, so no extra query is
    needed to report it (avoiding an N+1 on the list endpoint)."""

    id: uuid.UUID
    event_type: str
    occurred_on: date
    recorded_at: datetime
    inputs: dict[str, Any]
    status: str
    undone_at: datetime | None
    notes: str | None
    effects: list[EntityEffectResponse]
    audit_action: str


# ── Responses ────────────────────────────────────────────────────────────


class LifeEventCreateResponse(BaseModel):
    life_event: LifeEventResponse
    # The actual AuditLog row's own id (a live, targeted read done by the
    # router right after recording — see life_events.py), distinct from
    # life_event.id itself: this is "the audit trail's own reference to
    # this event," not a repeat of the event's own primary key.
    audit_reference: uuid.UUID


class LifeEventListResponse(BaseModel):
    items: list[LifeEventResponse]
    total: int
    limit: int
    offset: int


class LifeEventPreviewResponse(BaseModel):
    event_type: str
    effects: list[EntityEffectResponse]
    affected_entities: list[str]
    validation_errors: list[str] = Field(default_factory=list)


class UndoConflictResponse(BaseModel):
    effect_id: uuid.UUID
    entity_table: str
    entity_id: uuid.UUID
    reason: str


class UndoResponse(BaseModel):
    success: bool
    blocked: bool
    conflicts: list[UndoConflictResponse] = Field(default_factory=list)
