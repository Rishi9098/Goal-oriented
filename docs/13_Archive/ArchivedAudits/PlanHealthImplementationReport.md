# Plan Health Implementation Report — Phase 3

**Scope:** Exactly what `PlanHealthUXReview.md` decided — explain the existing score everywhere it appears (sidebar, Reports), introduce it honestly in onboarding before the user meets it cold, and give AI Copilot an easy way in. `planning_service.compute_plan_health()` was not read as something to change, and was not changed.

---

## Files Changed

| File | Change |
|---|---|
| `code/src/components/PlanHealthInfo.tsx` | **New.** Shared explanation component (a `Popover`, not a `Tooltip` — deliberately, since the content includes an interactive link). Static "what it means" copy; a distinct, non-alarming message when `goalCount === 0`; a lazily-fetched (`enabled: open`) list of the specific goals dragging the score down, built entirely from the already-computed `goal.probability`/`goal.onTrack` fields `GET /goals` already returns — no new calculation, no re-implementation of the weighted-average formula. |
| `code/src/components/app-shell.tsx` | Sidebar's Plan Health mini-card is now a `PlanHealthInfo` trigger (button, not a static `<div>`), with a small info icon added next to the label. `goalCount` (from the already-fetched `["dashboard"]` query) passed through — no new fetch on every page load. |
| `code/src/routes/app.reports.tsx` | `StatCard` gained one new, optional `info` prop (used only by the Plan Health card — the other three stat cards are unaffected). Wired to the same `PlanHealthInfo` component. |
| `code/src/routes/onboarding.tsx` | One new sentence on the final "You're all set" screen, introducing the score honestly before the user ever sees it: reflects goal odds, not a financial grade, starts low until real goals exist. (This edit also picked up a same-file `eslint --fix` pass — see Automated Validation — that reformatted ~14 pre-existing, unrelated Prettier violations already in this file; confirmed via diff review to be whitespace-only, zero logic changes.) |
| `code/src/routes/app.copilot.tsx` | Added "Explain my Plan Health score" as the first static suggested prompt. |

## Files Not Changed (and why)

| File / area | Reason |
|---|---|
| `backend/app/services/planning_service.py` (`compute_plan_health`) | This phase's explicit, non-negotiable constraint. Read and understood, never touched. |
| Any other backend file | Confirmed via `ruff`/`mypy` re-run and the absence of any backend file in this phase's diff — every explanation is built from data already returned by existing, unmodified endpoints (`GET /dashboard`'s `goal_count`, `GET /goals`'s `probability`/`on_track`). |
| `app.family.index.tsx`, `app.financials.tsx`, and every other Phase 2 file | Plan Health doesn't appear on those screens; no reason to touch them in this phase. |

## Implementation Summary

1. Read `compute_plan_health()` directly rather than assuming what "Plan Health" measures — this is what revealed the two concrete, previously-undocumented facts driving this phase's design: the score is a *pure* goal-probability weighted average (nothing else feeds it), and it is *exactly* 0 whenever a user has zero goals, indistinguishable today from a genuinely bad score.
2. Built one shared component, reused verbatim by both surfaces that show the number, so the explanation can never drift between the sidebar and Reports.
3. The "what's holding it back" list is built from data the backend already computed and already returns (`probability`, `on_track` on each `Goal`) — filtered and sorted for display, never recomputed. This is the same class of operation the Goals page's own "At risk" filter tab already performs on the same fields; it does not duplicate `compute_plan_health()`'s weighted-average math, which never runs anywhere except the backend.
4. The goals fetch is lazy (`enabled: open`), so visiting any page does not cost an extra request — the cost is only paid if a user actually opens the explanation, mirroring the Command Palette's own already-established lazy-fetch convention in this codebase.

## Manual Validation

Performed live in Chrome against the running dev build (`localhost:8080`, backend `localhost:8010`), same real test account used in Phase 2 (one retirement goal, 4.6%–5% probability depending on rounding, hence the low score):

- **Sidebar:** Clicking the mini-card opens the popover. Confirmed content: "What is Plan Health?" explanation, "What's holding it back → Retire at 60 — 4.6% likely" (real, lazily-fetched data, not a placeholder), improvement guidance, and a working "Review your goals" link that navigated to `/app/goals` and closed the popover.
- **Reports:** The small info icon next to "PLAN HEALTH" opens the identical popover with identical content, confirming the shared component renders consistently across both surfaces.
- **AI Copilot:** "Explain my Plan Health score" renders as the first static suggested prompt, alongside Phase 2's dynamic "Based on your recent activity" suggestion — both present simultaneously, confirmed no conflict between the two.
- **Onboarding:** Not re-run through the full 11-step flow this phase (already exercised end-to-end in the earlier Life Events frontend work this session) — the new sentence's rendering was confirmed by direct code/diff review instead, consistent with how a copy-only addition to an already-validated screen is normally checked.
- Console checked (`read_console_messages`, filtered `error|Error`): only the same pre-existing, unrelated Grammarly-extension hydration warning seen in Phases 1 and 2.

## Automated Validation

- `npx tsc --noEmit` — clean, zero errors.
- `npx eslint` on all five changed/new files — three Prettier-only issues found in `onboarding.tsx`, all pre-existing and unrelated to this phase's own added lines (verified by line number); resolved via `eslint --fix` on that file, then diff-reviewed in full to confirm every change was whitespace/line-wrapping only, zero logic altered.
- `npm run build` (full Vite + Nitro production build) — succeeded.
- Backend: `ruff check app/` and `mypy --strict app/` — both clean (87 source files, no issues); confirmed zero backend files are part of this phase's diff.
- Backend test suite: not re-run — zero backend code changed; the existing 673-pass baseline from earlier in this session remains valid.

## Regression Risk

**Low.** The sidebar's Plan Health card changed from a static `<div>` to a `<button>` wrapping the same visual markup — confirmed via screenshot that its appearance is unchanged when the popover is closed, and its layout/sizing is identical (`w-[calc(100%-1.5rem)]` preserved). `StatCard`'s new `info` prop is optional and unused by the three other stat cards on Reports, so their rendering is untouched (confirmed by screenshot — Net Worth, Goals On Track, and Monthly Savings render exactly as in Phase 2's own screenshots). The lazy goals query uses the same `["goals"]` query key Dashboard already uses, so opening the popover on Dashboard hits an already-warm cache rather than issuing a genuinely new request.

## Performance Impact

Negligible, and in the best case, zero. The one new network call (`GET /goals`, inside `PlanHealthInfo`) only fires when a user actually opens the explanation (`enabled: open`) — never on page load, never in the background. On Dashboard specifically, this call shares the exact `["goals"]` cache key the page's own Goals card already populates, so opening the popover there is typically a cache hit, not a new request.

## Backward Compatibility

Fully preserved. No prop, route, or exported type changed shape in a breaking way — `StatCard`'s new `info` prop is additive and optional; every existing call site (Net Worth, Goals On Track, Monthly Savings) is untouched and compiles/renders identically without it.

## Outstanding Risks

1. The "what's holding it back" list only surfaces goals where `on_track` is `false` — a goal that's nominally "on track" per that boolean but still has a probability well below what a user might intuitively expect won't appear in the list. This mirrors the Goals page's own existing on-track/at-risk distinction exactly (no new threshold invented here), but is worth knowing: the explanation's "drivers" list is only as fine-grained as that existing boolean, not a full breakdown of every goal's contribution weight.
2. Onboarding's new sentence was validated by code/diff review, not a fresh full click-through of the 11-step wizard this phase — a reasonable, proportionate choice for a pure copy addition to an already-tested screen, but flagged here for completeness rather than silently assumed.

## Ready for Next Phase

**Yes.** Phase 3's scope is closed and validated. Continuing automatically to Phase 4 (Microcopy) per the mission's instruction not to pause between phases.
