# Consistency Audit — Phase 6

**Date:** 2026-07-13
**Method:** Direct grep across every route/component for the specific inconsistencies `ProductDesignAuthorityReview.md` flagged, followed by a broader sweep to check whether each one is really an outlier or, in fact, the majority convention — since assuming the earlier review's framing was correct without re-verifying would risk "fixing" the wrong side of a real inconsistency.

---

## 1. A correction to the earlier review's own framing

`ProductDesignAuthorityReview.md` characterized Reports' raw Tailwind color classes (`text-emerald-400`, `text-red-400`, etc.) as "not the shared semantic tokens used elsewhere" — implying Reports was the outlier. Direct investigation found this is **only half right**:

- `text-success`/`text-warning` (the semantic tokens) are used in exactly **one context app-wide**: goal on-track/at-risk indicators (Dashboard, Goals). 15 files, 34 occurrences.
- Raw `text-red-400`/`bg-red-500/10`/`border-red-500/30` for **error banners and messages** is actually the dominant, established convention **across 22 files** (auth screens, onboarding, every Family sub-page, Financials, Life Events, Goals) — 50 occurrences. Reports' own error banner already matches this majority pattern almost exactly (one small opacity difference, `/5` vs. the majority's `/10` — fixed below).

**Conclusion:** Reports' error banner was never the inconsistency. The real, fixable inconsistency is narrower and different: **Reports' `pctColor`/`pctBar` functions and its Goal Breakdown "on track" pills invent their own raw-color, 3-tier scheme instead of reusing the semantic tokens Dashboard/Goals already established for the exact same on-track/at-risk concept.**

## 2. Findings and fixes

### 2.1 Goal status pills styled differently for the identical concept

**Where:** Reports' Goal Breakdown "On track" / "Needs attention" pills vs. Dashboard's/Goals' pills for the same `on_track` boolean on the same `Goal` data.

**Before:** Reports: `text-emerald-400 bg-emerald-500/10 border border-emerald-500/20` / `text-amber-400 bg-amber-500/10 border border-amber-500/20`. Dashboard/Goals: `bg-success/15 text-success` / `bg-warning/15 text-warning`.

**Fix:** Reports now uses the identical `bg-success/15 text-success` / `bg-warning/15 text-warning` classes — the same goal, on two screens, now looks like the same goal.

### 2.2 A three-tier color function with no semantic-token equivalent

**Where:** `pctColor()`/`pctBar()`, used for Plan Health's stat-card value and every goal's probability bar/percentage in Goal Breakdown.

**Before:** Raw `emerald-400`/`amber-400`/`red-400` (text) and `emerald-500`/`amber-500`/`red-500` (bar fill) with hardcoded 80/60 thresholds.

**Fix:** Mapped onto the same three semantic tokens the rest of the app already defines (`success`/`warning`/`destructive`), keeping Reports' own 80/60 threshold logic — that finer three-way split is a legitimate, deliberate difference from Dashboard/Goals' binary on-track pill (a denser report reasonably wants more granularity than a single pill), so only the **color vocabulary** was unified, not the threshold design.

### 2.3 Per-goal probability shown with no word attached, unlike everywhere else

**Where:** Reports' Goal Breakdown row shows a bare `"5%"` next to each goal's progress bar. Dashboard and Goals show the identical Monte Carlo probability as `"5% likely"`.

**Fix:** Reports now appends "likely," matching the wording used for the same number everywhere else it appears. (The separate "X% success rate" sub-label on the "Goals On Track" stat card is a genuinely different metric — the share of goals that are on track, not any single goal's own probability — and was left as its own, correctly-distinct wording.)

### 2.4 The same dollar figure rendered two different ways on two different screens

**Where:** Reports has its own `fmt()` (abbreviates: `"$45k"`, `"$2.30M"`); every other screen (Dashboard, Goals, Financials, Life Events) uses the shared `formatCurrency()` (full precision: `"$45,231"`). A user going from Goals ("$0 of $500,000") to Reports for the identical goal sees `"$500k"` for the same number.

**Fix:** Reports now imports and uses the same `formatCurrency()` as everywhere else, and its local `fmt()` is removed. At this product's actual data scale (figures in the thousands-to-low-millions, not billions), full precision remains perfectly scannable in a stat card, and a user should never have a reason to wonder whether a "report" figure and a "live" figure for the same thing disagree.

### 2.5 Error banner opacity, a small residual difference

**Where:** Reports' error banner used `bg-red-500/5`; the majority convention (Goals, Sign In, and 20 other files) uses `bg-red-500/10`.

**Fix:** Aligned to `/10`.

### 2.6 Net Savings figure not using the semantic success token

**Where:** Reports' cash-flow strip colors "Net Savings" with raw `text-emerald-400`; Dashboard's equivalent "Monthly income"/"Net savings" figures use `text-success`.

**Fix:** Aligned to `text-success`.

## 3. What this phase explicitly does not do

- Does not touch the app-wide `text-red-400` error-banner convention itself — confirmed to be the genuine, dominant, working pattern across 22 files; changing it everywhere to `text-destructive` would be a much larger, riskier, out-of-scope rewrite for a inconsistency that (per §1) doesn't actually exist.
- Does not unify Reports' "Generated {long date}" header format with Life Events' shorter list-row date format — the header is a one-off "as of" timestamp (a common, reasonable convention for a formal document), not a repeated list format; the two "Life Events This Year" list rows Reports already added in Phase 2 already match Life Events' own short-date convention.
- Does not touch backend calculations, endpoints, or the `ReportSummary`/`Goal` schemas — every fix here is a display-layer formatting/class change over data already returned.
