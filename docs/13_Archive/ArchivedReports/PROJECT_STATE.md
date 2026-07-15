# Project State

**Purpose:** Tracks implementation milestone status across the multi-milestone transformation plan (see `ProductRoadmapReport.md` / `PrioritizedBacklog.md` for the research-phase origin of this plan). Updated after every completed milestone, per the implementation directive's documentation requirement.

---

## Milestone Status

| Milestone | Status | Completed |
|---|---|---|
| **1 — Foundation** | ✅ Complete | 2026-07-06 |
| **Foundation Reconciliation** | ✅ Complete | 2026-07-06 |
| 2 — Family Financial Planning | 🚧 In Progress (Task 1/12 complete) | — |
| 3 — Government Policy Engine (logic/lookup) | Not started | — |
| 4 — Calculation Engine | Not started | — |
| 5 — Recommendation Engine | Not started | — |
| 6 — AI Financial Advisor | Not started | — |
| 7 — Scenario Planning | Not started | — |
| 8 — Document Intelligence | Not started | — |

---

## Milestone 1 — Foundation (Complete)

**Scope:** New database entities only — household/family, versioned government policy storage, estate/nominee, insurance, recommendation, and audit tables. No routers, no business logic, no UI. Per the milestone's own requirements: zero breaking changes, backward-compatible migration, seed data, rollback support.

### What Was Built

- **20 new tables** across 6 SQLAlchemy model files (`app/models/household.py`, `policy.py`, `estate.py`, `insurance.py`, `recommendation.py`, `audit.py`) — full list and rationale in `docs/database.md`'s new "Milestone 1" section and `DatabaseDesignReport.md`.
- **Migration `005_family_policy_foundation`** — additive only, verified upgrade/downgrade/upgrade cycle against the real dev database with existing data intact throughout.
- **Seed script `backend/scripts/seed_policy_data.py`** — populates verified government scheme rates and tax data (PPF, EPF, NPS, SSY, SCSS, NSC, KVP, APY, PMVVY; both tax Acts; new-regime tax slabs) sourced exclusively from `GovernmentPolicyReport.md`. Deliberately does **not** seed the old tax regime's full slab structure or the 2025 Act's Section 80CCD(1B) mapping — both were flagged as unverified in that report, and inventing them would violate the "never invent financial policies" rule.
- **14 new tests** (`tests/test_household_policy_models.py`) covering relationships, cascade deletes, and the `nominees.percentage_share` CHECK constraint (0 < share ≤ 100).

### Validation Evidence

```
Backend tests:     178 passed (was 164 before this milestone), 96.98% coverage
Ruff (app/):       All checks passed
mypy --strict:     Success, no issues found in 46 source files
Frontend tsc:      Clean (unaffected — backend-only milestone)
Migration:         upgrade → downgrade → upgrade cycle verified against real Postgres;
                    existing user data (5 rows) confirmed intact throughout
Running server:    Picked up all changes with zero downtime/crash (live health check
                    confirmed after every model change)
```

### Zero Breaking Changes — How Verified

- No existing table, column, or index was altered — migration 005 is 100% `CREATE TABLE`/`CREATE INDEX`, no `ALTER`/`DROP` on anything pre-existing.
- Full backend test suite re-run after every batch of changes; all 164 pre-existing tests pass unchanged alongside the 14 new ones.
- The actual running dev server (not just the test suite) was queried live after the migration and model changes landed — `/health` continued returning `200 {"status":"ok","db":"ok"}` without a restart being required, confirming the running application tolerated the new tables without any disruption.

### Decision Log

- **HUF entities included in Milestone 1** even though the milestone brief's explicit entity list didn't name them separately (it named "Family entities" and "Nominee entities") — HUF is verified, gated, family-adjacent infrastructure from `FamilyHUFPlanningReport.md`/`DatabaseDesignReport.md`, and Milestone 2's brief explicitly requires "Inheritance" support, which depends on it. Reusing the already-designed, already-verified HUF schema now avoids a later schema patch.
- **`AI_CONVERSATIONS`/`AI_MESSAGES` and `notifications` deliberately deferred**, despite being designed in `DatabaseDesignReport.md` — the Milestone 1 brief doesn't list them, and they belong naturally to Milestone 6 (AI Advisor) and whichever milestone first needs a notification trigger, respectively. Building them now would be exactly the kind of "add abstractions before they're needed" the implementation principles warn against.
- **`ASSET_SOURCE_DETAIL`** (HNI/NRI extension table) also deferred for the same reason — narrow-reach per `FeatureGapAnalysisReport.md`, not needed until those specific features are scheduled.
- **Old tax regime's slab structure intentionally incomplete** (only the ₹2.5L basic exemption seeded) — `GovernmentPolicyReport.md` verified only that figure, not the full bracket table. Seeding fabricated numbers to "complete" the picture would violate the explicit "do not invent financial policies" rule; the gap is documented in the seed script's own docstring so it isn't silently forgotten.

### Next Milestone (superseded — see Foundation Reconciliation below before starting)

---

## Foundation Reconciliation (Complete)

**Scope:** Architecture reconciliation only, per a dedicated Future Compatibility Audit (`FutureCompatibilityAuditReport.md`) run against Milestone 1. Resolved all four HIGH-severity findings from that audit. No Milestone 2 feature work, no recommendation logic, no routers, no UI. Full detail: `FoundationReconciliationReport.md` (decision log + architectural/database review), `FutureCompatibilityAuditReport_v2.md` (re-verdicted per-milestone compatibility).

### What Was Built

- **Migration `006_foundation_reconciliation`** — additive only:
  - Nullable `huf_entity_id` FK (→ `huf_entities.id`, `ON DELETE SET NULL`) added to `income_sources`, `expenses`, `assets`, `liabilities` — resolves Finding B (HUF entities couldn't hold their own financial data).
  - New tables `best_practice_rules`, `company_policies` — resolves Finding D (Policy Engine Layers 2-3 missing; the Recommendation Engine milestone's ranking logic depends on them). Structural only, no seeded rows, no logic.
- **Two legacy fields marked deprecated in code** (no schema change): `user_profiles.dependents`/`marital_status` (Finding A) and `financial_assumptions.tax_rate` (Finding C) — each carries an inline comment naming its authoritative replacement and pointing to the documented migration plan.
- **7 new tests** (`tests/test_foundation_reconciliation.py`) — HUF ownership defaulting to NULL, HUF attribution, `ON DELETE SET NULL` survival (the DB-level null-out half verified separately, live, against real Postgres — see below), and `company_policies.policy_code` uniqueness.

### Validation Evidence

```
Backend tests:     185 passed (was 178 before reconciliation), 97.05% coverage
Ruff (app/):       All checks passed
mypy --strict:     Success, no issues found in 47 source files
Frontend tsc:      Clean (unaffected)
Migration:         upgrade → downgrade → upgrade cycle verified against real Postgres
ON DELETE SET NULL: Verified live (INSERT/DELETE/SELECT in a rolled-back transaction) —
                    SQLite's test backend doesn't enforce this without a pragma this
                    suite doesn't set, so this specific behavior was checked against
                    the real target database directly rather than assumed
Orphan check:      0 orphaned huf_entity_id references across all 4 modified tables
Running server:    Zero downtime through every change
```

### Decision Log Summary (full reasoning in `FoundationReconciliationReport.md`)

- **Finding A/C (duplicate sources of truth):** legacy fields kept, marked deprecated, authority declared, migration plan documented — not physically resolved, per the task's own instruction that a documented deprecation is an acceptable resolution.
- **Finding B (HUF ownership):** a nullable `huf_entity_id` sibling column, not parallel HUF tables (rejected: unnecessary duplication) and not a polymorphic `Owner` supertype (rejected: premature generalization for a third owner type that isn't concretely planned; would require breaking `user_id`'s existing FK target).
- **Finding D (Policy Engine):** built the two missing tables now, since the Recommendation Engine milestone's own design depends on them and building them now avoids that milestone needing its own reconciliation pass first.

### Findings Deliberately Left Open

Findings E, F, G, H, I, J, K, M from the original audit were **not** in scope for this reconciliation (only the four HIGH findings were authorized) and remain open. Most relevant going forward: **Finding E** (no joint-goal/joint-income ownership model) will need a small schema addition early in Milestone 2; **the tax-regime-election field gap** (noted in the original audit's Tax Planning section, never one of the four authorized findings) will need one before Milestone 4 can fully ship. Both are small, additive, already-identified — not surprises waiting to be discovered mid-milestone.

### Next Milestone (superseded — see Milestone 2 progress below)

Milestone 2 (Family Financial Planning) can now proceed. Per `FutureCompatibilityAuditReport_v2.md`, it is **Partially Supported** — recommend resolving Finding E (joint ownership) early within that milestone rather than treating it as a late surprise, since it's the one schema gap in an otherwise-ready foundation.

---

## Milestone 2 — Family Financial Planning (In Progress)

**Scope:** Per the approved `Milestone2ImplementationContract.md` and `ImplementationChecklist.md` — implemented exactly one task at a time, never combining unrelated work, per the standing "one feature at a time" instruction. This entry covers Task 1 only.

### Task 1 — Migration: Milestone 2 Schema Additions (✅ Complete, 2026-07-06)

**What was built:** The three additive schema changes specified in `Milestone2ImplementationContract.md` §0, resolving the schema gaps identified while writing that contract:

- **Migration `007_family_goal_tagging`** — additive only:
  - New table `goal_household_members` (join table, `UNIQUE(goal_id, household_member_id)`, both FKs `ON DELETE CASCADE`) — a purely descriptive "who this goal affects" tag. `goals.user_id` remains the sole owner of record; this table never changes goal ownership.
  - `goals.custom_inflation_rate` (nullable float) — per-goal override of `financial_assumptions.inflation_rate` for education/medical goals.
  - `dependents.has_own_insurance` (nullable varchar(10): `yes`\|`no`\|`not_sure`) — captures a parent-dependent's existing insurance status, feeding the future Family Insurance recommendation (Task 10).
- **New model** `app/models/goal_household_member.py` (`GoalHouseholdMember`) — deliberately no `relationship()` back-references added to `Goal`/`HouseholdMember` yet; that wiring belongs to Task 8 (the actual tagging feature), not this schema-only task.
- **10 new tests** (`tests/test_family_goal_tagging_schema.py`) — column defaults, all three `has_own_insurance` values, unique-constraint rejection, and cascade-delete behavior (the DB-enforced half verified live against real Postgres, same documented pattern as the Foundation Reconciliation's `ON DELETE SET NULL` case — SQLite's test backend doesn't enforce FK cascade without a pragma this suite doesn't set).

### Validation Evidence

```
Backend tests:     195 passed (was 185 before this task), 97.07% coverage
Ruff (app/):       All checks passed
mypy --strict:     Success, no issues found in 48 source files
Frontend tsc:      Clean (unaffected — schema-only task, no frontend/API work yet)
Migration:         upgrade → downgrade → upgrade cycle verified against real Postgres
Cascade delete:    Verified live (INSERT × 5 / DELETE / SELECT in a rolled-back
                    transaction) — deleting a goal left 0 remaining
                    goal_household_members rows
Orphan check:      0 orphaned goal_id/household_member_id references
Running server:    Zero downtime through every change
```

### Self-Review

- **What changed?** Three additive schema elements only — one new join table, two new nullable columns on existing tables. No router, no service, no API, no frontend.
- **Why?** These three gaps were discovered while writing `Milestone2ImplementationContract.md` §0 — the approved Family Planning UX (goal tagging, education-goal inflation, the parent-insurance-status question) cannot be built on the certified Foundation schema alone. Building them first, isolated from any feature logic, lets every subsequent task assume the schema already exists.
- **What risks remain?** None new beyond what `RiskChecklist.md` already names for the tasks that consume this schema (Tasks 8, 9, 10) — this task itself is low-risk, purely additive, and fully tested.
- **How was it tested?** Model-level unit/integration tests (10 new, SQLite) + live verification of DB-enforced cascade behavior against real Postgres (rolled back, no data left behind) + full existing suite re-run (195/195) + migration up/down/up cycle + orphan-record check + live server health check.
- **What documentation changed?** This entry; `docs/database.md`'s new Milestone 2 section (below); `CHANGELOG.md`.
- **What future features depend on this?** Task 8 (Family Goals tagging) depends on `goal_household_members`; Task 9 (Education Planning) depends on `goals.custom_inflation_rate`; Task 10 (Family Insurance) depends on `dependents.has_own_insurance`. No task before Task 8 depends on this schema being present (Tasks 2-7 use only certified Foundation tables).

**Stopping here per instruction. Task 2 (Household & Member service + router) has not been started and requires separate review/approval before beginning.**

---

### Task 2 — Household & Member Service + Router (✅ Complete, 2026-07-06)

**What was built:** `/api/v1/family/*` — `onboarding-seed`, `GET /family` (with lazy-provision), and full member CRUD (`POST/PUT/GET/DELETE /family/members[/{id}]`). `app/services/family_service.py`, `app/routers/family.py`, `app/schemas/family.py`.

**Blocker discovered and resolved (see `docs/database.md`'s Task 2 section for full detail):** while validating dependencies before writing code, found that `household_members`/`dependents` had no field to store a person's **name** — the only realistic case in Milestone 2 (a spouse/child/parent with no login). User approved folding the fix into Task 2. While implementing, two more gaps in the same category surfaced (`gender`, a relationship-detail field for mother/father/free-text) — resolved together in one migration (`008_household_member_name`) rather than three incremental ones. Also corrected `Milestone2ImplementationContract.md`'s assumption that spouse-type members don't get a `Dependent` row — they do now, since that's the only place a spouse's DOB/gender can live.

**Frontend: intentionally not built this task** — per `ImplementationChecklist.md`, the Onboarding Family Step (Task 4) and Family Home screen (Task 5) are separate, later tasks. Building them now would combine unrelated checklist tasks into one PR.

**`eligible_schemes` intentionally always empty** — the shared scheme-eligibility service is Task 3's scope; returning the field (rather than omitting it) keeps the response shape stable for when Task 3 lands, without duplicating eligibility logic now.

### Validation Evidence

```
Backend tests:     221 passed (was 195 before this task), 96.94% coverage
Ruff (app/):       All checks passed
mypy --strict app/: Success, no issues found in 51 source files
Frontend tsc:      Clean (unaffected)
Migration:         upgrade → downgrade → upgrade cycle verified against real Postgres,
                    re-run after the mid-task amendment (name + gender + relationship_detail)
Live server:       New router live via auto-reload, zero restart — confirmed via
                    OpenAPI schema listing all 4 new paths and a live 403 on GET /family
                    with no auth header
Full suite:        26/26 new family-router tests pass, including 4 explicit
                    cross-household negative-path tests (RiskChecklist.md #2)
```

### Reviews

**Design Review** (new permanent stage, applied here for the first time — no UI exists yet this task, so this review covers the API's user-facing surface: field names, error messages, and the shape a future screen will consume):
- Does this reduce financial anxiety? N/A directly (no UI), but the API shape supports it: incomplete members are clearly flagged (`is_complete`), never silently hidden.
- Is it understandable without financial knowledge? Field names (`has_own_insurance`, `relationship_detail`) are plain language, not jargon.
- Does it increase trust? The `eligible_schemes: []` (always empty this task) is honest — it doesn't fabricate a scheme match before Task 3 exists.
- Simpler interaction? The lazy-provision pattern (every Family endpoint silently creates a household on first use) removes a whole class of "set up your household first" friction the Contract didn't explicitly ask for but which follows directly from `UX_PRINCIPLES.md` #11 (empty states are normal states).
- Consistent with the rest of the product? Soft-delete, `is_active` filtering, and the audit-log-on-every-mutation pattern all match existing conventions exactly.

**Architecture Review:** Router stays thin (query + 404/400 checks only); all business rules (type-specific field requirements, dependent_type mapping) live in `family_service.py`, per `docs/ENGINEERING_CONSTITUTION.md` Rule 1. No duplicate logic — `eligible_schemes` deliberately deferred rather than half-implemented. Migration additive-only, per Rule 3.

**Security Review:** Household-ownership check applied to all 4 member endpoints, with 4 explicit cross-household negative-path tests (not just the happy path) — the first "act on data not keyed directly to user_id" pattern in this codebase, flagged in `RiskChecklist.md` #2 as needing exactly this scrutiny. Every mutation writes an `audit_logs` row (`household_created`, `family_member_added`, `family_member_updated`, `family_member_removed`).

**Performance Review:** Every query is a single indexed lookup or a two-table outer join bounded by realistic household size (2-8 rows) — no N+1 pattern introduced. No pagination needed at this scale, per the Contract's own Performance Baseline.

**Self-Review:**
- **What changed?** New `/api/v1/family/*` endpoints (backend + API only, per Task 2's scope) plus a 3-column schema correction (`household_members.name`, `dependents.gender`, `dependents.relationship_detail`) discovered while implementing.
- **Why?** To make the household/member CRUD the Contract specifies actually possible — the schema correction was a precondition, not a scope expansion.
- **What risks remain?** None new beyond what `RiskChecklist.md` already tracks. The household-ownership pattern is new but is the most heavily negative-tested part of this task.
- **How was it tested?** 26 new integration tests (happy path, validation failures, cross-household denial, soft-delete, self-member protections) + full 221-test regression + migration cycle + live server verification.
- **What documentation changed?** `docs/database.md`, `docs/backend.md`, this entry, `CHANGELOG.md`.
- **What future features depend on this?** Task 4 (onboarding frontend) and Task 5 (Family Home frontend) consume these endpoints directly; Task 6 (Add Member frontend) also depends on Task 3 (eligibility service) for the SSY callout this task's `eligible_schemes` field stubbed out.

**Stopping here per instruction. Task 3 (Scheme eligibility evaluation service) has not been started and requires separate review/approval before beginning.**

---

### Task 3 — Scheme Eligibility Evaluation Service (✅ Complete, 2026-07-06)

**Blocker found and resolved (see `DependencyValidationReport.md`, approved before proceeding):** `scheme_eligibility_rules` had zero rows — Milestone 1's seed script never populated it. Extended `seed_policy_data.py` with three rows (SSY `max_age<10` + `gender=female`; SCSS `min_age>=60`), each a direct quote from `GovernmentPolicyReport.md`. SCSS's verified 55+/50+ special-case routes deliberately not seeded — no field anywhere records retirement/defense-service status to evaluate them against.

**What was built:** `app/services/scheme_eligibility_service.py` — `evaluate_household_eligibility()` (full three-bucket household view, for Task 11) and `check_ssy_eligibility()` (single-child helper, reusing the same rule logic). Wired into Task 2's already-shipped `PUT/POST /family/members` endpoints, which previously stubbed `eligible_schemes` empty — completing that field exactly as it was designed to be completed (see `ContractDeviationReport.md` Deviation 3), not a new router.

**Real bug caught during test-writing, fixed before merge:** age was originally computed as `(as_of - dob).days / 365.25` — an approximation that drifts across an exact age boundary depending on leap-day count in the specific span measured. A test for the exact 10th-birthday case failed under this approximation; replaced with exact calendar-date arithmetic. This is exactly the kind of "age-boundary precision" risk `ImplementationChecklist.md` flagged for this task in advance — caught by writing the boundary test, not by luck.

**Governance documents checked, no conflict found:** `ENGINEERING_CONSTITUTION.md` Rule 7 (no premature abstraction — only 3 rule_types built, matching seeded data) and Rule 4 (never invent — SCSS's special cases left unseeded rather than guessed) both directly informed this task's scope and were consistent with each other and with `PRODUCT_PRINCIPLES.md`/`UX_PRINCIPLES.md` throughout. No stop-and-report-conflict situation arose.

### Validation Evidence

```
Backend tests:     234 passed (was 221 before this task), 96.89% coverage
Ruff (app/):       All checks passed
mypy --strict app/: Success, no issues found in 52 source files
Frontend tsc:      Clean (unaffected)
Seed script:       Extended, run against real Postgres, idempotent re-run confirmed
                    (still exactly 3 rows after a second run)
Live smoke test:   Real user, real 7-year-old daughter via the actual running
                    server + Postgres → SSY correctly returned in eligible_schemes,
                    citing the real seeded rate/rule data. A 7-year-old boy and a
                    12-year-old girl both correctly returned empty. Smoke-test
                    data cleaned up afterward.
Boundary tests:    Exact 10th birthday → not eligible; one day younger → eligible.
                    Both directions of the boundary explicitly tested, not just one.
Running server:    Zero downtime through every change
```

### Reviews

**Design Review** (full report: `DesignReview.md`) — reviewed from Apple/Linear/Financial Planner/Accessibility/First-time-user/Parent/Senior-citizen perspectives. Two concrete decisions made and recorded: the 5-year "potentially eligible" window (a product decision, not a policy fact), and SCSS's unmodeled special cases staying a code/docs-level disclosure rather than user-facing caveat text (balances Linear's transparency instinct against `UX_PRINCIPLES.md` #4's "never overwhelm," siding with not overwhelming the ~95% of users the gap doesn't affect).

**Architecture Review:** No duplicate logic — one rule-evaluation function (`_evaluate_rules_for_member`) serves both the household-wide view and the single-child inline check. No duplicate ownership — `scheme_eligibility_rules` remains the sole authority for eligibility facts, the service only reads it. Deliberately narrow (3 rule_types), per Constitution Rule 7.

**Security Review:** Read-only service, no new authorization surface (reuses Task 2's existing household-ownership resolution for the household-wide function). No PII beyond what's already captured elsewhere is exposed.

**Performance Review:** Household-wide evaluation is a small in-memory cross-product (household size × scheme count, e.g. 5×9=45 checks) over already-fetched rows — no new query-count risk. The inline single-child check is 2 additional small indexed queries per member create/update (scheme lookup + rule lookup), negligible.

**Accessibility Review:** N/A directly (no UI this task) — but the reason-string wording this task produces is the actual text a future screen renders verbatim; confirmed plain-language, self-contained, no reliance on visual context (Design Review).

**Code Quality Review:** `ruff`/`mypy --strict` clean. No premature generalization — `residency_status` (the third rule_type the Contract anticipated) has no branch built for it since nothing seeds it yet; adding an unused branch "for completeness" would have been exactly the premature abstraction the Constitution warns against.

**Product Review:** Trust — every reason string names the specific fact that decided it, never a generic "criteria not met" (reduces financial anxiety, satisfies `PRODUCT_PRINCIPLES.md` #2). Simplicity — "Not Eligible" schemes with no seeded rules yet (7 of 9) correctly fall to `not_eligible` with an honest "not yet configured" reason rather than a fabricated one. Explainability — the household-wide bucketing (eligible/potentially/not) is the direct data source Task 11's screen will render with zero further design work needed on the wording.

**Self-Review:**
- **What changed?** Seed script extended (3 new rows); new `scheme_eligibility_service.py`; Task 2's two member endpoints now call it instead of stubbing `eligible_schemes` empty.
- **Why?** Task 3's entire purpose — a rule-evaluation service needs real rules to evaluate, which required fixing a Milestone-1-era gap first (approved as a folded-in blocker fix, same pattern as Task 2).
- **What risks remain?** None new. The one real risk this task carried (age-boundary precision) was found and fixed via testing, not left open.
- **How was it tested?** 13 new unit/integration tests (every rule_type, both directions of the age boundary, the `closed_to_new` filter, the self-exclusion limitation, the no-rules-yet case) + full 234-test regression + live smoke test against the real running server and Postgres with cleanup after.
- **What documentation changed?** `docs/database.md`, `docs/backend.md`, this entry, `CHANGELOG.md`, plus `DependencyValidationReport.md`/`DesignReview.md`/`ContractDeviationReport.md` from this task's own process.
- **What future features depend on this?** Task 11 (Family Government Schemes screen) calls `evaluate_household_eligibility()` directly — no further backend work needed for that screen's data layer. Task 6 (Add Member frontend) can now render a real SSY callout instead of an always-empty one.

**Stopping here per instruction. Task 4 (Onboarding Family Step frontend) has not been started and requires separate review/approval before beginning.**

---

### Task 4 — Onboarding Family Step Frontend (✅ Complete, 2026-07-06)

**What was built:** Replaced the onboarding wizard's Family step (previously a "Marital status" dropdown + "Number of dependents" field, writing to the now-deprecated `user_profiles.marital_status`/`dependents`) with the approved 3-question + count design from `FamilyPlanningDesign.md` Part 3, wired to Task 2's `POST /family/onboarding-seed`.

- `code/src/lib/api.ts` — `seedFamilyOnboarding()` with a real-shaped mock fallback (mirrors the backend's self+spouse+children+parent row-creation behavior, per CLAUDE.md's "mock fallback must always work" rule).
- `code/src/components/onboarding/wizard-steps.tsx` — new `FamilyStepFormState` type; `StepFamily` rewritten as three Yes/No questions with a conditional children-count stepper (`UX_REVIEW.md`'s required revision #1) and a reassurance line ("You'll be able to add each child's name and details afterward in Family").
- `code/src/routes/onboarding.tsx` — new `familyStep` state, rewritten `handleFamily` (client-side validation before the API call, matching the existing `handleGoal` pattern) — `marital_status`/`dependents` removed from `ProfileFormState`/`DEFAULT_PROFILE` (confirmed via grep these were used nowhere else in `onboarding.tsx`/`wizard-steps.tsx`; `UserProfile`'s own type and `app.profile.tsx`'s unrelated usage of these fields were left untouched — out of this task's scope).

**User Trust Review (Step 4, done inline — no blocking issues, one small copy addition):** reviewed as first-time user, parent, married couple, senior citizen, financial advisor, accessibility expert. All personas found the copy clear, warm, and jargon-free. One improvement made: added the "you'll be able to add details afterward" reassurance line under the children-count field, since `UX_REVIEW.md`'s approved revision suggested either a stepper or that copy — implemented both.

**Design Review (Step 5):** Checked against `PRODUCT_PRINCIPLES.md` (progressive disclosure — three questions, not a census), `UX_PRINCIPLES.md` #1 (one primary action — dropped the redundant "Skip" button since defaulting every question to "No" already achieves the same effect losslessly), and `ENGINEERING_CONSTITUTION.md` (no new patterns invented — reused the existing `SelectField`/`InputField`/`NavRow` components rather than building new ones).

### Validation Evidence

```
Backend tests:     234 passed (unaffected — frontend-only task)
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on all touched lines (pre-existing violations in
                    untouched lines of the same files left as found, not
                    fixed — avoids unrelated-diff noise)
Live UI test:       Full click-through via Chrome automation against the
                    real running backend + Postgres: registered a real
                    user, answered Yes/Yes(2)/Yes on the three questions,
                    submitted, confirmed the wizard advanced to step 3
                    (Employment). Verified directly against Postgres:
                    exactly 5 household_members rows created (self, spouse,
                    2 children, 1 parent), matching the UI input exactly.
                    Test data cleaned up afterward.
Regression:        Confirmed via grep that marital_status/dependents are
                    used nowhere else in the onboarding wizard's other 9
                    steps — their removal from ProfileFormState cannot
                    have affected them.
```

### Reviews

**Architecture Review:** Frontend-only change, no backend/API/schema touched. Reuses Task 2's already-tested `onboarding-seed` endpoint as-is — no duplicate logic.

**Security Review:** No new attack surface — this screen only calls an already-reviewed, already-authenticated endpoint (Task 2). Client-side validation (`children_count` bounds) is a UX convenience; the server-side bound (`ValidationMatrix.md`) remains the real enforcement.

**Performance Review:** No new network calls beyond the one `onboarding-seed` POST this step already required; bundle impact is a net removal (one dropdown + one input replaced by three selects + a conditional input, no new dependencies).

**Accessibility Review:** All three Yes/No questions use the existing `SelectField` (a native `<select>`, keyboard- and screen-reader-accessible by default, no new custom widget introduced). The conditional children-count field is a real `<input>` with its own `<label>`, inserted into the DOM (not hidden via CSS), so it's reachable by both keyboard tab order and screen readers as soon as it appears.

**Product Review:** Trust — the reassurance copy under the children-count field directly addresses `UX_REVIEW.md`'s flagged risk (a multi-child household feeling under-registered). Simplicity — three questions, one conditional field, one primary action; matches the wireframe in `FamilyPlanningDesign.md` exactly. Explainability — the one-line "why we ask" at the top of the step (not per-question, matching the approved design) sets expectations before any input is requested.

**Self-Review:**
- **What changed?** One onboarding wizard step's UI and its backend call — nothing else.
- **Why?** `user_profiles.marital_status`/`dependents` were marked deprecated in the Foundation Reconciliation; continuing to write to them from new code would have been building on a field this project already decided to move away from.
- **What risks remain?** None new. A pre-existing incidental note: killing a stale local dev-server process while setting up this session's live UI test required a restart — no data or code was affected, purely a local dev-environment hiccup, not a project risk.
- **How was it tested?** Full live browser click-through against the real backend + Postgres (not just tsc/eslint) — registered a real user, submitted real answers, confirmed the exact expected rows in the database, cleaned up afterward.
- **What documentation changed?** This entry, `CHANGELOG.md`.
- **What future features depend on this?** None block on this — Task 5 (Family Home screen) is independent frontend work; Task 6 (Add Member flows) depends on Tasks 2/3/5, not this one.

**Stopping here per instruction. Task 5 (Family Home screen) has not been started and requires separate review/approval before beginning.**

**Continuous Architecture Health checkpoint:** not yet due — 4 of 5 tasks completed since the last checkpoint (none yet run this milestone). Will trigger after Task 5.

---

## Stabilization Sprint (In Progress) — Product Consistency Critical Findings

**Trigger:** `ProductConsistencyAudit.md` (2026-07-06) identified 3 Critical findings via a full-application first-time-Indian-user walkthrough. Per explicit instruction, feature development (Milestone 2 Task 5 onward) is frozen until all three are resolved. Resolving one finding at a time, each with its own full lifecycle and stop-for-approval — same discipline as every prior milestone task.

### PCA-1 — Onboarding promises a "Family" destination that does not exist (✅ Resolved, 2026-07-07)

**Root cause:** Milestone 2 Task 4 (onboarding Family step) shipped before Task 5 (Family Home screen), per the approved one-feature-at-a-time sequencing. The Family step's own copy referenced "Family" as a place to add details later — correct relative to the approved design, but a dead reference in the currently-shipped product.

**Scope decision:** Building Task 5 now to fulfill the promise would be a new feature, explicitly forbidden this sprint. The only in-scope fix is to stop making a promise the product can't currently keep — a pure copy change, not a feature.

**What changed:** `code/src/components/onboarding/wizard-steps.tsx`, `StepFamily` component — two lines of copy:
- *"you can add full details anytime from Family"* → *"you don't need to add every detail right now"*
- *"You'll be able to add each child's name and details afterward in Family"* → *"You'll be able to add each child's name and other details later"*

Both changes remove the specific, currently-false destination reference while preserving the legitimate progressive-disclosure reassurance (`UX_PRINCIPLES.md` #2) that motivated the original copy. Per `UX_PRINCIPLES.md` #7 ("Honesty over polish") and `PRODUCT_PRINCIPLES.md` #7 ("Never claim capability the data model doesn't actually have," extended here to UI navigation capability).

**Design Review:** Checked against `PRODUCT_PRINCIPLES.md`, `UX_PRINCIPLES.md`, `ENGINEERING_CONSTITUTION.md` — no conflicts found. Minimal diff (Rule 7): exactly two lines of JSX text, no logic, no schema, no API involvement.

**Testing:**
```
Backend tests:  234 passed (unaffected — frontend-only change)
Frontend tsc:   Clean
Frontend eslint: Clean
Live smoke test: Registered a real user via the actual running app, reached
                 the Family step, confirmed both corrected lines render
                 exactly as written, confirmed the "Yes" branch's
                 children-count sub-copy also renders correctly. Test
                 account cleaned up afterward.
```

**User Trust Review:** From a first-time user's seat, the step now reassures without promising a specific place that doesn't exist — the intent of the original copy (you can skip depth now) survives; the broken part (a named destination) does not.

**Documentation:** This entry; `CHANGELOG.md`; `ProductConsistencyAudit.md` and `ProductConsistencyRoadmap.md` updated to mark PCA-1 Resolved.

**Stopping here per instruction. PCA-2 (Profile's deprecated Household field) has not been started and requires separate review/approval before beginning.**

---

### PCA-2 — Profile's Household field contradicted the family data just entered (✅ Resolved 2026-07-07)

**Investigation:** `DataSourceMigrationReport.md` — found the problem was worse than originally reported. PCA-2 was filed as a read-side issue, but the Profile form's Save button also **wrote** to the deprecated fields: the "Household" dropdown's canned strings were parsed backward via regex (`form.household.includes("Single parent")`, `match(/(\d+)\s*child/)`) into `marital_status`/`dependents` on every save, fully disconnected from the real household model. Also confirmed: no other screen duplicates this logic (grep-verified), and no frontend caller of the existing `GET /api/v1/family` endpoint existed yet.

**Adjacent, explicitly out-of-scope discovery:** the Risk Profile field on this same page shows a "Saved" confirmation but was never actually sent to any API in `handleSubmit` — a real, separate, pre-existing bug, unrelated to deprecated-field usage. Flagged in the migration report, not fixed here, per "resolve only PCA-2."

**What changed:**
- `code/src/lib/api.ts` — added `getFamilyHome()`, wrapping the existing `GET /api/v1/family` endpoint (Milestone 2 Task 2). No new backend API.
- `code/src/routes/app.profile.tsx` — removed `householdFromProfile()` (the deprecated mapping layer) and `HOUSEHOLD_OPTIONS`; the Household field now renders the real household members directly (name + relationship, e.g., "Priya · Spouse"), sourced from `getFamilyHome()`. Made read-only for this sprint, with copy that names no unbuilt destination: *"This reflects the family details you've shared and can't be edited here yet."* Removed the now-empty `api.upsertProfile({marital_status, dependents})` call from `handleSubmit` (nothing left to send once those two fields were removed) and the now-unused `api.getProfile()` call from the initial fetch.
- `docs/ENGINEERING_CONSTITUTION.md` — added Rule 11 (Deprecation Completion), citing this exact incident.

**Design Review:** `UX_PRINCIPLES.md` #7 (honesty over polish — real data, no broken edit affordance), `PRODUCT_PRINCIPLES.md` #7 (never claim capability the data model doesn't have), `ENGINEERING_CONSTITUTION.md` Rule 7 (no new summary-computation function — real members rendered directly instead).

**Testing:**
```
Backend tests:   234 passed (unaffected — no backend change)
Frontend tsc:    Clean
Frontend eslint: Clean on both touched files
Live smoke test: Registered a real user, answered Yes/Yes(2 children)/Yes during
                 onboarding, confirmed via direct API call that GET /api/v1/family
                 returned exactly 5 members (self, spouse, 2 children, parent)
                 matching the input. Navigated to Profile: household list matched
                 exactly — no more "2 adults" mismatch. Edited and saved the full
                 name field; confirmed via captured network requests that exactly
                 one call was made (PUT /api/v1/auth/me) and PUT /profile was
                 never called. Test account cleaned up afterward.
```
Note: the browser automation session disconnected mid-verification and was successfully reconnected without losing test state (the backend session/data were unaffected — only the browser control channel dropped).

**User Trust Review:** Household now shows exactly what the user told onboarding, every time — the exact contradiction PCA-2 identified no longer exists. The read-only note is honest about the current limitation without naming a place that doesn't exist (consistent with PCA-1's resolution).

**Documentation:** This entry; `CHANGELOG.md`; `docs/ENGINEERING_CONSTITUTION.md` Rule 11; `ProductConsistencyAudit.md`/`ProductConsistencyRoadmap.md` marked PCA-2 Resolved.

**Stopping here per instruction. PCA-3 (non-deterministic Monte Carlo recomputation on read) has not been started and requires separate review/approval before beginning — it also has its own mandatory pre-implementation investigation (Special Rule) per the sprint instructions.**

---

### PCA-3 — Non-deterministic Monte Carlo recomputation on read (✅ Resolved 2026-07-07)

**Investigation:** `MonteCarloConsistencyReport.md` — traced the complete execution path: `GET /dashboard` and `GET /reports/summary` both called `planning_service.get_dashboard()` → `refresh_goal_probabilities()`, which re-ran an unseeded 2,000-path simulation for every active goal and persisted the result on every view. `on_track` (derived from `probability >= 70.0`) could flip between page loads for a boundary-case goal with zero user action and zero audit trail. Also found: `settings.monte_carlo_seed` was already correctly wired into `/simulate`'s full engine but never into the fast `quick_probability`/`quick_probability_async` path used here — the seeding mechanism existed, it just wasn't reused.

**Decision:** `ArchitectureDecisionRecord.md` (ADR-001) — approved architectural rule, broader than the originally recommended minimal option: **read operations must never perform or persist financial calculations.** Monte Carlo execution is centralized behind the goal's actual Calculation Context changing (create/update), not behind any read.

**What changed:**
- `backend/app/services/planning_service.py` — removed `refresh_goal_probabilities()` (batch mutate-on-read). Added `calculate_goal_probability(goal)` — the single, centralized trigger, now seeded via `settings.monte_carlo_seed`. Added `_active_goals()` — a plain read-only fetch. `get_dashboard()` now calls only `_active_goals()`; it performs zero Monte Carlo passes.
- `backend/app/routers/goals.py` — removed the duplicate `_refresh_probability()`/`_years_to_goal()` implementation; `create_goal`/`update_goal` now call the centralized `planning_service.calculate_goal_probability()` — one Monte Carlo execution path, not two parallel ones.
- `backend/app/services/monte_carlo.py` — added `seed` parameter to `quick_probability`/`quick_probability_async` (previously accepted by `run_simulation`/`run_simulation_async` only), reusing the existing seeding mechanism `routers/simulate.py` already relied on, rather than introducing a new one.
- `backend/app/routers/reports.py` — updated a now-inaccurate code comment (previously described avoiding a second Monte Carlo pass; there are now zero).
- `docs/architecture.md` — new "Calculation Lifecycle" design-decision section documenting the rule.
- `docs/backend.md` — updated `quick_probability` description to reflect the two remaining legitimate callers (optimizer probes, centralized goal-probability calculation) and the seeding behavior.

**AI Copilot consumer check:** confirmed `routers/copilot.py` only reads `goal.probability` from already-fetched goal rows — no separate simulation call, no change needed. `/simulate` and `/simulate/optimize` were confirmed untouched and unaffected — different, correctly-designed code paths (append-only history, and read-only exploration respectively).

**Testing:**
```
Backend tests:   238 passed (was 234 — replaced 2 obsolete tests for the
                 removed batch-concurrency function with 4 new tests for
                 calculate_goal_probability/_active_goals; added 2 new
                 regression tests: repeated Dashboard/Reports reads never
                 change a goal's probability, and Dashboard/Reports agree)
Ruff / mypy --strict: clean on every touched file
Live verification: created a goal deliberately near the 70% on_track
                 boundary (81.7%), polled GET /goals, GET /dashboard, and
                 GET /reports/summary five times each — zero drift across
                 all three endpoints and all five rounds. Test account
                 cleaned up afterward.
```

**Verification against the sprint's explicit checklist:**
- Page refreshes never change financial results — confirmed (5-round live poll + new automated regression test).
- Dashboard and Reports always display identical probabilities for identical inputs — confirmed (both live and via automated test).
- Existing simulations remain valid — confirmed; no backfill/reset was needed or performed (per `MonteCarloConsistencyReport.md` §10).
- No unnecessary recalculations occur — confirmed; `get_dashboard()` contains zero calls to any Monte Carlo function.

**User Trust Review:** A goal's probability and on-track status are now stable across every screen, every refresh, indefinitely — the exact instability PCA-3 identified no longer exists, and the fix reduces (not adds) code, since two parallel per-goal calculation implementations became one.

**Documentation:** This entry; `CHANGELOG.md`; `docs/architecture.md`; `docs/backend.md`; `ArchitectureDecisionRecord.md` (ADR-001); `ProductConsistencyAudit.md`/`ProductConsistencyRoadmap.md` marked PCA-3 Resolved.

**All three Stabilization Sprint Critical findings (PCA-1, PCA-2, PCA-3) are now resolved. Per the sprint's closing instruction: stopping here. Feature development remains frozen until the user reviews this and explicitly approves resuming it.**

---

## Milestone 2 — Family Financial Planning (Resumed)

Milestone Resumption certified `READY TO RESUME` (`MilestoneResumptionCertification.md`) — all 8 remaining tasks re-verified against the Stabilization Sprint's changes, no blockers. Resuming at Task 5.

### Task 5 — Frontend: Family Home Screen (✅ Complete, 2026-07-07)

**Dependency validation (`BlockerReport.md`):** Task 5's own certified scope (`Milestone2ImplementationContract.md` §2) was not blocked — `GET /api/v1/family` (Task 2) and Task 4's onboarding data were both confirmed compatible and live-tested. However, this turn's brief asked for a broader 8-section "Family Financial Dashboard," 5 of which (Upcoming Family Goals, Insurance Status, Government Scheme Eligibility, AI Recommendations, Recent Changes) have no certified backend API yet — each is explicitly Task 8, 10, 11, or 12's scope, confirmed via `grep` across `backend/app/routers/` (zero matches for `family-tags`, `family/insurance`, `family/schemes`, `family/dashboard`). Resolved by implementing Task 5's real scope fully, and rendering the five unbuilt sections as honest, clearly-secondary "Coming soon" cards rather than fabricating data or silently omitting them.

**What was built:**
- `code/src/routes/app.family.index.tsx` — the real Family Home screen: household summary (a literal tally of the `relationship_type` values `GET /family` already returns — no independent bucketing), the member list (one card per member, completeness sourced directly from `member.is_complete`), Quick Actions, and the five "Coming soon" teasers.
- `code/src/routes/app.family.tsx` — converted to a thin `<Outlet/>` layout after discovering (live, via browser testing) that TanStack Router's file-routing convention nests `app.family.add.tsx`/`app.family.members.$id.tsx` under any `app.family.*` file — the original single-file version silently swallowed both child routes' content. Fixed by splitting exactly the way `app.tsx`/`app.index.tsx` already do.
- `code/src/routes/app.family.add.tsx`, `app.family.members.$id.tsx` — honest stub destinations ("coming soon," not a broken link or a fabricated form) for the two flows Tasks 6 and 7 will build.
- `code/src/lib/family.ts` — extracted `relationshipLabel`/`relationshipIcon` as shared helpers, refactoring `app.profile.tsx` to use them too, avoiding a second copy of PCA-2's own label mapping.
- `code/src/components/app-shell.tsx` — added "Family" to the sidebar nav (positioned per `FamilyPlanningDesign.md`'s concrete diagram, which disagrees with that same document's prose — flagged, diagram followed as the more specific artifact) and rebuilt the mobile bottom nav into `Dashboard · Goals · Family · Copilot · More`, with Reports/Profile/Settings behind a new accessible "More" popover.

**Bug found and fixed during implementation:** naive pluralization (`${label}s`) rendered "3 Childs" instead of "3 Children" — caught live during the first-time-user walkthrough, fixed with an explicit irregular-plural map.

**Reviews:**
- **Architecture Review:** No duplicate services/APIs/calculations introduced. `relationshipLabel`/`relationshipIcon` centralized rather than duplicated a second time. Consumes only certified APIs; zero backend changes.
- **Product Review:** Every section answers a real question (who's in my household / how many depend on me / what should I do next) — none is a vanity metric. The five deferred sections state their gap honestly rather than fabricating content, per `PRODUCT_PRINCIPLES.md` #7 — the same principle PCA-1/PCA-2 were built around.
- **User Trust Review:** Reviewed as first-time user, parent, married couple, senior citizen, financial advisor (see `FIRST_TIME_USER_REVIEW.md` addendum for the live walkthrough backing this). No card failed to answer a real question; none were removed as a result since all passed.
- **Accessibility Review:** Semantic `<h3>` per member name, `aria-hidden` emoji glyphs with real text labels (avoiding the double-announcement bug `UX_REVIEW.md` flagged in advance), visible focus rings verified live via keyboard tab order on both member cards and Quick Actions, `role="menu"`/`aria-expanded` on the new mobile "More" popover, `aria-busy`/`sr-only` loading and error states.
- **Performance Review:** Single `GET /family` call per page view (`useQuery`, 30s `staleTime`), no N+1, no client-side aggregation beyond a literal tally of already-fetched data.
- **Self-Review:** see below.

**Testing:**
```
Backend tests:     238 passed (unaffected — frontend-only task)
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Frontend unit/component tests: none exist in this codebase (no test runner
                   configured — confirmed via package.json) — consistent
                   with every prior frontend-only task this milestone;
                   verification is tsc + eslint + live browser walkthrough
Live smoke test:   Full first-time-user walkthrough via Chrome automation
                   against the real running backend + Postgres — registered
                   a real user, answered Yes/Yes(3 children)/Yes in
                   onboarding, opened Family Home, confirmed the household
                   summary and member list matched onboarding exactly
                   (6 people, correct relationship breakdown after the
                   pluralization fix). Cross-checked Profile showed
                   identical data. Tested both stub routes (member card tap,
                   both Quick Actions) render correctly after the routing
                   fix. Tested responsive layout at 375px, 768px, and 1440px
                   — mobile "More" menu opens/closes/navigates correctly.
                   Tested keyboard tab order — focus rings visible on
                   member cards and Quick Actions. Test account fully
                   cleaned up afterward.
```

**Self-Review:**
- **What changed?** One new real screen (Family Home) plus two honest stub destinations, a shared label helper, and the nav/mobile-nav restructuring the approved design required. No backend changes.
- **Why?** Task 5 per `Milestone2ImplementationContract.md` §2 and `FamilyPlanningDesign.md` Part 4.1 — the household member-list workspace onboarding has promised (post-PCA-1 fix) is finally reachable.
- **What risks remain?** None new. The routing bug found during implementation was fixed and verified before completion, not left as a known issue.
- **What is intentionally NOT implemented?** Real Add/Edit member forms (Task 6), Family Member Detail (Task 7), goal tagging, insurance, scheme eligibility, and AI recommendations (Tasks 8/10/11/12) — all honestly deferred per `BlockerReport.md`, none fabricated.
- **What assumptions were made?** That the design doc's concrete nav-order diagram should win over its own contradictory prose (flagged, not silently resolved); that literal relationship_type tallying (not a new summary function) satisfies "Household Summary" without violating the "no frontend calculation" rule, since it's a direct presentational transform of already-fetched data, not an inference.
- **What documentation changed?** This entry, `CHANGELOG.md`, `docs/frontend.md` (route table), `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md`, `PR_REPORT.md`.
- **What future features depend on this?** Tasks 6, 7, 8, 10, 11, 12 all build on this screen's existence and its stub destinations.

**Stopping here per instruction. Task 6 (Add Family Member flows) has not been started and requires separate review/approval before beginning.**

---

### Task 6 — Add Family Member Flows (✅ Complete, 2026-07-07)

**Note on instructions:** this task's brief referenced "MASTER_ENGINEERING_WORKFLOW.md" as the process to follow — confirmed via a full repository search that no such file exists anywhere in this codebase. Flagged transparently rather than silently fabricated or silently ignored; proceeded using the explicit four-review-then-implement sequence spelled out directly in the same instructions (Dependency Validation, Data Integrity Review, User Trust Review, Design Review), which is self-contained and consistent with this project's established discipline.

**Dependency Validation, Data Integrity Review, Design Review (combined, no blockers found):** Read the actual current `backend/app/schemas/family.py`, `backend/app/routers/family.py`, and `backend/app/services/family_service.py` rather than relying on `Milestone2ImplementationContract.md`'s illustrative JSON, which turned out to differ from the real schema (no `dependent_type` field at the request level; a real `is_tax_dependent` field the Contract's wireframes never mention). Confirmed: `POST`/`PUT /api/v1/family/members[/{id}]` (Task 2) already perform full server-side validation (`validate_member_fields`), already write the required audit log row on every mutation (`family_member_added`/`family_member_updated`, Task 2), and already compute SSY eligibility inline via Task 3's `scheme_eligibility_service` — Task 6 is a pure frontend consumer of already-certified, already-tested backend behavior; no backend work was needed or performed.

**What was built:**
- `code/src/components/family/FamilyMemberForm.tsx` — one shared form, branching by `relationshipType` (spouse/child/parent/other), with client-side validation mirroring (not duplicating the authority of) the backend's `validate_member_fields`.
- `code/src/routes/app.family.add.tsx` — real implementation (previously a stub): `POST /family/members` for net-new parent/other members, entered via Family Home's two persistent Quick Actions (`?type=parent`/`?type=other`).
- `code/src/routes/app.family.members.$id.tsx` — real implementation (previously a stub): fetches the member via `GET /family/members/{id}`, renders the same shared form pre-filled, saves via `PUT`. Completing a placeholder and editing an already-complete member are the same code path — matching Task 7's own contract spec, which says its future "Edit" button reuses this exact form rather than rebuilding one. A `relationship_type === "self"` guard shows a short redirect-to-Profile message instead of a form, since self can't be edited via this endpoint (backend returns 400).
- `code/src/lib/api.ts` — added `createFamilyMember`/`updateFamilyMember`/`getFamilyMember`, wrapping the three existing, certified endpoints. No new backend API.
- The SSY eligibility callout (`role="status"`) renders directly from the API response's `eligible_schemes` — never recomputed client-side.

**User Trust Review:** performed as first-time user, parent, married couple, senior citizen, financial advisor — see `FIRST_TIME_USER_REVIEW.md`'s new addendum for the live walkthrough. Headline result: the exact gap the Task 5 walkthrough flagged (Quick Actions leading to a generic stub) is now closed — each entry point opens a form that immediately acknowledges its own intent.

**Testing:**
```
Backend tests:     238 passed (unaffected — frontend-only task)
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a real user, answered Yes/Yes(1 child)/No in
                   onboarding, then: completed the Spouse placeholder (PUT,
                   Complete ✓ confirmed on return), completed the Child
                   placeholder with a girl born 2019 (PUT, SSY callout
                   rendered with the real backend's own reason text), added
                   a new Parent via the Quick Action (POST, ?type=parent,
                   client-side validation confirmed by submitting empty
                   first), and confirmed the household summary updated
                   correctly at every step (2 → 3 → 4 people) with no manual
                   refresh. Verified via a read-only database query that
                   exactly 4 audit log rows were written (1 household
                   creation + 2 updates + 1 add) and that the account's one
                   goal was completely untouched (updated_at predated every
                   family change) — confirming no unintended downstream
                   effects. Test account fully cleaned up afterward.
```

**Reviews:** Architecture (no duplicate logic — shared form, shared label helpers, zero new backend), Product (every form field carries an honest "why we ask," matching the approved design's tone), User Trust (see above), Accessibility (`role="status"` on the SSY callout — not `role="alert"`, per `UX_REVIEW.md`'s explicit finding; keyboard tab order verified live through both add and edit forms with visible native focus rings throughout), Performance (one GET + one mutation per save, cache invalidation instead of a full page reload), Self-Review below.

**Self-Review:**
- **What changed?** Two previously-stubbed routes now do real work; one new shared form component; three new API client functions wrapping existing endpoints. No backend changes.
- **Why?** Task 6 per `Milestone2ImplementationContract.md` §3-6 — the forms Task 5's stubs promised were coming.
- **What risks remain?** None new. No hidden technical debt: the shared form is reused by both the add and edit paths rather than duplicated, matching Task 7's own stated intent to reuse it too.
- **What is intentionally NOT implemented?** The full read-only Family Member Detail view (goals list, coverage list, Remove button) — that remains Task 7's scope; this task only replaces the stub with a working add/edit form.
- **What assumptions were made?** That Task 5's two Quick Action CTAs ("Add a parent," "Add someone else") are the only net-new-member entry points Milestone 2 designs for — confirmed against the Contract's own UI Components spec, which lists exactly these two and no "+Add a spouse/child" affordance.
- **What documentation changed?** This entry, `CHANGELOG.md`, `docs/frontend.md` (route table), `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum), `PR_REPORT.md`.
- **What future features depend on this?** Task 7 (Family Member Detail) reuses this task's shared form for its Edit button rather than rebuilding one.

**Stopping here per instruction. Task 7 (Family Member Detail) has not been started and requires separate review/approval before beginning.**

---

### Task 7 — Family Member Detail (✅ Complete, 2026-07-07)

**Note on referenced instructions:** this task, like Task 6, referenced a process document ("MASTER_ENGINEERING_WORKFLOW.md") that does not exist anywhere in this repository. Same handling as before: flagged transparently, proceeded using the explicit review sequence spelled out directly in the instructions (Dependency Validation, Identity Integrity Review, Data Integrity Review, User Trust Review, Design Review).

**Dependency Validation / Data Integrity Review (one genuine, narrow backend gap found and fixed):** `GET /api/v1/family/members/{id}` did not return `is_complete` — only the Family Home list endpoint did. Building the read-only-vs-form branching this task requires without that field would have forced the frontend to re-derive completeness from raw fields, duplicating `family_service.is_complete()`'s exact rule set — precisely the kind of second, drifting definition PCA-2 already taught this project to avoid. Resolved by renaming the private `_is_complete()` to a public `is_complete()` and calling it from `create_family_member`/`update_family_member`/`get_family_member` too — a field addition to three already-existing, already-certified endpoints, not a new backend API (the instruction's own "unless a verified blocker requires it" allowance was read narrowly: no new endpoint, no new route, no new business logic — the exact same pure function, just exposed one more place it was always meant to be read from).

**Identity Integrity Review:** Traced `update_family_member`/`delete_family_member` end to end — both operate strictly by `member_id` fetched via `get_member_and_dependent(household, member_id)`, scoped to the caller's own household; `PUT` never inserts, only updates the one row found. Added two new backend regression tests (`test_editing_never_creates_a_duplicate_member`, `test_editing_one_member_never_changes_another`) directly encoding this task's two explicit requirements ("edits update only the intended member," "no duplicate members through editing") as permanent, automated checks — not just a one-time manual verification.

**What was built:**
- `backend/app/services/family_service.py`, `schemas/family.py`, `routers/family.py` — the minimal `is_complete` field addition described above.
- `code/src/routes/app.family.members.$id.tsx` — rebuilt from Task 6's always-show-the-form version into: a real read-only detail view (header with name/relationship/DOB, "Goals involving X" with an honest empty state, "Health coverage" with an honest empty state, Edit and Remove actions) for complete members, while preserving Task 6's direct-to-form behavior for incomplete placeholders exactly as `Milestone2ImplementationContract.md` §2's Acceptance Criteria requires. Edit toggles to Task 6's shared form inline (reused, not rebuilt) with a Cancel path back to the read-only view. Remove uses an inline confirm toggle matching the codebase's real existing pattern (`GoalSimPanel.tsx`'s "Delete this goal" → "Are you sure? Yes/Cancel") — the Contract's text describing a focus-trapping modal doesn't match what actually exists in this codebase; the real pattern was followed instead of inventing new dialog infrastructure for one button. Focus returns to the Remove button on cancel (live-verified via keyboard).
- `code/src/lib/api.ts` — added `deleteFamilyMember` (wraps the existing, certified `DELETE /family/members/{id}`) and `is_complete` on `FamilyMemberDetail`.
- `backend/tests/test_family_router.py` — 5 new/extended tests: `is_complete` assertions on create/update/get responses, plus the two Identity Integrity regression tests above.

**User Trust Review:** performed as first-time user, parent, married couple, senior citizen, financial advisor — see `FIRST_TIME_USER_REVIEW.md`'s new addendum.

**Testing:**
```
Backend tests:     240 passed (was 238 — 2 new Identity Integrity tests;
                   3 existing tests extended with is_complete assertions)
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a real user, answered Yes/Yes(2)/No in
                   onboarding, completed the Spouse placeholder, then
                   opened the now-complete member's card — confirmed the
                   real read-only detail view (not the form) rendered:
                   header, "No goals tagged yet," "Not yet covered under
                   any policy," Edit and Remove buttons. Tested Edit →
                   pre-filled form → Cancel → back to the same detail view
                   unchanged. Tested Remove → inline "Are you sure?" →
                   Cancel → confirmed via keyboard that focus returned to
                   the Remove button. Tested Remove → Yes, remove →
                   navigated back to Family Home with the spouse gone and
                   the household summary correctly updated (4 → 3 people).
                   Verified via read-only database queries: the removed
                   member's row still exists with is_active=false (soft
                   delete, not hard delete); exactly the 3 expected audit
                   log rows existed (household_created, family_member_
                   updated, family_member_removed); the account's one goal
                   was completely untouched throughout. Completed one of
                   two child placeholders and confirmed live that the
                   sibling remained exactly as it was (untouched, still
                   incomplete) — Identity Integrity confirmed both live and
                   via the new automated tests. Confirmed via a final
                   database query that no duplicate member rows existed
                   after all edits (exactly 4 rows, matching the 4 distinct
                   people). Test account fully cleaned up afterward.
```

**Reviews:** Architecture (one shared form reused for both add and edit, per Task 6; the read-only view introduces no new backend dependency beyond the one justified field), Product (empty states teach rather than apologize — "No goals tagged yet," not a blank space), User Trust (see above), Accessibility (semantic `<h1>` for the person's name; Remove's confirm toggle returns focus to its trigger on cancel, live-verified via keyboard; native focus rings visible throughout), Performance (one GET per detail view; Edit/Remove reuse the same query-invalidation pattern Task 6 established), Self-Review below.

**Self-Review:**
- **What changed?** One backend field addition (`is_complete`, reusing an existing pure function) across 3 existing endpoints; one frontend route rebuilt from "always show the form" to "show the real detail view, with the form reachable via Edit." No new backend endpoints.
- **Why?** Task 7 per `Milestone2ImplementationContract.md` §7 — the read-only consolidated view (goals, coverage, edit/remove access) the design has always specified, which Task 6 deliberately deferred.
- **What risks remain?** None new. The two Identity Integrity requirements this task specifically called out are now permanent automated tests, not just a one-time manual check.
- **What is intentionally NOT implemented?** Tagged goals and coverage remain structurally empty until Tasks 8 (goal tagging) and 10 (insurance) ship — this task renders whatever the certified endpoints return today, honestly, per the same pattern `BlockerReport.md` established for Task 5.
- **What assumptions were made?** That the Contract's description of a "focus-trapping confirm dialog" was aspirational/imprecise relative to this codebase's actual, simpler existing pattern (`GoalSimPanel.tsx`) — followed the real precedent rather than inventing new dialog infrastructure for a single button.
- **What documentation changed?** This entry, `CHANGELOG.md`, `docs/backend.md`, `docs/frontend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Task 8 (goal tagging) will populate the "Goals involving X" section this task already renders; Task 10 (insurance) will populate "Health coverage" the same way — neither requires touching this screen's structure again.

**Stopping here per instruction. Task 8 (Family Goals tagging) has not been started and requires separate review/approval before beginning.**

---

### Task 8 — Family Goal Tagging (✅ Complete, 2026-07-07)

**Dependency Validation:** Confirmed `goal_household_members` (migration 007, Task 1) exists with the exact shape needed (`goal_id`, `household_member_id`, unique constraint, cascade deletes) and that `family_service.get_member_detail()` (Task 2/7) already queries it — no schema change required. Confirmed no `goal_service.py` file exists (the Checklist's text names one that was never actually created); goal CRUD lives inline in `routers/goals.py`, unchanged by this task except for one new endpoint.

**Goal Ownership Review (the central requirement of this task):** Traced every write path in the new `family_service.set_goal_household_tags()` — it touches only the `goal_household_members` join table (insert/delete rows), never reads or writes `goal.user_id`. `goals.user_id` is set exactly once, at creation, by the pre-existing `POST /goals` endpoint, completely untouched by this task's code. Verified with a permanent test (`test_tagging_never_changes_goal_owner`) and live (checked `GET /goals/{id}` before and after tagging — owner identical). No second ownership field, no "co-owner" column, no joint-ownership concept introduced anywhere.

**Data Integrity Review:**
- Confirmed the tagging endpoint reuses the caller's own household resolution (`family_service.get_or_create_household`) — the same function every other Family endpoint uses — rather than a second household-membership check. A `household_member_id` outside the caller's household returns 422, verified live and by a permanent test (`test_cross_household_member_id_rejected_not_silently_ignored`) that also confirms the goal's tag list is untouched afterward (not silently partially applied).
- Confirmed tagging never triggers `calculate_goal_probability` — this is not a Calculation Context change per `docs/architecture.md`'s Calculation Lifecycle (ADR-001), and Monte Carlo probability/on_track must stay exactly as computed at creation/last edit. Verified with a permanent test (`test_tagging_never_changes_goal_probability`) and live (probability/on_track identical before and after tagging in the browser).
- Confirmed repeated tagging with the same member never creates duplicate `goal_household_members` rows — the endpoint deletes the goal's existing tag rows and re-inserts the given set in one call, so the table's unique constraint is never at risk of being hit. Verified with a permanent test (`test_repeated_tagging_never_creates_duplicate_rows`, tags 3 times) and live (re-tagged the same goal twice with the same member, final tag count stayed 1 both in the UI and via a database query).
- Confirmed no recommendation logic exists to duplicate — the Family Dashboard/Recommendation Engine (Task 12, Milestone 5) hasn't been built yet, so there was nothing to reuse or risk duplicating here.

**User Trust Review:** The mandatory disclosure text ("This goal belongs to your account. [Name] can see it if you share access, but their own contributions aren't tracked separately yet.") renders on every goal with ≥1 tag, live-updating as checkboxes change, before the user even saves — confirmed for both a single name and two names joined naturally ("Anjali Rao and Vikram Rao"). See `FIRST_TIME_USER_REVIEW.md`'s new addendum for the full walkthrough, including one honest observation about how the same wording reads slightly oddly when a user tags themselves (not fixed — noted as a minor, non-blocking rough edge rather than over-engineering a self-specific variant of the sentence).

**Design Review:** The "who does this affect" control is a real `<fieldset>`/`<legend>` with checkboxes, per the Contract's accessibility requirement — not a custom chip-picker. Goals grouped by tagged member render the same goal under every group it's tagged with (display grouping only, confirmed live: tagging one goal with both household members made it appear under both "Anjali Rao" and "Vikram Rao" sections simultaneously, with only one underlying `goal_household_members` row per tag, not a duplicated goal).

**A genuine bug found and fixed during live verification (not by static review):** `GoalTagRow`'s local `selected` checkbox state was initialized once at mount from `goal.tagged_members` and never resynced. Because the same goal can render as multiple mounted instances (once per tagged-member section) that persist across a tag-change elsewhere, reopening the editor on an already-mounted instance showed stale, pre-change checkbox state — live-caught when re-opening a row right after untagging showed both checkboxes still checked. Fixed by resetting `selected` from the current `goal.tagged_members` every time the editor opens (`code/src/routes/app.family.goals.tsx`), not just at first mount. Re-verified live after the fix: reload, open, edit, close, reopen all show correct current state.

**What was built:**
- `backend/app/services/family_service.py` — `resolve_member_name()` (public, moved from a private `routers/family.py` helper so both routers can reuse it without a second copy), `set_goal_household_tags()`, `list_goals_with_tags()`.
- `backend/app/schemas/family.py` — `TaggedMemberSummary`, `FamilyTagsRequest`, `FamilyTagsResponse`, `FamilyGoalSummary`.
- `backend/app/routers/goals.py` — new `PUT /goals/{goal_id}/family-tags` endpoint (the one new backend route this task required, per the Contract's own API Contract for Task 8 — not a "blocker" exception, this is the task's designed scope).
- `backend/app/routers/family.py` — new `GET /family/goals` endpoint (read-only, reuses `list_goals_with_tags`).
- `backend/tests/test_family_goal_tagging.py` — 16 new tests covering ownership, identity/duplication, cross-household rejection, calculation-lifecycle compatibility, and the Task 7 cross-integration.
- `backend/tests/conftest.py` — promoted `other_user`/`other_auth_headers` fixtures here (were private to `test_family_router.py`) so the new test file can reuse them without a second copy.
- `code/src/routes/app.family.goals.tsx` — the new Family Goals screen: goals grouped by tagged member plus an honest "Not yet tagged" bucket, inline tag/untag editor per goal, live-updating mandatory disclosure, link to the existing goal-creation flow (not rebuilt).
- `code/src/routes/app.family.index.tsx` — "Upcoming family goals" removed from the Coming Soon list; replaced with a real `FamilyGoalsLink` card now that the feature exists.
- `code/src/lib/api.ts` — `getFamilyGoals()`, `setGoalFamilyTags()`, `TaggedMember`/`FamilyGoalSummary` types, with mock fallbacks.

**Testing:**
```
Backend tests:     256 passed (was 240 — 16 new), 97.07% coverage
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a real user, onboarded with a spouse and one
                   goal, completed the spouse placeholder, opened Family
                   Goals from Family Home's new real link (replacing the
                   old Coming Soon card), tagged the goal with both
                   household members, watched the mandatory disclosure
                   text live-update as checkboxes changed, saved, and
                   confirmed the goal appeared under BOTH members'
                   sections simultaneously (display grouping, not
                   duplication). Untagged one member, confirmed their
                   section disappeared while the goal stayed intact under
                   the other. Re-tagged and confirmed via a direct
                   database query: the goal's owner/probability/on_track
                   were untouched throughout, exactly the expected 2
                   family_goal_tag_changed audit rows existed (one per
                   save), and goal_household_members held exactly the
                   rows matching the final on-screen state (no
                   duplicates). Verified the Task 7 member-detail
                   cross-integration: the tagged member's "Goals involving
                   X" section correctly showed the goal with zero changes
                   to that screen's code. Test account fully cleaned up
                   afterward.
```

**Reviews:** Architecture (tagging logic lives in `family_service`, reusing household resolution rather than a new implementation; goal-ownership check stays inline in `routers/goals.py` matching its existing sibling endpoints), Product (grouped-by-member view matches the Contract's wireframe; empty "Not yet tagged" bucket keeps the screen honest about goals with no tags rather than hiding them), User Trust (see above), Accessibility (real fieldset/legend/checkboxes, not a chip-picker), Performance (one GET per page load; tagging is a single PUT that replaces the full set, no N+1), Self-Review below.

**Self-Review:**
- **What changed?** One new backend endpoint (`PUT /goals/{id}/family-tags`, explicitly in-scope per the Contract's own Task 8 API Contract), one new read endpoint (`GET /family/goals`), one new frontend route, one Family Home card swapped from placeholder to real link.
- **Why?** Task 8 per `Milestone2ImplementationContract.md` §8 — say who each goal affects, with the mandatory joint-ownership disclosure UX_REVIEW.md flagged as non-negotiable.
- **What risks remain?** None new beyond the fixed staleness bug above (now covered by a live re-verification, though not yet by an automated frontend test — this project has no frontend test runner, consistent with every prior task).
- **What is intentionally NOT implemented?** No automatic "tag now" prompt injected into the existing goal-creation flow — Family Goals is reached separately, per the Contract's own description ("routes to the existing goal-creation flow, then prompts for tags" was read as "the existing flow, plus a place to tag afterward," not as license to modify `app.goals.tsx`'s creation flow itself, which this task's "reuse existing goal services" instruction argues against touching).
- **What assumptions were made?** That tagging oneself (the "self" household member) is a legitimate, if slightly awkward, option — the disclosure sentence isn't self-case-specialized; flagged as a minor honest rough edge in the User Trust Review rather than solved with special-casing.
- **What documentation changed?** This entry, `CHANGELOG.md`, `docs/backend.md`, `docs/frontend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Task 12 (Family Dashboard / recommendations) can now read `GET /family/goals` for member-aware goal summaries without inventing a second query.

**Stopping here per instruction. Task 9 has not been started and requires separate review/approval before beginning.**

---

### Task 9 — Family Goals & Custom Inflation (✅ Complete, 2026-07-07)

**Dependency Validation:** Confirmed Tasks 1–8 complete (`PROJECT_STATE.md` headings, in order); `PATCH /goals/{goal_id}` exists; `goals.custom_inflation_rate` column exists (migration 007, unexposed on any schema until this task); Task 8's goal tagging exists and is reused for the SSY-callout context.

**Calculation Context Review — a real, load-bearing tension surfaced and resolved with the user before any code was written.** This task's own brief stated "changing custom_inflation_rate is a Calculation Context change," but `Milestone2ImplementationContract.md` §9 explicitly and deliberately says the opposite: inflation is a display-only input to a separate future-cost projection this milestone, and wiring it into the Monte Carlo engine is named as Milestone 4 (Calculation Engine) scope. Produced `CalculationContextReview.md` answering all seven required questions, flagged the tension explicitly rather than guessing, and stopped for the user's decision. **Decision: Path A (follow the Contract)** — `custom_inflation_rate` never touches `goal.probability`/`on_track`; `calculate_goal_probability()` is never invoked because of it.

**A second, closely-related correctness gap found during the same review (not part of the original tension, but required to actually honor the decision):** `routers/goals.py`'s `update_goal()` called `calculate_goal_probability()` unconditionally on *any* field change — and since `settings.monte_carlo_seed` is unset in this environment, an unconditional recompute is not a no-op, it silently perturbs `probability` via RNG variance. Fixed by making recalculation conditional on whether the PATCH body actually includes one of the five documented Calculation Context fields (`planning_service.CALCULATION_CONTEXT_FIELDS`, the single source of truth, reused by the router rather than duplicated) — the literal implementation of `calculate_goal_probability()`'s own pre-existing docstring, which the endpoint had never actually honored.

**Data Integrity Review:** Goal ownership unchanged (existing `PATCH` ownership check, untouched). Family tags remain descriptive (Task 9 writes nothing to `goal_household_members`; the SSY callout only reads it). Inflation overrides scoped to one goal only (per-goal nullable column, verified live and by test that a second goal's rate stays `null`). Existing calculations remain deterministic (verified live: 3 repeated custom-rate PATCHes never changed `probability`, plus a permanent test). No duplicate calculations (the FV projection is a separate, on-the-fly frontend computation, never touching the Monte Carlo path). No stale recommendations (none exist yet to go stale — Task 12 not built).

**User Trust Review & Design Review:** See `UserTrustAndDesignReview_Task9.md` and `FIRST_TIME_USER_REVIEW.md`'s new addendum. The mandatory "what does NOT change" sentence sits directly under the projection, in plain language, and was live-verified to hold (identical probability across Goals/Dashboard/Reports after setting a rate). No suggested default rate is shown (per `CalculationEngineReport.md` #12's unverified-figure flag) — the field starts empty with an explicit "no suggested default" label rather than inventing a number.

**A genuine cross-task bug found and fixed during live verification (not by static review):** `GET /family/members/{id}` (Task 7) had never populated `eligible_schemes` — only Task 6's create/update responses did. This was a real, silent gap that predates this task; it surfaced only now because Task 9's SSY callout was the first consumer to rely on that field from the GET path. Fixed with a minimal addition (`routers/family.py`) mirroring the exact `if dependent else` null-guard pattern already used for every other dependent-derived field in the same function (the "self" member has no dependent row and would otherwise crash `scheme_eligibility_service`'s `dependent.date_of_birth` access). Backed by two new permanent tests.

**What was built:**
- `backend/app/services/planning_service.py` — `CALCULATION_CONTEXT_FIELDS` (public constant, the single source of truth for what triggers recomputation).
- `backend/app/routers/goals.py` — `update_goal()`'s recalculation made conditional on that constant.
- `backend/app/schemas/goal.py` — `custom_inflation_rate` added to `GoalUpdate` (bound `[0, 0.5]`, matching `FinancialAssumptions.inflation_rate`'s own bound) and `GoalResponse`.
- `backend/app/routers/family.py` — `get_family_member` now populates `eligible_schemes` (the cross-task bug fix above).
- `backend/tests/test_goal_inflation.py` — 11 new tests (persistence, bound validation, per-goal scoping, cross-user rejection, and — the central guarantee — probability never changes from this field alone, including under repeated PATCHes).
- `backend/tests/test_family_router.py` — 2 new tests for the `eligible_schemes` fix (positive SSY match via GET, and the "self" member's null-dependent safety).
- `code/src/components/dashboard/EducationPlanningSection.tsx` — new component: default/custom projection text, dismissible prompt (no suggested default), inline rate editor, SSY callout (reused, not reimplemented).
- `code/src/components/dashboard/GoalSimPanel.tsx` — renders the new section for `category === "education"` goals only.
- `code/src/lib/api.ts`, `code/src/lib/mock-data.ts` — `customInflationRate` added to the `Goal` type and the backend↔frontend mapping.

**Testing:**
```
Backend tests:     269 passed (was 256 — 13 new), 97.17% coverage
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a user, added a 7-year-old daughter (SSY-
                   eligible), created an education goal, tagged it to
                   her. Opened the goal panel: confirmed the default
                   global-rate projection, the dismissible prompt (no
                   suggested default), and the SSY callout all rendered
                   correctly. Set a custom 8% rate — projection updated
                   to the new figure, "100% current probability" stayed
                   unchanged in the same panel, and on fresh visits to
                   Dashboard and Reports. Verified via a direct database
                   query: custom_inflation_rate persisted (0.08),
                   probability/on_track byte-identical to the values at
                   goal creation. Test account fully cleaned up
                   afterward. (Note: this session's screenshot tool
                   intermittently rendered stale frames for this
                   animated slide-over panel — confirmed via direct DOM
                   inspection that the actual application state was
                   correct throughout; not an app defect.)
```

**Reviews:** Architecture (recalculation trigger centralized in one constant, reused not duplicated; SSY callout reuses Task 3/6/7's existing evaluation path), Calculation (the core focus of this task — see Calculation Context Review above), Product (no suggested default rate; empty states read as honest, not incomplete), User Trust (see above), Accessibility (text-equivalent projection summary alongside the number, matching the Contract's explicit accessibility note), Performance (one-time `GET /assumptions` + `GET /family/goals` + per-tagged-member `GET /family/members/{id}` on panel open, bounded by household size), Self-Review below.

**Self-Review:**
- **What changed?** One new frontend component (education-goal-only), one conditional-recalculation fix to an existing endpoint, one additive schema field, and one unrelated-but-real bug fix in a Task 7 endpoint that Task 9 was the first to expose.
- **Why?** Task 9 per `Milestone2ImplementationContract.md` §9 — give education goals a realistic, family-aware cost projection without inventing a Monte Carlo integration this milestone was never scoped to build.
- **What risks remain?** None new. The one genuine risk this task carried (accidentally coupling inflation to probability) is now closed by both a permanent test and a live-verified guarantee across three separate screens.
- **What is intentionally NOT implemented?** No Monte Carlo integration of inflation (explicitly Milestone 4 scope, per the Contract and the user's own decision after review). No invented default inflation rate (unverified per `CalculationEngineReport.md` #12).
- **What assumptions were made?** That "goal-detail extension" meant extending the existing `GoalSimPanel` slide-over (the only per-goal detail surface that exists today) rather than building a new dedicated route, since no such route exists and Task 9's Checklist entry doesn't call for one.
- **What documentation changed?** This entry, `CalculationContextReview.md`, `DataIntegrityReview_Task9.md`, `UserTrustAndDesignReview_Task9.md`, `CHANGELOG.md`, `docs/backend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Milestone 4's Calculation Engine can build genuine inflation-aware Monte Carlo on top of the already-captured `custom_inflation_rate` input without needing a new field or migration.

**Stopping here per instruction. Task 10 has not been started and requires separate review/approval before beginning.**

---

### Task 10 — Family Insurance (✅ Complete, 2026-07-07)

**Dependency Validation:** Confirmed Tasks 1–9 complete; `health_policies`/`health_policy_coverage` exist (never previously written to); `dependents.has_own_insurance` exists and is already captured via Task 6; the verified base 80D figure (₹25,000) exists as structured, queryable data in `tax_sections` (confirmed live against this dev DB, not assumed); the existing `age_years()` age-computation utility (Task 3) promoted to public for reuse rather than reimplemented.

**Recommendation Integrity Review — the centerpiece of this task's pre-implementation work.** Produced `RecommendationIntegrityReview_Task10.md` addressing all five required guarantees explicitly: (1) figures come only from the seeded `tax_sections` row plus a structurally-derived 2× senior multiplier, never a hardcoded fallback; (2) every recommendation the service can return always carries `why`/`why_now`/`what_used`/`what_missing`, never partially populated; (3) a missing date of birth cites only the base figure with the gap explicitly listed, never guessing senior status either way; (4) the recommendation is deliberately **not** persisted to the pre-existing `recommendations` table — computed fresh on every `GET` instead, since it's a pure deterministic function of current data and writing it on read would reintroduce exactly the "reads mutate stored data" anti-pattern ADR-001/PCA-3 already eliminated elsewhere; (5) confirmed no shared table or function between `scheme_eligibility_service.py` (schemes) and the new `family_insurance_service.py` (insurance) beyond the domain-agnostic age helper.

**Data Integrity Review:** Household ownership unchanged (existing FK + membership check, reused from Task 8's exact pattern). Resolved a genuine textual ambiguity in the Contract before writing code — the Business Rule names `'no'`/`'not_sure'` explicitly, but the Acceptance Criteria's negative case ("all parents marked yes") implies an unanswered value should also count; resolved in favor of the Acceptance Criteria (an unanswered field carries less confidence of coverage, not more), documented rather than picked silently. Added a cross-check the Contract's literal text doesn't call for but correctness requires: a parent already covered by an active policy on file is excluded from the recommendation even if their `has_own_insurance` answer is stale — live-verified this exact scenario (see Testing below).

**User Trust Review & Design Review:** See `UserTrustAndDesignReview_Task10.md` and `FIRST_TIME_USER_REVIEW.md`'s new addendum. The recommendation frames itself as an opportunity, not a warning; uncertainty is stated as a possibility, never asserted as fact; the four-field explanation structure is shown as natural sentences plus a collapsed `<details>` disclosure (native, not custom-built), never as raw internal labels.

**What was built:**
- `backend/app/services/scheme_eligibility_service.py` — `_age_years` promoted to public `age_years`.
- `backend/app/schemas/insurance.py` — `HealthPolicyCreate`/`CoverageUpdateRequest`/`HealthPolicyResponse`/`InsuranceRecommendation`/`FamilyInsuranceResponse`.
- `backend/app/services/family_insurance_service.py` — policy CRUD (create, list-with-coverage, replace-coverage) and `compute_insurance_recommendation()` (the calculation-lite fact application).
- `backend/app/routers/family.py` — `GET /family/insurance`, `POST /family/insurance/policies`, `PUT /family/insurance/policies/{id}/coverage`.
- `backend/tests/test_family_insurance.py` — 21 new tests covering every Recommendation Integrity/Data Integrity guarantee as a permanent regression, not just a one-time manual check.
- `backend/tests/test_family_router.py` — no changes needed this task (unlike Task 9, no cross-task gap was found in this direction).
- `code/src/routes/app.family.insurance.tsx` — new screen: recommendation card with collapsed disclosure, policy list, Add Policy / Edit Coverage forms (reusing the same checkbox-fieldset multi-select pattern Tasks 8/9 established).
- `code/src/routes/app.family.index.tsx` — "Insurance status" Coming Soon card replaced with a real `FamilyInsuranceLink`.
- `code/src/lib/api.ts` — `getFamilyInsurance()`, `createInsurancePolicy()`, `updatePolicyCoverage()`, and the associated types.

**Testing:**
```
Backend tests:     290 passed (was 269 — 21 new), 97.27% coverage
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a user, added a mother with insurance status
                   "No" (no date of birth captured — parent-type members
                   don't require one). Confirmed the recommendation
                   rendered correctly: base ₹25,000 figures cited (DOB
                   unknown, so no senior-tier claim), the collapsed
                   disclosure expanded to show exactly the used/missing
                   data points, and the mandatory why/why_now sentences
                   were both present. Added a family floater policy
                   covering that parent — confirmed the recommendation
                   disappeared entirely on the next load (verified this
                   is the coverage signal taking precedence, not a
                   coincidence, since has_own_insurance stayed 'no').
                   Verified via direct database queries: the policy and
                   coverage persisted exactly as entered, and the
                   pre-existing `recommendations` table has zero rows
                   across the entire database — confirming the
                   recommendation is genuinely computed fresh on every
                   read, never persisted. Test account fully cleaned up
                   afterward.
```

**Reviews:** Architecture (recommendation logic centralized in one service function, reusing the household/age/name-resolution utilities Tasks 2/3/7 already built), Recommendation Integrity (the primary focus — see above), Data Integrity (see above), User Trust (see above), Design (progressive disclosure via native `<details>`, matching the Contract's own accessibility note for the not-yet-built Schemes screen so the pattern doesn't need reinventing there either), Product Consistency (`PRODUCT_CONSISTENCY_REVIEW.md` addendum), Recommendation Consistency (`RecommendationConsistencyReview_Task10.md` — a new, post-implementation review verifying the design guarantees held under real, repeated, state-changing use), Self-Review below.

**Self-Review:**
- **What changed?** One promoted utility function, one new schema module, one new service, three new endpoints, one new frontend route, one Family Home card swapped from placeholder to real link.
- **Why?** Task 10 per `Milestone2ImplementationContract.md` §10 — surface the family-floater-vs-standalone-parent-policy tax opportunity concretely, using the verified doubled-deduction fact, without over-building toward Milestone 5's full Recommendation Engine.
- **What risks remain?** None new. The one genuine risk this task carried (a recommendation that could go stale relative to real policy data, or fabricate a senior-citizen claim without evidence) is closed by both permanent tests and a live-verified guarantee.
- **What is intentionally NOT implemented?** No `Recommendation`/`RecommendationCitation` row is ever written — a deliberate choice, not a gap (see Recommendation Integrity Review #4). No date-of-birth requirement was added to parent-type members — the recommendation degrades gracefully (lower confidence, explicit missing-info note) rather than blocking on data the existing schema never required.
- **What assumptions were made?** That "reuse existing recommendation infrastructure" meant reusing the `Recommendation` model's *shape* (reasoning/confidence/alternatives/assumptions, extended to this task's explicit four-field structure) as a plain response schema, not literally writing a DB row on every read — documented explicitly in `RecommendationIntegrityReview_Task10.md` rather than picked silently, given the real tension with ADR-001's read-purity lesson.
- **What documentation changed?** This entry, `DependencyValidation_Task10.md`, `RecommendationIntegrityReview_Task10.md`, `DataIntegrityReview_Task10.md`, `UserTrustAndDesignReview_Task10.md`, `RecommendationConsistencyReview_Task10.md`, `CHANGELOG.md`, `docs/backend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Task 12 (Family Dashboard) can surface this same recommendation via its own aggregation card, reusing `compute_insurance_recommendation()` directly rather than recomputing the fact a second time.

**Stopping here per instruction. Task 11 has not been started and requires separate review/approval before beginning.**

---

### Task 11 — Family Recommendations (✅ Complete, 2026-07-07)

**A task-identity mismatch was found and resolved before any code was written.** This turn's brief was titled "Task 11 (Family Recommendations)," but its actual content (aggregate multiple recommendation sources, detect conflicts, reuse the insurance *and* eligibility engines) matched what `Milestone2ImplementationContract.md` assigns to **Task 12's** Dashboard recommendation feed — the Contract's own Task 11 is a single-source "Family Government Schemes" screen with no aggregation concept at all. Documented in `DependencyValidation_Task11.md` and surfaced to the user via a direct question rather than guessed at; the user confirmed: build the aggregation layer now, reusing Task 3's eligibility-evaluation function directly rather than waiting on a dedicated Schemes screen.

**Dependency Validation:** Tasks 1–10 complete; Task 10's `family_insurance_service.compute_insurance_recommendation()` and Task 3's `scheme_eligibility_service.evaluate_household_eligibility()` both exist, certified, tested. No missing-dependency blocker — only the task-identity ambiguity above, resolved by the user before implementation began.

**Recommendation Conflict Review** (`RecommendationConflictReview_Task11.md`) — the centerpiece, and a new review type for this engagement. Defined a genuine conflict narrowly: two recommendations sharing a subject **and** a `reference_code` (the same bounded deduction/scheme ceiling) — deliberately narrower than "same person, multiple recommendations," since an insurance (80D) and a scheme (80C/123) recommendation about the same person are compatible, not conflicting. Verified by construction that the two current sources can never actually conflict (SSY only matches children under 10, SCSS only matches seniors 60+ — no person can be both), stated honestly rather than fabricating a scenario to "prove" the mechanism works. If a real conflict were ever detected, both recommendations remain visible — conflicts are additive context, never a suppression mechanism (no hardcoded source priority).

**Recommendation Integrity Review** (`RecommendationIntegrityReview_Task11.md`): every aggregated recommendation, regardless of source, carries all five required fields (why/why_now/used/missing/confidence) — mandatory on the shared `FamilyRecommendation` schema, not optionally populated. Scheme recommendations only ever come from the `"eligible"` bucket (never `"potentially_eligible"`/`"not_eligible"`); confidence is 1.0 since eligibility is a deterministic rule match, not an estimate. Nothing is persisted — computed fresh on every `GET`, same reasoning as Task 10.

**Data Integrity Review** (`DataIntegrityReview_Task11.md`): documented a known, minor limitation carried forward rather than silently worked around — `EligibilityResult` identifies a subject only by name (not `household_member_id`), since Task 3's already-certified output shape was never designed to carry one; conflict-grouping uses that same name string, an acceptable tradeoff given small household sizes.

**User Trust Review & Design Review** (`UserTrustAndDesignReview_Task11.md`): each recommendation keeps its source's own established visual language (Task 10's insurance card shape; the existing SSY callout's tone for scheme cards) rather than a flattened generic template, so two very different kinds of advice read as independent and well-reasoned side by side.

**What was built:**
- `backend/app/schemas/insurance.py` — `InsuranceRecommendation` gained a `subjects: list[str]` field (additive; exposes data the engine already computed internally).
- `backend/app/services/family_insurance_service.py` — populates the new `subjects` field.
- `backend/app/schemas/family_recommendations.py` — new: `FamilyRecommendation`, `RecommendationConflict`, `FamilyRecommendationsResponse`.
- `backend/app/services/family_recommendations_service.py` — new: aggregates Task 10 + Task 3's engines, pure `_detect_conflicts()` helper.
- `backend/app/routers/family.py` — new `GET /family/recommendations`.
- `backend/tests/test_family_recommendations.py` — 13 new tests (9 integration, 4 unit tests against `_detect_conflicts` directly).
- `code/src/routes/app.family.recommendations.tsx` — new screen.
- `code/src/routes/app.family.index.tsx` — "AI recommendations" Coming Soon card replaced with a real, deliberately-renamed "Family Recommendations" link (never "AI," since this is rule-based logic).
- `code/src/lib/api.ts` — `getFamilyRecommendations()` and associated types.

**Testing:**
```
Backend tests:     303 passed (was 290 — 13 new), 97.41% coverage,
                    family_recommendations_service.py at 100%
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a user, added a mother with no recorded
                    insurance/DOB and a 7-year-old SSY-eligible daughter
                    (added via a direct authenticated API call, since the
                    existing "Add someone else" form has no gender field —
                    a pre-existing gap, not introduced by this task).
                    Confirmed both recommendations rendered side by side
                    with zero false conflicts, each fully explained via
                    its own collapsed disclosure. Verified via direct
                    database query: the recommendations table remained at
                    zero rows across the entire database. Test account
                    fully cleaned up afterward.
```

**Reviews:** Dependency Validation (surfaced and resolved a task-identity mismatch), Recommendation Conflict Review (centerpiece), Recommendation Integrity Review, Data Integrity Review, User Trust Review, Design Review, Product Consistency Review (`PRODUCT_CONSISTENCY_REVIEW.md` addendum), Self-Review below.

**Self-Review:**
- **What changed?** One additive schema field, one new schema module, one new aggregation service, one new endpoint, one new frontend route, one Family Home card renamed from "AI recommendations" to "Family Recommendations" and made real.
- **Why?** To surface both of this milestone's recommendation sources (insurance, schemes) together, with real conflict detection between them, ahead of the full Task 12 Dashboard.
- **What risks remain?** None new. The one genuine risk (a false-positive conflict flag confusing the user) is closed by the narrow, defined conflict criterion plus both automated and live verification.
- **What is intentionally NOT implemented?** No dedicated "Family Government Schemes" screen (the Contract's literal Task 11) — this task reused the underlying eligibility-evaluation function directly rather than building that screen as a prerequisite, per the user's explicit decision.
- **What assumptions were made?** That "reuse existing eligibility engine" meant calling `evaluate_household_eligibility()` directly, not requiring the not-yet-built Schemes screen to exist first — confirmed with the user via `DependencyValidation_Task11.md` before implementation, not assumed silently.
- **What documentation changed?** This entry, `DependencyValidation_Task11.md`, `RecommendationConflictReview_Task11.md`, `RecommendationIntegrityReview_Task11.md`, `DataIntegrityReview_Task11.md`, `UserTrustAndDesignReview_Task11.md`, `CHANGELOG.md`, `docs/backend.md`, `docs/frontend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Task 12 (Family Dashboard) can call `family_recommendations_service.get_family_recommendations()` directly for its own recommendation feed, rather than re-aggregating the two engines a second time.

**Stopping here per instruction. Task 12 has not been started and requires separate review/approval before beginning.**

---

### Task 12 — Family Dashboard Integration (✅ Complete, 2026-07-07)

**Dependency Validation** (`DependencyValidation_Task12.md`): Tasks 1–11 complete; every service this task's reuse list names exists and is certified. Two findings, neither blocking, both resolved by the brief's own constraints:
- **Finding 1:** the Contract references an "existing emergency-fund-months calculation" that does not exist anywhere in the codebase. Inventing it on the backend would violate this task's explicit "no financial calculations during read operations" / "no parallel business logic" requirements — so the backend passes through `get_dashboard()`'s authoritative `liquid_assets`/`monthly_expenses` verbatim and the frontend renders "X months covered" as display arithmetic, exactly Task 9's precedent (which deliberately kept the future-cost projection on the frontend for the same reason). Zero expenses shows an honest "add income & expenses" empty state, never a fabricated figure.
- **Finding 2:** the Parents card's literal Contract condition (raw `has_own_insurance != 'yes'`) would contradict the recommendations feed on the same screen whenever a parent with a stale answer is actually covered by an on-file policy (Task 10's staleness guard). Resolved by extracting the uncovered-parents determination from `compute_insurance_recommendation()` into public `family_insurance_service.uncovered_parents()`, consumed by **both** — the warning and the recommendation are structurally incapable of disagreeing.

**Integration Integrity Review** (`IntegrationIntegrityReview_Task12.md`) — the centerpiece, with a card-by-card authoritative-source map produced before any code: every card is a persisted value or an existing certified service's output; the dashboard layer contains zero arithmetic beyond counting and min-by-date; the feed is a verbatim call to Task 11's aggregation (not a second aggregation); partial failures degrade to null cards (logged, never silently swallowed, never rendered as fake zeros) with an explicit `recommendations_unavailable` flag distinguishing "we couldn't check" from "nothing to show"; loading/empty/error states defined per section before implementation.

**Recommendation Integrity Review** (`RecommendationIntegrityReview_Task12.md`): no recommendation logic added or duplicated; the feed shows a recommendation iff its source screen would, by construction; this also closes the consistency question `RecommendationConsistencyReview_Task10.md` explicitly deferred to Task 12.

**Data Integrity Review** (`DataIntegrityReview_Task12.md`): coverage and dependents cards share one member snapshot so their denominators can never disagree; nothing persisted on read — freshness falls out of statelessness rather than cache invalidation.

**User Trust & Design Review** (`UserTrustAndDesignReview_Task12.md`): one question, one answer per card; warnings only when the product would also recommend acting; unavailable never dressed up as fine; cards are real links (never clickable divs); the `/app` card is deliberately quiet and renders nothing on error rather than breaking the money dashboard.

**What was built:**
- `backend/app/services/family_insurance_service.py` — extracted `uncovered_parents()` + `_covered_member_ids()` (pure refactor of Task 10 logic into shared, named authorities; all 21 Task 10 tests pass unchanged).
- `backend/app/schemas/family_dashboard.py` — new: six nullable card schemas + `FamilyDashboardResponse`.
- `backend/app/services/family_dashboard_service.py` — new: read-only composition with per-section `_safe()` failure isolation.
- `backend/app/routers/family.py` — new `GET /family/dashboard`.
- `backend/tests/test_family_dashboard.py` — 14 new tests, including the feed-identity test, the card-and-recommendation-move-together test, two partial-failure tests (monkeypatched section/feed failures → 200 with null card / explicit flag), nothing-persisted, and calculation-lifecycle tests.
- `code/src/routes/app.family.index.tsx` — new Family Dashboard section: six-card grid (skeleton loading, per-card empty/unavailable states, warning styling on the Parents card) + compact recommendations feed linking to the full Recommendations screen.
- `code/src/routes/app.index.tsx` — new quiet `FamilyCard` on the money dashboard ("Family — N people · X suggestions to review"), rendering nothing while loading or on error.
- `code/src/lib/api.ts` — `FamilyDashboard` type + `getFamilyDashboard()` (real + mock).

**Testing:**
```
Backend tests:     317 passed (was 303 — 14 new), 97.50% coverage,
                    family_dashboard_service.py at 100%
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Registered a user with real financials (₹12L salary,
                    ₹40,000/mo expenses, ₹3,00,000 savings, retirement
                    goal), added an uninsured mother, an SSY-eligible
                    daughter, and a tagged education goal. All six cards
                    rendered correct, cross-checkable values (including
                    "7.5 months covered" = 3,00,000 ÷ 40,000, verifiable
                    against the money dashboard's own stats). The central
                    Acceptance Criterion held: recording one policy
                    covering the mother updated the Parents card, the
                    Coverage card, and the recommendations feed all at
                    once on the next load. Verified at the database:
                    recommendations table at zero rows after many loads;
                    both goals' persisted probabilities byte-identical
                    (21.2 / 3.9). Test account fully cleaned up.
```

**Self-Review:**
- **What changed?** One extraction refactor in the insurance service, one new schema module, one new composition service, one new endpoint, one dashboard section on Family Home, one quiet card on the money dashboard.
- **Why?** Task 12 per `Milestone2ImplementationContract.md` §12 — one screen answering "who depends on me, and are we okay," assembled entirely from what Tasks 3–11 already built.
- **What risks remain?** None new. The two integration risks (a card contradicting its source screen; one failed section taking down the dashboard) are both closed structurally and covered by permanent tests.
- **What is intentionally NOT implemented?** No backend months-covered calculation (Finding 1 — frontend display arithmetic instead); no dashboard-state persistence or caching (freshness falls out of statelessness); no second expanded-recommendation UI (feed entries link to the Recommendations screen, which remains the single home of the full disclosure view).
- **What assumptions were made?** That the Contract's nonexistent "emergency-fund-months calculation" should be resolved by passthrough + display arithmetic rather than invented backend logic — dictated by this task's own explicit constraints and Task 9's precedent, documented in Finding 1 rather than silently picked.
- **What documentation changed?** This entry, `DependencyValidation_Task12.md`, `IntegrationIntegrityReview_Task12.md` (with post-implementation live addendum), `RecommendationIntegrityReview_Task12.md`, `DataIntegrityReview_Task12.md`, `UserTrustAndDesignReview_Task12.md`, `CHANGELOG.md`, `docs/backend.md`, `docs/frontend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).
- **What future features depend on this?** Milestone 4's Calculation Engine can upgrade any card's underlying figure (e.g., a real emergency-months model) and the dashboard inherits it automatically, since it computes nothing itself.
- **Honest milestone status:** Tasks 1–12 as instructed are complete. One Contract item remains unbuilt: the §11 Family Government Schemes *screen* (`/app/family/schemes`) — the user redirected Task 11 to the aggregation layer instead (see `DependencyValidation_Task11.md`), so the schemes *engine* is fully consumed (SSY callouts, recommendations, dashboard feed) but the dedicated three-bucket browsing screen does not exist. Flagged here so it isn't silently forgotten; building it is a decision for the user, not an assumption.

**Stopping here per instruction. The next milestone has not been started and requires separate review/approval before beginning.**

---

## Milestone 2.1 — Production Stabilization Sprint

**Source of truth:** `Milestone2CertificationReport.md` (Milestone 2 was certified WITH CONDITIONS, not for unconditional production use). This sprint works exactly one finding at a time, in user-trust/production-risk priority order, with the full review pipeline (Dependency Validation → Root Cause Analysis → Design Review → User Trust Review → Implementation → Testing → Live Verification → Documentation → PR Report) per finding, stopping for approval after each one.

### P0 — Risk Profile Persistence Bug (✅ Fixed, 2026-07-07)

**Root cause:** not a wiring oversight — there has never been an account-level "risk profile" field anywhere in the backend (`User`, `UserProfile`, `FinancialAssumptions` all lack one; only `Goal.risk_profile`, per-goal, and `Simulation.risk_profile` are real). Profile's "Risk Profile" selector was scaffolded to look like a working field (same three options as the real per-goal selector) but was never connected to any endpoint — `handleSubmit` only ever sent `full_name`. The UI still showed "✓ Saved" after changing it, a false confirmation.

**Fix (user-confirmed design decision, not silently picked):** removed the false capability rather than building a new backend concept under stabilization-sprint discipline — the exact precedent PCA-1/PCA-2 already set (remove the false claim; don't build the missing feature under time pressure). `code/src/routes/app.profile.tsx`: removed the Risk Profile field, its header summary, `RISK_OPTIONS`, and every `riskProfile` reference from `FormState`/`isDirty`/initial state. No backend change — none was ever needed, since no backend field existed. The real, working per-goal risk profile (`/app/goals`, onboarding's first-goal step) is untouched.

**Testing:** `tsc`/`eslint` clean, single-file diff. Live-verified with a fresh test account: the field and its header label are gone everywhere; the form's one genuine save (Full Name) still works and persists across a reload — the fix didn't regress real functionality.

**Documentation:** `DependencyValidation_M2.1-P0.md`, `RootCauseAnalysis_M2.1-P0.md`, `DesignReview_M2.1-P0.md`, `UserTrustReview_M2.1-P0.md`, `Testing_M2.1-P0.md`, this entry, `CHANGELOG.md`, `PR_REPORT_M2.1-P0.md`.

**Incidental observation (not fixed, out of scope for this finding):** during live verification, the top-nav avatar initials and the Profile page's own avatar initials appeared to render differently after a name change in one screenshot — not confirmed as a real bug (could be a screenshot artifact), not investigated further per "implement exactly one finding at a time." Worth a quick look during a future finding if it recurs.

**Stopping here per instruction. Awaiting approval before starting the next Milestone 2.1 finding.**

### P1 — Government Schemes Screen (✅ Fixed, 2026-07-07)

**Why this gap existed (not a defect):** the Contract's §11 dedicated Schemes screen was never built — Milestone 2's actual Task 11 was redirected to the recommendation-aggregation layer per an explicit user decision at the time (`DependencyValidation_Task11.md`). Consequence: `evaluate_household_eligibility()`'s `"eligible"` bucket was surfaced (via the Recommendations feed/Dashboard), but `"potentially_eligible"` and `"not_eligible"` — two-thirds of the three-state design — had zero UI surface anywhere. `ProductConsistencyRoadmap.md`'s PCA-7 was therefore only partially resolved, as the Certification Report itself stated.

**Dependency Validation** (`DependencyValidation_M2.1-P1.md`): the Scheme Eligibility Service (`evaluate_household_eligibility()`, Task 3) already returns all three buckets in one call — no new eligibility logic needed, only a thin new endpoint exposing the full output (previously only ever consumed narrowly: the inline SSY callout, or the Recommendations feed's "eligible"-only slice). Verified against the real dev database: 9 schemes seeded, only SSY/SCSS have configured rules — the other 6 correctly read "not yet configured," never fabricated.

**Root Cause Analysis** (`RootCauseAnalysis_M2.1-P1.md`): confirmed no backend bug exists — this is a missing screen, not broken logic. Explicitly scoped out: the self-member eligibility gap (Task 3's own pre-existing, documented boundary — a user's own eligibility is never evaluated) and the 6 unconfigured schemes — both carried forward honestly, not something this finding attempts to fix.

**User Trust Review** (`UserTrustReview_M2.1-P1.md`): every displayed scheme traces to live seeded data; missing information (no DOB, unconfigured scheme) is explained honestly rather than guessed into a verdict; the screen and the Recommendations feed/Dashboard cannot disagree, since both call the same function with no caching between them.

**Design Review** (`DesignReview_M2.1-P1.md`): `GET /family/schemes` — a direct passthrough, zero new eligibility logic. Frontend follows `FamilyPlanningDesign.md` Part 7's mockup exactly: Eligible and Potentially Eligible always expanded (the latter being the bucket this finding exists to make visible); Not Eligible collapsed behind a native `<details>` disclosure (can contain multiple per-member rows, not just per-scheme).

**What was built:**
- `backend/app/schemas/family_schemes.py` — new, a direct passthrough schema.
- `backend/app/routers/family.py` — new `GET /family/schemes`.
- `backend/tests/test_family_schemes.py` — 8 new tests, including one asserting reason-text identity with the Recommendations endpoint (the "cannot disagree" guarantee, tested, not just asserted).
- `code/src/routes/app.family.schemes.tsx` — new screen: three-bucket layout, loading/error/empty states, `focus-visible` on every interactive element (explicitly checked this time, per the Certification Report's Task 10/11 finding).
- `code/src/routes/app.family.index.tsx` — "Government scheme eligibility" Coming Soon replaced with a real link.
- `code/src/lib/api.ts` — `FamilySchemes`/`SchemeEligibilityItem` types + `getFamilySchemes()`.

**Testing:** 325 backend tests passing (was 317 — 8 new), 97.52% coverage. `tsc`/`eslint` clean.

**Live verification:** household with an SSY-eligible daughter, a gender-ineligible son, and a mother 3 years from SCSS eligibility. All three buckets rendered correctly; the Potentially Eligible entry ("will reach the age 60+ requirement... within the next 5 years") was the first time this signal has ever been visible in the product. Confirmed byte-identical reason text between this screen and the Recommendations feed for the same scheme/member. Confirmed the `recommendations` table stayed at zero rows. Test account fully cleaned up.

**Documentation:** this entry, `DependencyValidation_M2.1-P1.md`, `RootCauseAnalysis_M2.1-P1.md`, `UserTrustReview_M2.1-P1.md`, `DesignReview_M2.1-P1.md`, `CHANGELOG.md`, `PR_REPORT_M2.1-P1.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).

**Stopping here per instruction. Awaiting approval before starting the next Milestone 2.1 finding.**

### P2 — Insurance Policy Audit Logging (✅ Fixed, 2026-07-07)

**Why the gap existed:** `family_service.py` established the audit-log pattern early (household creation, member add/update/remove, goal tagging) and applied it consistently; `family_insurance_service.py` (Task 10) was built later, reusing many of `family_service`'s patterns, but the audit-log call was not among them — a straightforward omission, not a deliberate scoping decision (confirmed by re-reading Task 10's own review documents, which never mention audit logging).

**Dependency Validation** (`DependencyValidation_M2.1-P2.md`): exactly two real write functions exist (`create_policy`, `replace_policy_coverage`) — confirmed via full read of `family_insurance_service.py`. **No delete/deactivate action exists anywhere for policies today** (`HealthPolicy.is_active` is a real column but nothing ever sets it to `False`) — this finding logs the two real actions; it does not add a delete endpoint just to have something to audit. No existing code queries `audit_logs` anywhere, so nothing could break from adding two new action strings.

**Root Cause Analysis** (`RootCauseAnalysis_M2.1-P2.md`): confirmed this is a completeness gap, not a security defect — the Certification's Security Review already found no IDOR/ownership issue on any insurance endpoint.

**Data Integrity Review** (`DataIntegrityReview_M2.1-P2.md`): one audit call per write function, placed once, matching the single-call-per-write shape every existing site uses — no duplicate-entry path exists. "Audit logging failures do not corrupt the primary transaction" verified against the actual transaction boundary (`get_db()` commits the whole request atomically, exactly as every existing audit call site already relies on) — and the audit payload contains only already-validated primitives (UUIDs, floats, strings) copied from the just-created object, so there's no independent failure mode.

**Security Review** (`SecurityReview_M2.1-P2.md`): no PII (names, DOB, insurance-status text) written to audit records — only policy figures and member UUIDs, matching the existing pattern. No new read endpoint added for audit data.

**User Trust Review** (`UserTrustReview_M2.1-P2.md`): backend-only change, no user-visible behavior differs; closes the one gap where insurance writes were the sole exception to an otherwise-consistent audit posture across every other Family write.

**What was built:**
- `backend/app/services/family_insurance_service.py` — `insurance_policy_created` audit log in `create_policy()`; `insurance_policy_coverage_updated` (with before/after covered-member-id sets, mirroring `family_goal_tag_changed`'s exact shape) in `replace_policy_coverage()`.
- `backend/tests/test_family_insurance.py` — 4 new tests: create is logged once with no PII, coverage-update is logged with correct before/after ids, no duplicate entries per action, and reads never produce an audit entry.

**Testing:** 329 backend tests passing (was 325 — 4 new), 97.52% coverage.

**Live verification:** created a policy and edited its coverage for a real test account; queried the real database directly and confirmed both `insurance_policy_created` and `insurance_policy_coverage_updated` rows exist exactly once each, with the correct before/after covered-member-ids and zero PII — format byte-for-byte consistent with the pre-existing `household_created`/`family_member_added` rows in the same table. Test account fully cleaned up.

**Documentation:** this entry, `DependencyValidation_M2.1-P2.md`, `RootCauseAnalysis_M2.1-P2.md`, `DataIntegrityReview_M2.1-P2.md`, `SecurityReview_M2.1-P2.md`, `UserTrustReview_M2.1-P2.md`, `CHANGELOG.md`, `PR_REPORT_M2.1-P2.md`.

**Stopping here per instruction. Awaiting approval before starting the next Milestone 2.1 finding.**

### Accessibility Polish (✅ Fixed, 2026-07-08)

**Note on numbering:** this finding was instructed as "P2," the same label already used for Insurance Audit Logging. Documentation files use the `M2.1-P3` suffix (the next sequential slot) purely to avoid filename collision — referred to by name here, not by number.

**Why the gap existed:** `focus-visible` styling was applied inconsistently as this milestone's screens were built one task at a time — Task 12 (built most recently) applied it to every element from the start; earlier screens (Tasks 5–8, 10–11) were built before that discipline was consistently the pattern to copy. Inconsistent execution of an already-known pattern, not a missing capability.

**Dependency Validation** (`DependencyValidation_M2.1-P3.md`): the Certification named Tasks 10/11 specifically; direct file inspection found the actual gap is broader — 24 interactive elements missing focus-visible styling across 6 files: `app.family.insurance.tsx` (6 + 1 `<summary>`), `app.family.recommendations.tsx` (2 + 1 `<summary>`), `app.family.goals.tsx` (5), `app.family.members.$id.tsx` (7), `FamilyMemberForm.tsx` (1, shared by 2 routes), `app.family.index.tsx` (3). One item explicitly scoped out: the shared `field-input` CSS utility (used by every text input/select app-wide) has a weaker focus treatment, but changing it is an app-wide design-system concern outside "Family screens," so it's flagged separately, not fixed here.

**Root Cause Analysis** (`RootCauseAnalysis_M2.1-P3.md`): confirmed this is a pure styling omission, not a logic or design defect — every affected element was already a correct native `<button>`/`<Link>`/`<summary>`, already keyboard-focusable by the browser; only the visible indicator was missing.

**Accessibility Review** (`AccessibilityReview_M2.1-P3.md`): focus order unchanged (no DOM reordering, `className`-only edits); all controls already keyboard-reachable (no `<div onClick>` pattern found anywhere); screen-reader labels already correct (checked incidentally, no new gap found); color-never-alone re-confirmed for the Parents card and Schemes buckets (unchanged, already correct).

**User Trust Review** (`UserTrustReview_M2.1-P3.md`): fix is invisible to mouse users (`:focus-visible` only ever renders on keyboard-detected focus) — pure gain for keyboard/screen-reader users with zero visual change for anyone else.

**Design Review** (`DesignReview_M2.1-P3.md`): same existing utility-class string applied everywhere, no new pattern invented, no layout/logic/component-API change.

**What was built:** 24 `className` additions (the identical `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background` string, plus `rounded` on inline/text controls) across `app.family.insurance.tsx`, `app.family.recommendations.tsx`, `app.family.goals.tsx`, `app.family.members.$id.tsx`, `FamilyMemberForm.tsx`, `app.family.index.tsx`. Fixing `FamilyMemberForm`'s Save button once covered both its call sites (Add Family Member and Member Detail's edit mode).

**Testing:** `tsc`/`eslint` clean across every touched file. No dedicated accessibility test suite exists in this project (a standing, pre-existing condition) — verified via live keyboard-only navigation instead, per instruction.

**Live (keyboard-only) verification:** tabbed through `/app/family/insurance` and `/app/family/recommendations` using only the keyboard (no mouse) — confirmed a clearly visible cyan focus ring renders on "Back to Family" and "Add a policy" (Insurance) and "Back to Family" (Recommendations), exactly the elements fixed. Confirmed via direct inspection that `:focus-visible` correctly does *not* render after a mouse click (expected, spec-correct browser behavior, not a bug). Test account fully cleaned up.

**Documentation:** this entry, `DependencyValidation_M2.1-P3.md`, `RootCauseAnalysis_M2.1-P3.md`, `AccessibilityReview_M2.1-P3.md`, `UserTrustReview_M2.1-P3.md`, `DesignReview_M2.1-P3.md`, `PR_REPORT_M2.1-P3.md`.

**Stopping here per instruction. Awaiting approval before starting the next Milestone 2.1 finding (dashboard performance optimization not begun, per instruction).**

### Dashboard Query Optimization (✅ Fixed, 2026-07-08)

**Note on numbering:** this finding was instructed as "P3," matching the label already used for Accessibility Polish. Documentation uses the `M2.1-P4` file suffix (next sequential slot) purely to avoid collision — referred to by name throughout.

**Why the inefficiency existed:** Task 12's Family Dashboard was deliberately designed with per-card failure isolation (each of six cards computes under its own guard, so one failure never takes down the whole dashboard) — a genuinely good design the Certification praised. The unmeasured cost: two pairs of cards independently fetched the same underlying data (household members; goals-with-tags), and `compute_insurance_recommendation()` fetched the same covered-member-ids twice within itself. `list_policies_with_coverage()` also had a classic N+1 (one query per policy).

**Dependency Validation** (`DependencyValidation_M2.1-P4.md`): traced the full call graph and empirically measured (via a temporary `AsyncSession.execute` instrumentation, not guesswork) **25 SELECT queries** for one `GET /family/dashboard` call against a realistic household. Identified 4 fixable duplications and 1 deliberately-deferred one (see Performance Review).

**Root Cause Analysis** (`RootCauseAnalysis_M2.1-P4.md`): confirmed this is redundant work, not incorrect work — every duplicate query returns the identical result as its sibling call; no test ever caught a wrong value because there wasn't one.

**Performance Review** (`PerformanceReview_M2.1-P4.md`): measured before/after — **25 → 22 queries** (12% reduction) from sharing the members-list and goals-with-tags fetches plus deduplicating the intra-function covered-ids call. Separately, the N+1 in `list_policies_with_coverage()` was fixed (batched into one query across all policy IDs) — measured directly: a 2-policy household now issues exactly 1 coverage query instead of 2, and this gap widens with more policies. The cross-service `uncovered_parents` duplication (Parents card vs. Recommendations feed) was deliberately **not** fixed — closing it would require changing `family_recommendations_service.get_family_recommendations()`'s public signature to thread a pre-computed value through three functions across two service files, coupling two services deliberately kept independent by design. Documented as remaining, non-blocking debt, consistent with the Certification's own framing.

**Architecture Review** (`ArchitectureReview_M2.1-P4.md`): confirmed no business logic, API response shape, or authoritative data source changed; confirmed the failure-isolation architecture is preserved exactly (a shared-fetch failure degrades the same set of cards to `None` as before, since these are deterministic reads, not independently-flaky calls); confirmed no new coupling between services.

**What was built:**
- `backend/app/services/family_dashboard_service.py` — `get_family_dashboard()` now fetches members and goals-with-tags once each, sharing them between the two cards that need each; the four card-builder functions that used to fetch their own data now receive it as a parameter.
- `backend/app/services/family_insurance_service.py` — `uncovered_parents()` gained an optional `covered_ids` parameter (backward-compatible, defaults to `None`, unchanged behavior for every existing caller); `compute_insurance_recommendation()` now computes `covered_ids` once and passes it through instead of querying it twice; new `_covered_members_for_policies()` batches the per-policy coverage lookup that `list_policies_with_coverage()` previously ran once per policy.
- `backend/tests/test_family_insurance.py` — 1 new test confirming the batched coverage lookup correctly keeps each policy's covered members distinct (not mixed up across policies).

**Testing:** 330 backend tests passing (was 329 — 1 new), full suite unaffected. `ruff`/`mypy --strict` clean.

**Measurement (before/after, both empirical):**
```
GET /family/dashboard, realistic household (1 parent, 1 child, 1 policy, 2 goals):
  Before: 25 SELECT queries
  After:  22 SELECT queries  (−3, −12%)

list_policies_with_coverage, 2-policy household:
  Before: 3 queries (1 policy list + 1 per policy = N+1)
  After:  2 queries (1 policy list + 1 batched coverage lookup)
```

**Live verification:** registered a fresh test account, added a parent (insurance gap) and an SSY-eligible child, confirmed `GET /family/dashboard`'s JSON response and the rendered UI were identical in shape and content to every prior verification session for the same scenario. Test account fully cleaned up.

**Documentation:** this entry, `DependencyValidation_M2.1-P4.md`, `RootCauseAnalysis_M2.1-P4.md`, `PerformanceReview_M2.1-P4.md`, `ArchitectureReview_M2.1-P4.md`, `CHANGELOG.md`, `PR_REPORT_M2.1-P4.md`.

**This was the final engineering finding in this Milestone 2.1 Production Stabilization Sprint, per instruction. Milestone 3 has not been started and requires separate review/approval before beginning.**

## Global Shell — Phase 0: Persistent AppShell Foundation (✅ Complete, 2026-07-08)

Following the Milestone 2 re-certification (CERTIFIED FOR PRODUCTION) and the Global Shell Architecture Review (`GlobalShellArchitecture.md`, `GlobalShellImplementationPlan.md`), this is Phase 0 of that plan — the prerequisite foundation for Profile Menu, Global Search, Notifications, and Keyboard Shortcuts (none of which were implemented in this phase).

**Why this phase existed:** `AppShell` was rendered independently by 13 separate leaf routes rather than once by the shared `/app` layout, so it fully unmounted and remounted on every navigation — refetching the user's identity and plan-health score from scratch each time, with no data surviving between screens.

**Dependency Validation** (`DependencyValidation_Phase0.md`): confirmed via direct code/route-tree inspection that TanStack Router's existing `/app` layout route (`app.tsx`) was the correct, already-present seam for this fix — no incorrect assumption found, no stop condition triggered.

**Architecture Review** (`ArchitectureReview_Phase0.md`): root-caused the remounting to component placement (not a router bug); designed the fix as moving `AppShell`'s single render site to the layout, replacing two raw `useEffect`+promise fetches with `useQuery`, and replacing the per-route `title` prop with route `staticData` (plus a narrow context-based override for the one route — `app.family.add.tsx` — whose title is dynamic). Found, as a bonus, that aligning the shell's plan-health query key with the Dashboard route's own existing `["dashboard"]` key would let the two share one cached request.

**Performance Baseline** (`PerformanceBaseline_Phase0.md`): measured, not estimated, via real network capture and a direct DOM node-identity check — **14 `auth/me` and 12 `dashboard` requests across 6 navigations**, and direct proof (different DOM node references, old node detached from document) that `AppShell` was fully remounting, not just re-rendering.

**Design Review** (`DesignReview_Phase0.md`): confirmed, item-by-item, that no visual, UX, or accessibility change was in scope — purely internal/architectural.

**What was built:**
- `code/src/routes/app.tsx` — now renders `<AppShell><Outlet/></AppShell>` once, instead of `AppLayout` rendering a bare `<Outlet/>`.
- `code/src/components/app-shell.tsx` — no longer takes a `title` prop; derives it from the current route's `staticData.shellTitle` via `useMatches`, with a per-render override channel for the one route that needs it. Replaced raw `auth.me()`/`api.getDashboard()` promise calls with `useQuery` (the dashboard query intentionally shares the Dashboard route's own `["dashboard"]` cache key).
- `code/src/lib/shell-title.ts` (new) — the narrow `ShellTitleOverrideContext`/`useShellTitle` escape hatch for `app.family.add.tsx`'s dynamic title.
- `code/src/lib/router-static-data.d.ts` (new) — TypeScript module augmentation declaring `staticData.shellTitle` on TanStack Router's route options.
- All 13 leaf routes under `/app/*` — removed their own `<AppShell title="...">` wrapper; added `staticData: { shellTitle: "..." }` (12 routes) or `useShellTitle(dynamicTitle)` (the 1 dynamic-title route).

**Testing:** `tsc --noEmit` clean; `eslint` clean (0 errors, 0 warnings) on every touched file — a stray fast-refresh warning was fixed by splitting the hook into its own file rather than left as a known warning. Full backend suite (330 tests, unrelated to this frontend-only change) still passing, confirming no accidental cross-boundary regression.

**Performance Verification** (`PerformanceComparison.md`): re-measured with the identical method — **`auth/me` 14→2** (residual 2 attributed to `app.copilot.tsx`'s own separate, pre-existing, out-of-scope identity fetch), **`dashboard` 12→0** (fully served from cache across the entire 6-navigation sequence), and the DOM node-identity check flipped from `false`/`false`/`false` to `true`/`true`/`true` — direct proof `AppShell` now persists across navigation instead of remounting.

**Live verification:** walked through Dashboard, Goals, Family, Reports, Settings, AI Copilot, Government Schemes, Family Insurance, and both dynamic-title variants of Add Family Member (`?type=parent` / `?type=other`, including via direct URL load, not just in-app navigation) — every screen rendered identically to its pre-Phase-0 appearance, sidebar/header/mobile-nav behavior unchanged, avatar initials and plan-health card correct. Two fresh test accounts used and fully cleaned up.

**Product Consistency Review:** header, sidebar, layout, and mobile bottom-nav behavior confirmed identical across every screen visited; no route produced a different title, a missing plan-health card, or a broken avatar — the one previously-untested edge case (a route with a search-param-dependent title) was specifically verified rather than assumed.

**First-Time User Review:** navigating the app feels identical to before — no perceptible change in what appears on screen, only (per the performance data) fewer redundant loading flickers on repeat visits to the Dashboard, which is a strict improvement, not a behavior change requiring re-review.

**Documentation:** this entry, `DependencyValidation_Phase0.md`, `ArchitectureReview_Phase0.md`, `PerformanceBaseline_Phase0.md`, `DesignReview_Phase0.md`, `PerformanceComparison.md`, `CHANGELOG.md`, `PR_REPORT_Phase0.md`.

**Stopping here per instruction. Phase 1 (Profile Menu), Phase 2 (Search + Keyboard Shortcuts), and Phase 3 (Notifications) have not been started and await review and approval.**

## Global Shell — Phase 1: Profile Avatar Menu & Mobile Sign-out (✅ Complete, 2026-07-08)

**Why this phase existed:** the header avatar was a plain, non-interactive `<div>` (Interactive Product Audit's Dead Click Report #3), and the only working "Sign out" control lived inside the desktop-only sidebar — mobile users had no way to sign out at all.

**Dependency Validation** (`DependencyValidation_Phase1.md`): confirmed the avatar, logout flow, and both nav surfaces directly against source. One correction to the task's framing: no `AuthContext`/`AuthProvider` exists anywhere — auth state is `localStorage` plus the `["currentUser"]` cache Phase 0 already introduced inside `AppShell`, reused directly rather than via a separate context.

**Design Review** (`DesignReview_Phase1.md`): one deliberate, documented deviation from the earlier `ProfileMenuDesign.md` — a single `DropdownMenu` is used at every viewport (not a Dropdown/Drawer split), specifically because this phase's instruction required "no duplicate menu infrastructure." The avatar lives in the shared header (rendered at all viewports), so one implementation closes the mobile gap.

**What was built:** `app-shell.tsx`'s avatar `<div>` became a `DropdownMenu` trigger (reusing the existing, previously-unused `components/ui/dropdown-menu.tsx`) with an identity header (name/email from `AppShell`'s already-fetched `currentUser`) and exactly three real, working items — My Profile, Settings, Sign Out (reusing the existing `handleSignOut`) — no placeholder entries.

**Testing:** `tsc`/`eslint` clean. No backend touched.

**Live verification:** at an 809px viewport (below the sidebar breakpoint), confirmed the menu opens, is fully keyboard-operable (Tab → Enter opens, arrows navigate, Enter activates, Escape closes and returns focus to the trigger — all via Radix, no hand-built logic), and Sign Out genuinely clears the session (`localStorage` token confirmed `null` after) and allows clean re-login. A dedicated ≥1024px desktop-width screenshot pass was not completed in this session (interrupted mid-verification) — flagged explicitly in `PR_REPORT_Phase1.md` as a low-risk gap, since the implementation is a single code path with no viewport branching.

**Documentation:** this entry, `DependencyValidation_Phase1.md`, `DesignReview_Phase1.md`, `CHANGELOG.md`, `PR_REPORT_Phase1.md`.

**Stopping here per instruction. Phase 2 (Global Command Palette & Search) begins next, per direction. Phase 3 (Notifications) remains not started.**

## Global Shell — Phase 2: Global Command Palette & Search (✅ Complete, 2026-07-08)

**Why this phase existed:** the header search bar was a static, non-functional `<div>` with a fake "⌘K" hint (Interactive Product Audit).

**Dependency Validation** (`DependencyValidation_Phase2.md`): confirmed `cmdk`/`command.tsx` fully built and unused. Found one real gap (`CommandDialog` lacks a `DialogTitle` — a Radix accessibility requirement) and one pre-existing, out-of-scope inconsistency (the Goals page itself doesn't share the `["goals"]` cache key the Dashboard uses).

**Architecture Review** (`ArchitectureReview_Phase2.md`, finalized in `ArchitectureReview_Phase2_Final.md`): one palette, lazily-loaded entity queries sharing existing cache keys, one global keyboard listener registered once (Phase 0's persistent-mount guarantee). Surfaced a genuine constraint — no goal/scheme/policy detail view or the "New goal" modal is URL-addressable — resolved with one small, explicitly-flagged `?new=true` search-param addition to `app.goals.tsx` so "Create Goal" is a real action, not a placeholder.

**What was built:** `code/src/components/global-palette.tsx` (new) — searches Goals, Family Members, Government Schemes, and Family Insurance by name; navigates to all 10 real pages; exposes 2 real quick actions (Create Goal, Add Family Member); shows a per-user Recent-searches list. Wired into `app-shell.tsx` via a single global `⌘K`/`Ctrl+K` listener and a real, tappable search button (reachable at all viewports, not just desktop).

**Two real bugs found during live verification and fixed before sign-off** (full detail in `ArchitectureReview_Phase2_Final.md`): (1) "Create Goal" silently did nothing when already on the Goals page, because TanStack Router doesn't remount a route for a search-param-only navigation — fixed with a `useEffect` that re-checks the param on every navigation, not just first mount; (2) entity search results appeared unfiltered on an empty query, contradicting the UX Review's own design — fixed by gating all four entity groups on a non-empty query.

**Testing:** `tsc`/`eslint` clean (0 errors, 0 warnings) on every touched file. Full backend suite (330 tests) unaffected — zero backend files touched, per this phase's explicit scope.

**Live verification:** `⌘K` and `Ctrl+K` both confirmed opening the palette from multiple pages; typed search correctly filtered to real goals/family members with zero false negatives; a family-member result correctly deep-linked to that exact member's real ID; Escape and click-outside both close the palette; Recent searches persisted correctly across a full page navigation; a genuine 390px mobile viewport confirmed the search icon is tappable and opens the identical palette.

**Documentation:** this entry, `DependencyValidation_Phase2.md`, `ArchitectureReview_Phase2.md`, `UXReview_Phase2.md`, `ArchitectureReview_Phase2_Final.md`, `SearchPerformanceReport.md`, `CHANGELOG.md`, `PR_REPORT_Phase2.md`.

**Stopping here per instruction. Awaiting review and approval before Phase 3 (Notifications).**

## Global Shell — Phase 3: Notification Center (✅ Complete, 2026-07-08)

**Why this phase existed:** the header bell was a static, non-functional decoration (Interactive Product Audit).

**Dependency Validation** (`DependencyValidation_Phase3.md`): confirmed five of six candidate notification sources (Insurance, Schemes, Family Member Added, Goal at Risk, Goal Completed) are reachable with zero new calculation — pure reads of already-computed/already-stored/already-logged data. Confirmed ADR-001 (goal probability recalculation) is fully implemented in code despite its own status line still reading "Proposed." "Goal probability changed" was the one candidate requiring genuinely new state and was deliberately not built.

**Architecture Review** (`ArchitectureReview_Phase3.md`): evaluated Fully Generated (disqualified — can't support read/unread), Fully Persisted (rejected — recreates the exact recommendation-engine drift risk `RecommendationConsistencyReview_Task10.md` already proved the live engines avoid), chose Hybrid — notification content is never persisted, only a seen/read/dismissed marker keyed by a deterministic `uuid5` identity (`NotificationIdentityReview.md`). Established that no `GET` endpoint in this feature may ever write, directly informed by this project's own ADR-001 precedent.

**What was built:** one new table (`notification_markers`), a new `notification_service.py` that collects the five sources fresh on every read, and a new `NotificationCenter` component (bell + Radix `Popover` panel, previously-unused scaffold) with Today/Earlier grouping, mark-read, and dismiss.

**Two real bugs found and fixed during implementation/verification** (full detail in `NotificationArchitecture.md`): (1) `family_member_added` notifications initially showed no name, since `AuditLog.after_state` only stores `member_id`/`relationship_type` — fixed via a `HouseholdMember` lookup; (2) the notification panel stayed open after navigating away from a clicked item — fixed by making the `Popover` a controlled component.

**One environment issue correctly diagnosed, not misattributed to the feature**: an unrelated project's backend intermittently claimed port 8000 during live verification (and respawned once after being stopped), briefly making the app appear broken — traced to the actual cause and resolved with the user's explicit go-ahead, rather than assumed to be a regression in this phase's code.

**Testing:** backend `ruff`/`mypy` clean; full suite 341/341 passing (330 pre-existing + 11 new), 97.53% coverage. Frontend `tsc`/`eslint` clean.

**Live verification:** all five notification types confirmed firing with live, correct content; badge count tracked read/dismiss actions correctly; state persisted across a full page reload; clicking a notification navigated to the matching real page with identical content; full keyboard accessibility confirmed (Tab/Enter/Escape, focus trapping and return, all via Radix `Popover`).

**Documentation:** this entry, `DependencyValidation_Phase3.md`, `ArchitectureReview_Phase3.md`, `NotificationIdentityReview.md`, `NotificationArchitecture.md`, `NotificationPerformanceReport.md`, `CHANGELOG.md`, `PR_REPORT_Phase3.md`.

**Stopping here per instruction. Awaiting review and approval. Not beginning any Milestone 3 work.**

## Global Shell Certification (2026-07-08) — CERTIFIED WITH CONDITIONS

A full ten-review certification of Phases 0-3 as a single, integrated capability found the shell production-ready with one condition: the Profile Menu didn't close when the Command Palette opened via ⌘K, allowing both to be simultaneously visible — a real, cross-phase interaction gap none of the four individual phase reviews could have caught in isolation. Everything else (architecture, performance, accessibility, mobile, consistency, first-time-user experience, regression, security) passed with direct, live-verified evidence. Full detail: `GlobalShellCertification.md`, `GlobalShellPerformanceReport.md`, `GlobalShellAccessibilityReport.md`, `GlobalShellRegressionReport.md`, `GlobalShellTechnicalDebt.md`, `ExecutiveSummary.md`.

## M2.6.1 — Overlay Mutual Exclusion Fix (✅ Complete, 2026-07-08)

**Why this task existed:** resolve the single certification condition above — nothing else.

**Dependency Validation** (`DependencyValidation_M2.6.1.md`): traced the exact root cause — `AppShell`'s `⌘K` handler could only ever toggle its own `paletteOpen` boolean; the profile menu's open state was fully uncontrolled Radix internals invisible to the rest of the tree, and the notification popover's open state was controlled but never lifted out of `NotificationCenter`. Also explained why the bug was inconsistent (notifications happened to auto-close on palette open, profile menu didn't) — coincidental agreement between two different Radix primitives' own default dismiss behavior, not a designed guarantee.

**Architecture Review** (`ArchitectureReview_M2.6.1.md`): consolidated four independent overlay booleans into one shared `activeOverlay: "palette" | "notifications" | "profile" | "more" | null` state owned by `AppShell` — structurally guarantees only one overlay can ever be open, reusing `GlobalPalette`'s existing controlled-component pattern for `NotificationCenter` and the profile `DropdownMenu` rather than introducing a new mechanism (no Context provider, no event bus).

**What was built:** `code/src/components/app-shell.tsx` and `code/src/components/notification-center.tsx` updated to read/write the single `activeOverlay` state. Zero backend changes, zero new dependencies, zero changes to Search/Notification/Profile functionality, Routing, Navigation, Theme, or AI.

**Testing:** `tsc`/`eslint` clean on both files. Live-verified every pairwise overlay combination (Palette↔Profile, Palette↔Notifications, Notifications↔Profile, and the mobile "More" sheet against both) at desktop and mobile widths — confirmed mutually exclusive in every case, including the certification's exact reproduction sequence. Six rapid open/close cycles produced no stuck overlays and no new console errors (one pre-existing, unrelated Grammarly-extension hydration warning noted and traced, not caused by this fix).

**Documentation:** this entry, `DependencyValidation_M2.6.1.md`, `ArchitectureReview_M2.6.1.md`, `AccessibilityReview_M2.6.1.md`, `CHANGELOG.md`, `PR_REPORT_M2.6.1.md`.

**Stopping here per instruction. Awaiting final certification. Not beginning Milestone 3.**
