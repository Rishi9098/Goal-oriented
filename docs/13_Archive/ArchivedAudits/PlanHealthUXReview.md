# Plan Health UX Review — Phase 3

**Date:** 2026-07-12
**Scope:** Communication only. `planning_service.compute_plan_health()` is not touched, read, or reasoned about as something to change — only as something to finally *explain*.

---

## 1. What the score actually is (verified directly in code, not assumed)

`backend/app/services/planning_service.py::compute_plan_health()`:

```python
def compute_plan_health(goals: list[Goal]) -> int:
    if not goals:
        return 0
    total_weight = sum(g.target_amount for g in goals)
    if total_weight == 0:
        return 0
    weighted_sum = sum(g.probability * g.target_amount for g in goals)
    raw = weighted_sum / total_weight
    return min(100, max(0, round(raw)))
```

Plan Health is **a target-amount-weighted average of each active goal's Monte Carlo success probability.** Nothing else. Not net worth, not savings rate, not debt-to-income, not emergency fund adequacy, not diversification — despite the name implying a holistic financial checkup. Two consequences follow directly from the formula, both currently invisible to the user:

- **Zero goals → score is exactly 0.** A brand-new user who hasn't added a goal yet sees the same "0" a user in genuine trouble would see — there is no way today to distinguish "nothing to measure yet" from "your plan is failing."
- **One ambitious, distant goal can single-handedly produce a very low number.** Our own test account — one retirement goal, $500,000 by 2046, $0/mo contribution set during onboarding — shows **5/100**. That is not a broad verdict on the user's finances (net worth is a positive $23,000, savings rate is 72%); it is the literal, correct, narrow statement "at $0/month, this one goal has a 5% chance of hitting $500k by 2046." The number is accurate. The *impression* it gives, with zero context, is not.

## 2. Where it currently appears, and what each screen tells the user (verified in code)

| Surface | What's shown | Explanation present? |
|---|---|---|
| Sidebar mini-card (`app-shell.tsx`) — every screen, always visible | A bare number + a progress bar | **None.** No tooltip, no link, no label beyond "Plan health." |
| Reports' "Plan Health" stat card (`app.reports.tsx`) | Number + "out of 100" + a color (red/amber/green by threshold) | **None.** |
| Onboarding | Nothing | The score is never mentioned before it appears — a user's very first encounter with it is cold, on the Dashboard, immediately after finishing a ten-step interview. |
| AI Copilot | Nothing | No suggested prompt references it; the model is never given an easy, pre-worded way for a user to ask about it. |
| Dashboard itself (`app.index.tsx`) | Not shown directly — only via the always-present sidebar card | — |

This confirms `ProductDesignAuthorityReview.md`'s P0 finding precisely: the single most anxiety-inducing element in the product is a number with zero surrounding context, shown everywhere, permanently.

## 3. Decision — explain, don't change

Per this phase's explicit constraint, `compute_plan_health()` is untouched. Every change below is either new copy or a new, read-only explanation surface built from data the frontend already has or can cheaply, lazily fetch — never a recalculation, never a second implementation of the weighted-average formula.

1. **Sidebar mini-card becomes an interactive disclosure** (a `Popover`, not a `Tooltip` — deliberately: the explanation needs to hold a goal list and a link, and Radix's own guidance is that interactive/complex content belongs in a `Popover`, not a hover-only `Tooltip`; wiring up `ui/tooltip.tsx`/`ui/popover.tsx` here is exactly the "reuse the already-scaffolded, already-installed primitive" pattern `GlobalShellArchitecture.md` established for this exact codebase). Clicking it reveals:
   - **What it means**, always shown, static copy: a weighted average of how likely the user is to reach each goal — explicitly *not* a grade on overall finances.
   - **Zero-goals case, detected from `dashData.goal_count` (already fetched, no new call)**: a distinct, non-alarming message — "nothing to measure yet," not "0/100 you're failing."
   - **Drivers, lazily fetched only when opened** (`enabled: open`, mirroring the Command Palette's own existing lazy-fetch rule): the specific goals dragging the score down, by name and probability — using the *already-computed* `goal.probability`/`goal.on_track` fields the backend returns, filtered/displayed, never recomputed.
   - **How to improve**: one line plus a direct link to Goals.
2. **Reports' Plan Health stat card** gets the same explanation, reusing a small shared `PlanHealthInfo` component so the wording never drifts between the two surfaces.
3. **Onboarding's final "You're all set" screen** gets one added sentence, introducing the score honestly *before* the user meets it cold: it reflects goal odds, not a full financial grade, and starts low until real goals with real numbers are in place.
4. **AI Copilot** gets one new static suggested prompt, "Explain my Plan Health score," so a user who's confused has an obvious, zero-effort way to ask.

## 4. What this phase explicitly does not do

- Does not change `compute_plan_health()`, its weighting, its zero-goals behavior, or any threshold — this phase's entire mandate is communication.
- Does not add a new backend endpoint. The "drivers" explanation reuses `GET /goals` (already called by the Dashboard) and `dashData.goal_count` (already part of `GET /dashboard`'s existing response) — nothing new is fetched that isn't already fetched somewhere in the app today.
- Does not attempt to broaden what Plan Health measures (e.g., folding in net worth or savings rate) — that would be a calculation-engine change, explicitly out of scope, and arguably a Phase 5 (Automation)/backend-engineering decision, not a Phase 3 communication one. This review only makes the *existing, narrow* definition legible.
- Does not add the explanation to every possible surface exhaustively (e.g., a dedicated FAQ page) — the two places the number actually appears, plus the two natural moments a user would first encounter or ask about it (onboarding, AI Copilot), are the highest-leverage, smallest-correct set.
