# ENGINEERING FINDINGS SUMMARY

**Companion document to Volumes 1 and 2 of the Northstar Project Engineering Bible**
**Date compiled:** 2026-07-09
**Method:** every finding below was independently verified against executable code, a passing/failing test, or a live-verified behavior — not carried over from a prior report without re-checking. One correction to Volume 1 is folded in here: that document claimed no CI/CD pipeline exists; re-verification for this document found `.github/workflows/ci.yml`, a real, working pipeline. This is noted explicitly (EF-016) rather than silently fixed elsewhere, per this engagement's own standing rule that documentation errors get corrected in the open, not quietly.

---

## Quick-Scan Index

| ID | Severity | Category | Title | Status |
|---|---|---|---|---|
| EF-001 | High | Calculation | `financial_assumptions.expected_return_*` fully disconnected from Monte Carlo | Open |
| EF-002 | Medium | Calculation | `NetWorthProjection.tsx` hardcoded rates disconnected from assumptions | Open |
| EF-003 | Medium | Calculation | `retirement_age`/`social_security_monthly` have zero calculation consumers | Open |
| EF-004 | Medium | Calculation | `years_to_goal` computed three inconsistent ways | Open |
| EF-005 | Medium | Security | Audit logging scoped to Family domain only | Open (scoped by design, coverage gap real) |
| EF-006 | Medium | Architecture | No frontend automated test suite | Open |
| EF-007 | Medium | Performance | Rate limiter is in-memory, single-process only | Open (documented trade-off) |
| EF-008 | Medium | Performance | Two frontend pages bypass the shared React Query cache | Open |
| EF-009 | Low | Calculation | `ANNUAL_INFLATION` constant is dead code | Open |
| EF-010 | Low | Calculation | 70% on-track threshold is a hardcoded, non-configurable literal | Open |
| EF-011 | Low | Calculation | No golden-value regression test for the Monte Carlo engine | Open |
| EF-012 | Low | UX | Command Palette cannot deep-link to Goal/Scheme/Insurance detail | Open (documented limitation) |
| EF-013 | Low | Data Model | `financial_assumptions.tax_rate` deprecated but not removed | Open (documented deprecation) |
| EF-014 | High → **Resolved** | Architecture | Global Shell overlays could be simultaneously open | **Fixed in M2.6.1** |
| EF-015 | Info | Data Model | Multiple fully-migrated, zero-consumer schema domains | Intentional |
| EF-016 | Info | Architecture | CI pipeline exists and is functioning (corrects Volume 1) | Confirmed-good |
| EF-017 | Info | Architecture | Notification Center uses polling, not push, by design | Intentional |
| EF-018 | Info | Security | Cross-user data isolation verified via live testing | Confirmed-good |
| EF-019 | Info | Security | Refresh-token rotation + CSRF double-submit pattern | Confirmed-good |
| EF-020 | Info | Security | Ownership checks inlined into every resource query | Confirmed-good |
| EF-021 | Info | Data Model | Nullable-sibling-column chosen over polymorphic owner model for HUF | Intentional |
| EF-022 | Info | Data Model | Goal ownership kept separate from household-member tagging | Intentional |

---

## High Severity

### EF-001 — `financial_assumptions.expected_return_*` fully disconnected from the Monte Carlo engine

- **Severity:** High
- **Category:** Calculation
- **Evidence:** `backend/app/models/assumptions.py` defines `expected_return_conservative`/`_balanced`/`_aggressive` (defaults 0.05/0.07/0.09), fully exposed via `GET`/`PUT /api/v1/assumptions` (`backend/app/routers/assumptions.py`). `backend/app/services/monte_carlo.py`'s `PROFILE_PARAMS` is a hardcoded module-level dict (mu=0.055/0.075/0.095, sigma=0.07/0.12/0.18) used by every simulation. `grep -rn "expected_return_conservative\|expected_return_balanced\|expected_return_aggressive" backend/app/` returns matches only in `models/`, `schemas/`, and `routers/assumptions.py` — zero matches in any `services/` file.
- **Current Impact:** A user can change their configured expected-return assumption via the Assumptions API and it has **zero effect** on any Monte Carlo simulation or goal probability they subsequently see. This is a direct trust/correctness gap: the product implies a user's stated assumptions drive their plan, and they do not.
- **Recommended Action:** Either (a) wire `PROFILE_PARAMS` to read per-user values from `FinancialAssumptions` when present, falling back to the current hardcoded defaults, or (b) if the hardcoded values are intentional (e.g. to keep simulations comparable across users), remove or clearly label the Assumptions UI fields as not yet connected to simulations, so the product never implies a capability it doesn't have (per this project's own `docs/PRODUCT_PRINCIPLES.md #7`).
- **Intentional or accidental?** Accidental / unresolved. No code comment, test, or design document found during this engagement's exploration justifies this disconnect the way other gaps (e.g. EF-013) are explicitly justified — it reads as an incomplete integration, not a considered decision.

---

## Medium Severity

### EF-002 — `NetWorthProjection.tsx` hardcoded rates disconnected from `financial_assumptions`

- **Severity:** Medium
- **Category:** Calculation
- **Evidence:** `code/src/components/dashboard/NetWorthProjection.tsx`'s `RATES` constant (`{ conservative: 0.05, balanced: 0.07, aggressive: 0.09 }`) is a hardcoded literal; the component never calls `api.getAssumptions()`. Its values numerically match `financial_assumptions`' *defaults* — confirmed coincidental, not integrated, since no fetch call exists to read the stored value.
- **Current Impact:** A user who changes their stored assumptions away from the defaults sees a Net Worth Projection chart that silently continues using the original hardcoded 5/7/9% figures — a second, independent instance of EF-001's underlying pattern, in a different subsystem, with no volatility/uncertainty term at all (unlike Monte Carlo, this projection presents a single deterministic line per scenario with no confidence range).
- **Recommended Action:** Fetch `api.getAssumptions()` in this component (the same call `EducationPlanningSection.tsx` already makes) and use the stored per-user rates instead of the hardcoded constant.
- **Intentional or accidental?** Accidental. The numeric coincidence with the backend defaults suggests this was written to match the defaults at the time, without anticipating that a user might later change them.

### EF-003 — `retirement_age` and `social_security_monthly` have zero calculation consumers

- **Severity:** Medium
- **Category:** Calculation
- **Evidence:** `grep -rn "social_security_monthly\|retirement_age" backend/app/` outside `models/assumptions.py`, `schemas/assumptions.py`, and `routers/assumptions.py` returns no matches. No dedicated retirement decumulation/withdrawal-phase calculation exists anywhere in the codebase — a `category="retirement"` goal is Monte-Carlo-simulated identically to a travel or wealth goal.
- **Current Impact:** These two fields are collected from the user (via onboarding/settings) and stored, but never influence any output — a retirement-specific planning capability the product's data model gestures at but does not deliver.
- **Recommended Action:** Either build the retirement-specific calculation these fields imply (a withdrawal-phase model incorporating retirement age and Social Security income), or remove/hide the fields from user-facing input until that capability exists, consistent with the same product-honesty principle cited in EF-001.
- **Intentional or accidental?** Accidental / incomplete feature. Unlike `tax_rate` (EF-013), these fields carry no deprecation comment — they appear to be scaffolding for a retirement engine that was never built, not a deliberately-shelved decision.

### EF-004 — `years_to_goal` computed three inconsistent ways

- **Severity:** Medium
- **Category:** Calculation
- **Evidence:** Backend (`planning_service.calculate_goal_probability`): `(goal.target_date - date.today()).days / 365.25`. Frontend edit form (`GoalSimPanel.tsx`, `goalToEditForm`): `new Date(g.targetDate).getFullYear() - new Date().getFullYear()`, floored at 1. Frontend education projection (`EducationPlanningSection.tsx`, `yearsUntil`): a millisecond-based `(targetMs - nowMs) / (365.25*24*60*60*1000)` calculation — actually consistent in *method* with the backend's day-count approach, but computed independently rather than shared.
- **Current Impact:** A goal created in, say, November with a target date the following January can show "1 year" in the edit form (calendar-year subtraction) while the backend's actual simulation horizon is closer to 0.2 years — a real, user-visible discrepancy between what the edit UI implies and what the Monte Carlo engine actually simulates against. The two frontend implementations (edit form vs. education projection) can also disagree with each other.
- **Recommended Action:** Consolidate to one shared "years until date" utility function, used identically by the edit form, the education projection, and (ideally) mirrored exactly from the backend's day-count formula, eliminating both frontend duplicates.
- **Intentional or accidental?** Accidental. No comment anywhere acknowledges the three implementations diverge; each appears to have been written independently for its own immediate need.

### EF-005 — Audit logging scoped to the Family domain only

- **Severity:** Medium
- **Category:** Security
- **Evidence:** `grep -rln "AuditLog" backend/app/services/` returns matches only in `family_service.py` (`household_created`, `family_member_added/_updated/_removed`, `family_goal_tag_changed`) and `family_insurance_service.py` (`insurance_policy_created`, `insurance_policy_coverage_updated`). No matches in `planning_service.py` or `routers/financials.py`'s underlying service logic.
- **Current Impact:** Goal creation/update/deletion and Financials (income/expense/asset/liability) CRUD operations — all of which mutate financially consequential data — have no audit trail. If a dispute or investigation ever needed to reconstruct "what did this user's goal look like before this edit," that history does not exist outside the Family domain.
- **Recommended Action:** Extend the same `AuditLog` pattern already proven in `family_service.py` to `routers/goals.py` and `routers/financials.py`'s mutating endpoints, at minimum for create/delete operations.
- **Intentional or accidental?** Appears intentionally scoped at the time it was built (the Family domain was the first to need this discipline, per its own documented HUF/nomination/estate compliance motivations) — but the resulting coverage gap for Goals/Financials is a real, current fact, not something to leave unexamined indefinitely.

### EF-006 — No frontend automated test suite

- **Severity:** Medium
- **Category:** Architecture
- **Evidence:** No `*.test.tsx` or `*.test.ts` files were found under `code/src/` in this exploration. The CI pipeline's frontend job (`.github/workflows/ci.yml`) runs only a type-check (`bun run build --mode development`) and lint (`bun run lint`) — no test-execution step exists for the frontend, confirmed by reading the workflow file directly.
- **Current Impact:** Frontend correctness is currently verified only via `tsc`/`eslint` (catches type and style errors, not behavioral regressions) plus manual/live browser verification performed ad hoc during feature work — there is no automated safety net catching a frontend behavioral regression on a future change.
- **Recommended Action:** Introduce a frontend test runner (Vitest is the natural fit alongside this Vite-based stack) starting with the calculation-bearing components flagged elsewhere in this document (`NetWorthProjection.tsx`'s `project()`, `EducationPlanningSection.tsx`'s `projectedCost()`) — these are pure functions, cheap to test, and exactly the kind of logic a silent regression could corrupt undetected.
- **Intentional or accidental?** Accidental gap, compensated for (not solved) by this project's own established practice of live, manual verification for UI-facing work — a real and reasonable interim strategy, but not a substitute for automated coverage.

### EF-007 — Rate limiter is in-memory, single-process only

- **Severity:** Medium
- **Category:** Performance
- **Evidence:** `backend/app/middleware/rate_limit.py`'s own module docstring: *"This is intentionally lightweight (no Redis dependency)... For multi-process deployments, replace the in-memory store with Redis and a Lua INCR script."* The `_buckets` dict is a plain in-process `OrderedDict`, not backed by any shared store.
- **Current Impact:** If Northstar is ever deployed behind multiple uvicorn worker processes or horizontally-scaled instances, each process maintains its own independent rate-limit state — an attacker (or just a normal user with retried requests) can receive up to N× the intended request budget, where N is the number of running processes/instances, since each has its own bucket.
- **Recommended Action:** Before any multi-process/multi-instance production deployment, replace the in-memory bucket store with a shared Redis-backed implementation, exactly as the module's own docstring already prescribes.
- **Intentional or accidental?** Intentional, explicitly documented trade-off — included here as Medium severity because the trade-off's condition (multi-process deployment) is a normal, likely production configuration, not a remote edge case.

### EF-008 — Two frontend pages bypass the shared React Query cache

- **Severity:** Medium
- **Category:** Performance
- **Evidence:** `code/src/routes/app.goals.tsx` and `code/src/routes/app.profile.tsx` fetch data via raw `useEffect`+`fetch`/`Promise.all` rather than `useQuery` — confirmed by `grep -c "useQuery" code/src/routes/app.goals.tsx code/src/routes/app.profile.tsx` returning zero for both, contrasted with every other route/shell component's consistent `useQuery` usage. Verified live via network capture during this engagement's Global Shell Certification: repeat navigation to these two pages produced redundant `/goals` and `/auth/me`/`/family` requests not seen elsewhere.
- **Current Impact:** These two pages issue a fresh network request on every visit, never populating or reading the cache the rest of the shell (`AppShell`, `GlobalPalette`) relies on — a real, measured (not theoretical) source of redundant backend load.
- **Recommended Action:** Migrate both pages to `useQuery` with the existing shared cache keys (`["goals"]`, `["currentUser"]`) already established elsewhere in the codebase.
- **Intentional or accidental?** Accidental technical debt — pre-dates the Global Shell work and was flagged, but explicitly not fixed, during Milestone 2.6 Phase 2 as out of that phase's scope.

---

## Low Severity

### EF-009 — `ANNUAL_INFLATION` constant is dead code

- **Severity:** Low
- **Category:** Calculation
- **Evidence:** `backend/app/services/monte_carlo.py` declares `ANNUAL_INFLATION: float = 0.03` with the comment "Inflation rate applied to real-term comparisons." `grep -rn "ANNUAL_INFLATION" backend/app/` returns exactly one match — its own declaration.
- **Current Impact:** None functionally (the constant is never read), but its presence and comment actively mislead a reader into believing the Monte Carlo engine performs a real-term (inflation-adjusted) comparison somewhere — it does not.
- **Recommended Action:** Remove the constant, or if a real-term comparison is planned, implement it and wire this value in.
- **Intentional or accidental?** Accidental — leftover from an earlier iteration or an unfinished feature; the comment describes a capability that doesn't exist in the current code.

### EF-010 — 70% on-track threshold is a hardcoded, non-configurable literal

- **Severity:** Low
- **Category:** Calculation
- **Evidence:** `planning_service.calculate_goal_probability`: `goal.on_track = probability >= 70.0` — the literal `70.0` appears exactly once, is not read from any settings/assumptions table, and has no per-user or per-persona variation anywhere in the codebase.
- **Current Impact:** Every downstream consumer of "on track" (Dashboard alerts, Notification Center's "at risk" trigger, Family Dashboard's retirement card, goal-card coloring) inherits this exact same fixed boundary — a conservative retiree and an aggressive young saver are held to an identical bar with no product rationale documented for why 70% specifically was chosen.
- **Recommended Action:** Low priority as-is (a single, consistent threshold is defensible for an MVP), but worth deciding explicitly — either document why 70% is the right universal bar, or make it configurable if a future persona-specific product need arises.
- **Intentional or accidental?** Unclear from the code — plausible as a deliberate MVP simplification, but no comment, test, or design document confirms this was a considered choice rather than an arbitrary starting value.

### EF-011 — No golden-value regression test for the Monte Carlo engine

- **Severity:** Low
- **Category:** Calculation
- **Evidence:** Full read of `backend/tests/test_monte_carlo.py` (84 lines, 10 tests) — every assertion is a range check (`0 <= success_rate <= 100`), an ordering check (`p10 <= p25 <= ... <= p90`), a monotonicity check (higher contribution → equal-or-higher success rate), or an equality-under-fixed-seed check. None assert against an independently hand-calculated expected value.
- **Current Impact:** A subtle regression in the simulation math (e.g. an off-by-one in the Itô correction term, or an incorrect monthly-to-annual conversion) that preserves all the tested *properties* (ordering, monotonicity, range) but silently shifts every output by some amount would not be caught by the current test suite.
- **Recommended Action:** Add at least one test that runs `run_simulation` with a fixed seed and asserts the exact resulting `success_rate`/`p50` against a value independently verified (e.g., computed once via a separate script or spreadsheet, then pinned) — a legitimate regression guard on top of the existing property tests, not a replacement for them.
- **Intentional or accidental?** Defensible as a testing-strategy choice for a stochastic engine (property tests are a reasonable primary strategy here), but the *absence* of even one pinned golden value is a real gap worth closing, not an obviously correct decision either way.

### EF-012 — Command Palette cannot deep-link to a specific Goal, Government Scheme, or Insurance Policy

- **Severity:** Low
- **Category:** UX
- **Evidence:** `code/src/components/global-palette.tsx` — Goal/Scheme/Insurance search results all navigate to their respective list page (`/app/goals`, `/app/family/schemes`, `/app/family/insurance`), never to a specific record. Only Family Member results deep-link precisely, since `/app/family/members/$id` is the one entity type with a real, URL-addressable detail route. Documented explicitly in `ArchitectureReview_Phase2.md §7` and re-confirmed during the Global Shell Certification.
- **Current Impact:** Selecting a specific goal from search results lands a user on the full Goals list, requiring one more click/scroll to find the item they searched for — a minor friction cost, not a broken feature (the item is genuinely present and findable on the destination page).
- **Recommended Action:** If a URL-addressable detail view is ever built for Goals, Schemes, or Insurance Policies (none exists today), extend the palette's navigation to deep-link to it at that point — not before, since building one now would be scope creep beyond the palette's own job.
- **Intentional or accidental?** Intentional, honestly disclosed limitation — the palette's own design review explicitly named this constraint rather than faking a deep link that doesn't functionally exist.

### EF-013 — `financial_assumptions.tax_rate` deprecated but not removed

- **Severity:** Low
- **Category:** Data Model
- **Evidence:** `backend/app/models/assumptions.py`'s own code comment: *"DEPRECATED (2026-07-06, FutureCompatibilityAuditReport.md Finding C)... Confirmed unread by any service/router as of this reconciliation — grep shows it is only ever set to its default, never computed against."* Re-confirmed in this pass: `grep -rn "\.tax_rate" backend/app/services/` returns no matches outside the field's own model/schema/router definition.
- **Current Impact:** Minimal — the field is inert, explicitly documented as such, and the versioned `tax_regimes`/`tax_slabs` tables are named as its intended replacement (though those tables are *also* currently unread by any calculation — see EF-003's sibling gap, not separately numbered here to avoid double-counting the same underlying "tax calculation doesn't exist yet" fact).
- **Recommended Action:** No urgency; a future tax-calculation feature should read from `tax_regimes`/`tax_slabs`, at which point `tax_rate` should be fully removed per this project's own Rule 11 (Deprecation Completion) in `docs/ENGINEERING_CONSTITUTION.md` — grep the whole codebase (frontend included) for every reader before removing, not just the one call site a change happens to touch.
- **Intentional or accidental?** Intentional — this is the one deprecated field in this document that carries a full, dated, cited deprecation comment explaining exactly why it's inert and what replaces it.

---

## Resolved (formerly High)

### EF-014 — Global Shell overlays could be simultaneously open — **RESOLVED**

- **Severity:** High at time of discovery → **Resolved**
- **Category:** Architecture
- **Evidence:** Found and reproduced during this engagement's Global Shell Certification (`GlobalShellCertification.md`): the Profile Menu (`DropdownMenu`, fully Radix-uncontrolled) did not close when the Command Palette opened via ⌘K, while the Notification popover (`Popover`) did — an inconsistency traced to two different Radix primitives' own, differing default dismiss-on-outside-interaction behavior, not a designed guarantee. Root-caused in `DependencyValidation_M2.6.1.md`, fixed in `code/src/components/app-shell.tsx` and `code/src/components/notification-center.tsx` by consolidating four independent overlay booleans into one shared `activeOverlay` discriminated-union state.
- **Current Impact:** None — fix verified live across every pairwise overlay combination (palette↔profile, palette↔notifications, notifications↔profile, mobile "More" sheet against all three) at both desktop and mobile widths, with 6 rapid open/close cycles producing no stuck state and no new console errors. Full detail: `PR_REPORT_M2.6.1.md`.
- **Recommended Action:** None required. Documented here for completeness of this findings register, and as a durable example of the underlying principle (§ Architecture Review M2.6.1): relying on multiple independent third-party components' *coincidentally agreeing* default behaviors is not the same guarantee as one shared, structurally-enforced state — worth remembering if a fifth overlay-type feature is ever added to this header.
- **Intentional or accidental?** Accidental — an emergent property of four overlays each independently choosing their own state-management approach across four separate development phases, none of which tested the others' interaction until the dedicated Certification pass did.

---

## Info (Intentional Decisions and Confirmed-Good Patterns)

### EF-015 — Multiple fully-migrated, zero-consumer schema domains

- **Severity:** Info
- **Category:** Data Model
- **Evidence:** `Recommendation`/`RecommendationCitation` (`models/recommendation.py`), `HUFEntity`/`HUFCoparcener`/`Nominee`/`EstateDocument` (`models/estate.py`), `BestPracticeRule`/`CompanyPolicy` (`models/company_policy.py`) — `grep -rln "HUFEntity\|CompanyPolicy\|BestPracticeRule\|Recommendation\b" backend/app/routers backend/app/services` returns no matches for any of these class names.
- **Current Impact:** None currently — these tables exist in the schema, are migrated, but are read/written by nothing. They impose zero runtime cost (empty tables) but do represent schema surface area a new engineer must learn to recognize as "not yet active" rather than assume is load-bearing.
- **Recommended Action:** None required now. When a future milestone activates one of these domains, verify the schema still matches that milestone's actual needs before building against it (models were designed ahead of the feature, not from the feature's finalized requirements).
- **Intentional or accidental?** Intentional — each model file's own comments cite the specific future-milestone report justifying its early existence (e.g. `FutureCompatibilityAuditReport.md`), a deliberate "build the runway before the feature" pattern.

### EF-016 — CI pipeline exists and is functioning (corrects Volume 1)

- **Severity:** Info
- **Category:** Architecture
- **Evidence:** `.github/workflows/ci.yml` — three jobs: backend (ruff, mypy, pytest), frontend (type-check via `bun run build`, lint), and a Docker build-check for the backend image. Volume 1 of this Bible incorrectly stated no CI configuration was found; this was a real research gap in that document (the `.github` directory was not checked during that pass), corrected here.
- **Current Impact:** Positive — every push/PR to `main`/`develop` is gated on lint, type-check, and the full backend test suite passing, plus a Docker build sanity check.
- **Recommended Action:** None required for the CI pipeline itself. Note the pipeline is CI (lint/test/build-check) only — no CD/deployment step exists in this workflow, and no frontend Dockerfile exists (the `docker` job builds only `./backend`) — a real, separate gap from the one Volume 1 mistakenly described.
- **Intentional or accidental?** Confirmed-good, functioning infrastructure. The correction itself (this document vs. Volume 1) is a reminder that even a careful reverse-engineering pass can miss a dotfile-prefixed directory — worth double-checking `.github`, `.gitlab-ci.yml`, etc. explicitly in any future audit of this repository.

### EF-017 — Notification Center uses polling, not push, by design

- **Severity:** Info
- **Category:** Architecture
- **Evidence:** `code/src/components/notification-center.tsx`'s `useQuery` config: `refetchInterval: 120_000`. `GlobalShellArchitecture.md` (Milestone 2.6 design phase) explicitly names this as the intended approach: *"Any 'real-time' notification design must in practice mean polling via the React Query the app already uses everywhere else"* — since no WebSocket/SSE library exists in `package.json`.
- **Current Impact:** A new notification can take up to 2 minutes to appear without a manual refresh or panel re-open — an accepted, bounded latency, not an unbounded or accidental one.
- **Recommended Action:** None required unless real-time delivery becomes a stated product requirement, at which point this is a scoped, well-understood follow-up (introduce WebSocket/SSE infrastructure), not a bug to fix quietly.
- **Intentional or accidental?** Intentional, documented design choice, made explicitly during the pre-implementation Architecture Review rather than discovered as a limitation after the fact.

### EF-018 — Cross-user data isolation verified via live testing

- **Severity:** Info
- **Category:** Security
- **Evidence:** During this engagement's Global Shell Certification, a second, unrelated test account was created and used to attempt access to the first account's `Goal` and `HouseholdMember` records by ID, using the second account's own valid token — both attempts returned `404`, not a data leak or a `403` that would confirm the resource's existence. The Notification feed for the first account was checked directly and contained zero trace of the second account's data.
- **Current Impact:** Positive confirmation — every resource-scoped query across `goals.py`, `family.py`, and `notifications.py` filters by the requesting user's ownership in the same query that fetches the row (verified directly in Volume 1's exploration), and this behavioral guarantee was independently re-confirmed live, not just inferred from reading the code.
- **Recommended Action:** None required. Worth re-running this exact live cross-account test after any future change to ownership-check logic in these three routers, given how load-bearing this property is.
- **Intentional or accidental?** Confirmed-good, consistent architectural pattern applied without exception across every resource-scoped endpoint checked.

### EF-019 — Refresh-token rotation + CSRF double-submit pattern

- **Severity:** Info
- **Category:** Security
- **Evidence:** `backend/app/routers/auth.py`: the refresh token is delivered as an httpOnly cookie scoped to `/api/v1/auth` only, paired with a separate, JS-readable CSRF cookie whose value must be echoed back as an `X-CSRF-Token` header, compared via `secrets.compare_digest` (constant-time, not `==`). Every successful `/auth/refresh` call issues a **new** refresh token and CSRF pair (`_set_auth_cookies` called again), not a token reused across its full lifetime.
- **Current Impact:** Positive — this closes the XSS-exfiltration path a fully-`localStorage`-based refresh-token design would have, and rotation shrinks the replay window if a token is ever leaked.
- **Recommended Action:** None required.
- **Intentional or accidental?** Deliberate, well-executed security pattern — confirmed by the presence of the constant-time comparison specifically (an easy detail to get wrong, correctly handled here).

### EF-020 — Ownership checks inlined into every resource query

- **Severity:** Info
- **Category:** Security
- **Evidence:** Every single-resource endpoint read in `goals.py`, `financials.py`, `family.py`, and `notifications.py` (e.g. `select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)`) filters by ownership in the *same* query that fetches the row — no "fetch, then separately check ownership" two-step pattern exists anywhere, which would be a place a future edit could forget the check.
- **Current Impact:** Positive — this is a structurally safer pattern than a separate authorization check, since there's no code path where the data-fetch and the authorization-check could accidentally be decoupled.
- **Recommended Action:** None required; worth preserving as the standard for any new resource-scoped endpoint.
- **Intentional or accidental?** Consistent, deliberate pattern — applied without exception across every router checked in this engagement.

### EF-021 — Nullable-sibling-column chosen over a polymorphic owner model for HUF support

- **Severity:** Info
- **Category:** Data Model
- **Evidence:** `backend/app/models/financials.py`'s own code comment: a fully generalized polymorphic "owner" abstraction (`User` and `HUFEntity` both implementing a common `Owner` supertype) was explicitly considered and rejected, because only two owner types exist today and changing `user_id`'s FK target would be a breaking change to a stable column. A nullable `huf_entity_id` sibling column was chosen instead — additive, no existing column's meaning changes.
- **Current Impact:** None negative — a defensible, documented trade-off consistent with this project's own `docs/ENGINEERING_CONSTITUTION.md` Rule 7 (no premature abstraction).
- **Recommended Action:** None required; revisit only if a genuine third owner type emerges.
- **Intentional or accidental?** Fully intentional and documented, with the rejected alternative explicitly named in the code comment — a model of how an architectural trade-off should be recorded.

### EF-022 — Goal ownership kept separate from household-member tagging

- **Severity:** Info
- **Category:** Data Model
- **Evidence:** `backend/app/models/goal_household_member.py`'s own comment: this table is explicitly "not a joint-ownership model" — `goals.user_id` remains the sole owner of record for tax attribution, contribution tracking, and access control for the entire lifetime of the row, regardless of how many household members a goal is tagged with.
- **Current Impact:** None negative — this is the correct modeling choice given the schema genuinely does not support per-person contribution tracking, and the product's own UI is required to disclose this (per `docs/PRODUCT_PRINCIPLES.md #7`) rather than imply joint ownership the data model can't back up.
- **Recommended Action:** None required unless a genuine joint-ownership/shared-contribution-tracking feature is scoped in the future, at which point this table's purely-descriptive nature (not its existence) would need to change.
- **Intentional or accidental?** Fully intentional, documented directly in the model file and cross-referenced in this project's own `Milestone2ImplementationContract.md §0.1`.

---

## Summary Statistics

| Severity | Count |
|---|---|
| High (open) | 1 |
| High (resolved) | 1 |
| Medium | 7 |
| Low | 5 |
| Info | 8 |
| **Total findings** | **22** |

| Category | Count |
|---|---|
| Calculation | 8 |
| Data Model | 5 |
| Security | 4 |
| Architecture | 4 |
| Performance | 2 |
| UX | 1 |

**Single most consequential open finding:** EF-001 — the complete disconnection between user-configurable return assumptions and the Monte Carlo engine that actually drives every probability shown in the product. Every other Calculation-category finding in this register (EF-002, EF-003, EF-009, EF-010, EF-011) is a variant or consequence of the same underlying pattern: this codebase has several independent numeric-assumption surfaces that were each built correctly in isolation but never integrated with each other.

---

**End of Engineering Findings Summary.** Every entry reflects the repository state as verified on 2026-07-09, with exact grep commands and test names included so each finding can be independently re-checked in seconds. Re-verify before acting on any finding if significant time has passed since this date.
