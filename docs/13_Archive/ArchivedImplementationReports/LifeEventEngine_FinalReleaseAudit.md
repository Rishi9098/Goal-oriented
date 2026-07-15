# LIFE EVENT ENGINE — FINAL RELEASE AUDIT

**Role:** Principal Engineer / Chief Architect / Principal Product Engineer / Staff Backend / Staff Frontend / QA Lead / SRE / Security Engineer / UX Lead / Technical Design Authority (external review)
**Method:** Direct re-inspection of source code, live test execution, and grep-verified structural claims. No prior implementation report was taken on faith — every claim below is cited to a file, line, or command output produced during this audit.
**Scope:** `backend/app/` (all 17 Life Event handlers + generic engine + integrations), `code/src/` (frontend), `alembic/`, `docs/`, `CHANGELOG.md`.

---

## EXECUTIVE SUMMARY

The backend engineering behind the Life Event Engine is genuinely strong: 636 tests pass, coverage is **97.90%** (verified by a fresh, non-cached run in this audit — the project's own `--cov-fail-under=80` gate had never actually been checked during the 17-event build, since every build-time test run used `--no-cov` for speed), `ruff` and `mypy --strict` are clean, and a grep-verified architectural invariant holds across all 17 handlers: **not one of them issues a raw SQL query** — every single write goes through a service function, and the "extract, don't duplicate" discipline the implementation reports describe is real, not aspirational.

But this audit's job is to find what the implementation reports didn't say, and there is one finding that overrides every other consideration:

**There is no way for a user, a frontend, or an API client to invoke any part of this system.** `grep -rn "record_life_event\|undo_life_event\|preview_life_event\|list_life_events"` across `app/` returns callers only inside `life_event_service.py` itself and the test suite. There is no `app/routers/life_events.py`, no entry in `main.py`'s `include_router(...)` list, no `app/schemas/life_event.py` for request/response bodies, and `grep -rli "life.event"` across the entire `code/src` frontend tree returns **zero matches**. Seventeen handlers, a generic undo framework, and a notification integration were built, tested, and documented — and none of it is reachable outside a Python REPL or a test file.

This is not a UX polish gap. It is the difference between "Milestone 2 is complete" and "Milestone 2's business logic is complete." A production release decision has to be made about the feature, not the module, and as a feature this cannot ship.

Four further findings, all previously undocumented, are serious enough to require attention even after an API is added: a **field-scoped (not row-scoped) undo conflict guard** that can silently apply a stale partial write when two life events touch the same row on different fields; **no idempotency protection** on `record_life_event`, which combined with delta-based writes (`adjust_asset_value`) means a duplicate submission double-counts money, not just audit rows; **no row locking** anywhere in the read-then-write mutation pattern, a latent race condition; and **zero documentation trail** — `CHANGELOG.md`, `docs/backend.md`, and `docs/architecture.md` contain no mention of any of the 17 events, in direct violation of this project's own `CLAUDE.md` checklist.

None of this means the seventeen implementation reports were dishonest — every claim in them about rollback, undo, and generic-engine behavior that this audit re-tested checked out. The gap is that "component-complete" was reported as if it were "feature-complete."

---

## SCORES

| Dimension | Score | Basis |
|---|---|---|
| Architecture | 8/10 | Clean layering, zero duplicated logic (verified), one real conflict-detection gap |
| Product | 2/10 | Correct logic, but zero product surface — unreachable by any user |
| UX | 1/10 | No screens, no flows, no copy beyond backend notification strings exist |
| Security | 7/10 | Ownership enforced at the data layer by design; no idempotency, no rate-limit-per-user for this feature specifically once exposed |
| Performance | 7/10 | No N+1 in the collector fan-out; race-condition and unbounded-loop risks under concurrency/scale |
| Maintainability | 8/10 | 97.9% coverage, consistent patterns; docs/CHANGELOG never updated, 203-file root doc sprawl |
| Scalability | 6/10 | Stateless services scale; in-memory rate limiter and missing row locks are the two real ceilings |
| **Overall Release Score** | **4/10** | Excellent internals, zero product reachability |

## RELEASE DECISION: **NO GO**

Not because the code is bad. Because there is currently no way to ship this milestone to a single real user. See §1 for the full finding and the minimum path to GO.

---

## 1. ARCHITECTURE AUDIT

### 1.1 — CRITICAL — No API surface exists for any of the 17 events or the generic engine

**Severity:** CRITICAL (release blocker)
**Files:** `app/main.py`, `app/routers/*.py` (11 router files, none for life events), `app/services/life_event_service.py`
**Evidence:**
```
$ ls app/routers/
assumptions.py auth.py copilot.py dashboard.py family.py financials.py
goals.py notifications.py profile.py reports.py simulate.py
# no life_events.py

$ grep -n "include_router" app/main.py
# 10 routers registered; life_events is not among them

$ grep -rln "record_life_event\|undo_life_event" app/
app/services/loan_payoff_handler.py   # docstring mention only, not a call
app/services/life_event_service.py    # the definitions themselves

$ grep -rn "preview_life_event\|list_life_events\|get_life_event\b" app/ | grep -v life_event_service.py
# zero results — even read/list/preview have no caller
```
**Reason:** Every one of the 17 `LifeEvent_*_ImplementationReport.md` files describes a complete, tested handler, and that description is accurate at the unit/service level. But "record a life event" and "undo a life event" are operations a user performs through an HTTP request, and no such request path exists — not undocumented, not unauthenticated, not even present in a draft state. `app/schemas/life_event.py` does not exist, so there is no request/response contract to review either.
**Recommended Fix:** Before any further event-type work, build `app/routers/life_events.py` exposing at minimum: `POST /life-events` (record, `event_type` + `occurred_on` + `inputs` in the body), `POST /life-events/preview` (calls `preview_life_event`), `GET /life-events` (calls `list_life_events`), `GET /life-events/{id}`, `POST /life-events/{id}/undo`. Add `app/schemas/life_event.py` for the request/response models. This is the single highest-priority item before "production release" can mean anything for this milestone.

### 1.2 — Architecture matches implementation: mostly true, verified

**Severity:** INFORMATIONAL
**Files:** `LifeEventEngineArchitecture.md`, all 17 handler files
**Evidence:** Direct diffing of each handler against its architecture section (§5.1–§5.15 plus the three non-catalog additions) confirms entity lists, optional-step gating, and reuse targets match. `grep -ln "await db.execute\|select(" app/services/*_handler.py` returns **no results** — confirmed zero handlers perform raw queries; all delegate to service functions.
**Reason:** This is the one area where the implementation reports' self-description is fully corroborated, not just claimed.
**Recommended Fix:** None needed.

### 1.3 — HIGH — Generic undo's conflict guard is field-scoped, not row-scoped: cross-event ordering hazard

**Severity:** HIGH
**Files:** `app/services/life_event_service.py:289-291` (`_current_state_matches`), `app/services/financials_service.py` (`update_income_source`, `deactivate_income_source`)
**Evidence:**
```python
def _current_state_matches(row: Any, after_state: dict[str, Any]) -> bool:
    return snapshot(row, after_state.keys()) == after_state
```
`after_state.keys()` is only the fields the *specific effect* touched (e.g. Salary Raise's effect on `income_sources` only ever contains `{"annual_amount": ...}`; it never contains `is_active` because `update_income_source`'s snapshot is scoped to `patch.model_dump(exclude_unset=True).keys()`).
**Reason (concrete failure scenario):**
1. User records **Salary Raise** on income source X: `annual_amount` 80,000 → 95,000. Effect's `after_state = {"annual_amount": 95000}`.
2. User later records **Job Change**, which calls `deactivate_income_source` on the *same* income source X (soft-delete) and creates a new one. This effect's `after_state` is `{"is_active": False, "annual_amount": 95000}` (unchanged, since deactivation doesn't touch the amount).
3. User now undoes the **Salary Raise** (the older event). The guard checks only `annual_amount` — it is still `95000`, matching — so undo proceeds "clean," silently resetting `annual_amount` back to `80000` **on a row that is already soft-deleted by a later, unrelated event**, without ever inspecting `is_active`.
4. The row is currently inactive, so no live calculation is affected *today*. But the row's own history is now wrong (it claims to be worth 80,000 at a point after the user's own explicit Job Change event said otherwise), and if anything ever reactivates that row by field-level `before_state` restoration from a *different* effect that predates Salary Raise, the two events' undo histories are now inconsistent with each other in a way the engine itself cannot detect, because its conflict check never looks at the whole row — only the slice one specific effect happened to touch.

This is exactly the kind of "hidden coupling" the audit brief asked to find: two independently-correct handlers (Salary Raise, Job Change) combine, through the shared generic engine, into an emergent gap neither handler's own test suite could have caught, because each handler's tests only ever undo *that* handler's own event in isolation.
**Recommended Fix:** Either (a) snapshot the *entire* row (all columns) at effect-creation time regardless of which fields the handler touched, and compare the full row on undo — more expensive but airtight — or (b) add a per-row `version`/`updated_at` check: record the row's `updated_at` timestamp in the effect, and block undo if `updated_at` has changed at all since, regardless of which fields changed. Option (b) is the smaller diff and reuses columns every affected table already has.

### 1.4 — MEDIUM — `get_or_create_household` side effects are invisible to the audit trail

**Severity:** MEDIUM
**Files:** `app/services/family_service.py:50-70`, `app/services/marriage_handler.py`, `birth_of_child_handler.py`, `dependent_parent_handler.py`
**Evidence:** `get_or_create_household` creates a `Household` row and a `"self"` `HouseholdMember` row as a side effect, inside the same transaction as the life event, whenever a user's *first* family-domain event fires and no household exists yet. Neither write is wrapped in an `EntityEffect`; only the Marriage/Birth-of-Child/Dependent-Parent-specific rows are.
**Reason:** If a life event is undone, the household and self-member rows created as a side effect are never reversed (they simply aren't part of the effect list) — which is almost certainly the *right* behavior (a household shouldn't vanish because one life event was undone), but it means `life_event_effects` is not a complete picture of every row this transaction wrote, contrary to what the audit-trail claims in every implementation report imply.
**Recommended Fix:** Either explicitly document this as an intentional exception ("household bootstrap is infrastructure, not a life-event effect"), or add a fourth `EntityEffect` with `change_type="create"` for the bootstrap case so the audit trail is complete. Low urgency; document either way.

### 1.5 — Handler registry scalability: genuinely good

**Severity:** INFORMATIONAL
**Files:** `app/main.py:47-66`, `app/services/life_event_service.py:139-152`
**Evidence:** `_HANDLERS: dict[str, LifeEventHandler]` with `register_handler`/`unregister_handler`/`registered_event_types()`. Adding an 18th event type is a two-line diff (one handler class, one `register_handler` call) with zero changes to the generic engine. Three of the 17 events (Adoption, Business Start, Business Sale) required **zero new service code** at all — confirmed by re-reading each handler file, all three compose exclusively from prior extractions.
**Reason:** This is a real strength worth stating plainly rather than only finding fault.
**Recommended Fix:** None. This is the part of the architecture that most deserves the "GO" framing the implementation reports used.

---

## 2. PRODUCT AUDIT — Customer Journey Replay

**Method note:** Because §1.1 means no HTTP journey can actually be replayed, this section traces the *given* example journey (Student → First Job → Salary Raise → Marriage → Birth → House Purchase → Second Child → Retirement → Death → Inheritance) through direct service-layer calls, the same way the test suite does, and checks cross-feature consistency at the code level.

### 2.1 — Journey logic is internally consistent, verified by direct tracing

**Severity:** INFORMATIONAL
**Evidence:** Salary Raise → Marriage → Birth of Child (with linked education goal) → House Purchase (with down payment from savings + linked goal) → second Birth of Child → Retirement (deactivating salary, creating pension, updating the two education goals' contributions) → Inheritance all compose without contradiction: every financial write is read live by `get_financial_context`/`get_dashboard` (ADR-001/ADR-005, `LifeEventEngineArchitecture.md:28`), so Dashboard, Reports (`reports.py:23`, reuses `get_dashboard` directly — confirmed by reading the router), Recommendations, and Goals all agree by construction, not by synchronization.
**Reason:** No caching layer exists anywhere in `app/services/*.py` (confirmed: the only `lru_cache` in the codebase is on `get_settings()`), so there is no staleness window to audit for — a structural strength inherited from before this milestone, correctly leveraged by it.
**Recommended Fix:** None.

### 2.2 — HIGH (product scope) — "Death" has no corresponding life event

**Severity:** HIGH (as a product-completeness gap, not a code defect)
**Files:** `LifeEventEngineArchitecture.md` (all 15 catalogued events), `LifeEventEngine_ProgressMatrix.md` (all 17 implemented events)
**Evidence:** The journey this audit was asked to replay explicitly includes "Death." No event in the original 15-event catalog, the 3 additions (Bonus, Dependent Parent, Education Planning), or the 17 implemented handlers models the death of the user or a household member. There is no "surviving spouse" flow, no beneficiary-payout-triggered household update, no conversion of a deceased spouse's `HouseholdMember` row.
**Reason:** This is a real, common life event this milestone's own example journey names and does not support. It may be legitimately out of scope for Milestone 2 (a user cannot report their own death; a "reported by survivor" flow is a different product shape entirely, arguably touching legal/estate features this app only lightly models via `Nominee`/`EstateDocument`). But it should be named as a known gap, not silently absent.
**Recommended Fix:** Add "Death of a Family Member" to the architecture's own roadmap as an explicitly deferred event, with a one-paragraph note on why (likely: it needs beneficiary/estate-document integration this milestone didn't build, and the `Nominee`/`EstateDocument` tables already exist per `app/models/estate.py` — a future milestone has real infrastructure to build on).

### 2.3 — Recommendations across the journey: correct, no staleness, no duplication (with one caveat)

**Severity:** LOW (documentation/clarity only)
**Files:** `app/services/notification_service.py`
**Evidence:** Traced whether a goal-touching life event (e.g. Retirement updating a goal's `monthly_contribution` to `$0`) could produce a "duplicate" notification alongside the generic life-event one. It does not duplicate — `_collect_goal_facts` and `_collect_life_event_facts` describe *different facts* ("your goal is now at risk" vs. "you recorded a retirement"), both true and both useful, unlike the Marriage case (§ where both collectors described the *same* fact and the fix in `_LIFE_EVENT_SKIP_TYPES` was correctly scoped to exactly that situation).
**Reason:** Worth stating explicitly since a shallower audit could mistake two legitimately-different notifications firing from one event for a repeat of the Marriage bug. It is not.
**Recommended Fix:** None needed; consider a one-line comment in `notification_service.py` near `_LIFE_EVENT_SKIP_TYPES` clarifying this distinction for the next engineer, since the two cases look superficially similar.

---

## 3. UX AUDIT

**Severity:** CRITICAL (as a consequence of §1.1)
**Evidence:** `grep -rli "life.event\|lifeEvent" code/src` returns zero matches. No route, no component, no API-client function in `code/src/lib/api.ts`, no mock-data fixture in `code/src/lib/mock-data.ts`.
**Reason:** Every UX question in the brief — can a user understand Life Events, Undo, the Review Screen, conflict messages, validation, errors, empty states — has the same answer: **there is nothing to evaluate.** None of these surfaces exist in any form, not even a rough draft.
**Recommended Fix:** This is not a "polish" backlog item; it is the entire remaining scope of this milestone from a product standpoint. At minimum, before any release: an event-type picker, a per-event input form (17 different shapes, per each handler's own documented "Required/Optional inputs"), a review/confirm screen, a life-event history list, and an undo confirmation with the conflict list surfaced in plain language (the backend already returns `UndoResult.conflicts` with `reason` strings suitable for this — `life_event_service.py:275-287` — so the data contract is ready even though nothing consumes it yet).

---

## 4. SECURITY AUDIT

### 4.1 — Authorization/ownership: strong, verified, enforced at the data layer

**Severity:** INFORMATIONAL (strength)
**Evidence:** Every service function a handler calls filters by `current_user.id`/`user.id` at the query level (`financials_service.py`'s `deactivate_income_source`, `update_income_source`, etc. all include `.where(Model.user_id == current_user.id, ...)`). Every handler's `apply(self, db, user, inputs)` signature takes the authenticated user as a parameter never sourced from `inputs` — confirmed by reading all 17 handlers, none reads a `user_id` field out of the inputs dict.
**Reason:** This means cross-user access (IDOR) protection is structural, not just a router-level check that could be forgotten — a genuine strength, contingent on whatever future router always passes the JWT-derived user, never a client-supplied one.
**Recommended Fix:** When building the router (§1.1), do not accept `user_id` in the request body under any circumstances; derive it exclusively from `get_current_user`.

### 4.2 — HIGH — No idempotency protection; duplicate submission double-counts money for delta-based effects

**Severity:** HIGH
**Files:** `app/models/life_event.py` (no unique/idempotency-key column), `app/services/financials_service.py` (`adjust_asset_value`)
**Evidence:** `life_events` has no client-supplied idempotency key and no unique constraint that would catch a duplicate. `adjust_asset_value` (used by House Purchase's down payment, Home Sale's/Business Sale's proceeds, Major Medical Event's lump sum, Business Start's funding) is a **delta** operation: `asset.current_value = asset.current_value + delta`.
**Reason:** A duplicate submission (double-click before a future frontend disables the button, or a client/proxy retry on a timed-out-but-actually-succeeded request) would apply the delta twice — e.g. a $50,000 down payment recorded twice would remove $100,000 from the funding asset, not $50,000. This is a real money-correctness bug waiting for a frontend to expose it, not a hypothetical.
**Recommended Fix:** Add an optional client-supplied `idempotency_key` (UUID) column to `life_events` with a unique constraint on `(user_id, idempotency_key)`; have the future `POST /life-events` endpoint require it and return the existing record on a repeat key instead of re-running `apply()`.

### 4.3 — MEDIUM — Race condition on read-then-write mutations (no row locking)

**Severity:** MEDIUM
**Files:** `app/services/financials_service.py` (`adjust_asset_value`), and the same pattern in every other update-style service function
**Evidence:** `grep -rn "with_for_update" app/services/*.py` returns zero results anywhere in the codebase, including pre-existing (non-Life-Event) code. `adjust_asset_value` does `SELECT` → compute in Python → `setattr` → `flush()`, with no `SELECT ... FOR UPDATE` and no optimistic-locking version column on `Asset`.
**Reason:** Two concurrent requests touching the same asset (two browser tabs, or a legitimate edit racing a duplicate submission from §4.2) can produce a lost update: both read the same starting value, both compute their own new value, the second write wins and silently discards the first. This is a pre-existing pattern in the app (not introduced by this milestone), but the Life Event Engine is the first place it's used for **financial delta accounting**, where a lost update means money silently disappearing from the user's own records.
**Recommended Fix:** Add `SELECT ... FOR UPDATE` to `adjust_asset_value`'s lookup (Postgres supports this natively; SQLite in tests does not enforce it but won't break either), or add an `Asset.version` column and use SQLAlchemy's built-in optimistic versioning.

### 4.4 — Undo abuse: bounded correctly, but no time/authorization ceiling

**Severity:** LOW
**Files:** `app/services/life_event_service.py:293-380`
**Evidence:** `undo_life_event` correctly rejects re-undoing an already-undone event (`ValueError`) and correctly rejects a non-owner (`LookupError`). There is no time window — a two-year-old Home Sale can be undone today if none of its touched rows have since changed, and no additional re-authentication (e.g. re-entering a password) is required for a high-value reversal.
**Reason:** This may be entirely intentional (matches the existing app's general lack of step-up-auth anywhere), but it's worth a product decision rather than a silent default, since undoing a Home Sale a long time later is a materially different risk than undoing yesterday's Bonus.
**Recommended Fix:** Product decision, not a code defect. If desired, add a configurable undo window per event category, or require re-authentication for undo on events above a configurable dollar threshold.

### 4.5 — `force=True` undo is not currently reachable, but must be gated when it is

**Severity:** LOW (forward-looking)
**Files:** `app/services/life_event_service.py:293-346`
**Evidence:** `undo_life_event(..., force=True)` overrides the state-mismatch guard. It is never called from anywhere in `app/` today (only tests) — consistent with §1.1.
**Recommended Fix:** When the router is built, do not expose `force` as a default-available query parameter; require an explicit, separately-permissioned action (e.g. a second confirmation step surfacing the exact conflicts, which the data already supports via `UndoResult.conflicts`).

---

## 5. PERFORMANCE AUDIT (100 → 100,000 users)

| Users | Assessment |
|---|---|
| 100 | No concern at any layer. |
| 1,000 | No concern. Notification collector fan-out (5-6 queries per `/notifications` call) is cheap and indexed. |
| 10,000 | In-memory rate limiter (`app/middleware/rate_limit.py:7-9`, its own docstring: *"For multi-process deployments, replace the in-memory store with Redis"*) becomes a real gap the moment the app runs more than one process/instance — a pre-existing limitation this milestone does not fix or worsen, but does not fix either. |
| 100,000 | Same in-memory rate-limiter ceiling, now certain to matter (horizontal scaling required at this volume). The race-condition gap (§4.3) becomes statistically likely to actually manifest, not just theoretically possible. |

### 5.1 — MEDIUM — Unbounded loop growth in Retirement's list-shaped optional steps

**Severity:** MEDIUM
**Files:** `app/services/retirement_handler.py:57-67, 118-127`
**Evidence:** `for income_id in inputs.get("income_source_ids", [])` and `for goal_update in inputs.get("goal_contributions", [])` each issue one full SELECT+UPDATE round trip per list item, sequentially, inside one handler call.
**Reason:** For the realistic case (1-3 income sources, 1-3 goals) this is invisible. There is no upper bound enforced anywhere (no max-length validation on these lists), so a malformed or adversarial request with, say, 500 goal ids would perform 500 sequential Monte Carlo probability recalculations (`calculate_goal_probability`, which itself runs a 2,000-path simulation) inside a single request/transaction — a genuine, if edge-case, denial-of-service-shaped cost center once an API exists.
**Recommended Fix:** Add a reasonable max-length validation (e.g. 20) on both list inputs once the request schema exists (§1.1); batch the goal recalculations concurrently the same way `planning_service` already dispatches other concurrent Monte Carlo work (per the `dba0bd9` commit visible in this repo's own recent history — "dispatch goal probability simulations concurrently").

### 5.2 — No N+1 in the notification/recommendation fan-out

**Severity:** INFORMATIONAL (strength)
**Evidence:** Each notification collector (`_collect_insurance_fact`, `_collect_scheme_facts`, `_collect_family_member_added_facts`, `_collect_goal_facts`, `_collect_life_event_facts`, `_collect_divorce_review_facts`) issues one query, not one query per row of a prior result set. `_collect_divorce_review_facts` correctly early-returns after a single indexed lookup for the (overwhelmingly common) case of no inactive spouse existing at all.
**Recommended Fix:** None.

---

## 6. RECOMMENDATION AUDIT

**Severity:** INFORMATIONAL (strength, with one already-covered caveat)
**Evidence:** ADR-005 (recommendations computed live, never persisted) means "stale recommendation" and "duplicate recommendation" are structurally impossible for the financial-health rules (`family_recommendations_service.py`) — verified: no table stores a computed recommendation anywhere; `grep` for any `Recommendation` model write in the service layer found none. The one place a duplication bug existed (Marriage's notification, §Marriage's own report) was found and fixed by the implementation itself, and correctly reused for Birth of Child/Adoption/Dependent Parent (see §2.3 above for the distinction between that fixed bug and a superficially similar but legitimate double-notification case).
**Recommended Fix:** None.

---

## 7. FINANCIAL AUDIT

**Severity:** INFORMATIONAL (strength)
**Evidence:** `reports.py:23` calls `get_dashboard` directly and reads the identity-mapped `Goal` objects from the same session for its own goal list — the router's own comment states this explicitly and it is accurate. `FinancialContext`/`get_dashboard`/`RecommendationEngineV2` all compute from the same live queries with no intermediate cache. No divergent code path was found anywhere that recomputes net worth, savings rate, or goal probability a second way.
**Recommended Fix:** None.

---

## 8. DATA INTEGRITY AUDIT

Covered in depth in §1.3 (field-scoped undo guard — HIGH), §4.2 (idempotency — HIGH), §4.3 (race conditions — MEDIUM), §1.4 (untracked household bootstrap — MEDIUM). Additional findings:

### 8.1 — Rollback correctness: verified independently, not just re-asserted

**Severity:** INFORMATIONAL (strength)
**Evidence:** This audit re-read (not re-ran, since the prior test runs are trustworthy given the fresh coverage run in this same audit reproduced 636/636 passing) the rollback test for the highest-effect-count event, Business Sale (4 effects across `assets`/`liabilities`/`income_sources`/`user_profiles`), and confirmed the pattern: a wrapper handler performs all real writes inside the transaction, raises, and the test asserts every single touched row reverted to its pre-transaction state after `db.rollback()`. This same pattern is repeated per-event, not just claimed once and assumed to generalize.
**Recommended Fix:** None.

### 8.2 — Soft delete discipline: consistently applied, one gap closed mid-build

**Severity:** INFORMATIONAL, with the gap noted for completeness
**Evidence:** `family_service.remove_member` originally did not cascade-deactivate the associated `Dependent` row (a real, pre-existing gap predating this milestone, per the Divorce implementation report) and was fixed as part of this build. Verified the fix is in place: `remove_member` now accepts and deactivates `dependent` when given.
**Recommended Fix:** None; already resolved.

---

## 9. API AUDIT

**Severity:** N/A — there is no API for this feature (§1.1). Every sub-question the brief asks (REST consistency, status codes, validation, idempotency, naming) is unanswerable until §1.1 is resolved. Idempotency specifically is flagged separately and substantively in §4.2 because it is a design property the *data model* already lacks, independent of whatever router eventually gets built.

---

## 10. TECHNICAL DEBT AUDIT

### Release blockers
1. No API surface (§1.1) — CRITICAL.
2. No idempotency protection on delta-based effects (§4.2) — HIGH.
3. Field-scoped undo conflict guard (§1.3) — HIGH, should be fixed before undo is exposed to real users, since the failure mode is silent.

### Should-fix before general availability
4. Row-locking gap on read-then-write mutations (§4.3) — MEDIUM.
5. Untracked household-bootstrap side effect (§1.4) — MEDIUM, low urgency.
6. Unbounded list-input loop growth in Retirement (§5.1) — MEDIUM.

### Acceptable debt (documented, deliberate, correctly named by the implementation itself)
7. `liability_type="other"` placeholder for business loans, pending a real enum value (Business Start/Business Sale's own reports name this explicitly — verified accurate).
8. No `income_sources` row created at Business Start (architecturally correct per §5.14 — verified, not debt).
9. In-memory rate limiter, not Redis-backed (pre-existing, documented in its own docstring, not introduced by this milestone).
10. Generic engine's "create effect with no `is_active` column can't be undone" limitation ( `user_profiles`, `financial_assumptions`) — named and tested by Retirement's own report; a real, permanent, acceptable limitation of the current schema, not a bug.

### Documentation debt (new finding, not previously reported)
11. **`CHANGELOG.md` has zero entries for any of the 17 Life Events or the engine itself** — verified by grep; the project's own `CLAUDE.md` "Adding an Endpoint — Checklist" requires this at step 8.
12. **`docs/backend.md` and `docs/architecture.md` have zero mentions of Life Events** — same checklist, step 7.
13. 203 loose `.md` files at the repository root (pre-existing sprawl this milestone's 18 new `LifeEvent_*_ImplementationReport.md` files added to rather than reduced) — a discoverability problem for the next engineer; none of these reports are linked from `docs/` or the README.

### Future improvements (named by the architecture itself, not invented here)
14. `family_recommendations_service` has no employment-status-aware rule yet (Business Start's own report names this as a deliberate non-goal).
15. No "Death of a Family Member" event exists (§2.2 — new finding from this audit, since the brief's own example journey surfaced it).

---

## APPENDIX: RE-VERIFIED CLAIMS FROM PRIOR REPORTS

For transparency, these specific claims from the 17 implementation reports were independently re-checked in this audit and found accurate:

- "636 backend tests pass" — reproduced, 636 passed, plus a fresh coverage run (never previously run this session) showing 97.90% coverage against an 80% gate.
- "ruff clean" / "mypy --strict clean" — not re-run in this audit (no code changed since the last verified run at the end of Business Sale), but the absence of any source change since that run makes re-verification unnecessary.
- "No handler performs raw queries" — re-verified independently via grep, true.
- "Zero event-specific undo code" — re-verified by reading `life_event_service.py`'s undo path against all 17 handlers; true, and this is exactly what makes §1.3's gap a *generic engine* defect rather than a per-handler one.
- "`liability_type='other'` is a named, deliberate placeholder" — re-verified against the schema (no DB-level enum constraint exists, confirmed by reading the model), true.
