# User Trust Review & Design Review — Task 9 (Family Goals & Custom Inflation)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

---

## User Trust Review

Reviewed as four personas against the four required questions.

### Does the user understand why custom inflation exists?

**Parent:** Yes — the copy leads with the concrete reason, not the mechanism: *"Education costs typically rise faster than general inflation — want to use a more accurate estimate?"* This states the *why* (education costs outpace the number already being used) before ever mentioning a percentage.

**Financial planner:** Also yes, and specifically appreciates that no invented number is presented as fact. `CalculationEngineReport.md` #12 is explicit that a verified education-cost-inflation figure does not exist yet — so the prompt offers a rate field with **no suggested default**, rather than a specific-looking number that would imply false precision. A planner reviewing this would see an honest gap, not a fabricated statistic.

### Does the user understand when to use it?

**Married couple, planning a joint education goal:** The feature only appears on goals where `category = 'education'` — it doesn't show up on unrelated goals (retirement, travel, etc.), so there's no ambiguity about when it's relevant. The prompt only appears once per goal until a value is set, avoiding repeated nagging.

**First-time investor:** Might not know what "inflation" means for a savings goal at all. The text-equivalent summary makes the effect concrete rather than abstract: *"Projected cost in 11 years: ₹X, using a Y% annual inflation assumption"* — a first-time investor doesn't need to understand compound growth math to read "this will probably cost ₹X by then."

### Does the user understand what changes?

**All personas:** Setting a custom rate changes exactly one thing — the projected future cost shown on this goal's own detail view. This is stated in-UI, not just implied: the projection line names its own inputs plainly ("Projected cost in N years... using a Y% annual inflation assumption").

### Does the user understand what does NOT change?

**This is the single most important trust question for this feature, given it sits right next to Monte Carlo `probability`/`on_track`.** The risk: a user who just set a custom inflation rate might reasonably expect their goal's displayed success probability to update to reflect it — and if it silently doesn't, that could read as a bug rather than a deliberate boundary.

Resolution: the goal-detail panel's Monte Carlo probability display and the new inflation projection are visually and physically separated — the probability lives in the existing Progress section (unchanged), the inflation projection lives in its own distinct card below, with its own explanatory line. No shared number, no implied connection. Additionally, per Design Review below, the projection card's copy explicitly states its own scope ("this changes what we project this will cost, not your Monte Carlo odds of hitting your current target") — stated plainly, in the product's own established voice for limitations (the same "state the real thing, don't gloss over it" pattern used since PCA-1/PCA-2), rather than left to the user to infer or assume.

**Financial jargon avoided:** No use of "Calculation Context," "Monte Carlo," "nominal vs. real value," or "compound annual growth rate" anywhere in user-facing copy — those terms are used only in this document and the code, never shown to the user.

---

## Design Review

### Simple UI, progressive disclosure

Three states, revealed one at a time, matching the Contract's own Business Rules exactly:
1. **No custom rate set (default):** the standard global-rate projection is always visible (Acceptance Criterion #1) *plus* a dismissible one-time prompt suggesting a custom rate — the prompt does not block or replace the existing projection.
2. **Prompt accepted:** reveals a single input (no suggested default value, per the unverified-rate constraint) — the user supplies their own number.
3. **Custom rate set:** the prompt disappears permanently (persisted server-side via `custom_inflation_rate` being non-null — Acceptance Criterion #2, "reappears only if the user hasn't set a value"); the projection now uses the custom rate and says so explicitly.

### Natural language

- "Education costs typically rise faster than general inflation" instead of "category-specific inflation multiplier."
- "Projected cost in N years" instead of "future value."
- "Using the standard Y% assumption" / "using your custom Y% assumption" — plain, always names which rate is active.

### Why education (and medical) goals often use a different rate — explained in-UI

One short, factual sentence accompanies the prompt: *"Tuition, fees, and related costs have historically climbed faster than general prices — a flat inflation number can understate what you'll actually need."* This is the *reason*, stated once, not repeated as a nag on every visit.

### Progressive disclosure, not overwhelm

- The feature is invisible on all five other goal categories — zero UI footprint added to retirement/home/travel/wealth/emergency goals.
- SSY callout (if the goal is tagged with an eligible girl child) appears as a single additional card, reusing the exact existing visual pattern (icon, `role="status"`, color) from the Add Family Member flow — not a new visual language the user has to learn.
- No new navigation, no new route, no new page — everything lives inside the existing goal-detail panel (`GoalSimPanel`) the user already knows how to open and close.
