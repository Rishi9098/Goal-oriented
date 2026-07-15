"""Life Event Engine, Phase A — foundation tables (no event type is seeded)

Revision ID: 010
Revises: 009
Create Date: 2026-07-11 00:00:00.000000

life_events / life_event_effects: a domain-specific specialization of the
existing generic audit_logs before/after pattern, grouping a *set* of
related entity changes under one atomic, user-narrated event, with per-row
undo safety a single audit_logs blob cannot express. See
LifeEventEngineArchitecture.md §3 and LifeEventArchitectureValidation.md.
This migration creates the two tables only — no life event type, handler,
or API surface ships in this phase.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS life_events (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_type    VARCHAR(50) NOT NULL,
            occurred_on   DATE NOT NULL,
            recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            inputs        JSON NOT NULL,
            status        VARCHAR(20) NOT NULL DEFAULT 'applied',
            undone_at     TIMESTAMPTZ,
            notes         TEXT,
            is_active     BOOLEAN NOT NULL DEFAULT TRUE
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_life_events_user_id ON life_events(user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_life_events_event_type ON life_events(event_type);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS life_event_effects (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            life_event_id  UUID NOT NULL REFERENCES life_events(id) ON DELETE CASCADE,
            entity_table   VARCHAR(50) NOT NULL,
            entity_id      UUID NOT NULL,
            change_type    VARCHAR(20) NOT NULL,
            before_state   JSON,
            after_state    JSON,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_life_event_effects_life_event_id "
        "ON life_event_effects(life_event_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_life_event_effects_entity_id "
        "ON life_event_effects(entity_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS life_event_effects;")
    op.execute("DROP TABLE IF EXISTS life_events;")
