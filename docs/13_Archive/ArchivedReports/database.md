# Database Reference

## Engine

PostgreSQL 16. All connections go through asyncpg via SQLAlchemy's async session.

## Schema

### `users`

| Column           | Type                  | Constraints              |
|------------------|-----------------------|--------------------------|
| id               | UUID (PK)             | default uuid_generate_v4 |
| email            | VARCHAR(255)          | UNIQUE NOT NULL          |
| hashed_password  | VARCHAR(255)          | NOT NULL                 |
| full_name        | VARCHAR(255)          | nullable                 |
| is_active        | BOOLEAN               | NOT NULL default true    |
| is_verified      | BOOLEAN               | NOT NULL default false   |
| created_at       | TIMESTAMPTZ           | NOT NULL default now()   |
| updated_at       | TIMESTAMPTZ           | NOT NULL default now()   |

Index: `ix_users_email` on `email`.

### `goals`

| Column               | Type                          | Constraints                     |
|----------------------|-------------------------------|----------------------------------|
| id                   | UUID (PK)                     | default uuid_generate_v4        |
| user_id              | UUID (FK → users.id CASCADE)  | NOT NULL                        |
| name                 | VARCHAR(255)                  | NOT NULL                        |
| category             | ENUM goal_category            | NOT NULL                        |
| target_amount        | FLOAT                         | NOT NULL                        |
| current_amount       | FLOAT                         | NOT NULL default 0              |
| target_date          | DATE                          | NOT NULL                        |
| monthly_contribution | FLOAT                         | NOT NULL default 0              |
| risk_profile         | ENUM risk_profile             | NOT NULL default 'balanced'     |
| priority             | INTEGER                       | NOT NULL default 1              |
| on_track             | BOOLEAN                       | NOT NULL default true           |
| probability          | FLOAT                         | NOT NULL default 0              |
| is_active            | BOOLEAN                       | NOT NULL default true           |
| created_at           | TIMESTAMPTZ                   | NOT NULL default now()          |
| updated_at           | TIMESTAMPTZ                   | NOT NULL default now()          |

Indexes: `ix_goals_user_id`.

**Enum `goal_category`:** `retirement` | `education` | `home` | `travel` | `wealth` | `emergency`

**Enum `risk_profile`:** `conservative` | `balanced` | `aggressive`

### `simulations`

| Column               | Type                           | Constraints                       |
|----------------------|--------------------------------|-----------------------------------|
| id                   | UUID (PK)                      | default uuid_generate_v4         |
| user_id              | UUID (FK → users.id CASCADE)   | NOT NULL                         |
| goal_id              | UUID (FK → goals.id CASCADE)   | nullable                         |
| num_simulations      | INTEGER                        | NOT NULL                         |
| initial_amount       | FLOAT                          | NOT NULL                         |
| monthly_contribution | FLOAT                          | NOT NULL                         |
| years_to_goal        | FLOAT                          | NOT NULL                         |
| risk_profile         | VARCHAR(50)                    | NOT NULL                         |
| success_rate         | FLOAT                          | NOT NULL                         |
| p10                  | FLOAT                          | NOT NULL                         |
| p25                  | FLOAT                          | NOT NULL                         |
| p50                  | FLOAT                          | NOT NULL                         |
| p75                  | FLOAT                          | NOT NULL                         |
| p90                  | FLOAT                          | NOT NULL                         |
| distribution         | JSONB                          | NOT NULL default '{}'            |
| created_at           | TIMESTAMPTZ                    | NOT NULL default now()           |

Indexes: `ix_simulations_user_id`, `ix_simulations_goal_id`.

## Milestone 1: Family, Household & Government Policy Engine Foundation

Added via migration `005_family_policy_foundation` (2026-07-06). Purely additive — zero existing tables or columns were changed. Full design rationale: `DatabaseDesignReport.md`; verified source data: `GovernmentPolicyReport.md`.

**Household / Family:** `households`, `household_members` (`user_id` nullable — a dependent with no login, e.g. a minor child, can still be a household member), `dependents`.

**Government Policy Engine (versioned, never hardcoded):** `schemes` (`status`: `active` | `closed_to_new` | `sunset`), `scheme_rates` (effective-dated numeric facts — interest rates, contribution limits), `scheme_eligibility_rules`, `tax_acts`, `tax_sections` (models the Income-tax Act 1961 → 2025 renumbering, e.g. Section 80C → Section 123, both independently queryable by effective date), `tax_regimes`, `tax_slabs`, `policy_citations`.

**Estate / Nominee:** `huf_entities` (`funding_source` is a required, enumerated field — HUF recommendations must be gated on a real funding source, not offered generically), `huf_coparceners`, `nominees` (per-asset, up to 3, `percentage_share` CHECK constraint `0 < share <= 100`, mirrors SEBI's May 2026 nomination rule), `estate_documents` (stores status only, never document content).

**Insurance:** `health_policies`, `health_policy_coverage` (separate from `assets` — floater pricing keys off the eldest covered member's age, a different calculation shape than a bank balance).

**Recommendation / Audit:** `recommendations` (`reasoning`, `confidence_score`, `alternatives_considered` JSON, `assumptions_used` JSON), `recommendation_citations` (links a recommendation to the exact `scheme_rates`/`tax_sections` row it relied on), `audit_logs` (generic before/after JSON diff).

Reference data (schemes, rates, tax acts/sections/slabs) is seeded via `backend/scripts/seed_policy_data.py` — idempotent, safe to re-run in any environment including production, since this is reference data every environment needs, not dev-only demo data.

## Foundation Reconciliation: HUF Ownership & Policy Engine Layers 2-3

Added via migration `006_foundation_reconciliation` (2026-07-06), resolving the HIGH-severity findings in `FutureCompatibilityAuditReport.md`. Full decision log: `FoundationReconciliationReport.md`.

**HUF financial ownership:** `income_sources`, `expenses`, `assets`, and `liabilities` each gained a nullable `huf_entity_id` FK (→ `huf_entities.id`, `ON DELETE SET NULL`) alongside their existing, unchanged, required `user_id`. `user_id` still resolves access control (which login manages the row); `huf_entity_id`, when set, marks the row as beneficially owned by that HUF rather than the individual — the distinction Tax Planning needs to compute an HUF's own tax position. Deleting an HUF nulls this column on its financial rows rather than deleting them (verified live against Postgres).

**Policy Engine Layers 2-3:** `best_practice_rules` (financial-planning conventions, each tagged with a `confidence` tier — verified / convention / unverified_flag — so a cited figure is never presented with the same confidence as an untested heuristic) and `company_policies` (Northstar's own product decisions — hard gates, soft preferences, ranking weights — stored as JSON `rule_definition` so a policy can reference Layer 1/2 facts loosely). Structural only: no seeded rows, no ranking/recommendation logic — that belongs to the Recommendation Engine milestone.

**Two pre-existing fields marked deprecated, not changed:** `user_profiles.dependents`/`marital_status` (superseded by the `household_members`/`dependents` entities) and `financial_assumptions.tax_rate` (superseded by `tax_slabs`/`tax_regimes`; confirmed via grep that no service currently reads this field). Both carry inline deprecation comments naming their replacement; neither was removed, to avoid any API or behavior change. See `FoundationReconciliationReport.md`'s Decision Log for the migration plan for eventual removal.

## Milestone 2, Task 1: Family Goal Tagging Schema

Added via migration `007_family_goal_tagging` (2026-07-06), per `Milestone2ImplementationContract.md` §0. Schema-only — no router/service/frontend yet; see `PROJECT_STATE.md`'s Milestone 2 section for what's built vs. pending.

**`goal_household_members`** (new table): a purely descriptive `goal_id` ↔ `household_member_id` tag (`UNIQUE` pair, both FKs `ON DELETE CASCADE`) answering "who does this goal affect" for the Family Goals screen. **Not a joint-ownership model** — `goals.user_id` remains the sole owner of record for every purpose (tax attribution, contribution tracking, access control); this table only drives a "grouped by household member" display and a mandatory UI disclosure that the goal still belongs to one account.

**`goals.custom_inflation_rate`** (new nullable column): per-goal override of `financial_assumptions.inflation_rate`, for education/medical goals that run 2.5-3x general inflation. `NULL` (the default for every existing goal) means "use the global rate," unchanged.

**`dependents.has_own_insurance`** (new nullable column, `'yes'|'no'|'not_sure'`): captures whether a parent-type dependent already has their own health coverage — feeds the (not-yet-built) Family Insurance recommendation. Not applicable to every `dependent_type`; enforced at the application layer when that logic is built, not a DB constraint.

## Milestone 2, Task 2: Household & Member Service (blocker-fix schema + backend/API)

Added via migration `008_household_member_name` (2026-07-06). Three more nullable, additive fields were discovered missing while implementing Task 2's service layer, resolved in this single migration rather than three incremental ones since all three were found in the same pass:

**`household_members.name`** — the only other source of a name (`User.full_name` via `household_members.user_id`) doesn't cover the common case Milestone 2 is built around: a spouse, child, or dependent parent has no login (`user_id` stays `NULL`), per `FamilyPlanningDesign.md`'s explicit design. For `relationship_type='self'`, this column stays `NULL` and the API resolves the name from the `User` record instead, so it's never duplicated.

**`dependents.gender`** — drives the (not-yet-built, Task 3) SSY eligibility check for child-type dependents.

**`dependents.relationship_detail`** — `'mother'`/`'father'` for parent-type dependents, free text for other-type; distinct from `household_members.relationship_type` (the coarse spouse/child/parent/other bucket).

**Corrected assumption:** `Milestone2ImplementationContract.md` originally stated spouse-type members don't get a `Dependent` row. Implementation found this doesn't work — a spouse's `date_of_birth`/`gender` have nowhere else to live — so every non-`self` `HouseholdMember` now gets exactly one `Dependent` row, including spouse (`dependent_type='spouse'`).

**Backend built this task:** `app/services/family_service.py`, `app/routers/family.py` (`/api/v1/family/*`), `app/schemas/family.py`. Household-ownership resolution (`resolve_owned_household`/`get_or_create_household`) is the first authorization pattern in this codebase for data not keyed directly to the caller's own `user_id` — see `RiskChecklist.md` #2. No frontend yet (Tasks 4/5).

## Milestone 2, Task 3: Scheme Eligibility Rules (seed data) + Evaluation Service

**Blocker resolved (see `DependencyValidationReport.md`):** `scheme_eligibility_rules` had zero rows — Milestone 1's seed script never populated it. Extended `backend/scripts/seed_policy_data.py` with exactly three rows, each directly quoting `GovernmentPolicyReport.md`:

| Scheme | rule_type | operator | value | Verified source |
|---|---|---|---|---|
| SSY | `max_age` | `lt` | `10` | "Girl child must be under 10 at account opening" |
| SSY | `gender` | `eq` | `female` | "Resident parent/legal guardian of a girl child" |
| SCSS | `min_age` | `gte` | `60` | "Individuals 60+" (base case only) |

**Deliberately not seeded:** SCSS's two verified special-case routes (55+ for VRS retirees, 50+ for defense personnel) — this app has no field anywhere recording retirement or defense-service status, so a rule for either fact could never be evaluated. Seeding one would silently never match, which is worse than not seeding it. See the seed script's own docstring.

**New service:** `app/services/scheme_eligibility_service.py` — `evaluate_household_eligibility()` (the full three-bucket eligible/potentially_eligible/not_eligible evaluation, for the future Schemes screen, Task 11) and `check_ssy_eligibility()` (a narrow single-child helper reusing the same rule logic, wired into `family_service.create_member`/`update_member` so the Add-Child inline SSY callout — Task 2's endpoint, previously stubbed empty — now returns real, live-sourced results). Evaluates only non-`self` household members (spouse/child/parent/other, the ones with a `Dependent` row) — a `self` member's own age lives on `UserProfile`, a different join this task's two illustrative use cases don't require; a documented future extension, not a bug.

**Age calculation uses exact calendar-date arithmetic**, not a `days / 365.25` approximation — the latter was found, during test-writing, to drift across an exact age boundary (e.g. a child's precise 10th birthday) depending on how many leap days happen to fall in the specific span being measured. Fixed before merge, not left as a latent precision bug.

## Relationships

```
users ──< goals ──< simulations
users ──< simulations
```

- A user owns many goals (1:N, cascade delete)
- A goal owns many simulations (1:N, cascade delete)
- A simulation may belong to a user without a specific goal (for ad-hoc what-if runs)

## Migrations

Migrations are managed by Alembic. All schema changes must be expressed as Alembic revisions.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing a model
alembic revision --autogenerate -m "add risk_tolerance column"

# Roll back one step
alembic downgrade -1

# Show migration history
alembic history --verbose
```

Never modify the database schema manually in production.

## Soft Delete Pattern

Goals are never hard-deleted. Setting `is_active = false` hides a goal from all API responses while preserving simulation history. This avoids FK violations and supports undo.

## Connection Pooling

Production pool settings (configurable via `.env`):

| Setting              | Default |
|----------------------|---------|
| pool_size            | 10      |
| max_overflow         | 20      |

Total max connections: 30 per application instance.

## Backup

Recommended: `pg_dump` to S3 nightly with point-in-time recovery enabled on managed PostgreSQL (e.g. AWS RDS, Supabase).

```bash
pg_dump -Fc northstar > northstar_$(date +%Y%m%d).dump
```
