# IMPLEMENTATION ROADMAP — PreLaunchProductAudit.md

**Role:** Principal Architect
**Scope:** Convert every finding in `PreLaunchProductAudit.md` into a scheduled, dependency-ordered engineering roadmap. No code is written or proposed at the line level in this document — file-level and schema-level scope only.
**Method:** Every finding below was re-verified against current source during this pass, not merely copied from the audit. Three corrections to the audit's own claims surfaced during that re-verification and are called out explicitly, because an implementation roadmap built on an overstated backend surface would under-scope Milestone 1:

1. **`backend/app/routers/financials.py` has no companion service file.** All CRUD logic is inline in the router — a direct violation of `CLAUDE.md`'s "Keep routers thin" rule. Any work touching this router should extract a `financials_service.py` while it's open, not perpetuate the pattern.
2. **Income and Expense have no update capability at all — frontend *or* backend.** `schemas/financials.py` defines `IncomeSourceCreate`/`Response` and `ExpenseCreate`/`Response` only; there is no `IncomeSourceUpdate` or `ExpenseUpdate`, and the router has no `PATCH` route for either. Only `Asset` and `Liability` have `Update` schemas and `PATCH` endpoints. The audit's claim that "backend CRUD... is fully implemented server-side" for all four entities is an overstatement for two of the four. Milestone 1 has backend scope, not just frontend scope.
3. **`PUT /api/v1/auth/me` (backend/app/routers/auth.py:218-225) only ever reads `body.full_name`.** There is no server-side email-update path at all — PLA-011 is not a wiring bug in the frontend alone; the backend capability doesn't exist yet either.
4. **`goal_household_members` is explicitly documented as a non-authoritative, purely descriptive join table** (`family_service.py:298-306`, citing `Milestone2ImplementationContract.md §0.1`). This meaningfully downgrades PLA-008: the cascade on family-member delete clears a *tag*, not a goal, an insurance policy, or any owned data. The finding survives as a UX-disclosure improvement, not a data-integrity defect — reflected in its milestone placement and severity below.

Every gap discussed narratively in the audit (Parts 4, 5, 6, 7) but never assigned a PLA number is formally numbered here (PLA-004 through PLA-007, PLA-012 through PLA-015) so nothing is scheduled off-the-books.

---

## PART A — PER-FINDING ENGINEERING ANALYSIS

### PLA-001 — No post-onboarding CRUD for Income / Expenses / Assets / Liabilities
**Root cause:** The frontend route was never built; the backend was completed asymmetrically (Asset/Liability got full CRUD, Income/Expense did not) as if UI work would immediately follow and reveal the gap. It never did.
**Frontend files:** New route file(s) — likely `code/src/routes/app.financials.tsx` plus sub-components under a new `code/src/components/financials/` directory (mirroring `code/src/components/dashboard/` and `onboarding/` conventions). Reuse candidates: `code/src/components/onboarding/wizard-steps.tsx` (the list-add/list-delete UI for these exact four entities already exists there and is the correct starting point, not a rewrite). `code/src/lib/api.ts` already has typed client functions for all eight operations; only two (`updateIncome`, `updateExpense`) need new backend endpoints to back them.
**Backend APIs:** Existing: `GET/POST/DELETE /api/v1/financials/{income,expenses}`, full CRUD on `/api/v1/financials/{assets,liabilities}`. New: `PATCH /api/v1/financials/income/{id}`, `PATCH /api/v1/financials/expenses/{id}`.
**DB tables:** `income_sources`, `expenses`, `assets`, `liabilities` — no schema change required for the CRUD itself (columns already exist); only new Pydantic `Update` schemas, not new columns.
**Services:** New `backend/app/services/financials_service.py` (extracted from the router, closing the "routers thin" violation as part of this work rather than as separate cleanup).
**Calculation engines affected:** None directly — none of these four entities are in the Monte Carlo Calculation Context frozenset (`{current_amount, monthly_contribution, target_date, risk_profile, target_amount}`, all goal-level fields). This is a load-bearing fact for scope control: **shipping this milestone cannot regress Monte Carlo goal-probability output**, because Monte Carlo never reads these tables.
**Recommendation engine impact:** None — `family_recommendations_service.py` does not consume `income_sources`/`expenses`/`assets`/`liabilities` per the audit's grep. Dashboard aggregation (`planning_service.get_dashboard`) is the only consumer, and it already reads live — no dashboard code changes needed for values to start reflecting reality once writes are possible.
**Complexity:** High — largest single unit of work in this roadmap, but low-risk work: additive schemas, additive endpoints, one new route, no changes to existing calculation paths.
**Dependencies:** None upstream. This is the root dependency for PLA-003, PLA-007, PLA-012, PLA-015, and partially for PLA-006.
**Migration risk:** Low. No new columns required for the CRUD itself. If a "last updated" timestamp is added per PLA-003's recommendation, that's one additive, nullable-with-default column per table — consistent with the existing additive-only Alembic discipline (migrations 001-009).

### PLA-002 — No post-onboarding UI for Planning Assumptions; onboarding copy is false
**Root cause:** Same pattern as PLA-001, but the backend here is *already complete* — `GET/PUT /api/v1/assumptions` and `FinancialAssumptionsUpdate` schema both exist and are fully field-complete (`inflation_rate`, three `expected_return_*` tiers, `tax_rate`, `retirement_age`, `social_security_monthly`). This is frontend-only scope.
**Frontend files:** New section in `code/src/routes/app.settings.tsx` (a fifth card alongside `ChangePasswordSection`/`DeleteAccountSection`), or promote to its own settings sub-route if the form grows past a simple card. Also a one-line copy fix in `code/src/components/onboarding/wizard-steps.tsx` (the Assumptions step) if the settings section does not ship in the same release — the false claim must not survive that gap unaddressed.
**Backend APIs:** `GET/PUT /api/v1/assumptions` — already implemented, zero backend work.
**DB tables:** `financial_assumptions` — no schema change.
**Services:** Existing assumptions service/router logic — no change needed.
**Calculation engines affected:** `monte_carlo.py` reads `inflation_rate` for real-return math (the only assumption field with verified numerical effect, per Volume 2). Editing assumptions post-onboarding means a user's next goal edit will silently pick up the new inflation rate on its next Monte Carlo run — this is correct, expected behavior, not a regression, but should be called out in release notes since it changes historical goal-probability numbers going forward.
**Recommendation engine impact:** None directly verified; `tax_rate` is a plausible input to insurance/scheme recommendation math and should be spot-checked during implementation (not re-derived here — flag for the implementing engineer to confirm against `family_insurance_service.py`).
**Complexity:** Low — single form, existing backend, existing schema.
**Dependencies:** None. Can ship independently of, and in parallel with, PLA-001.
**Migration risk:** None.

### PLA-003 — Dashboard values frozen at onboarding-day data
**Root cause:** Entirely downstream of PLA-001 — the read path (`planning_service.get_dashboard`) is correct and already live; there is simply never a write to read.
**Frontend files:** None required for the core fix (resolves automatically once PLA-001 ships). Optional enhancement: a "last updated" indicator on Dashboard cards, which would touch `code/src/routes/app.index.tsx` and whichever dashboard card components render Net Worth/Savings.
**Backend APIs:** None required for the core fix. Optional: extend `GET /api/v1/dashboard` response with a `financials_last_updated_at` field.
**DB tables:** Optional: additive `updated_at` (or reuse existing `updated_at` if already present at the row level — verify during implementation) on `income_sources`, `expenses`, `assets`, `liabilities`.
**Services:** `planning_service.get_dashboard` — optional addition of a `MAX(updated_at)` aggregation across the four tables.
**Calculation engines affected:** None.
**Recommendation engine impact:** None directly, but staleness of the *inputs* recommendations are silently built on (per Part 9 of the audit) is exactly what a "last updated" indicator would make visible to the user for the first time.
**Complexity:** Trivial once PLA-001 ships (the core fix is free); Low for the optional staleness-indicator enhancement.
**Dependencies:** Hard dependency on PLA-001.
**Migration risk:** Low, same additive pattern as PLA-001's optional timestamp columns — coordinate into the same migration if both ship together to avoid two near-identical Alembic revisions.

### PLA-004 — Insurance policy CRUD incomplete (coverage sub-object only)
*(Numbered now; discussed in audit Part 1/Part 5 without a PLA id.)*
**Root cause:** `family.py` router exposes `PUT /insurance/policies/{id}/coverage` but no create/edit/delete for the parent `HealthPolicy` record itself — the coverage sub-resource was built before (or instead of) the parent resource's own CRUD.
**Frontend files:** `code/src/routes/app.family.insurance.tsx` and whatever renders the policy list there.
**Backend APIs:** New — `POST/PUT/DELETE /api/v1/family/insurance/policies`.
**DB tables:** `health_policies`, `health_policy_coverage`.
**Services:** `backend/app/services/family_insurance_service.py`.
**Calculation engines affected:** 80D deduction calculation reads policy + coverage data — no calculation logic changes, only the ability to keep the input current.
**Recommendation engine impact:** `family_recommendations_service.py` surfaces insurance-gap recommendations computed from this data; same "correct math, frozen input" pattern as PLA-001.
**Complexity:** Medium.
**Dependencies:** None; can run in parallel with PLA-001.
**Migration risk:** Low — no schema change, only new endpoints.

### PLA-005 — No account-level risk profile; per-goal and onboarding-time risk answers never reconcile
*(Numbered now; Part 7 of the audit.)*
**Root cause:** Product-design gap, not a bug — risk profile was deliberately scoped per-goal (`GoalSimPanel.riskProfile`), and the onboarding-time risk questionnaire answer that seeds `FinancialAssumptions`' expected-return tiers was never exposed as an editable, named concept afterward.
**Frontend files:** Would require a new "default risk profile" concept surfaced in the (new, PLA-002) Assumptions settings section, with copy explaining its relationship to per-goal overrides.
**Backend APIs:** None new — `FinancialAssumptions.expected_return_*` fields already exist; this is a UI/product-definition task, not a backend gap.
**DB tables:** None.
**Services:** None.
**Calculation engines affected:** None — clarifies an existing input, does not change Monte Carlo logic.
**Recommendation engine impact:** None.
**Complexity:** Low, but primarily a **product decision**, not an engineering one — recommend resolving the product question ("should there even be an account-level default, or is per-goal-only the intended design?") before scheduling engineering work.
**Dependencies:** Soft dependency on PLA-002 shipping first (same settings surface).
**Migration risk:** None.

### PLA-006 — No restore/undo on any soft-deleted entity
*(Numbered now; Part 5 of the audit.)*
**Root cause:** Delete UI was built with a confirm step as the only safety net; no "Trash" or restore concept exists anywhere in the product for goals (the one entity with soft-delete today) or, prospectively, for the financials entities once PLA-001 ships.
**Frontend files:** New — a "Recently deleted" view, plausibly under Settings or Goals.
**Backend APIs:** New — `GET /api/v1/goals?include_inactive=true` (or a dedicated `/goals/trash` endpoint), `POST /api/v1/goals/{id}/restore`.
**DB tables:** `goals` (`is_active` already exists and is exactly the field this would flip back). If PLA-001 adopts soft-delete for financials entities (see note below), the same pattern extends there.
**Services:** `planning_service` — add a restore path alongside the existing soft-delete path.
**Calculation engines affected:** Restoring a goal should re-trigger `calculate_goal_probability` (its stored probability is stale from before deletion) — this is a real recalculation-trigger requirement, not just a data flip.
**Recommendation engine impact:** None.
**Complexity:** Medium.
**Dependencies:** None hard; **coordinate with PLA-001** on whether new financials entities should be soft-deleted (`is_active` column) or hard-deleted (current router behavior for all four). Recommend soft-delete for consistency with the goals pattern and with `CLAUDE.md`'s existing soft-delete principle — this is an architectural decision that should be made once, in PLA-001, not retrofitted later.
**Migration risk:** Low if decided during PLA-001 (additive `is_active` columns, same migration). Medium if retrofitted later (requires a follow-up migration plus a backfill of `is_active = true` on all existing rows, and an audit of the existing hard-DELETE endpoints' callers before behavior changes underneath them).

### PLA-007 — Settings "Coming Soon" cards omit the (more consequential) Financials section
*(Numbered now; Part 6 of the audit.)*
**Root cause:** Messaging/prioritization gap — Notifications and Linked Accounts were flagged as upcoming; Financials, the larger gap, was not, because it wasn't tracked as a discrete backlog item until this audit.
**Frontend files:** `code/src/routes/app.settings.tsx`.
**Backend APIs:** None.
**DB tables:** None.
**Services:** None.
**Calculation engines affected:** None.
**Recommendation engine impact:** None.
**Complexity:** Trivial.
**Dependencies:** Self-resolves once PLA-001/PLA-002 ship (the "Coming Soon" card is simply removed and replaced by the real section). If either milestone slips, add the card as an interim honesty fix — same pattern already used correctly for Household on the Profile page.
**Migration risk:** None.

### PLA-008 — Family-member delete cascade is undisclosed (downgraded from the audit's framing — see correction #4 above)
**Root cause:** The delete-confirmation component was copied from the goal-delete pattern (no cascade) without adapting the copy for family members, whose removal clears entries in the *descriptive* `goal_household_members` join table. Since that table is documented as non-authoritative, no goal, policy, or owned record is destroyed — only a "this goal also affects..." tag is cleared, which is arguably the *correct* behavior when someone leaves the household.
**Frontend files:** `code/src/routes/app.family.members.$id.tsx`.
**Backend APIs:** Extend `DELETE /api/v1/family/members/{id}` response, or add a pre-flight `GET /api/v1/family/members/{id}/impact` the frontend calls before showing the confirm dialog.
**DB tables:** Read-only query against `goal_household_members` and the insurance dependent-link table for the impact preview — no schema change.
**Services:** `family_service.py` — add an impact-preview query alongside the existing delete function.
**Calculation engines affected:** None.
**Recommendation engine impact:** None.
**Complexity:** Low.
**Dependencies:** None.
**Migration risk:** None.

### PLA-009 — Scenario planning not implemented
**Root cause:** Never built; not a regression. The audit explicitly recommends no action (YAGNI) absent a product decision to build it.
**Disposition:** **Not scheduled.** Retained here only so it isn't silently dropped from the record. Revisit only if product strategy calls for it explicitly.

### PLA-010 — No retirement decumulation modeling
**Root cause:** Deliberate v1 engine-scope decision (per Volume 9 ADR context) — Monte Carlo models accumulation to a target only.
**Frontend files:** Near-term: a tooltip/info-panel on retirement-category goals in `GoalSimPanel` clarifying the scope. Long-term (not scheduled here): a genuinely new goal-detail UI for withdrawal-phase inputs.
**Backend APIs:** None for the near-term documentation fix. Long-term: new fields/endpoint for withdrawal rate, would require its own schema design pass.
**DB tables:** None for near-term. Long-term: new columns or a new `retirement_withdrawal_plan` table.
**Services:** None for near-term.
**Calculation engines affected:** `monte_carlo.py` — long-term work only; out of scope for this roadmap's milestones.
**Recommendation engine impact:** None for near-term.
**Complexity:** Trivial (documentation/tooltip) now; High (new simulation phase) if ever scheduled — explicitly **not** part of Milestones 1-6 below.
**Dependencies:** None for the near-term fix.
**Migration risk:** None for near-term.

### PLA-011 — Profile email field editable but silently discarded (backend gap confirmed, not just frontend)
**Root cause:** `handleSubmit` in `app.profile.tsx` never sends `email`, **and** `PUT /api/v1/auth/me` never reads it even if sent — the feature is incomplete on both sides, not a one-line frontend wiring fix. A real email change also implies re-verification (the `User.is_verified` field exists and would need a path to flip back to unverified + resend a verification email), which does not exist anywhere in the current auth flow.
**Frontend files:** `code/src/routes/app.profile.tsx:74-87`.
**Backend APIs:** `PUT /api/v1/auth/me` needs to accept and persist `email`, with uniqueness validation (email is presumably unique-constrained on `users` — confirm during implementation) and a decision on re-verification flow.
**DB tables:** `users` (`email`, `is_verified`).
**Services:** `auth_service.py`, plus whatever the (currently token-only, no email provider wired) verification-token flow is — the same "no email/SMS provider wired up yet" limitation noted in `auth.py`'s forgot-password comments applies here too and should be scoped honestly, not assumed away.
**Calculation engines affected:** None.
**Recommendation engine impact:** None.
**Complexity:** Medium — larger than it looks once re-verification is accounted for. **Two shippable options exist and should be an explicit decision, not an implementation default:** (a) full email-change-with-reverification flow (Medium-High complexity, blocked on the same missing email provider noted elsewhere in the codebase), or (b) make the field read-only immediately (Trivial) as a launch-blocking stopgap, with full support deferred.
**Dependencies:** Option (a) is blocked on an email-delivery provider being wired up — currently not the case anywhere in the codebase (`auth.py`'s own comments confirm this). Option (b) has no dependencies.
**Migration risk:** None for option (b). None for option (a) either — no schema change, `is_verified` already exists.

### PLA-012 — Job loss / income disruption has no bulk workflow
*(Numbered now; Part 2 of the audit.)*
**Root cause:** Consequence of PLA-001 (no income CRUD at all) compounded by the absence of any cross-goal bulk action — even after PLA-001 ships, "pause all contributions" would still require editing each goal individually.
**Frontend files:** Depends on PLA-001 shipping first for the income side; a bulk action would live in `code/src/routes/app.goals.tsx`.
**Backend APIs:** New — a bulk-update endpoint, e.g. `PATCH /api/v1/goals/bulk` accepting a list of goal IDs and a partial update (e.g. `monthly_contribution: 0`).
**DB tables:** `goals` — no schema change.
**Services:** `planning_service` — new bulk-update function; must call `calculate_goal_probability` per affected goal, so this is an N-simulation operation, not a single one — worth a complexity flag for response-time behavior on accounts with many goals.
**Calculation engines affected:** Monte Carlo, once per affected goal.
**Recommendation engine impact:** None directly.
**Complexity:** Medium.
**Dependencies:** Soft dependency on PLA-001 (income-side of the same life event) for the workflow to be complete end-to-end, though the goal-bulk-pause half is independently shippable.
**Migration risk:** None.

### PLA-013 — "Starting a business" not modeled as a goal category or asset/liability type
*(Numbered now; Part 2 of the audit.)*
**Root cause:** Not built — no evidence it was ever in scope.
**Frontend files:** `code/src/components/onboarding/wizard-steps.tsx` (asset/liability type pickers), goal category picker in `GoalSimPanel` and goal-create flow.
**Backend APIs:** None new if simply adding an enum value; `goal_category` and the `asset_type`/`liability_type` strings are not strongly typed at the DB level (`String(50)`, per `financials.py`), so adding a new category value is a validation/schema change, not a migration.
**DB tables:** `goal_category` Postgres enum (defined via `name="goal_category"` in `goal.py`) — **this one is a real enum type, unlike asset/liability types, so adding a value requires an `ALTER TYPE ... ADD VALUE` migration**, which is additive but has a documented Postgres caveat (cannot run inside the same transaction as other DDL in older Postgres versions; confirm behavior on the project's Postgres 16).
**Services:** None beyond validation updates.
**Calculation engines affected:** `monte_carlo.py`'s `PROFILE_PARAMS` are keyed by risk profile, not goal category, so a new category needs no new simulation parameters — low risk to the engine.
**Recommendation engine impact:** None verified; worth a spot-check in case any recommendation rule branches on `goal.category`.
**Complexity:** Low-Medium (the enum migration caveat is the only real wrinkle).
**Dependencies:** None.
**Migration risk:** Low-Medium — flagged above as the one enum-type migration in this entire roadmap; every other change in this document is additive columns/tables or new endpoints.

### PLA-014 — No dedicated Emergency Fund entity
*(Numbered now; Part 2/Part 9 of the audit.)*
**Root cause:** Never modeled as data — it exists today only as static recommendation text (`planning_service.py:110`).
**Frontend files:** New — an Emergency Fund card/section, plausibly on Dashboard or as a new goal category (product decision needed: is this a special goal, or a wholly new entity?).
**Backend APIs:** New, dependent on the product decision above.
**DB tables:** New — either a dedicated `emergency_funds` table or reuse of `goals` with `category="emergency_fund"` (much lower migration risk, reuses the existing enum-and-Monte-Carlo machinery).
**Services:** `planning_service.py` — replace the static recommendation with a data-backed one once an entity exists.
**Calculation engines affected:** If modeled as a goal, Monte Carlo applies unchanged. If modeled as a new entity, a new (likely much simpler, non-Monte-Carlo) target-vs-current calculation would need to be written.
**Recommendation engine impact:** The existing static recommendation card gets replaced by a real, data-driven one.
**Complexity:** Low if reusing the goal model; Medium-High if building a bespoke entity.
**Dependencies:** Benefits from PLA-001 shipping first (liquid-asset tracking is already correct there; an emergency fund target is most useful when compared against real, current liquid assets).
**Migration risk:** Low if reusing `goals` (zero new tables); Medium if new table (new migration, but additive, no backfill needed since no existing data to migrate).

### PLA-015 — No debt payoff / amortization workflow
*(Numbered now; Part 2 of the audit.)*
**Root cause:** `liabilities` are captured as flat balances with no payoff-strategy modeling (snowball/avalanche, payoff-date projection) anywhere in the backend.
**Frontend files:** New — payoff-strategy UI, most naturally added to the Financials screen from PLA-001 rather than as a separate route.
**Backend APIs:** New — a payoff-projection endpoint (pure calculation, no new persisted state required if computed on demand from `liabilities.balance`/`interest_rate`/`minimum_payment` — confirm these fields exist on the model during implementation; if not, they're additive columns).
**DB tables:** `liabilities` — possibly additive columns (`interest_rate`, `minimum_payment`) if not already present.
**Services:** New calculation logic, plausibly a small new module rather than folded into `monte_carlo.py` (amortization is deterministic, not stochastic — it does not belong in the Monte Carlo engine).
**Calculation engines affected:** A new, separate deterministic calculator — explicitly not Monte Carlo, and should not be built inside `monte_carlo.py`.
**Recommendation engine impact:** Could feed a new "pay off high-interest debt first" recommendation rule — optional, not required for the base feature.
**Complexity:** Medium.
**Dependencies:** Should ship after PLA-001 (liabilities CRUD) since payoff planning is meaningless without editable liability data.
**Migration risk:** Low — additive columns only, if needed at all.

---

## PART B — MILESTONES

### Milestone 1 — Financial Profile Management
**Purpose:** Close the single largest gap in the product — give users a durable way to keep their income, expenses, assets, liabilities, and planning assumptions current after onboarding. This is the dependency root for nearly everything else in this roadmap.
**Features:** Full CRUD screen for Income / Expenses / Assets / Liabilities (PLA-001); Assumptions section in Settings (PLA-002); backend `PATCH` endpoints and `Update` schemas for Income and Expense to reach parity with Asset/Liability; extraction of `financials_service.py` from the router.
**Files:** `code/src/routes/app.financials.tsx` (new), `code/src/components/financials/*` (new), `code/src/routes/app.settings.tsx` (extended), `code/src/lib/api.ts` (two new client calls), `backend/app/routers/financials.py` (thinned), `backend/app/services/financials_service.py` (new), `backend/app/schemas/financials.py` (two new `Update` schemas), `backend/app/routers/assumptions.py` (unchanged — already complete).
**Components:** Reused list-add/list-edit/list-delete patterns from `wizard-steps.tsx`; reused two-step delete-confirm pattern from `GoalSimPanel`.
**Services:** `financials_service.py` (new), existing assumptions service (unchanged).
**APIs:** 2 new (`PATCH /financials/income/{id}`, `PATCH /financials/expenses/{id}`); 0 new for assumptions (already exists).
**Estimated LOC:** Backend ~300-400 (2 endpoints, 2 schemas, service extraction preserving existing logic, tests). Frontend ~900-1300 (new route, 4 CRUD sections, Assumptions settings card, form validation, empty/loading/error states matching existing conventions).
**Testing strategy:** Extend `backend/tests/test_financials.py` with the two new `PATCH` endpoints (mirror existing Asset/Liability update tests). New `backend/tests/test_assumptions.py` if one does not already exist (confirmed absent from the current test directory listing) covering the settings-triggered `PUT`. Frontend: component tests for the new financials forms plus a Playwright end-to-end journey (add → edit → delete an income source, an asset; edit an assumption) — per this project's web-testing convention, E2E should cover the golden path at minimum, screenshotted at the 320/768/1024/1440 breakpoints given the Deep Navy Premium design system is frozen and must render correctly at all of them.
**Rollback strategy:** Purely additive backend (new endpoints, new schemas, no altered response shapes on existing endpoints) — safe to revert independently. Frontend route is net-new — disabling it is a route removal / nav-link removal, zero impact on any other screen. No feature flag is strictly required given the additive nature, but a flag is recommended for staged rollout given this is the highest-traffic new surface in the roadmap.
**Success criteria:** A user can add, edit, and delete at least one row of each of the four financial-fact types and one Assumptions field without a page reload losing state; Dashboard Net Worth/Savings numbers visibly change after an edit on next load; zero change to any existing Monte Carlo goal-probability output for goals untouched by this work (regression-test existing goals' probabilities before/after deploy).

### Milestone 2 — Life Events
**Purpose:** Build the event-specific workflows that raw CRUD (Milestone 1) doesn't cover on its own — the gaps identified by walking through actual life events rather than entities.
**Features:** Bulk goal-contribution pause for income disruption (PLA-012); new "business" goal category / asset-liability type (PLA-013); Emergency Fund entity and dashboard card (PLA-014); debt payoff/amortization projection (PLA-015); insurance policy full CRUD (PLA-004).
**Files:** `code/src/routes/app.goals.tsx` (bulk action UI), `code/src/components/onboarding/wizard-steps.tsx` and `GoalSimPanel` (new category option), new Emergency Fund component (location per product decision — Dashboard vs. Goals), `code/src/routes/app.financials.tsx` (debt payoff panel, built on Milestone 1's screen), `code/src/routes/app.family.insurance.tsx` (policy CRUD).
**Components:** New bulk-select UI pattern (does not currently exist anywhere in the product — this is the one genuinely new interaction pattern in this roadmap, not a reuse of an existing one).
**Services:** `planning_service` (bulk update + emergency-fund calculation), new deterministic amortization module (explicitly separate from `monte_carlo.py`), `family_insurance_service.py` (policy CRUD).
**APIs:** `PATCH /api/v1/goals/bulk` (new), emergency-fund endpoint(s) (new, scope depends on product decision in PLA-014), debt-payoff-projection endpoint (new), `POST/PUT/DELETE /api/v1/family/insurance/policies` (new).
**Estimated LOC:** Backend ~500-700 across four sub-features (varies significantly by the PLA-014 product decision — reusing `goals` keeps this toward the low end). Frontend ~700-1000.
**Testing strategy:** Backend integration tests per new endpoint, matching existing `test_family_insurance.py`/`test_financials.py` conventions. Explicit regression test asserting bulk goal update triggers one `calculate_goal_probability` call per affected goal and no more (avoid an N+1-style over-simulation bug). Frontend: Playwright coverage for the bulk-pause flow and the debt-payoff panel as the two highest-complexity new interactions.
**Rollback strategy:** Each of the four sub-features is independently toggleable/revertable — they share no code with each other. The `goal_category` enum addition (PLA-013) is the one irreversible-in-practice change (Postgres does not support removing enum values cleanly) — treat that specific migration as a one-way door and get product sign-off on the category name before running it.
**Success criteria:** A simulated job-loss scenario (pause all goal contributions) completes in one user action and every affected goal's probability updates correctly; a business-category goal can be created and simulated; an emergency-fund target can be set and tracked against real liquid assets (post-Milestone-1 data); a liability shows a payoff date projection; an insurance policy can be created end-to-end without any onboarding-only workaround.

### Milestone 3 — Dashboard Improvements
**Purpose:** Make the Dashboard trustworthy over time, not just on day one — close PLA-003 and add the staleness-signaling the audit's Part 9 (CFP perspective) identifies as the product's biggest trust risk.
**Features:** Core fix is automatic once Milestone 1 ships (live data now exists to read); this milestone adds the explicit "last updated" signal on financial-fact-derived cards, and (optionally) a periodic review reminder notification sourced from `notification_service.py`'s existing live-computed pattern.
**Files:** `code/src/routes/app.index.tsx`, dashboard card components under `code/src/components/dashboard/`, `backend/app/services/planning_service.py` (`get_dashboard`), `backend/app/services/notification_service.py` (optional new notification source, following its existing pattern of five live-computed sources).
**Components:** New "last updated" badge component (small, reusable across the affected cards).
**Services:** `planning_service.get_dashboard` (extend response), `notification_service` (optional).
**APIs:** `GET /api/v1/dashboard` — additive response field, non-breaking.
**Estimated LOC:** Backend ~80-150. Frontend ~150-250.
**Testing strategy:** Extend `backend/tests/test_dashboard.py` to assert the new field's presence and correctness against fixture data with known `updated_at` values. Frontend: snapshot/visual test confirming the badge renders and updates after an edit made in Milestone 1's screen.
**Rollback strategy:** Fully additive API field and a purely cosmetic frontend badge — trivially revertable, zero risk to existing dashboard consumers (frontend or otherwise).
**Success criteria:** After editing any financial fact via Milestone 1's screen, the Dashboard visibly shows an updated "last updated" timestamp on next load without a manual refresh workaround.

### Milestone 4 — UX Improvements
**Purpose:** Fix the trust-breaking and messaging-inconsistency issues that don't require new data models — the fast, high-trust-impact wins.
**Features:** Profile email field fix or read-only stopgap (PLA-011); Settings "Coming Soon" card correction (PLA-007); onboarding Assumptions copy fix if Milestone 1's Settings section is not yet shipped (PLA-002's copy half); family-member delete impact disclosure (PLA-008); Milestone 1's own new screens should follow the Household-field precedent (`app.profile.tsx:164`) for any UI still marked as pending.
**Files:** `code/src/routes/app.profile.tsx`, `code/src/routes/app.settings.tsx`, `code/src/components/onboarding/wizard-steps.tsx`, `code/src/routes/app.family.members.$id.tsx`, `backend/app/routers/auth.py` (only if PLA-011's full option (a) is chosen over the read-only stopgap).
**Components:** Impact-preview text/component for the family-member delete confirm step.
**Services:** `auth_service.py` (only for PLA-011 option (a)), `family_service.py` (impact-preview query for PLA-008).
**APIs:** `PUT /api/v1/auth/me` (extended, option (a) only), `GET /api/v1/family/members/{id}/impact` (new, for PLA-008).
**Estimated LOC:** ~200-350 total across all sub-items if PLA-011 ships as the read-only stopgap; +300-500 more if the full email-change-with-reverification flow is chosen (and that flow is blocked on an email provider being wired up — see PLA-011's dependency note).
**Testing strategy:** Each fix is small enough for direct unit/integration coverage matching its existing test file (`test_family_router.py` for PLA-008, a new or extended auth test file for PLA-011). No new testing infrastructure needed.
**Rollback strategy:** All changes in this milestone are copy/UI-only or additive-endpoint — independently and trivially revertable, no shared blast radius between the sub-items.
**Success criteria:** No screen in the product shows a "Saved" confirmation for data that was not persisted; every place a feature is not yet available says so honestly (matching the Household-field precedent) rather than presenting a working-looking form that silently does nothing; family-member delete confirmation discloses affected goals/policies by count.

### Milestone 5 — Data Integrity
**Purpose:** Close the soft-delete/restore gap (PLA-006) and formalize the delete-safety architectural decision that Milestone 1 needs to make once, consistently.
**Features:** Soft-delete (`is_active`) adopted for the four financials entities, decided and implemented as part of — not after — Milestone 1; a "Recently deleted" restore view for goals (and financials entities, if soft-delete is adopted for them); restore correctly re-triggers Monte Carlo recompute for restored goals.
**Files:** `code/src/routes/app.goals.tsx` (or a new dedicated trash view), `backend/app/routers/goals.py`, `backend/app/services/planning_service.py`, and — if the soft-delete decision is made — `backend/app/routers/financials.py`/`financials_service.py`.
**Components:** New "Recently deleted" list component with restore action, reusing the existing card/list visual language.
**Services:** `planning_service` (new restore function, triggers `calculate_goal_probability`).
**APIs:** `GET /api/v1/goals?include_inactive=true` or `/goals/trash` (new), `POST /api/v1/goals/{id}/restore` (new).
**Estimated LOC:** ~250-400, more if the financials soft-delete decision (made in Milestone 1) is retrofitted here instead of decided upfront — strongly recommend deciding it during Milestone 1 to avoid a second migration.
**Testing strategy:** Backend test asserting a restored goal's probability is recalculated, not stale-restored. Test asserting soft-deleted rows are excluded from all normal list/aggregate queries (regression risk: `get_dashboard`'s asset/liability sums must already filter `is_active` if that column is added — verify no double-counting of "deleted" data).
**Rollback strategy:** Additive column + additive endpoints; the risk is entirely in the decision timing (see PLA-006's migration-risk note), not the mechanism itself. If retrofitted after Milestone 1 already shipped hard-deletes, existing hard-deleted rows are unrecoverable by definition — communicate that boundary clearly rather than implying retroactive restore capability that can't exist.
**Success criteria:** A deleted goal can be restored and its probability is correct (not stale) immediately after restore; no soft-deleted row appears in any dashboard aggregate, list, or recommendation computation.

### Milestone 6 — Accessibility
**Purpose:** Close the one dimension `PreLaunchProductAudit.md` explicitly declined to score — "no live accessibility audit was performed in this session or in Volume 6." This milestone has no PLA findings feeding it because none exist yet; it exists to schedule the audit itself before scheduling any fixes.
**Features:** A dedicated accessibility audit (automated `axe`-style scan plus manual keyboard-navigation and screen-reader passes across every route touched by Milestones 1-5, per this project's own web-testing convention of testing keyboard access, reduced-motion behavior, and color contrast) — and only then, a findings-driven fix backlog.
**Files:** Unknown until the audit runs — do not pre-guess scope here.
**Components:** N/A pending audit.
**Services:** N/A pending audit.
**APIs:** N/A pending audit.
**Estimated LOC:** Unscoped — audit first, estimate after.
**Testing strategy:** Automated accessibility scan integrated into CI (if not already present — not confirmed either way in this pass) plus manual screen-reader verification, matching this project's stated testing-priority order (visual regression → accessibility → performance → cross-browser → responsive).
**Rollback strategy:** N/A — this milestone is an audit, not a shipped change, until its findings are triaged into a follow-up milestone.
**Success criteria:** A findings register exists (mirroring the format of `PreLaunchProductAudit.md` itself) covering keyboard navigation, screen-reader labeling, and contrast across all new (Milestones 1, 2, 4) and existing screens — success for *this* milestone is the register's existence and severity-triage, not zero findings.

---

## IMPLEMENTATION ORDER

1. **Milestone 1 — Financial Profile Management** (root dependency for almost everything else; also make the soft-delete-vs-hard-delete decision for financials entities here, feeding Milestone 5)
2. **Milestone 4 — UX Improvements** (independent of Milestone 1 for most items; PLA-011's stopgap option and PLA-008 can ship in parallel with Milestone 1; only the PLA-007/PLA-002-copy items wait on Milestone 1's completion)
3. **Milestone 3 — Dashboard Improvements** (hard dependency on Milestone 1's data existing)
4. **Milestone 2 — Life Events** (soft dependency on Milestone 1 for the income/liabilities-backed sub-features; the goal-category and insurance-CRUD sub-features can start earlier if resourcing allows parallel tracks)
5. **Milestone 5 — Data Integrity** (the mechanism is independent, but the financials-soft-delete scope should already be settled by Milestone 1's decision, so scheduling it after avoids rework)
6. **Milestone 6 — Accessibility** (no hard dependency on any other milestone; schedule the audit itself as early as resourcing allows — ideally in parallel with Milestone 1 — since its findings may touch every other milestone's new UI before those screens' designs are finalized)

---

## RISK MATRIX

| Milestone | Technical Risk | Product Risk | Migration Risk | Regression Risk |
|---|---|---|---|---|
| M1 — Financial Profile Management | Low (additive endpoints/schemas, well-understood CRUD pattern already proven by Goals/Family) | Low | Low (additive columns only, or none) | Low — verified Monte Carlo does not read these tables; explicit regression test recommended anyway |
| M2 — Life Events | Medium (new bulk-update interaction pattern is genuinely novel; amortization calculator is new domain logic) | Medium (PLA-014's emergency-fund product decision is unresolved and blocks scope estimation) | Medium (one enum-type migration, PLA-013 — the only non-trivially-reversible schema change in this roadmap) | Low-Medium — bulk goal update must be tested for correct per-goal Monte Carlo re-trigger, not batch-averaged |
| M3 — Dashboard Improvements | Low | Low | Low (additive field) | Low |
| M4 — UX Improvements | Low (PLA-011 stopgap) to Medium (PLA-011 full option, blocked on missing email provider) | Low | None | Low |
| M5 — Data Integrity | Low-Medium | Low | Low if decided during M1; Medium if retrofitted | Medium — must verify soft-deleted rows are excluded from every existing aggregate query that wasn't written with `is_active` filtering in mind |
| M6 — Accessibility | Unknown pending audit | Low | None | Unknown pending audit — should run before, not after, M1/M2/M4 finalize their new UI to avoid rework |

---

## DEPENDENCY GRAPH

```
                        ┌────────────────────────────┐
                        │  Milestone 1                │
                        │  Financial Profile Mgmt      │
                        │  (PLA-001, PLA-002)          │
                        │  + soft-delete decision       │
                        └──────────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
   ┌────────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐
   │ Milestone 3          │   │ Milestone 2           │   │ Milestone 5            │
   │ Dashboard Improve.    │   │ Life Events            │   │ Data Integrity          │
   │ (PLA-003)             │   │ (PLA-012, PLA-014,     │   │ (PLA-006)               │
   │ hard dep. on M1        │   │  PLA-015 — soft dep.)  │   │ soft dep. on M1's        │
   │                        │   │ PLA-004, PLA-013       │   │ soft-delete decision      │
   │                        │   │  — independent          │   │                          │
   └────────────────────────┘   └─────────────────────────┘   └──────────────────────────┘

   ┌────────────────────────┐
   │ Milestone 4              │   independent of the above except:
   │ UX Improvements           │   PLA-007 waits on M1; PLA-002-copy-fix waits on M1
   │ (PLA-007, PLA-008,         │   PLA-011, PLA-008 ship anytime
   │  PLA-011)                  │
   └────────────────────────────┘

   ┌────────────────────────┐
   │ Milestone 6              │   fully independent — schedule in parallel,
   │ Accessibility              │   ideally starting before M1/M2/M4 finalize UI
   │ (audit-first, no PLA id)  │
   └────────────────────────────┘

   Not scheduled: PLA-009 (scenario planning — explicitly deferred per YAGNI),
   PLA-010's long-term decumulation engine (only its documentation/tooltip fix is scheduled, inside M2's insurance/goal work by extension — the simulation engine itself is out of scope for this roadmap).
```

---

## CRITICAL PATH

**Milestone 1 → Milestone 3** is the critical path for product credibility: the audit's headline finding (a financial planning product that cannot ingest new facts) is only fully resolved once Milestone 1 ships *and* Milestone 3's staleness-signaling makes that resolution visible to users. Every other milestone is parallelizable around this spine:

- Milestone 4's independent items (PLA-011 stopgap, PLA-008) and Milestone 6 (accessibility audit) can start on day one, in parallel with Milestone 1, with no dependency conflict.
- Milestone 2's independent sub-features (PLA-004 insurance CRUD, PLA-013 goal category) can also start in parallel with Milestone 1 if a second engineering track exists; its dependent sub-features (PLA-012, PLA-014, PLA-015) queue behind Milestone 1.
- Milestone 5 should make its one binding decision (soft-delete adoption for financials entities) *during* Milestone 1's design, even though its own implementation can trail — this is the one place in the roadmap where sequencing a decision matters more than sequencing the code.
- The single irreversible step in the entire roadmap is PLA-013's `goal_category` enum addition (Milestone 2) — it should not be executed until the category name is final, since Postgres enum values cannot be cleanly removed after the fact.

**Shortest path to closing the audit's stated launch blocker** (Part 10: "not launch-ready for a multi-year financial-planning promise"): Milestone 1 alone, shipped end-to-end including the soft-delete decision, converts the product's overall readiness score from the audit's 3/5 to what the audit itself characterizes as the threshold for a credible ongoing-planning product — everything past Milestone 1 in this roadmap is a should-fix that strengthens, rather than unblocks, that claim.
