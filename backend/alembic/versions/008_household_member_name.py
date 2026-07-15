"""Milestone 2 Task 2 — household member identity fields (blocker fixes)

Revision ID: 008
Revises: 007
Create Date: 2026-07-06 00:00:00.000000

Discovered while validating Task 2's dependencies (per
ImplementationChecklist.md's "Validate Dependencies" step, before writing
any backend code) and while implementing its service layer. Three fields
Task 2's own endpoints require, per Milestone2ImplementationContract.md's
ValidationMatrix, had nowhere to live in the certified schema:

- `household_members.name` — the only other source of a name
  (User.full_name via household_members.user_id) doesn't cover the common
  case this milestone is built around: FamilyPlanningDesign.md deliberately
  gives a spouse/child/dependent parent no login (user_id stays NULL).
- `dependents.gender` — drives the SSY eligibility check (female, age <10).
- `dependents.relationship_detail` — 'mother'/'father' for parent-type
  dependents, free text for other-type; distinct from
  household_members.relationship_type (the coarse spouse/child/parent/other
  bucket already in the certified schema).

Resolving all three together in one migration rather than three
incremental ones, since all three were found in the same implementation
pass and are the same size/shape of fix. Also corrects
Milestone2ImplementationContract.md's original assumption that spouse-type
members don't get a `Dependent` row — they do, as of this migration, since
that's the only place date_of_birth/gender can live for a spouse. See
PROJECT_STATE.md's Task 2 entry for the full decision log.

Additive only: nullable columns, no existing Foundation table's meaning
changes, no existing data affected.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE household_members ADD COLUMN IF NOT EXISTS name VARCHAR(255);")
    op.execute("ALTER TABLE dependents ADD COLUMN IF NOT EXISTS gender VARCHAR(10);")
    op.execute(
        "ALTER TABLE dependents ADD COLUMN IF NOT EXISTS relationship_detail VARCHAR(100);"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE dependents DROP COLUMN IF EXISTS relationship_detail;")
    op.execute("ALTER TABLE dependents DROP COLUMN IF EXISTS gender;")
    op.execute("ALTER TABLE household_members DROP COLUMN IF EXISTS name;")
