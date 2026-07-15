"""Milestone 2 Task 1 — Family Goal Tagging & Insurance-Status schema

Revision ID: 007
Revises: 006
Create Date: 2026-07-06 00:00:00.000000

Implements the three schema additions specified in
Milestone2ImplementationContract.md §0, per Task 1 of
ImplementationChecklist.md. All three are additive only — no existing
Foundation table's column meaning, nullability, or constraint changes.

§0.1 `goal_household_members` — a purely descriptive tag ("this goal
affects this household member"), never a joint-ownership model.
`goals.user_id` remains the sole owner of record for every purpose.

§0.2 `goals.custom_inflation_rate` — nullable per-goal override of
`financial_assumptions.inflation_rate`, for education/medical goals that
run 2.5-3x general inflation (CalculationEngineReport.md #10).

§0.3 `dependents.has_own_insurance` — nullable, captures whether a
parent-type dependent already has their own health coverage, driving the
Family Insurance separate-policy recommendation
(FamilyHUFPlanningReport.md's verified doubled-deduction finding).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── §0.2: per-goal inflation override ─────────────────────────────────
    op.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS custom_inflation_rate FLOAT;")

    # ── §0.3: parent-dependent insurance status ───────────────────────────
    op.execute(
        "ALTER TABLE dependents ADD COLUMN IF NOT EXISTS has_own_insurance VARCHAR(10);"
    )

    # ── §0.1: goal <-> household_member descriptive tag ───────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS goal_household_members (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            goal_id               UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
            household_member_id   UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_goal_household_members UNIQUE (goal_id, household_member_id)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_goal_household_members_goal_id "
        "ON goal_household_members(goal_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_goal_household_members_household_member_id "
        "ON goal_household_members(household_member_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS goal_household_members;")
    op.execute("ALTER TABLE dependents DROP COLUMN IF EXISTS has_own_insurance;")
    op.execute("ALTER TABLE goals DROP COLUMN IF EXISTS custom_inflation_rate;")
