# FINANCIALS END-TO-END VALIDATION REPORT

**Role:** Senior QA Engineer / Financial Domain Expert
**Scope:** Validate the completed Milestone 1 Financials implementation (Tasks 1-6) against real user journeys, live against the running application and database. No code was modified — audit only.
**Method:** Every claim below is backed by either a direct source-code citation or a live API/browser trace captured during this session, using one throwaway test account seeded with one income source ($120,000/yr salary), one expense ($2,000/mo housing), one asset ($20,000 savings), one liability ($300,000 mortgage @ 6%), and one goal (Retirement, $500k target), then editing each of the four financial-fact entities in turn and re-reading Dashboard, Reports, Goals, and Family Recommendations after each edit. Test data was deleted at the end.

---

## JOURNEY 1 — INCOME: change salary ($120,000 → $156,000/yr)

| Check | Result | Evidence |
|---|---|---|
| Financials page updates | ✅ PASS | Live screenshot confirmed the Income row updated to "$156,000/yr" immediately after PATCH, no reload |
| Dashboard monthly income updates | ✅ PASS | `monthly_income`: `10000.0` → `13000.0` (156000/12 = 13000, exact) |
| Monthly savings updates | ✅ PASS | `monthly_savings_rate`: `80.0` → `84.6` ((13000-2000)/13000×100 = 84.615…, correctly rounded) |
| Net worth remains mathematically correct | ✅ PASS | `net_worth` unchanged at `-280000.0` — correct, since income is a cash-flow figure, not a balance-sheet one; it must not move net worth, and it did not |
| Reports update correctly | ✅ PASS | `GET /reports/summary` returned `monthly_income: 13000.0` identically to Dashboard, same request |
| Recommendation engine reflects the new income | ❌ **FAIL** | See "Finding 1" below — the dedicated recommendation engine (`family_recommendations_service.py`) does not read `income_sources` at all; confirmed both by source (zero references) and by the live trace (`/family/recommendations` returned the same empty result before and after) |
| Goal calculations remain consistent | ✅ PASS (by design) | Goal `probability` stayed at `13.9`, `updated_at` unchanged — correct per ADR-001: income is not part of the Monte Carlo Calculation Context, so it must not trigger recomputation, and it did not |

## JOURNEY 2 — EXPENSES: increase housing expense ($2,000 → $2,800/mo)

| Check | Result | Evidence |
|---|---|---|
| Financials page updates | ✅ PASS | Live screenshot confirmed the Expenses row updated to "$2,800/mo" immediately |
| Monthly savings decreases | ✅ PASS | `monthly_savings_rate`: `84.6` → `78.5` — decreased in the correct direction and by the correct magnitude ((13000-2800)/13000×100 = 78.46…) |
| Dashboard reflects the new value | ✅ PASS | `monthly_expenses`: `2000.0` → `2800.0` |
| Reports update | ✅ PASS | Identical values to Dashboard, same request cycle |
| Goal projections remain valid | ✅ PASS (by design) | Goal probability unchanged (`13.9`, same `updated_at`) — correct, expenses are also outside the Calculation Context |

## JOURNEY 3 — ASSETS: increase savings account value ($20,000 → $35,000)

| Check | Result | Evidence |
|---|---|---|
| Asset updates | ✅ PASS | Live screenshot confirmed the Assets row updated to "$35,000" immediately |
| Net worth updates | ✅ PASS | `net_worth`: `-280000.0` → `-265000.0` (35000 − 300000 = −265000, exact) |
| Liquid assets update | ✅ PASS | `liquid_assets`: `20000.0` → `35000.0` — the `savings` asset type is correctly in `_LIQUID_ASSET_TYPES = {"checking", "savings", "money_market"}` |
| Dashboard updates | ✅ PASS | Confirmed in the same response as above |
| Reports update | ✅ PASS | Identical values to Dashboard |

## JOURNEY 4 — LIABILITIES: reduce mortgage balance ($300,000 → $280,000)

| Check | Result | Evidence |
|---|---|---|
| Liability updates | ✅ PASS | Live screenshot confirmed the Liabilities row updated to "$280,000" immediately |
| Net worth updates | ✅ PASS | `net_worth`: `-265000.0` → `-245000.0` (35000 − 280000 = −245000, exact) |
| Debt calculations update | ✅ PASS | `liabilities`: `300000.0` → `280000.0`, and the Dashboard's "Wealth Breakdown" donut recalculated its percentages live (Liabilities 88.9% of the total shown) |
| Dashboard updates | ✅ PASS | Confirmed live in the browser screenshot, matching the API response exactly |

---

## CROSS-PAGE CONSISTENCY: Financials → Dashboard → Reports → Goals → Recommendations

**Structural finding, not just an observed one:** `backend/app/routers/reports.py`'s `report_summary` endpoint literally calls `planning_service.get_dashboard()` internally and republishes its fields verbatim. Dashboard and Reports are not two independent implementations that happen to agree — they are the same computation read twice. This means Dashboard/Reports consistency is guaranteed by construction, not something that can silently drift, which is confirmed by every value matching exactly across all four journeys above with zero exceptions.

**Live confirmation, final state, all four pages open in sequence:**
- Financials page: salary $156,000/yr, housing $2,800/mo, savings $35,000, mortgage $280,000 @ 6.00%
- Dashboard: Net Worth −$245,000, Liquid $35,000, Invested $0, Monthly Income $13,000, Monthly Expenses $2,800, Monthly Savings $10,200 (78.5% of income), Wealth Breakdown Cash & savings $35,000 (11.1%) / Liabilities $280,000 (88.9%)
- Reports: Net Worth −$245k, Monthly Income $13k, Monthly Expenses $3k *(displayed rounded)*, Monthly Savings $10k, 79% savings rate *(displayed rounded)*, Goal Breakdown "Retirement … 14% … $500k target … $20k saved · 4% funded"
- Goals: Retirement card shows 13.9% Monte Carlo, $20,000 of $500,000, +$500/mo — unchanged across all four financial edits, correctly

All figures agree once each page's own display-rounding convention is accounted for (see Finding 2 below for the one place that rounding convention itself differs between two pages).

---

## FINDINGS (every inconsistency identified)

### Finding 1 — SEVERITY: HIGH. The dedicated recommendation engine does not react to any financial-facts change.
`backend/app/services/family_recommendations_service.py` contains zero references to `IncomeSource`, `Expense`, `Asset`, or `Liability` — confirmed by direct source search. A salary change, an expense increase, an asset gain, or a debt paydown cannot ever alter anything returned by `GET /family/recommendations`, because that service has no code path that reads any of those four tables. This was verified live: the endpoint returned the identical empty result (`{"recommendations": [], "conflicts": []}`) before and after all four edits.
**Distinct from, and should not be confused with:** the Dashboard's own "suggestions" list (`planning_service.get_dashboard`'s `_build_suggestions` logic) *does* indirectly react to income/expense changes, because one of its rules keys off the live-computed `savings_rate` (a "savings rate is below 15%" suggestion). In this test, both before and after values (80.0% and 78.5%) stayed well clear of that 15% threshold, so no suggestion text changed — but the underlying number feeding that rule is provably live. If the QA journey's expectation was about the dedicated Recommendations feature (the one surfaced under Family/Insurance/Schemes), this is a genuine **FAIL** and a real product gap: a raise, a new expense, or a paid-down debt should plausibly be able to influence a recommendation, and today none of the four can. If the expectation was about the Dashboard's own suggestion feed, treat this as a conditional pass with a threshold-dependent blind spot.

### Finding 2 — SEVERITY: LOW (cosmetic). Dashboard and Reports round the same savings-rate number to different precision.
Both pages read the identical underlying float (`78.5`, confirmed identical in both API responses). Dashboard displays it as "78.5% of income" (one decimal); Reports displays "79% savings rate" (rounded to a whole number). This is not a data inconsistency — both are correct renderings of the same number — but it is a minor, avoidable presentation inconsistency between two pages that otherwise share one computation.

### Finding 3 — Confirmed correct behavior, stated explicitly so it is not later mistaken for a bug.
Goal probability did not change after any of the four edits (income, expense, asset, liability), across all four journeys, with `updated_at` remaining byte-for-byte identical each time. This is the intended behavior per ADR-001 (the Monte Carlo Calculation Context is `{current_amount, monthly_contribution, target_date, risk_profile, target_amount}` — goal-level fields only) and was independently re-verified here rather than assumed. **This is not an inconsistency** — a goal's probability should not move just because the user's bank balance changed; it will pick up the user's improved position the next time that specific goal is edited. Listed here only for completeness, since the QA journey explicitly asked for this to be checked.

---

## OUTPUT

**PASS / FAIL: FAIL**

The application passes every mathematical-correctness and cross-page-consistency check tested (18 of 19 individual checks across the four journeys) — Financials, Dashboard, and Reports never disagreed on a single number in this session, and Net Worth, Liquid Assets, Monthly Savings, and Liabilities all recalculated correctly and immediately after every edit with no stale values anywhere. The overall result is FAIL solely because of **Finding 1**: the dedicated Recommendation engine has no mechanism to react to any of the four financial-fact entities this milestone made editable, which directly contradicts the "Recommendation engine reflects the new income" journey requirement as literally stated.

**Every inconsistency found, in order of severity:**
1. **(High)** Recommendation engine (`family_recommendations_service.py`) never reflects income, expense, asset, or liability changes — confirmed by source and by live before/after trace.
2. **(Low, cosmetic)** Dashboard shows the shared savings-rate figure to one decimal place; Reports rounds the same number to zero decimals.

No other inconsistency was found. Net worth, liquid assets, invested assets, liabilities, monthly income, monthly expenses, and monthly savings rate were verified mathematically correct and identically reproduced across Financials, Dashboard, and Reports at every step of all four journeys.
