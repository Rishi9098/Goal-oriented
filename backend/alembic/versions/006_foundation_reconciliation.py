"""Foundation reconciliation — HUF financial ownership + policy engine
Layers 2-3

Revision ID: 006
Revises: 005
Create Date: 2026-07-06 00:00:00.000000

Resolves two HIGH-severity findings from FutureCompatibilityAuditReport.md
(see FoundationReconciliationReport.md for the full decision log):

Finding B — HUF entities existed with no way to record their own income,
assets, expenses, or liabilities, which undermined the entire tax rationale
for modeling HUF as a separate entity. Fixed by adding a nullable
`huf_entity_id` sibling column (alongside the existing, unchanged, required
`user_id`) to all four financial tables. Purely additive: existing rows all
get NULL, meaning "not HUF-owned," which is the correct default for every
row that exists today.

Finding D — the Recommendation Engine's ranking/gating logic
(RecommendationEngineReport.md) depends on `company_policies` rows, and the
five-layer policy model (PolicyEngineReport.md) specifies a
`best_practice_rules` layer neither of which were built in Milestone 1.
Adds both tables — structural support only, no seeded rows, no
recommendation logic.

Findings A and C (duplicate "dependents" source of truth; unreconciled
`tax_rate`) are resolved via code-level deprecation documentation only
(see app/models/profile.py and app/models/assumptions.py) — no schema
change was required or made for those two.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Finding B: HUF financial ownership ───────────────────────────────
    for table in ("income_sources", "expenses", "assets", "liabilities"):
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS huf_entity_id UUID "
            f"REFERENCES huf_entities(id) ON DELETE SET NULL;"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_huf_entity_id "
            f"ON {table}(huf_entity_id);"
        )

    # ── Finding D: Policy Engine Layers 2-3 ───────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS best_practice_rules (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_code           VARCHAR(100) NOT NULL UNIQUE,
            applies_to_persona  VARCHAR(50),
            value               FLOAT,
            unit                VARCHAR(50),
            rationale_text      TEXT NOT NULL,
            source_type         VARCHAR(30) NOT NULL,
            confidence          VARCHAR(20) NOT NULL,
            last_reviewed_date  DATE NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_best_practice_rules_rule_code "
        "ON best_practice_rules(rule_code);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS company_policies (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_code       VARCHAR(100) NOT NULL UNIQUE,
            policy_type       VARCHAR(30) NOT NULL,
            rule_definition   JSON NOT NULL,
            effective_from    DATE NOT NULL,
            approved_by       VARCHAR(255),
            changelog_notes   TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_company_policies_policy_code "
        "ON company_policies(policy_code);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS company_policies;")
    op.execute("DROP TABLE IF EXISTS best_practice_rules;")

    for table in ("liabilities", "assets", "expenses", "income_sources"):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_huf_entity_id;")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS huf_entity_id;")
