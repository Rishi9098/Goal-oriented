# Engineering Handbook

**Status:** Canonical · **Last verified against code:** 2026-07-14
**Supersedes:** `ProjectOwnersHandbook.md` (archived — 90KB, the direct ancestor of this document), `PROJECT_STATE.md` (152KB, archived as a point-in-time snapshot — its Decision Log entries are folded into `docs/03_Engineering/ArchitectureDecisionRecords.md`, not repeated here), `EngineeringFindingsSummary.md`.
**Purpose:** the operational "how to work in this codebase" guide — what the architecture docs describe *is*, this document describes *how to safely change it*.

---

## 1. Golden Engineering Rules

*(Verbatim from the project's own Engineering Constitution, Product Principles, and UX Principles — real governing documents, not invented for this handbook.)*

| # | Rule | Why it exists |
|---|---|---|
| 1 | **Routers are thin. Always.** | The Calculation Lifecycle can only be structurally guaranteed if the *decision* to recalculate lives in exactly one place. A router containing its own recalculation logic is exactly how ADR-001's bug happened. |
| 2 | **Never hardcode a fact that can change without a code deploy.** | A PPF rate changes quarterly; a tax slab changes annually. This is why `scheme_rates`/`tax_sections` are database rows, not Python constants. |
| 3 | **Migrations are additive by default.** | A destructive migration can silently destroy real user data or break a still-running previous version during a rolling deploy. All 11 of this project's migrations follow this without exception. |
| 4 | **Never invent a financial policy, rate, or rule.** | The entire product's trust proposition rests on every number being real. |
| 5 | **`mypy --strict` and Ruff are the gate, not a suggestion.** | A wrong type flowing into `monte_carlo.py` can silently produce a wrong probability. |
| 6 | **Tests prove behavior; they do not get adjusted to match a bug.** | If a test fails, the default assumption must be "the code is wrong," never "the test is too strict." |
| 7 | **Minimal diff. No premature abstraction.** | Why the Scheme Engine only branches on 3 rule types, and why HUF ownership is a nullable sibling column, not a polymorphic owner model. |
| 8 | **Every non-obvious decision gets a decision log entry.** | This is why the repository has an extensive `.md` report history — it is policy, not clutter. |
| 9 | **Verify against real infrastructure, not just unit tests.** | The backend test suite runs against SQLite, not PostgreSQL — a deliberate speed trade-off with one real consequence (naive vs. aware datetimes); a handful of cascade/`SET NULL` behaviors were verified manually against real Postgres specifically because SQLite can't prove them. |
| 10 | **The AI Advisor computes nothing; it narrates what was already computed.** | The single most important rule for anything built in the AI layer. |
| 11 | **Deprecation Completion.** | A field marked deprecated in a comment is not actually deprecated until every consumer, frontend and backend, has been found and migrated — verified by grep, not assumed. Added directly because of a real incident (see `ArchitectureDecisionRecords.md`, ADR-004). |

**Product Principles that matter most to engineering:** #2 every recommendation must be explainable (why `FamilyRecommendation` has mandatory, never-optional `why`/`why_now`/`confidence_score` fields); #7 never claim capability the data model doesn't actually have (the rule the Landing page's security marketing copy currently violates — FE-001); #8 every unverified fact stays visibly unverified.

**UX Principles with real engineering consequences:** #5 every recommendation explains why it was generated; #7 honesty over polish (why a `null` Family Dashboard card renders "Temporarily unavailable" rather than a zero — a zero could be mistaken for a real answer); #11 empty states explain why they're empty, never a bare "No data."

**The one operational test to run on any change:** *"If I make this change, can a number reach a user's screen that no deterministic engine actually verified?"* If yes — stop.

---

## 2. Adding a New Feature — Playbooks

### A. New Government Scheme
1. `backend/scripts/seed_policy_data.py` — add a tuple; if eligibility fits the 3 existing rule types (`max_age`/`min_age`/`gender`), add rule rows too — **no other code change needed**, the engine is data-driven.
2. A genuinely new rule type requires one new `elif` branch in `scheme_eligibility_service._evaluate_rules_for_member` — the one place "no premature abstraction" means don't build a general interpreter ahead of this real second need.
3. Never seed a rate/eligibility fact you haven't verified against a real government source.
4. Add a boundary test following the existing exact-boundary pattern (e.g. the SSY 10th-birthday tests).
5. Frontend: nothing to change — `/app/family/schemes` is a direct passthrough.

### B. New Insurance Recommendation Logic
1. `family_insurance_service.py` owns the 80D calculation — extend it, never duplicate the age/coverage logic already in `uncovered_parents`.
2. Extend `InsuranceRecommendation` only with fields you can populate honestly.
3. Add both a positive and a "why it doesn't fire" test.
4. Update `lib/api.ts`'s type to match the new schema field exactly (snake_case, verbatim).
5. Cross-check `family_recommendations_service.py`'s conflict detection if the new recommendation should participate.

### C. New Dashboard Card
1. Add one `_x_card()` function to `family_dashboard_service.py` — pure read, wrapped in `_safe()`.
2. Add the card as a **nullable** field on the response schema — nullability is how graceful degradation works, not optional.
3. Add a happy-path test and a "this card fails, others still populate" test.

### D. New Goal Category
1. Add the value to the `goal_category` Postgres ENUM (requires a migration — additive-safe `ALTER TYPE ADD VALUE`).
2. **Frontend — three separate places, a real, known duplication:** `app.goals.tsx`'s `CATEGORIES`, `GoalSimPanel.tsx`'s `CATEGORIES`+`ICON_MAP`, `wizard-steps.tsx`'s `CATEGORIES`. Update all three or the category is selectable in one form and invisible in another.
3. Only add special Dashboard treatment (like retirement/education/emergency get) if there's a real, proven need.

### E. New Financial Calculation
1. Decide which service owns it, following the existing domain split — a goal calculation belongs in `planning_service.py`; a Family calculation belongs in the relevant `family_*_service.py`.
2. Must be deterministic and versioned-data-driven if it touches a government fact; must never live in a router or the frontend as the source of truth.
3. Write the test *first* where a closed-form answer exists; a property/invariant test where it doesn't (the Monte Carlo suite's own precedent).

### F. New Notification Source
1. Add one `_collect_x_fact(s)` function to `notification_service.py` — read an already-certified engine, compute nothing new, return `_Fact` objects keyed by `_dedupe_key(source, natural_key)`.
2. Add the new source string to the `NotificationSource` literal (both backend and frontend).
3. No frontend component change needed — `NotificationCenter` renders any item generically.
4. Verify the new source appears correctly *and* that reading it never creates a marker row — the single most important invariant in this domain.

### G. New AI Capability
1. Today (no tool layer): expand the context-assembly query and the prompt's JSON block, and expand `_fallback_response` with a matching rule. Do this sparingly — every prompt field is a field the model could get wrong, with no grounding validator to catch it.
2. Building toward the proposed tool-calling architecture: start with the tool registry as a façade over an *already-certified* service, not by editing the prompt.
3. **Never let the model compute a number itself** — build the calculation as a real, tested backend function first.

### H. New Family Feature (new relationship type or per-member field)
1. Add the field to `Dependent` (nullable, additive) or a new `relationship_type` value (`VARCHAR`, no migration-level type change — but the frontend's closed `RelationshipType` union **must** be updated).
2. Extend `family_service.validate_member_fields` with the new rule.
3. Extend `FamilyMemberForm.tsx`'s conditional field block and its client-side `validate()` — client-side UX only, never the real enforcement.
4. Decide deliberately whether the new type should be evaluated by the Scheme/Insurance engines — both currently gate on specific relationship types; don't assume automatic coverage.

---

## 3. Safe Modification Guide — What Breaks Downstream

**If you change Monte Carlo (`monte_carlo.py`):** touches `planning_service.calculate_goal_probability` → `goal.probability`/`.on_track` → Dashboard, Reports, Family Dashboard's Retirement card, Notifications' `goal_at_risk`/`goal_completed`, the AI Copilot, every goal card in the frontend. Touching `PROFILE_PARAMS` makes every existing goal's probability silently inconsistent with newly-created ones until each is re-saved. Re-run the full `test_monte_carlo.py` invariant suite before merging — these are property tests specifically because no golden numeric value exists to compare against.

**If you change inflation handling:** `inflation_rate`/`custom_inflation_rate` feed **exactly one place** — `EducationPlanningSection.tsx`'s frontend-only projection. They do not feed Monte Carlo (a documented, deliberate gap, not a bug to "fix" casually). Wiring inflation into Monte Carlo is a real, load-bearing architecture change — every goal's probability shifts, the entire `test_goal_inflation.py` suite (which currently asserts inflation *never* changes probability) must be rewritten with full team awareness.

**If you change the 70% on-track threshold:** one literal, but dozens of consumers assume it, mostly via hardcoded UI copy rather than a shared constant — grep the frontend for `"70"` first. There is no single frontend source of truth for this number; most places read the `on_track` boolean rather than re-comparing the raw number, which limits blast radius, but any raw comparison elsewhere would silently disagree with a changed backend threshold.

**If you change Family/household data shape:** cascades through up to 5 services (`scheme_eligibility_service`, `family_insurance_service`, `family_recommendations_service`, `family_dashboard_service`, `notification_service`). Before changing a field's *meaning* (adding one is always safe), grep all 5 for reads of that field — exactly the class of mistake Rule 11 exists to catch.

**If you change Recommendations (`family_recommendations_service.py`):** affects the standalone Recommendations screen and the Family Dashboard's embedded feed (guaranteed identical — they share one function call, not two). **Does not affect Notifications** — `notification_service.py` calls the Insurance/Scheme services **directly**, bypassing Recommendations entirely. Changing conflict-detection logic has zero effect on notifications.

**If you change the Dashboard (`planning_service.get_dashboard`):** affects the main Dashboard, `AppShell`'s Plan Health mini-card (shares the `["dashboard"]` query key), Reports (calls the identical function — why they're tested to agree exactly), and the Family Dashboard's Emergency card. Never affects goal probability — a strictly one-directional dependency that must stay that way.

**If you change the AI Copilot (`copilot.py`):** today, isolated — nothing else depends on it, it's a pure leaf consumer of `goals`. You can change the prompt/fallback/model freely as long as `ChatResponse`'s shape (`{reply, conversation_id}`) doesn't change. The moment a tool-calling layer is built, this changes completely — the Copilot becomes a *new caller* of every service it wraps.

---

## 4. Debugging Guide — Symptom First

**"A goal's probability changed unexpectedly":** (1) was it just created/PATCHed with a Calculation Context field? (2) is `monte_carlo_seed` unset — expected sampling noise on re-run, not a bug, unless the swing is large; (3) did this happen on a plain `GET`? **That's a real regression** — reads must never mutate (ADR-001); check `test_repeated_dashboard_reads_never_change_goal_probability` still passes.

**"A recommendation disappeared":** remember first — recommendations are never persisted, so "disappeared" always means "the underlying fact changed," never a backend caching bug. Check the specific engine (`uncovered_parents` for insurance, `_evaluate_rules_for_member` for schemes) for what changed. Query the live endpoint directly to confirm — if it agrees with what the user sees, the system is working correctly. If it disagrees, check the frontend's React Query `staleTime` for the relevant key before assuming a backend bug.

**"The Dashboard looks inconsistent":** compare `/dashboard` and `/reports/summary` directly — tested to be byte-identical for probability; a disagreement is a real bug in `reports.py`. Check for an `is_active=false` goal leaking into a total. Remember Family Dashboard and the main Dashboard are two different aggregation paths sharing exactly one card (Emergency) — a discrepancy there is a real bug; elsewhere, expected.

**"A notification is missing":** is it `family_member_added` older than 30 days (expected cutoff)? Was it dismissed (permanent, even if the fact still exists)? Does the underlying fact still genuinely exist? Check the specific `_collect_x_fact(s)` function.

**"The AI Copilot's reply seems disconnected from my data":** first, was the question about anything other than Goals? The Copilot has **zero access** to Family/Insurance/Schemes/Recommendations/Dashboard/Assumptions data today — expected, not a bug. If about a goal and still wrong, check `/goals` directly first. If the raw data is right but the reply misstates it, check whether an API key is configured — no key means `_fallback_response`'s literal text, no model behavior to debug.

---

## 5. Things Never To Do

1. **Never calculate inside a Dashboard read** — ADR-001, verbatim, the single most important rule in this codebase.
2. **Never duplicate recommendation logic** — if you find yourself re-deriving an eligibility or deduction figure anywhere outside the two owning services, stop and call the existing function.
3. **Never store a computed recommendation** — the unused `recommendations` tables exist precisely to demonstrate this was considered and rejected (ADR-005).
4. **Never bypass an ownership check by fetching first, then checking** — every real check filters by owner in the *same query* as the fetch; a mismatched owner returns 404, never confirming existence to a non-owner.
5. **Never duplicate a financial formula** — the `years_to_goal` triplication already happened once; it's known, accepted debt, not a pattern to add a third instance of.
6. **Never let `goal.user_id` change after creation** — family tagging is explicitly, repeatedly documented as descriptive, never ownership-transferring.
7. **Never hard-delete a user-owned row through the application layer** — every deletion path is soft-delete except joins/links reachable only through a parent cascade.
8. **Never write a non-additive migration without a decision log entry** — Rule 3 is enforced by convention across all 11 migrations, not a database-level guard.
9. **Never let the AI Copilot originate a number** — Rule 10, regardless of how confident the reply sounds.
10. **Never seed a government rate or eligibility rule you haven't verified against a real source** — every row carries a citation; SCSS's 55+/50+ routes are deliberately *unseeded* specifically to avoid this violation.
11. **Never assume a table's existence means a feature exists** — 12 tables in this schema are fully migrated and completely unused; check for a real consumer before building on top of any table.

---

## 6. Code Reading Guide

**One hour, in order:** `CLAUDE.md` (5 min) → `docs/ENGINEERING_CONSTITUTION.md` + `docs/PRODUCT_PRINCIPLES.md` (5 min) → `planning_service.py` (10 min — the Calculation Lifecycle in ~150 lines) → `monte_carlo.py` (10 min — 191 lines, heavily commented) → `routers/goals.py` (5 min — see the trigger's actual call site) → `scheme_eligibility_service.py`/`family_insurance_service.py`/`family_recommendations_service.py` in that order (15 min — leaf → one-hop → composition) → `lib/api.ts` skimmed (5 min) → `app-shell.tsx` (5 min).

**A full day instead:** add `family_dashboard_service.py` (the widest backend composition point), `notification_service.py` (the newest subsystem, built to deliberately reuse every pattern above), `app.family.index.tsx` (the widest single frontend screen), then read `docs/02_Architecture/SystemArchitecture.md` and `docs/02_Architecture/RecommendationEngine.md` in full.

---

## 7. Maintenance Checklist

**Weekly:** run the full backend suite locally too (`pytest -v`, confirm ≥80% coverage and still ~97%+, not just above the floor) — CI already runs this on every push/PR (`.github/workflows/ci.yml`), but a local run catches issues before they reach a PR. Frontend `tsc`/`eslint` are also CI-enforced (the `frontend` job runs `bun run build` for type-checking and `bun run lint`) — corrected in V2 from prior documents' stale "no CI enforces this" claim.

**Monthly/Quarterly/Before Release/Before Production:** see `docs/10_Operations/OperationsRunbook.md` for the full checklist — preserved there rather than duplicated here, since release cadence is an operations concern, not a day-to-day engineering one.

---

## Related Documents
`docs/03_Engineering/ArchitectureDecisionRecords.md` · `docs/03_Engineering/TechnicalDebt.md` · `docs/03_Engineering/DeveloperGuide.md` · every `docs/02_Architecture/*.md` doc this handbook's playbooks reference · `docs/10_Operations/OperationsRunbook.md`


## Related Tests
Every playbook in §2 names its own relevant test file inline (e.g. `test_scheme_eligibility_service.py` for the New Government Scheme playbook) — this document doesn't duplicate that list at the top level.

---

*Archived originals: `docs/13_Archive/ArchivedReports/ProjectOwnersHandbook.md`, `PROJECT_STATE.md`, `EngineeringFindingsSummary.md`.*
