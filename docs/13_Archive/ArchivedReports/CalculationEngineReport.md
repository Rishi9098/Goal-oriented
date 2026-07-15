# Calculation Engine Documentation

**Date:** 2026-07-06
**Method:** The formulas below (FV, PV, SIP, EMI, ratios) are standard financial mathematics — universal, not jurisdiction-specific facts subject to a budget cycle, so no web verification was needed for the math itself (unlike Phase 1's scheme rates). Tax-estimation logic explicitly reuses the verified Phase 1 figures. Two calculations (**Goal Prioritization**, **Decumulation**) are marked **NEW** — they don't exist in Northstar today and were identified as gaps in Phase 4's persona research, not in the current codebase.

Existing calculations (Monte Carlo, Optimizer, Plan Health, Dashboard Aggregates) are documented as **CURRENT** and cross-referenced to their real file location (`ProjectDiscoveryReport.md` §6).

---

## 1. Future Value (FV) — lump sum

| | |
|---|---|
| **Formula** | `FV = PV × (1 + r)^n` |
| **Inputs** | `PV` (present value), `r` (period rate), `n` (number of periods) |
| **Outputs** | `FV` (future value) |
| **Dependencies** | None — foundational |
| **Edge cases** | `r = 0` → `FV = PV`; negative `PV` (a liability growing) is valid and should not be rejected |
| **Validation** | `n >= 0`; `r > -1` (a rate of exactly -100% or below is not economically meaningful) |
| **Complexity** | O(1) |

```
def future_value(pv: float, r: float, n: float) -> float:
    return pv * (1 + r) ** n
```

## 2. Present Value (PV) — discounting

| | |
|---|---|
| **Formula** | `PV = FV / (1 + r)^n` |
| **Inputs** | `FV`, `r`, `n` |
| **Dependencies** | Inverse of #1 |
| **Edge cases** | `r = -1` → division by zero, must be rejected at validation, not caught at runtime |
| **Used for** | Converting a future goal's inflated cost back to "how much do I need today" |
| **Complexity** | O(1) |

## 3. SIP Future Value (systematic investment / annuity-due)

| | |
|---|---|
| **Formula** | `FV = PMT × [((1+r)^n − 1) / r] × (1+r)` (annuity-due, since SIP debits typically occur at the start of the period) |
| **Inputs** | `PMT` (periodic contribution), `r` (period rate), `n` (periods) |
| **Dependencies** | None |
| **Edge cases** | `r = 0` → `FV = PMT × n` (must special-case to avoid division by zero) |
| **Validation** | `PMT >= 0`; this is exactly the calculation the current `optimizer.py`'s contribution-increase suggestions are implicitly reasoning about, though today it's approximated via repeated Monte Carlo re-runs rather than this closed-form shortcut — worth noting as a potential fast-path optimization for the optimizer's "quick estimate before running a full simulation" step |
| **Complexity** | O(1) |

## 4. EMI (loan payment)

| | |
|---|---|
| **Formula** | `EMI = P × r × (1+r)^n / [(1+r)^n − 1]` where `P` = principal, `r` = monthly rate, `n` = number of months |
| **Inputs** | Loan principal, annual interest rate, tenure in months |
| **Edge cases** | `r = 0` → `EMI = P / n` |
| **Used for** | The `liabilities.monthly_payment` field already exists in the schema (Project Discovery) but there's no verification-of-consistency check between a liability's stored `balance`/`interest_rate`/`monthly_payment` triple — this formula is what such a validation would use: does the stored EMI actually amortize the stated balance at the stated rate? Currently unenforced. |
| **Complexity** | O(1) |

## 5. Net Worth

| | |
|---|---|
| **Formula** | `Net Worth = Σ(assets.current_value) − Σ(liabilities.balance)` |
| **Status** | **CURRENT** — `planning_service.get_dashboard()`, straight sums, confirmed in Project Discovery §6 |
| **Dependencies** | Assets, liabilities tables |
| **Edge cases** | Already handles negative net worth correctly on the dashboard (confirmed in the prior QA session); the Reports-page formatting bug for negative values was already found and fixed in an earlier session |
| **Household extension (new, Phase 5)** | `Household Net Worth = Σ over all household_members' individual net worths` — a pure aggregation with no new math, but requires the join through `household_members` designed in `DatabaseDesignReport.md` |

## 6. Monthly Cash Flow

| | |
|---|---|
| **Formula** | `Cash Flow = Σ(income_sources.annual_amount / 12) − Σ(expenses.monthly_amount)` |
| **Status** | **CURRENT** — confirmed in dashboard/reports routers |
| **Gap identified in Phase 4** | This is a *current-month snapshot*, not a forward projection. Monarch Money's forward cash-flow projection (Competitor Analysis) is a genuinely different calculation: project each recurring income/expense forward N months and produce a running balance, which requires each `income_source`/`expense` to carry a frequency/recurrence field the current schema's flat annual/monthly amounts don't fully capture for irregular items (e.g., an annual insurance premium due in a specific month, not smoothed) |

## 7. Savings Rate

| | |
|---|---|
| **Formula** | `Savings Rate % = (Monthly Income − Monthly Expenses) / Monthly Income × 100` |
| **Status** | **CURRENT** |
| **Edge cases** | `Monthly Income = 0` → undefined, must return `null`/`N/A`, not divide-by-zero crash or a misleading 0% |

## 8. Debt-to-Income Ratio

| | |
|---|---|
| **Formula** | `DTI % = Σ(liabilities.monthly_payment) / Monthly Income × 100` |
| **Status** | Formula exists implicitly in financial planning best practice but **not currently computed anywhere in Northstar** — the schema has all the data (`liabilities.monthly_payment`, income) but no router/service surfaces this ratio today |
| **Planning use** | Standard thresholds (not verified this pass, common industry convention): <36% healthy, 36-43% caution, >43% high-risk — flagged as needing a primary-source check (RBI lending guidelines or similar) before being surfaced as an authoritative threshold to users, consistent with this whole engagement's "verify before stating as fact" standard |

## 9. Emergency Fund Adequacy

| | |
|---|---|
| **Formula** | `Months Covered = Liquid Assets / Monthly Expenses`; adequacy threshold commonly cited as 3-6 months (freelancers/business owners per Phase 4 arguably need the higher end given income volatility) |
| **Status** | **CURRENT**, partially — `planning_service.py`'s suggestion-generation logic references an emergency-fund concept in its dashboard suggestions (per Project Discovery's calculation inventory), but the exact months-covered computation and persona-specific threshold (3 vs 6 months) is not confirmed as explicit in the current code — flagged for direct code confirmation before Implementation phase |

## 10. Inflation Adjustment

| | |
|---|---|
| **Formula** | `Real Value = Nominal Value / (1 + inflation_rate)^n`; equivalently, future cost `= Current Cost × (1 + inflation_rate)^n` |
| **Status** | **CURRENT**, but **single-rate only** — `FinancialAssumptions.inflation_rate` is one flat rate applied everywhere |
| **Gap identified in Phase 3** | Medical cost inflation (~11.5%/year, verified) runs roughly 2.5-3x general inflation (~4-5%). A single inflation rate systematically understates any medical/healthcare-linked goal. **Recommendation:** add a `goal_category`-specific inflation override (education and medical categories in particular need their own rate, general savings goals can keep using the flat rate) rather than a wholesale multi-rate redesign |

## 11. Retirement Corpus Required

| | |
|---|---|
| **Formula** | `Corpus = Annual Post-Retirement Expense (inflation-adjusted to retirement date) × Years in Retirement` (simple annuity-certain approximation), or more precisely, the corpus that, drawn down at a sustainable withdrawal rate (see #19, Decumulation) across the expected retirement horizon, reaches zero (or a bequest target) at life expectancy |
| **Status** | Not an explicit standalone calculation today — retirement is currently just "a goal like any other" with a `target_amount` the user enters manually, run through the same Monte Carlo engine as any goal. **This works for the accumulation phase** but doesn't independently *derive* what that target amount should be from the user's actual expected retirement expenses — the user must already know their own number. |
| **Recommendation** | A dedicated retirement-corpus calculator that takes current expenses + retirement age + life-expectancy assumption + category-specific inflation (see #10) and *proposes* a target_amount, rather than requiring the user to already have one |

## 12. Education Planning

| | |
|---|---|
| **Formula** | Same shape as Retirement Corpus (#11): `Future Cost = Current Education Cost × (1 + education_inflation_rate)^years_to_goal`, then run through the standard goal-probability Monte Carlo |
| **Status** | Not a distinct calculation today — an education goal is currently indistinguishable from any other goal category in the calculation engine, despite `category: "education"` existing as a schema value |
| **Recommendation** | Needs its own inflation rate (education cost inflation, not independently verified this pass — flagged for a future research pass rather than assumed equal to medical inflation) |

## 13. Insurance (Term Life) Adequacy

| | |
|---|---|
| **Formula (Human Life Value method)** | `Cover Needed = (Annual family expenses × years until youngest dependent is independent) + outstanding liabilities + future one-time goals (education/marriage) − existing liquid assets earmarked for these purposes` |
| **Status** | **Does not exist in Northstar at all** — no insurance-adequacy calculation, no `insurance` concept beyond the `health_policies` table designed in Phase 5 |
| **Identified as needed by** | Persona 7 (Family) in Phase 4 — "term-insurance sizing... a real calculation the current Northstar has no equivalent of" |
| **Dependencies** | Household composition (Group A schema), existing liabilities, existing goals |

## 14. Tax Estimation (Old vs. New Regime Comparison)

| | |
|---|---|
| **Formula** | `Tax(regime) = Σ over tax_slabs WHERE regime = X: slab_rate × min(income_in_slab, slab_width)`, minus applicable rebate (Section 87A-equivalent, new regime only, verified not available to HUFs in Phase 3), minus deductions (old regime only: 80C/123 up to ₹1.5L, 80D up to ₹25-50K, 80CCD(1B) up to ₹50K, etc., per Phase 1) |
| **Status** | **Does not exist** — `FinancialAssumptions.tax_rate` is a single flat user-entered percentage, not derived from any real slab structure |
| **Identified as needed by** | Every persona in Phase 4 without exception — "regime choice is the single highest-leverage decision" (fresh graduate persona), "recalculated annually" (salaried persona) |
| **Dependencies** | Directly consumes the `tax_slabs`/`tax_sections` policy-engine tables from `DatabaseDesignReport.md` Group B — this is the calculation that makes the entire versioned-policy-data schema design pay off; without this calculation, Group B's tables have no consumer |
| **Edge case — critical** | Must correctly exclude HUF entities from the Section 87A-equivalent rebate (verified difference in Phase 3) — a shared "compute tax for this regime" function must not silently apply an individual-only benefit to an HUF's tax computation |

## 15. Monte Carlo Simulation — CURRENT

Documented in full in `ProjectDiscoveryReport.md` §6. 10,000 (or 2,000 fast-probe) log-normal monthly-return paths, NumPy-vectorized, percentile + histogram output, offloaded to a thread pool. **No changes recommended** — this is Northstar's strongest, most defensible technical asset (Competitor Analysis: no researched competitor does this).

## 16. Goal Success Probability — CURRENT

The output of #15 applied against a specific goal's `target_amount`. Already correctly handles the case of a target that's unreachable at the current contribution rate (returns a low but non-zero probability, verified in the prior QA session's live testing against a real 4% probability scenario).

## 17. Optimization (Contribution / Risk-Shift Suggestions) — CURRENT

Documented in Project Discovery §6 (`optimizer.generate_suggestions`). **Recommendation for Phase 5 extension:** once #14 (Tax Estimation) exists, the optimizer should be able to rank a "contribute more to NPS for the 80CCD(1B) deduction" suggestion alongside its existing "contribute more / shift risk" suggestions — today it has no tax-awareness at all, so it cannot see that a contribution increase routed through NPS is more tax-efficient than the same rupee amount routed through a taxable investment.

## 18. Goal Prioritization — **NEW**

| | |
|---|---|
| **Problem** | When a household's surplus is insufficient to fully fund every active goal's ideal contribution simultaneously (explicitly identified as the common case for Persona 7, Family, in Phase 4 — "highest number of concurrent goals of any persona"), the engine needs to recommend *how to split limited surplus across goals*, not just optimize one goal in isolation the way `optimizer.py` does today |
| **Approach** | A constrained allocation problem: given total available surplus `S` and `N` goals each with a marginal-probability-improvement curve (derivable by running #17's optimizer per goal at several candidate contribution levels), allocate `S` across goals to maximize some objective — e.g., maximize the *minimum* probability across all goals (a "no goal left behind" objective), or maximize a weighted sum where weights come from user-declared priority (the existing `goals.priority` field, currently unused by any calculation, confirmed in Project Discovery's schema) |
| **Dependencies** | #15 (Monte Carlo), #17 (Optimizer, called repeatedly per goal), the existing but currently-unused `goals.priority` field |
| **Complexity** | Naively O(goals × candidate_contribution_levels × monte_carlo_cost) — expensive if done via repeated full 10,000-path simulations; the SIP-Future-Value closed-form shortcut (#3) is worth using for a fast first-pass allocation before refining with real Monte Carlo runs on the near-optimal candidates only |

## 19. Decumulation / Sustainable Withdrawal Rate — **NEW**

| | |
|---|---|
| **Problem** | Identified as entirely absent from Northstar in Phase 4 (Retiree persona): "the entire Monte Carlo engine is built around 'will I reach a target,' not 'will my corpus last through an unknown lifespan while I withdraw from it'" |
| **Formula (Monte Carlo decumulation, not a closed form)** | Run the *same* log-normal path engine (#15) but instead of adding a fixed contribution each period, *subtract* a fixed (or inflation-adjusted) withdrawal each period; success is defined as the corpus not reaching zero before the end of the modeled horizon (life expectancy assumption), rather than reaching a target by a certain date |
| **Inputs** | Starting corpus, desired annual withdrawal (nominal or inflation-adjusted), risk profile (asset allocation during retirement is typically more conservative — see Persona 8/9), horizon (life expectancy assumption, itself an uncertain input worth exposing to the user rather than hiding) |
| **Outputs** | Probability the corpus survives the full horizon (directly analogous to #16's goal-probability output, just inverted in meaning) |
| **Dependencies** | Reuses #15's engine's core path-generation code almost entirely — this is an extension of the existing Monte Carlo module, not a parallel system, since the underlying stochastic-return-path logic is identical; only the per-period cash-flow direction (add vs. subtract) and the success condition (reach a target vs. don't hit zero) differ |
| **Edge case** | Sequence-of-returns risk — a market downturn in the first few years of retirement is far more damaging than the same downturn late in retirement, because withdrawals compound the drawdown while there's no more contribution to offset it. A naive "average return" approximation of this calculation would be actively misleading; it must be genuinely path-based (which the existing Monte Carlo engine already is, so this is a real advantage of extending rather than building fresh) |
| **Complexity** | Same O(paths × months) as the existing engine — no asymptotic change, just a different per-step update rule |

---

## Summary Table — Build Status

| Calculation | Status | Effort to build (relative) |
|---|---|---|
| FV, PV, SIP, EMI | Standard math, not yet exposed as reusable utilities | Low |
| Net Worth, Cash Flow, Savings Rate | CURRENT | — |
| Debt-to-Income Ratio | Data exists, calculation doesn't | Low |
| Emergency Fund Adequacy | Partially current, needs confirmation | Low |
| Inflation Adjustment | CURRENT, single-rate only | Low (add category override) |
| Retirement Corpus, Education Planning | Goal mechanics exist, corpus-derivation doesn't | Medium |
| Insurance Adequacy | Does not exist | Medium |
| Tax Estimation | Does not exist | **High — but highest-leverage per Phase 4** |
| Monte Carlo, Goal Probability, Optimizer | CURRENT, strong | — |
| Goal Prioritization | Does not exist | Medium-High |
| Decumulation | Does not exist | Medium (extends existing engine) |

**The single highest-leverage build, per every persona in Phase 4:** Tax Estimation (#14). It's also the calculation that gives the Phase 5 database's entire policy-engine schema (Group B) a reason to exist — without it, `tax_slabs`/`tax_sections` are just unused tables.
