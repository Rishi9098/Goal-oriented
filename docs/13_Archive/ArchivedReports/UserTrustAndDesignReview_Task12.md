# User Trust Review & Design Review — Task 12 (Family Dashboard Integration)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

---

## User Trust Review

**One question, one answer — enforced per card.** Each of the six cards answers exactly the single question its title asks (per `UX_PRINCIPLES.md` #4 and `FamilyPlanningDesign.md` Part 6's stated rule): "2 of 4 people covered" is immediately actionable; no card shows a vanity metric or an unexplained composite score.

**The dashboard never contradicts the screens it summarizes.** This is the core trust property of a summary view, and it's guaranteed structurally (see `IntegrationIntegrityReview_Task12.md`): every number is the source screen's own number. A user who taps "Insurance coverage: 2 of 4" lands on the Insurance screen and sees the same two people covered — never a reconciliation exercise.

**A warning is only shown when the product would also recommend acting on it.** The Parents ⚠ state uses the recommendation engine's own uncovered-parents determination, so the dashboard never nags about a parent the user has already insured (the stale-answer case Task 10 solved). Warning and recommendation appear and disappear together.

**Unavailable is never dressed up as fine.** If a section can't be computed, its card says so — it doesn't render a zero, and the recommendations feed distinguishes "no recommendations" from "we couldn't check."

**Being single with no dependents is a normal state.** "Who depends on me? Just you right now" — per `FamilyPlanningDesign.md` Part 9, never an apology or a prompt-shaped guilt trip.

---

## Design Review

**Reuses the existing dashboard's visual grammar.** The six-card grid mirrors `/app`'s `Stat`/`StatSkeleton` pattern (per the Contract's explicit instruction) — same surface-card styling, same skeleton loading shape, so the Family dashboard reads as a sibling of the money dashboard, not a new design language.

**Every card is a real link, not a clickable `<div>`.** Per the Contract's Accessibility note: cards are `<Link>` elements with visible focus states, navigating to their source screen (Education → Family Goals, Insurance/Parents → Family Insurance, Retirement/Emergency → Goals).

**The feed reuses Task 11's card language in compact form.** Feed entries show each recommendation's `why` with its source icon (shield/institution — the same icons Tasks 10/11 established) and link to `/app/family/recommendations` for the full disclosure view — the expanded explanation UI continues to live in exactly one place.

**The `/app` card is deliberately quiet.** One compact card ("Family — N people · X suggestions") linking to `/app/family`; it renders nothing on error rather than breaking the money dashboard, and adds no second loading spinner to a screen that already has its own skeleton system.

**Accessibility:** Standard Baseline. Grid cards carry their question as the accessible name; the warning state is conveyed in text ("no own insurance"), never by color alone.
