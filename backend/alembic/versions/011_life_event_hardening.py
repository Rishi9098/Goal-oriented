"""Life Event Engine hardening — idempotency key + undo row fingerprint

Revision ID: 011
Revises: 010
Create Date: 2026-07-13 00:00:00.000000

Two additive columns, no existing column touched, both nullable so every
existing life_events/life_event_effects row (and every caller that never
passes the new optional arguments) is completely unaffected:

- life_events.idempotency_key: an optional, client-supplied token. A
  UNIQUE(user_id, idempotency_key) constraint lets a duplicate
  POST /life-events (a retried request, a double-click) return the
  original event instead of re-running the handler a second time. NULL
  values never collide with each other under standard SQL uniqueness
  semantics (both Postgres and SQLite), so every event recorded without a
  key — which is all of them today, since idempotency_key is optional —
  is entirely unaffected by this constraint.

- life_event_effects.after_updated_at: the touched row's own `updated_at`
  at the moment the effect was recorded. Every one of the nine entity
  tables this engine touches already has `updated_at` with
  `onupdate=func.now()` (a schema-wide convention, confirmed directly
  against every model file) — this lets undo's conflict guard detect a
  row that changed *at all* since the event, not just a change to the
  specific fields that one effect's own `after_state` happens to include
  (LifeEventEngine_FinalReleaseAudit.md §1.3's field-scoped-guard gap).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE life_events ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100);")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_life_events_user_idempotency_key "
        "ON life_events(user_id, idempotency_key);"
    )

    op.execute(
        "ALTER TABLE life_event_effects ADD COLUMN IF NOT EXISTS after_updated_at TIMESTAMPTZ;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE life_event_effects DROP COLUMN IF EXISTS after_updated_at;")
    op.execute("DROP INDEX IF EXISTS ux_life_events_user_idempotency_key;")
    op.execute("ALTER TABLE life_events DROP COLUMN IF EXISTS idempotency_key;")
