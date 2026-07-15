# RECOMMENDATION ENGINE V2 — ARCHITECTURE VALIDATION

**Role:** Technical Design Authority / Principal Software Architect
**Question being answered:** is `RecommendationEngineV2.md` safe to implement exactly as designed, tomorrow, with no further redesign?
**Method:** every conclusion below is backed by a fresh read of current source during this validation pass — not by re-trusting `RecommendationEngineV2.md`'s own claims about that source. Two concrete problems were found this way that the design document did not resolve (§1, §8) — both are fixable without redesigning the architecture, which is why the final verdict is what it is.

---

## VALIDATION ITEMS

### 1. Does `FinancialContext` duplicate existing logic?

**PASS — with one concrete gap the design must close before Phase 1.**

`FinancialContext` as designed is a genuine extraction, not a second implementation: every field except `debt_to_income_ratio` is copied verbatim from `planning_service.get_dashboard`'s existing computation (`backend/app/services/planning_service.py:160-171` — `total_assets`, `liquid_assets`, `invested_assets`, `total_liabilities`, `monthly_income`, `monthly_expenses`, `savings_rate`). No duplicate calculation exists in the design as written.

**The gap:** `get_dashboard` has a second branch the design's §3/§9 never mentions — `planning_service.py:174-191`:
```
if not assets and not liabilities:
    goal_total = sum(g.current_amount for g in active_goals)
    return DashboardResponse(net_worth=goal_total, ..., invested=goal_total, liabilities=0.0, ...)
```
When a user has zero asset and liability rows, `get_dashboard` reports `net_worth`/`invested` as the sum of goal `current_amount` fields instead of `0`/`0` — a deliberate fallback for accounts that predate this milestone's editable financials. If `get_financial_context` is extracted without this branch, it will disagree with `get_dashboard`'s own `net_worth`/`invested` for exactly this account state — reintroducing, in a smaller and specific form, the exact cross-page-disagreement class of bug `FinancialsE2EValidationReport.md` spent four journeys proving does not happen elsewhere. This does not invalidate the design's architecture; it is a correctness detail the extraction step must explicitly preserve. **Required before Phase 1 is marked done: `get_financial_context` must replicate this branch, and the Phase 1 verification test must include an account with zero assets/liabilities and at least one goal, asserting `FinancialContext.net_worth == get_dashboard's net_worth` for that specific state** — the design's existing Phase 1 test plan ("byte-for-byte identical") already would have caught this if it had enumerated this specific account shape; it should be named explicitly, not left implicit.

### 2. Can `planning_service`, `family_recommendations_service`, and `notification_service` consume the same `FinancialContext` without circular dependencies?

**PASS.**

Traced every import statement in the current dependency chain:
- `planning_service.py` imports only `app.config`, `app.models.financials`, `app.models.goal`, `app.models.user`, `app.schemas.simulation`, `app.services.monte_carlo` — **zero imports of any family/recommendation/notification service.**
- `family_recommendations_service.py` imports `family_insurance_service`, `scheme_eligibility_service` — neither of which imports `planning_service` (confirmed directly; `family_insurance_service.py` imports `family_service` and `scheme_eligibility_service.age_years`; `scheme_eligibility_service.py` imports only models).
- `notification_service.py` imports `family_insurance_service`, `family_service`, `scheme_eligibility_service` — same result, no path back to `planning_service`.
- `family_dashboard_service.py` (a fourth module, not named in the design but part of the same graph) imports `family_recommendations_service` — also confirmed to have no import of `planning_service`.

`planning_service` sits at the bottom of this graph today, imported by nothing above it. Adding `from app.services import planning_service` to `family_recommendations_service.py` and/or `notification_service.py` adds one new one-directional edge to an already-acyclic graph. There is no existing or newly-introduced path by which `planning_service` would ever import back into either of them. **No circular dependency is possible under this design as specified.**

### 3. Does `RecommendationEngineV2` preserve ADR-001 (financial facts must not trigger Monte Carlo recalculation)?

**PASS.**

ADR-001's exact decision text (`ArchitectureDecisionRecordBible.md`, ADR-001): *"Recalculate goal probability only when plan inputs change (Calculation Context fields). Dashboard/Reports become pure reads."* `CALCULATION_CONTEXT_FIELDS` is the literal, still-current frozenset in `planning_service.py:26-28`: `{"current_amount", "monthly_contribution", "target_date", "risk_profile", "target_amount"}` — no financial-facts field is or has ever been a member.

`RecommendationEngineV2.md`'s §6 rule table and §2 target architecture confirm every new rule reads only `FinancialContext` fields (income/expense/asset/liability aggregates) and never calls `calculate_goal_probability` or touches any `Goal` row. This was independently re-verified, not merely trusted: `family_recommendations_service.py` has zero references to `Goal` or `calculate_goal_probability` today, and the design adds no such reference. The existing test `test_calculation_lifecycle_untouched` (`backend/tests/test_family_recommendations.py:194`) already asserts a goal's probability is unaffected by calling `/family/recommendations`, and nothing in this design gives that test a reason to fail after Phase 2 ships — it should simply continue passing, unmodified.

### 4. Can Dashboard, Reports, Family Recommendations, Notifications, and a future AI Copilot all consume the same Recommendation Engine?

**CONDITIONAL PASS — proven for three surfaces today; the fourth and fifth are architecturally compatible but not yet real integrations.**

- **Dashboard** already has its own recommendation-shaped surface (`_generate_suggestions`, keyed off `savings_rate` and goal probability) — this is a *second* engine, not the one this design extends (see the design's own §1 root-cause analysis). The design does not merge them in Phase 2; §7's Phase 3 (optional) proposes sharing the one duplicated threshold constant. This is correctly scoped as optional, not required — confirmed no test or consumer depends on the two being unified.
- **Reports** consumes Dashboard's output only (`reports.py` calls `get_dashboard()` directly) — it has no direct relationship to `family_recommendations_service` at all, today or in this design. Reports "consuming the Recommendation Engine" is not something this design does or needs to do.
- **Family Recommendations** is the actual, direct target of this design — confirmed compatible via items 1-3 above.
- **Notifications** is architecturally compatible (item 2 proves it can import `planning_service` with no cycle) but the design correctly marks this **out of scope** for this change (§4's table: "not in this design's scope — flagged as a candidate follow-up"). No notification fact-collector for financial-health thresholds exists today; the design does not claim one does.
- **AI Copilot**: confirmed via direct source read that `backend/app/routers/copilot.py` contains zero references to recommendations, `FinancialContext`, or any of the services in this design. "Future AI Copilot can consume the Recommendation Engine" is an architectural compatibility claim, not a working integration — it is true only in the sense that nothing about this design would prevent it, and Engineering Constitution Rule 10 ("the AI Advisor computes nothing; it narrates what was already computed") is fully consistent with a future Copilot reading already-computed `FamilyRecommendation` objects rather than generating its own. This item should be read as "not blocked," not "verified working," since there is nothing built yet to verify.

### 5. Should `Recommendation`/`RecommendationCitation` become active, or remain unused?

**REMAIN UNUSED — this is not this validation's judgment call, it is already a formally accepted decision.**

`ArchitectureDecisionRecordBible.md`'s ADR-005 ("Recommendations Computed Live, Never Persisted") states directly: *"Compute every recommendation fresh on every read; the `recommendations`/`recommendation_citations` tables remain unused."* Its own Alternatives section records that persisting to this table "as originally designed" was implicitly rejected, citing ADR-001/PCA-3 as the reason. This is Status: Accepted & Implemented, not a proposal.

`RecommendationEngineV2.md`'s §2 and §12 independently reach the identical conclusion (reviving the table is "explicitly out of scope... a separate design decision, not a prerequisite") without citing ADR-005 by number — the two documents agree, but the design document should be read as *consistent with* an existing formal decision, not as the origin of this conclusion. There is also a live regression test protecting this exact property today: `test_nothing_is_persisted` (`test_family_recommendations.py:182`) queries the `Recommendation` table directly and asserts it is empty after calling the endpoint — this test must continue to pass after Phase 2, and nothing in the design's `_financial_health_recommendations` function writes to that table, so it will.

### 6. Is there a stale-data window? Must a cache become required?

**PASS — no stale-data window, no cache.**

Every read path in the design (`get_financial_context`, called fresh inside `get_family_recommendations` on every request) re-queries `income_sources`/`expenses`/`assets`/`liabilities` with no memoization, matching `get_dashboard`'s existing, already-proven-live pattern exactly. This is the same property `FinancialsE2EValidationReport.md` verified end-to-end for Dashboard and Reports across four separate edit journeys with zero exceptions. The design's own §10 explicitly considered and rejected an event-driven/cached alternative, citing the exact same lineage this validation independently found: ADR-001 → ADR-005 → (per the ADR Bible's own summary table) reapplied to Insurance, Schemes, Family Recommendations, and Notifications — four independent domains already converged on "recompute live," and this design is a fifth application of the same rule to the same codebase, not a new philosophy.

### 7. Verify every recommendation rule (Income, Expenses, Assets, Liabilities, Savings Rate, Debt Ratio, Net Worth)

| Rule | Inputs | Outputs | Dependencies | `confidence_score` | Reasoning quality |
|---|---|---|---|---|---|
| `income_concentration` | count of active `income_sources` rows | one `FamilyRecommendation` if count == 1 | `FinancialContext` only | 1.0 — correct; this is a count, not an estimate | `why` text given in design is adequate; `what_information_is_missing` not specified in the design's table for this rule — **minor gap, see Minor Improvements** |
| `expense_review_prompt` | `expenses.updated_at` (max), 180-day threshold | one recommendation if stale | `FinancialContext` **does not currently carry a raw `updated_at`/timestamp field** per the design's own §3 field list | 1.0 | **Gap:** this rule's trigger condition needs a value `FinancialContext` as specified does not contain — either `FinancialContext` must be extended with a `max(expenses.updated_at)` field, or this rule must query `expenses` directly (breaking the "one shared context object" principle the rest of the design follows). The design does not resolve this; flagged as a Critical Blocker below, not a redesign — it is a one-field addition to an already-planned data object |
| `low_liquidity` | `liquid_assets`, `monthly_expenses` | one recommendation if `liquid_assets < monthly_expenses × 3` | `FinancialContext` only | 1.0 | Sound; both inputs already exist in `FinancialContext` as designed |
| `high_interest_debt` | per-liability `interest_rate`, `balance` | one recommendation per qualifying liability | **Requires per-liability data, not an aggregate** — `FinancialContext` as designed carries only `total_liabilities` (a sum), not the individual `Liability` rows | 1.0 | **Gap, same shape as the expense-staleness gap:** this rule cannot be evaluated from the aggregate `FinancialContext` alone; it needs the raw `list[Liability]` (which `get_dashboard` already fetches internally before summing it — the design should pass that list through, not just the sum) |
| `low_savings_rate` | `savings_rate` | reuses the existing Dashboard rule, per §7's explicit "extract, don't duplicate" instruction | `FinancialContext` only | 1.0 | Correctly scoped — this is the one rule the design explicitly says not to reimplement, and that instruction is sound and specific enough to follow without further design work |
| `negative_net_worth_trend` | `net_worth` | one recommendation if `< 0` | `FinancialContext` only (once item 1's fallback-branch gap is closed) | 1.0 | Sound, contingent on item 1's fix |
| `high_debt_to_income` | `total_liabilities`, `monthly_income` (annualized) | one recommendation if ratio `> 0.36` | `FinancialContext` only | 1.0 | Sound; the design also correctly specifies a zero-income guard (§11's testing strategy names this explicitly) |

**Net finding for item 7:** three of seven rules (`low_liquidity`, `low_savings_rate`, `negative_net_worth_trend`, `high_debt_to_income` — four, not three) are fully specifiable from the `FinancialContext` shape as designed. **Two rules (`expense_review_prompt`, `high_interest_debt`) require data the designed `FinancialContext` does not carry** — a per-row timestamp and a per-row liability list, respectively, not just aggregates. This is a scope gap in §6's data model, not a flaw in the rule logic itself, and is listed as a Critical Blocker below because implementing these two rules exactly as specified is not possible against the `FinancialContext` shape exactly as specified — the two documents are inconsistent with each other on this one point.

### 8. Backward compatibility — will any existing endpoint, response, or frontend break?

**FAIL as specified — one concrete, reproducible frontend crash risk found; not present in the design document's own analysis.**

- `GET /dashboard`, `GET /reports/summary`: confirmed unchanged per items 1-3 (Phase 1 is a pure extraction).
- `GET /family/recommendations` response schema: additive, as the design states — confirmed no existing field is removed or retyped.
- **The concrete break:** `code/src/routes/app.family.recommendations.tsx:100` defines `const SOURCE_ICON = { insurance: ShieldCheck, schemes: Landmark } as const;` and line 103 does `const Icon = SOURCE_ICON[rec.source];` with **no fallback and no null-check**, immediately rendering `<Icon .../>` on the next line. `code/src/lib/api.ts:294` independently declares `export type RecommendationSource = "insurance" | "schemes";` — a closed, hand-maintained union with no automatic sync to the backend schema. The moment the backend returns one recommendation with `source: "financial_health"` (which Phase 2, as designed, will do), `SOURCE_ICON["financial_health"]` evaluates to `undefined` at runtime, and React throws rendering `<undefined />` — **this crashes the entire Family Recommendations page**, not just the one card, since `data.recommendations.map(...)` renders all cards in one component tree with no error boundary visible in this file. The design document's own §13 flagged this exact class of risk as hypothetical ("if any frontend code pattern-matches... this must be checked... this document does not assume which case applies") — this validation checked it, and confirms the risk is real, specific, and will reproduce on first use.
- **This is not a backend design flaw** — the backend-side additive change (§5, one new literal value) is exactly correct and exactly as small as the design claims. The gap is that Phase 2, as currently scoped in §12 ("Ship behind no flag... direct fix for Finding 1"), does not include the two-line frontend change required to make that backend change safe to ship. **Phase 2 must be redefined to include: (a) adding `"financial_health"` to `RecommendationSource` in `api.ts`, and (b) adding a corresponding entry (or a defensive default) to `SOURCE_ICON`.** This is a small, mechanical, non-architectural fix — it does not require redesigning anything in `RecommendationEngineV2.md` — but it is a required correction to the Phase 2 scope, not an optional nicety.

### 9. Are Phase A (extraction) → B (shared calculations) → C (new rules) → D (validation) the correct order?

**PASS, with the two gaps above folded into the existing phases, not new phases.**

The order is correct and should not change:
- Extracting first (Phase A/1) and verifying byte-identical output before any new rule exists is the right sequencing discipline — it isolates "did the refactor break anything" from "does the new rule work," which is exactly how `FinancialsE2EValidationReport.md`'s own methodology (one variable changed at a time, checked before moving on) already demonstrated value in this codebase.
- Item 1's fallback-branch fix belongs inside Phase A (it is a correctness requirement of the extraction itself, not a new feature).
- Item 7's two data-shape gaps (per-liability list, expense staleness timestamp) belong inside Phase B ("shared calculations") — extending what `FinancialContext` carries is exactly what that phase is for; it does not require inserting a new phase.
- Item 8's frontend fix belongs inside Phase C ("new recommendation rules"), since the two are causally linked — the frontend change is only needed *because* Phase C introduces a new `source` value; shipping Phase C without it is the actual bug, not a separate concern to schedule later.
- Phase D (validation) should explicitly re-run `FinancialsE2EValidationReport.md`'s four journeys with `GET /family/recommendations` added as a fifth checked surface at each step — this is already what the design's own §14 proposes; this validation confirms that plan is sufficient and does not need expansion.

**No phase needs to be reordered, split, or added.** The four gaps found in this validation are corrections *within* the existing four phases, not evidence the phase structure itself is wrong.

### 10. Hidden risks

- **Circular dependencies:** checked and ruled out (item 2).
- **Performance regressions:** the design's own §11 estimate (four additional indexed, single-user-scoped queries, matching `get_dashboard`'s already-proven-cheap pattern) holds up against the actual query code in `planning_service.py:138-158` — no new query shape is introduced, confirmed by direct comparison.
- **Incorrect recommendation ordering:** **not addressed by the design at all.** `family_recommendations_service.get_family_recommendations` returns `[*insurance, *scheme, *financial_health]` — plain list concatenation, no explicit ordering/priority field anywhere in `FamilyRecommendation`. Today, with two sources, this is invisible; with three, a user could see a `low_liquidity` recommendation listed before a materially more urgent `high_debt_to_income` one, with no signal to the frontend about which matters more. This is a real gap, but it is **pre-existing** (the current two-source list has no ordering logic either — confirmed, no `priority`/`severity` field exists in `FamilyRecommendation` today, unlike `DashboardSuggestion`, which does have a `severity` field). This design neither introduces nor fixes this gap; flagged as a Minor Improvement, not a blocker, since it is not a regression this design causes.
- **Duplicate recommendations:** not a risk — each new rule in §6 has a distinct `recommendation_type` string and fires at most once per request (none are per-item loops that could double-fire, unlike, say, the scheme engine's per-member loop, which is a different, already-tested pattern).
- **Conflicting recommendation sources:** covered by existing `_detect_conflicts`, confirmed generic over any `source` value (item 3's conflict-detection tests in `TestConflictDetection` construct `FamilyRecommendation` objects with an arbitrary `source: str`, not a closed enum, at the Python level — the backend has no closed-set assumption to break here, only the frontend does, per item 8).
- **Missing recommendation priority:** same finding as "incorrect ordering" above — pre-existing, not introduced, worth fixing but not a blocker for this specific change.
- **Missing explanation text:** checked against §6's table — every rule specifies a `why` example; the design's own text acknowledges `what_information_was_used`/`what_information_is_missing` must be filled "honestly per rule" without giving all seven concrete lists. This is a documentation completeness gap in the design, not an architectural one — folded into Minor Improvements.

---

## ARCHITECTURE SCORE: 7/10

The core architectural decisions — extract-don't-duplicate, no persistence, no event bus, additive schema, correct phase ordering, and the specific choice of which services should and should not consume `FinancialContext` — are all sound and each independently verified against real source and against a formally accepted ADR (ADR-005) that the design's authors evidently were not even aware existed, yet reached the identical conclusion anyway. The score is not higher because this validation found one reproducible frontend crash (item 8) and one internal inconsistency between the design's own data model and its own rule table (item 7) — both real, both fixable without touching the architecture, neither requiring a redesign.

## MIGRATION RISK: LOW

No schema migration, no data backfill, no breaking API change to any endpoint's existing fields. The two required fixes (extend `FinancialContext` with two more fields; add one frontend union member and icon mapping) are both small, additive, and testable in isolation before Phase C ships.

## DEPENDENCY GRAPH (confirmed against actual imports, not the design's own diagram)

```
app.models.financials (income_sources, expenses, assets, liabilities)
        │
        ▼
planning_service.py  ── imports: config, models.financials, models.goal, models.user,
   │                                schemas.simulation, services.monte_carlo
   │                     imported by: NOTHING today (confirmed — leaf-ward)
   │
   ├──▶ get_dashboard()  (existing, Phase A refactors its internals only)
   │        └──▶ reports.py (existing, unchanged)
   │
   └──▶ get_financial_context()  [NEW — Phase A/B]
              │
              ├──▶ family_recommendations_service.py  [NEW import edge, Phase C]
              │        (already imports family_insurance_service, scheme_eligibility_service —
              │         neither imports planning_service — no cycle)
              │
              └──▶ notification_service.py  [not built in this design; import-safe if ever added]
                       (already imports family_insurance_service, family_service,
                        scheme_eligibility_service — same no-cycle guarantee)
```

## IMPLEMENTATION PHASES (validated order, corrected scope per items 1/7/8)

| Phase | Original scope (per `RecommendationEngineV2.md`) | Correction required by this validation |
|---|---|---|
| A — Extraction | Extract `get_dashboard`'s math into `get_financial_context` | **Must explicitly preserve the zero-assets/zero-liabilities fallback branch (item 1)**; verification test must name this account shape specifically |
| B — Shared calculations | Add `debt_to_income_ratio` | **Must also add: a per-liability list (or equivalent) for `high_interest_debt`, and an expense-staleness timestamp for `expense_review_prompt` (item 7)** — both are data-shape additions to `FinancialContext`, not new architecture |
| C — New recommendation rules | Add `_financial_health_recommendations`, wire into `get_family_recommendations` | **Must ship together with the two-line frontend fix in `api.ts`/`app.family.recommendations.tsx` (item 8)** — Phase C is not complete, by this validation's definition, until that frontend change ships in the same release |
| D — Validation | Re-run `FinancialsE2EValidationReport.md`'s four journeys with Recommendations checked | Unchanged — already correctly scoped |

---

## CRITICAL BLOCKERS (must be resolved before Phase C ships; none require redesigning the architecture)

1. **Frontend crash risk (item 8).** `SOURCE_ICON`/`RecommendationSource` in the frontend do not account for a third source value and will throw at render time the first time a `financial_health` recommendation is returned. Fix: two small, additive frontend changes, shipped in the same phase as the backend change that introduces the new source value — not after.
2. **`FinancialContext` data-shape gap (item 7).** As designed, `FinancialContext` cannot support `expense_review_prompt` (needs a timestamp) or `high_interest_debt` (needs the per-liability list, not just its sum). Fix: extend `FinancialContext`'s field list during Phase B to include both — a data-completeness correction, not an architecture change.
3. **Fallback-branch omission (item 1).** `get_financial_context` must replicate `get_dashboard`'s zero-assets/zero-liabilities special case, or `net_worth`/`invested` will silently disagree between Dashboard and the Recommendation Engine for that specific, real account state. Fix: name this case explicitly in Phase A's own verification test.

## MINOR IMPROVEMENTS (do not block implementation)

- Add a `priority`/`severity`-equivalent field to `FamilyRecommendation` at some point — not required by this change, but the absence becomes more noticeable at three sources than it was at two. Pre-existing gap, not introduced by this design.
- Fill in the complete `what_information_was_used`/`what_information_is_missing` lists for all seven rules in the design document itself, matching the level of detail §6 already gives for `high_debt_to_income`, so an implementing engineer has zero remaining judgment calls (consistent with this whole project's stated bar for implementation-ready specifications).
- Consider, as a follow-up and not part of this change, whether `notification_service.py` should eventually gain a financial-health fact-collector — architecturally unblocked (item 2/4) but deliberately out of scope here, and should stay that way unless explicitly requested.

---

## GO / NO-GO DECISION

### **GO WITH MINOR CHANGES**

The architecture in `RecommendationEngineV2.md` is sound, consistent with this codebase's own strongest and most consistently-reapplied convention (compute live, never persist — ADR-001 through ADR-005, now a fifth application), introduces no circular dependency, preserves ADR-001 exactly, and correctly leaves the dead `Recommendation`/`RecommendationCitation` tables alone per an existing, formally accepted decision the design's authors arrived at independently. It does not require another architecture-level design pass.

It is not a clean GO because three concrete, evidenced gaps were found — a frontend crash risk, a data-shape gap between the design's own `FinancialContext` and its own rule table, and a fallback-branch omission — none of which change the architecture, all three of which are small, additive, and fully specified above. Implementation should proceed directly against the phase table in this document (which folds all three corrections into Phases A-C, adding no new phase), without returning to the design stage.
