"""Phase 3 — Notification Center seen/read/dismissed markers

Revision ID: 009
Revises: 008
Create Date: 2026-07-08 00:00:00.000000

Stores only seen/read/dismissed state, never notification content — see
ArchitectureReview_Phase3.md. `dedupe_key` is a uuid5 derived deterministically
from source + natural key (NotificationIdentityReview.md), computed in
application code, not by this migration.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_markers (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source        VARCHAR(50) NOT NULL,
            dedupe_key    UUID NOT NULL,
            read_at       TIMESTAMPTZ,
            dismissed_at  TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_notification_marker_user_key UNIQUE (user_id, dedupe_key)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_markers_user_id ON notification_markers(user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_markers_dedupe_key ON notification_markers(dedupe_key);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_markers;")
