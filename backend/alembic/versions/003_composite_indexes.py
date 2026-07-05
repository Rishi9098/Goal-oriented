"""Add composite indexes for common filtered queries

Revision ID: 003
Revises: 002
Create Date: 2026-07-05 00:00:00.000000

The most frequent query pattern across every entity table is:
    WHERE user_id = $1 AND is_active = TRUE
Adding a composite index on (user_id, is_active) lets PostgreSQL satisfy
these queries with an index-only scan instead of a sequential scan filtered
by user_id.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block — it
    # errors with "CREATE INDEX CONCURRENTLY cannot run inside a transaction
    # block", which is exactly what Alembic wraps every migration in by
    # default. autocommit_block() commits the current transaction, runs the
    # enclosed statements with the connection in autocommit mode, then opens
    # a fresh transaction for whatever migration runs next.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_goals_user_id_active ON goals(user_id, is_active);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_income_sources_user_id_active ON income_sources(user_id, is_active);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_expenses_user_id_active ON expenses(user_id, is_active);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_assets_user_id_active ON assets(user_id, is_active);"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_liabilities_user_id_active ON liabilities(user_id, is_active);"
        )
        # goals ordered by priority + created_at — covers the default list query
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_goals_user_id_priority ON goals(user_id, priority ASC, created_at ASC) "
            "WHERE is_active = TRUE;"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for idx in (
            "ix_goals_user_id_priority",
            "ix_liabilities_user_id_active",
            "ix_assets_user_id_active",
            "ix_expenses_user_id_active",
            "ix_income_sources_user_id_active",
            "ix_goals_user_id_active",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx};")
