# RECOMMENDATION ENGINE V2 — DESIGN DOCUMENT

**Role:** Principal Financial Systems Architect
**Input:** `FinancialsE2EValidationReport.md`, Finding 1 — the dedicated recommendation engine has no code path that reads income, expenses, assets, or liabilities, confirmed both by source inspection and a live before/after trace.
**Scope of this document:** design only. No code is written or modified anywhere below.

---

## 1. WHY THE RECOMMENDATION ENGINE IS DISCONNECTED FROM THE FINANCIAL ENGINE (ROOT CAUSE)

This is not a bug in the sense of a missed line of code — it is the predictable result of three separate design decisions, each individually correct at the time it was made, that were never later reconciled:

1. **The recommendation engine was scoped, from its first commit, to exactly two sources.** `backend/app/services/family_recommendations_service.py`'s own header comment states its job as "aggregation only... every why/why_now/used/missing/confidence value is read from an already-certified engine" — namely `family_insurance_service.compute_insurance_recommendation` and `scheme_eligibility_service.evaluate_household_eligibility`. It was built to combine two existing, certified engines, not to be a general-purpose rules platform. A third input category (financial facts) was never in its founding scope, so there was never a moment where "should this read income_sources?" was even a question that came up.

2. **Financial facts (income, expenses, assets, liabilities) did not have a first-class consumer to design around until this milestone.** Before Milestone 1, these four tables existed only as onboarding-time write targets with one read consumer: `planning_service.get_dashboard`. There was no second reader to generalize a pattern from, so no one had reason to ask "what else should read this."

3. **A parallel, narrower recommendation-like surface already existed and nobody unified it.** `planning_service.py`'s `_generate_suggestions(goals, savings_rate)` — surfaced via `GET /dashboard`'s `suggestions` field — already reacts to a derived financial number (`savings_rate`, itself computed from income and expenses). This function is a second, independent recommendation engine in every functional sense, but it was never merged with `family_recommendations_service`, so the codebase now has two things that behave like "recommendations," only one of which touches financial data, and they were never noticed as the same category of concern. A third parallel aggregator, `notification_service.py`'s five fact-collectors, has the identical shape again and also does not read financial facts.

The disconnection, in one sentence: **the codebase has three independent, hand-rolled live-aggregation engines (recommendations, dashboard suggestions, notifications), each scoped narrowly to the inputs that existed when it was built, and financial facts arrived after all three were already scoped — so none of them were extended, because extending "the recommendation engine" was never posed as a single question with a single answer.**

---

## 2. CURRENT ARCHITECTURE

```
GET /family/recommendations
  └─ family.py router
       └─ family_recommendations_service.get_family_recommendations(db, user, household)
            ├─ _insurance_recommendations(db, user, household)
            │    └─ family_insurance_service.compute_insurance_recommendation(db, user, household)
            │         reads: household_members, dependents, health_policies, tax_sections
            ├─ _scheme_recommendations(db, household)
            │    └─ scheme_eligibility_service.evaluate_household_eligibility(db, household.id)
            │         reads: household_members, dependents, scheme_eligibility_rules, schemes
            └─ _detect_conflicts(recommendations)
                 pure function, no I/O — groups by (subject, reference_code)

  Response: FamilyRecommendationsResponse { recommendations: FamilyRecommendation[], conflicts: RecommendationConflict[] }
  Computed fresh on every call. Nothing is persisted.
```

**A separate, undiscovered second engine exists in the same codebase:**
```
GET /dashboard
  └─ planning_service.get_dashboard(session, user)
       reads: goals, assets, liabilities, income_sources, expenses
       └─ _generate_suggestions(goals, savings_rate)
            reacts to: goal.probability, savings_rate (derived from income_sources + expenses)
```

**A third, also-separate live-aggregation engine:**
```
GET /notifications
  └─ notification_service.list_notifications(db, user)
       └─ _collect_facts(db, user)
            ├─ _collect_insurance_fact
            ├─ _collect_scheme_facts
            ├─ _collect_family_member_added_facts
            └─ _collect_goal_facts
       (no financial-facts collector)
```

**A fourth artifact, confirmed present but dead:** `backend/app/models/recommendation.py` defines a fully-built `Recommendation`/`RecommendationCitation` SQL model — reasoning, confidence_score, alternatives_considered, assumptions_used, citations linking back to `scheme_rates`/`tax_sections` rows — clearly designed for exactly this kind of explainable, auditable recommendation. `grep` across the entire backend shows it is referenced only in `app/models/__init__.py` (metadata registration for Alembic). It is never queried, inserted, or read anywhere. This table has existed, unused, since before the current recommendation engine was built, and the current engine's own code comments explicitly note that it does *not* write to this table ("never a Milestone 5 Recommendation Engine output... never persisted") — meaning the codebase's own history already anticipated a more complete recommendation engine arriving later. This design is that later arrival.

**Root architectural fact this design must respect:** financial facts (`income_sources`, `expenses`, `assets`, `liabilities`) are scoped to `user_id` — the account owner — with no household linkage. Insurance and scheme recommendations are scoped to the `household` (aggregating multiple members). A financial-health recommendation source is therefore inherently user-scoped, not household-scoped, mirroring exactly how `get_dashboard` and `get_reports_summary` already work today. This is an existing asymmetry in the data model, not a new problem this design introduces.

---

## 3. TARGET ARCHITECTURE

The fix is not "make `family_recommendations_service` read four more tables." That would just be a fourth ad-hoc extension of a service whose own header already claims a narrower job than what's being asked of it. The fix is to introduce one shared, explicit **Financial Context** — a single, cheaply-computed object carrying exactly the numbers a recommendation rule needs — and make it a first-class input to the recommendation engine alongside insurance and schemes, on equal footing.

```
GET /family/recommendations
  └─ family_recommendations_service.get_family_recommendations(db, user, household)
       ├─ _insurance_recommendations(...)              [unchanged]
       ├─ _scheme_recommendations(...)                 [unchanged]
       ├─ _financial_health_recommendations(financial_context)     [NEW]
       └─ _detect_conflicts(recommendations)            [unchanged]

  financial_context: FinancialContext  ← NEW, computed once per request
       source: planning_service.get_financial_context(db, user)
       (an extraction of get_dashboard's existing aggregation math into a
       reusable function — not a second, competing computation)
```

**`FinancialContext` is a plain data object, not a new persisted table:**
```
FinancialContext
  monthly_income: float
  monthly_expenses: float
  savings_rate: float          (already computed today, in get_dashboard)
  net_worth: float              (already computed today, in get_dashboard)
  liquid_assets: float          (already computed today, in get_dashboard)
  invested_assets: float        (already computed today, in get_dashboard)
  total_liabilities: float      (already computed today, in get_dashboard)
  debt_to_income_ratio: float   (NEW — the one genuinely new number: total_liabilities / (monthly_income × 12), guarded against a zero-income divide)
```

Every field except `debt_to_income_ratio` already exists inside `get_dashboard`'s function body today — this design does not invent new financial math, it **extracts existing, already-correct math into a shared, callable shape** so a second consumer (the recommendation engine) can use it without duplicating it. This is the same "compute once, reuse" principle already proven in this codebase by `reports.py` calling `get_dashboard()` directly rather than re-deriving its numbers — Recommendation Engine v2 extends that exact, already-successful pattern one level deeper, rather than introducing a new one.

---

## 4. WHICH SERVICES SHOULD CONSUME FINANCIAL CONTEXT

| Service | Should consume `FinancialContext`? | Reasoning |
|---|---|---|
| `family_recommendations_service.py` | **Yes — this is the fix.** | This is the service Finding 1 identified as disconnected. It gains a third source function, `_financial_health_recommendations`, parallel in structure to the two it already has. |
| `planning_service.get_dashboard` | **Already does — becomes the source of `FinancialContext`, not a new consumer.** | Its own aggregation logic is refactored (extracted, not rewritten) into `get_financial_context`, which `get_dashboard` then calls itself, so its own behavior and response shape do not change at all. |
| `notification_service.py` | **Not in this design's scope — flagged as a candidate follow-up, not a requirement.** | A "your debt-to-income ratio just crossed a threshold" notification is plausible future value, but Finding 1 was specifically about `/family/recommendations`, not `/notifications`. Adding a sixth fact-collector here should be a deliberate, separate decision, not a side effect of this fix — see §12, Migration Strategy. |
| `family_insurance_service.py` / `scheme_eligibility_service.py` | **No.** | These remain exactly what their own docstrings already say they are — calculation-lite fact appliers for one specific domain each. They should not be widened to know about `FinancialContext`; the aggregation layer (`family_recommendations_service`) is the correct place for cross-domain awareness, not the individual engines. |
| `optimizer.py` (goal optimizer) | **No.** | Confirmed by source inspection: zero references to any financials model today. Goal optimization is deliberately scoped to a single goal's own Monte Carlo inputs (ADR-001's Calculation Context). Widening it to read `FinancialContext` would blur the exact boundary ADR-001 exists to protect. Out of scope for this design.

---

## 5. WHICH APIS SHOULD CHANGE

**No new endpoint is required.** `GET /family/recommendations` already returns a `recommendations: FamilyRecommendation[]` array designed to hold entries from multiple sources — the fix is additive content inside an existing, already-general response shape, not a new resource.

**One schema change, additive:**
- `RecommendationSource` (currently `Literal["insurance", "schemes"]`, in `app/schemas/family_recommendations.py`) gains one new value: `Literal["insurance", "schemes", "financial_health"]`. This is the only wire-format change. It is backward compatible for any consumer that doesn't exhaustively `match` on the literal (see §11).

**One new internal function, not an API:**
- `planning_service.get_financial_context(db, user) -> FinancialContext` — an internal service function, not exposed as its own endpoint. It exists purely to be called from both `get_dashboard` and `family_recommendations_service`.

**No change to:**
- `GET /dashboard`'s response shape (it already returns everything `FinancialContext` needs; the extraction is internal).
- `GET /reports/summary` (continues to call `get_dashboard()` exactly as it does today — untouched).
- Any of the four `PATCH /financials/*` endpoints from Tasks 1-6 (they remain exactly as built; this design consumes their data, it does not change how that data is written).

---

## 6. RECOMMENDATION RULES — ONE PER REQUIRED SIGNAL

Every rule below follows the existing `FamilyRecommendation` envelope exactly (`source`, `recommendation_type`, `subjects`, `reference_code`, `why`, `why_now`, `what_information_was_used`, `what_information_is_missing`, `confidence_score`) — no new envelope shape is introduced, per the existing "every field is mandatory, no exceptions" rule already documented in `family_recommendations.py`.

| Signal | Rule (`recommendation_type`) | Trigger | `why` (example) | `confidence_score` |
|---|---|---|---|---|
| **Income** | `income_concentration` | Exactly one active income source exists | "All of your tracked income comes from a single source." | 1.0 (a count, not an estimate) |
| **Expenses** | `expense_review_prompt` | `monthly_expenses` has not changed (via `updated_at` on any `expenses` row) in over 180 days | "Your recorded expenses haven't been updated in 6 months — they may no longer reflect your actual spending." | 1.0 (a date comparison, not an estimate) |
| **Assets** | `low_liquidity` | `liquid_assets < monthly_expenses × 3` (i.e., under 3 months of expenses held liquid) | "Your liquid assets cover under 3 months of your recorded expenses." | 1.0 (arithmetic on already-verified inputs) |
| **Liabilities** | `high_interest_debt` | Any liability has `interest_rate > 0.10` (10%) and `balance > 0` | "This debt's interest rate is high enough that paying it down usually outperforms most investment returns." | 1.0 |
| **Savings Rate** | `low_savings_rate` | `savings_rate < 15%` | *(already exists today, in `planning_service._generate_suggestions` — this design's job is to make this same signal also reachable from `/family/recommendations`, not to invent a second copy of the rule; see §7)* | 1.0 |
| **Net Worth** | `negative_net_worth_trend` | `net_worth < 0` | "Your recorded liabilities currently exceed your recorded assets." | 1.0 |
| **Debt Ratio** | `high_debt_to_income` | `debt_to_income_ratio > 0.36` (a conventional 36% DTI ceiling) | "Your total debt is more than 36% of your annual income — a level most lenders treat as a risk signal." | 1.0 |

Every confidence score above is `1.0` deliberately, not because the recommendation is more "important" than an insurance or scheme one, but because every input is a plain arithmetic fact the user themselves entered — there is no eligibility judgment, tax-code interpretation, or estimate involved, unlike the insurance engine's confidence tiers (1.0 vs 0.7) which exist specifically to flag *interpretive* uncertainty. This distinction should be preserved, not flattened — a future engineer should not casually invent a non-1.0 confidence score for a pure arithmetic rule; that would misrepresent what confidence scoring means in this system.

**`what_information_was_used` / `what_information_is_missing`, filled honestly per rule:** e.g., `high_debt_to_income`'s `what_information_was_used` is `["total recorded liability balance", "total recorded annual income"]`, and its `what_information_is_missing` is `["any liabilities or income not entered in Financials"]` — carrying forward the existing pattern of disclosing that a recommendation is only as complete as the data underneath it, which the current insurance/scheme rules already do.

---

## 7. RULE ENGINE CHANGES

1. **Extract, don't duplicate, the `low_savings_rate` threshold.** Today the exact rule ("savings rate below 15%") lives inline inside `planning_service._generate_suggestions`. Recommendation Engine v2 must not hardcode a second `15` constant in `family_recommendations_service.py` — the threshold constant (and the comparison itself) should move to one shared location (a `financial_rules` module or similar, in `planning_service.py` alongside `FinancialContext` itself) that both `_generate_suggestions` (Dashboard) and the new `_financial_health_recommendations` (Family Recommendations) call. This is the one place in this design where an actual code change to existing logic (not just an addition) is warranted — everywhere else, the change is additive.
2. **New threshold constants**, named and centrally declared exactly like the existing `_INSURANCE_REFERENCE_CODE`/`_SAVINGS_SCHEME_REFERENCE_CODE` module-level constants already are in `family_recommendations_service.py`: `_LOW_LIQUIDITY_MONTHS = 3`, `_HIGH_INTEREST_THRESHOLD = 0.10`, `_HIGH_DTI_THRESHOLD = 0.36`, `_STALE_EXPENSE_DAYS = 180`. Each should carry a one-line comment citing the convention it's based on (e.g., 36% DTI is a widely-cited mortgage-underwriting convention, not a figure this product invented — the same "never invent a financial policy or rate" discipline the government-scheme engine already follows for scheme rates should apply here too, since a DTI or liquidity-buffer threshold is exactly the kind of number that must be attributable, not guessed).
3. **`_financial_health_recommendations(context: FinancialContext) -> list[FamilyRecommendation]`** — a new, pure function taking the already-computed context (never re-querying the database itself), mirroring `_insurance_recommendations`/`_scheme_recommendations`'s existing shape (an async function returning a list of the shared envelope type). Because it takes a plain data object rather than a database session, this specific function is trivially unit-testable with no database at all — a genuine testability improvement over the two existing source functions, which both require a live session.
4. **Conflict detection is untouched.** `_detect_conflicts` already groups by `(subject, reference_code)` across all sources generically — a `financial_health` recommendation naturally participates in conflict detection with zero code change, *provided* financial-health rules use `subjects: []` (they are about the account as a whole, not a named household member) or the account owner's own name where a subject makes sense. No financial-health rule in §6 currently shares a `reference_code` with any insurance/scheme rule, so no conflicts are expected in practice — this should be confirmed by a test (§14), not assumed.

---

## 8. DEPENDENCY GRAPH

```
                          ┌────────────────────────┐
                          │  income_sources          │
                          │  expenses                │
                          │  assets                  │
                          │  liabilities              │
                          │  (all user_id-scoped)      │
                          └────────────┬─────────────┘
                                       │ read by
                                       ▼
                       ┌───────────────────────────────┐
                       │ planning_service.get_financial_ │
                       │ context(db, user)  [NEW, extracted│
                       │ from get_dashboard's existing math]│
                       └───────┬───────────────────┬───────┘
                               │                    │
                               ▼                    ▼
              ┌─────────────────────────┐  ┌──────────────────────────────┐
              │ planning_service.        │  │ family_recommendations_       │
              │ get_dashboard             │  │ service._financial_health_    │
              │ (unchanged response       │  │ recommendations  [NEW]         │
              │  shape; internally now     │  └───────────────┬────────────────┘
              │  calls get_financial_      │                  │
              │  context instead of         │                  │ combined with
              │  re-deriving inline)         │                  ▼
              └───────────┬───────────────┘  ┌──────────────────────────────┐
                          │                   │ _insurance_recommendations    │
                          │ read by            │ _scheme_recommendations       │
                          ▼                   │ (both unchanged; read          │
              ┌─────────────────────────┐     │  household_members/policies/   │
              │ reports.report_summary   │     │  scheme_eligibility_rules,      │
              │ (unchanged — still just   │     │  as today)                      │
              │  calls get_dashboard)      │     └───────────────┬──────────────────┘
              └─────────────────────────┘                     │
                                                                ▼
                                               ┌──────────────────────────────┐
                                               │ family_recommendations_       │
                                               │ service.get_family_             │
                                               │ recommendations                  │
                                               │ (unchanged signature; one new     │
                                               │  source spliced into the same       │
                                               │  list, then _detect_conflicts)       │
                                               └───────────────┬──────────────────┘
                                                                │
                                                                ▼
                                               GET /family/recommendations
                                               (unchanged response schema,
                                                one new literal source value)
```

No new table, no new foreign key, no new cross-service dependency that didn't already exist in some form — `family_recommendations_service` already depends on two other services' outputs; it gains a third, structurally identical dependency.

---

## 9. DATA FLOW

1. A user edits an income, expense, asset, or liability value via the Financials page (Tasks 3-6) — unchanged, no part of this design touches that write path.
2. The next time the user (or anything acting on their behalf) requests `GET /family/recommendations`:
   a. `family_recommendations_service.get_family_recommendations` calls `planning_service.get_financial_context(db, user)`, which issues the same four SELECT statements `get_dashboard` already issues today (`income_sources`, `expenses`, `assets`, `liabilities`, all filtered to `is_active = true`), and derives `debt_to_income_ratio` as the one new computed field.
   b. The three source functions (`_insurance_recommendations`, `_scheme_recommendations`, `_financial_health_recommendations`) run — the first two exactly as today, unaffected by this change; the third evaluates the six thresholds in §6 against the freshly-read `FinancialContext`.
   c. `_detect_conflicts` runs over the combined list, exactly as today.
   d. The response is returned. Nothing is written back to the database as a result of this request — the "always live, never persisted" property this codebase has deliberately maintained for recommendations (and for goal-probability-on-read, per ADR-001) is preserved without exception.
3. Because step 2a re-reads the four tables fresh on every call, there is no possible staleness window between an edit on the Financials page and its effect on `/family/recommendations` — the same "PATCH now, read fresh next time" guarantee already proven for Dashboard and Reports in the validation report extends automatically to Recommendations, with zero new caching or invalidation logic required.

---

## 10. EVENT FLOW

This design is deliberately **not** event-driven, and that is a decision, not an omission. An alternative design would have a financials `PATCH` publish an event, a background worker recompute a `financial_health_score`, and store it for the recommendation engine to read. That alternative was considered and rejected:

- It would require the very persistence layer this codebase has consistently avoided for recommendations (§1's dead `Recommendation` table is the cautionary tale sitting right there — a persistence layer built once and never wired up correctly is worse than no persistence layer).
- It would introduce a staleness window (the time between the event firing and the worker finishing) into a system whose single biggest strength, per the validation report, is that Dashboard/Reports/Financials never disagree because nothing is cached.
- The actual computation involved (four `SELECT`s plus arithmetic) is cheap enough that computing it synchronously, on read, costs nothing worth optimizing around — see §11.

**The event flow that does exist, end to end:**
```
User action (PATCH /financials/{income,expenses,assets,liabilities}/{id})
   → row updated, transaction committed
   → (nothing further happens — no event, no queue, no background job)

Later, any read of:
   GET /dashboard          → recomputes live
   GET /reports/summary    → calls get_dashboard(), recomputes live
   GET /family/recommendations → NEW: calls get_financial_context(), recomputes live
   all three always reflect every write that has committed before the read began
```

---

## 11. PERFORMANCE IMPACT

- **Additional queries per `/family/recommendations` call: four** (`income_sources`, `expenses`, `assets`, `liabilities`), identical in shape and cost to the four `get_dashboard` already runs on every `/dashboard` call today — this is not new query *complexity*, it is the same, already-proven-cheap query pattern running once more, on a second endpoint.
- **No N+1 risk introduced.** `get_financial_context` issues exactly four flat `SELECT ... WHERE user_id = ...` queries, no per-row follow-up queries, matching the existing `get_dashboard` pattern exactly (which has already been through one documented query-count optimization pass, per `PerformanceReview_M2.1-P4.md`, referenced in `family_insurance_service.py`'s own comments — this design should be held to that same bar, not a lower one).
- **No new indexes required.** All four tables are already indexed on `user_id` (confirmed: `index=True` on `user_id` in `backend/app/models/financials.py` for all four models).
- **Marginal added latency per `/family/recommendations` call:** four additional small, indexed, single-user-scoped queries — the same cost `/dashboard` already pays, added to an endpoint that today issues zero financials queries. Expected to be low single-digit milliseconds against a warm connection pool; should be confirmed with a real measurement during implementation (per Engineering Constitution Rule 9 — verify against real infrastructure, not an estimate), not assumed from this document alone.
- **No change to Monte Carlo simulation cost.** This design does not touch `monte_carlo.py`, `optimizer.py`, or the goal Calculation Context in any way — confirmed nothing in §6's rules reads or writes any goal field.

---

## 12. MIGRATION STRATEGY

This is an additive change with no destructive step, staged as follows:

**Phase 1 — Extraction (no behavior change).** Extract `get_dashboard`'s existing inline aggregation math into `get_financial_context`, and have `get_dashboard` call it. This phase should ship and be verified *alone* first — `GET /dashboard`'s response must be byte-for-byte identical before and after, proven by re-running the exact assertions already captured in `FinancialsE2EValidationReport.md`'s four journeys. This phase carries zero product-visible change and de-risks every phase after it.

**Phase 2 — New rule addition.** Add `_financial_health_recommendations` and wire it into `get_family_recommendations`, additive to the existing two sources. Ship behind no flag — this is the direct fix for Finding 1, and per this codebase's own established pattern (recommendations are always computed fresh, never gated), there is no "old" persisted state to migrate away from.

**Phase 3 (optional, not required by this design) — Dashboard/Recommendations rule consolidation.** Move the `low_savings_rate` threshold to the shared location described in §7, so `_generate_suggestions` and `_financial_health_recommendations` both read one constant. This should be its own small, isolated change, verified by confirming `GET /dashboard`'s `suggestions` array is unchanged for every account whose savings rate doesn't cross the threshold.

**No database migration is required anywhere in this design.** No new table, no new column, no change to `income_sources`/`expenses`/`assets`/`liabilities`. The dead `Recommendation`/`RecommendationCitation` tables (§2) are neither touched nor required — reviving them is explicitly out of scope; if a future team wants recommendation history/audit trail, that is a separate design decision, not a prerequisite for closing Finding 1.

---

## 13. BACKWARD COMPATIBILITY

- **`GET /dashboard` response shape: unchanged.** Phase 1 is a pure refactor; every field name, type, and value stays identical, verified by the existing validation report's exact assertions.
- **`GET /reports/summary`: unchanged**, since it only ever reads `get_dashboard`'s output, which does not change.
- **`GET /family/recommendations` response shape: additive only.** Existing consumers reading `recommendations: FamilyRecommendation[]` continue to work unmodified — they simply may now see additional array entries. Any frontend code that renders recommendations generically (per-item, keyed by `id`/`recommendation_type`, not by a hardcoded `source` allowlist) requires no change at all.
- **One real compatibility risk to flag explicitly:** if any frontend code pattern-matches on `RecommendationSource` exhaustively (e.g., a TypeScript `switch` with no `default` case, or a lookup object indexed only by `"insurance"` and `"schemes"`), adding the `"financial_health"` literal will either fail to compile (good — caught at build time) or silently render nothing for the new source (bad — caught by testing, see §14). This must be checked against the actual frontend recommendation-rendering code before Phase 2 ships; this design does not assume which case applies, since that is a frontend fact, not a backend design fact, and this document does not implement or inspect the frontend rendering path.
- **No breaking change to any of the four `PATCH /financials/*` endpoints** — this design is a pure consumer of their already-shipped output.

---

## 14. TESTING STRATEGY

**Unit tests (no database required, per §7's testability improvement):**
- `_financial_health_recommendations` against a hand-constructed `FinancialContext`, one test per rule in §6: a case that crosses the threshold, a case that does not, and a boundary case (exactly at the threshold — e.g., `debt_to_income_ratio` at exactly `0.36`, confirming the comparison operator's direction is correct and intentional).
- `get_financial_context`'s `debt_to_income_ratio` guarded against `monthly_income == 0` (must not raise a division error — should return a defined value, e.g. `0.0` or `None`, decided explicitly during implementation, not left to accident).

**Integration tests (real database, matching this project's existing `pytest` + `httpx` convention):**
- Regression test: an account with no income/expenses/assets/liabilities at all still returns a valid (empty-of-financial-health-recommendations) response — mirroring the existing empty-household-empty-response case already proven in the validation report's baseline.
- Regression test: an account with only insurance/scheme conditions present (no financial-health thresholds crossed) returns *exactly* the same `recommendations`/`conflicts` as before this change — proving Phase 2 is additive, not a behavior change to the existing two sources.
- One test per §6 rule, seeded via the real `PATCH` endpoints (reusing the exact seeding pattern already used in `FinancialsE2EValidationReport.md`), asserting the corresponding `recommendation_type` appears after crossing its threshold and does not appear before.
- Conflict-detection test: confirm a financial-health recommendation and an insurance/scheme recommendation sharing a subject but *different* `reference_code`s never produce a spurious conflict (protects §7 point 4's assumption with an actual test, not just an argument).

**End-to-end verification (matching the exact method already used in `FinancialsE2EValidationReport.md`):**
- Re-run all four of that report's journeys (income, expenses, assets, liabilities), this time additionally asserting `GET /family/recommendations` after each edit — closing the specific gap Finding 1 identified, with the same live-trace rigor already established as this project's standard for this class of claim.

**Explicit non-goal for testing:** this design does not require new Monte Carlo or goal-probability regression tests, since nothing in it touches the Calculation Context — the existing regression guard (`creating/editing/deleting any financial fact must never change a goal's stored probability`) remains the correct, sufficient test for that boundary and needs no new sibling test for this specific change.
