# User Journey — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Every transition below names the exact screen(s)/API(s) involved, per `Milestone2ImplementationContract.md`'s numbering (§1-§12).

---

## Journey A: Single Professional → Married → Child Born → Parents Age → Retirement

```
Single professional
────────────────────
Registers → onboarding §1 → answers No/No/No
→ Family Home (§2) shows only "You" — a complete, normal state (UX_PRINCIPLES #11)
→ Sets up an emergency-fund goal and a retirement goal (existing goal flow, untouched)

        ↓ Gets married

→ Visits Family Home (§2) → taps "+ Add someone else"... no — taps the persistent
  spouse-add entry point (§3) → enters spouse's name + DOB
→ Family Home now shows "You" + "Spouse" (§2)
→ Opens an existing goal (e.g., "House down payment") → tags it with the spouse (§8)
→ Sees the mandatory disclosure: "This goal belongs to your account. [Spouse]
  can see it if you share access, but her own contributions aren't tracked
  separately yet." (UX_REVIEW.md revision #2, enforced at §8)

        ↓ Child is born

→ Family Home (§2) → "+ Add a child" (§4) → enters name + DOB (+ optional gender)
→ If daughter, age <10 → inline SSY callout renders immediately, sourced from
  live `scheme_rates`/`scheme_eligibility_rules` (§4, §11's data reused)
→ Creates an education-category goal for the child, tags it (§8) → Education
  Planning view (§9) offers the inflation-override prompt

        ↓ Parents begin to depend on the user

→ Family Home (§2) → "+ Add a parent" (§5) → enters name, relationship,
  "does she have her own insurance?" → answers "No"
→ Visits Family Insurance (§10) → sees the separate-policy recommendation,
  citing the verified doubled-deduction figure from `GovernmentPolicyReport.md`
→ Visits Family Government Schemes (§11) → sees SCSS in "Potentially Eligible"
  for the parent if she's near 60

        ↓ Retirement approaches

→ Family Dashboard (§12) "Retirement readiness" card reflects the existing
  plan-health calculation, now visible alongside the family context that's
  accumulated over the journey — no new calculation, same figure, richer framing.
```

**Every transition is user-initiated.** The app never infers a life event from elapsed time or any other signal — a user who never opens the Family workspace again after onboarding stays in a complete, valid, single-person state indefinitely.

---

## Journey B: Family-First User (married with kids and dependent parents at signup)

```
Registers → onboarding §1 → answers Yes/Yes(count:2)/Yes
→ Household seeded with: You, Spouse (placeholder), Child ×2 (placeholders),
  Parent (placeholder) — 5 rows total, all incomplete
→ Family Home (§2) shows 5 cards, 4 marked "+ Add details"
→ User completes Spouse (§3), then Child 1 (§4), then Child 2 (§4), then
  Parent (§5) — one screen at a time, in whatever order they choose
  (no forced sequence — the Family Home list doesn't dictate an order)
→ As each child is completed, the SSY check re-evaluates independently per child
→ Family Government Schemes (§11) updates incrementally as each member is
  completed — a user who's only finished 2 of 5 members still sees accurate
  eligibility for those 2, not a blocked/incomplete-looking screen
→ Family Dashboard (§12) shows partial data honestly (e.g., "Insurance
  coverage: 0 of 5 covered yet") rather than waiting for full completion
  to render anything (UX_PRINCIPLES #11 — a partially-complete household is
  a normal, valid, in-progress state, not an error state)
```

---

## Journey C: Pre-Milestone-2 Existing User (registered before Family shipped)

```
Existing user, no household row exists (Foundation-only account)
→ Visits /app/family for the first time
→ GET /api/v1/family lazily provisions an empty household + self-only
  member row (§2's Acceptance Criteria) rather than a 404
→ Sees the same empty state as a brand-new single-professional user
  (Journey A's starting point) — converges into the same experience,
  no separate "legacy user" code path needed beyond this one lazy-create step
```

---

## Cross-Journey Invariant

No journey above ever requires the user to revisit onboarding once complete — every family-composition change (marriage, birth, a parent's insurance status changing, removing a member) happens in the Family workspace, reachable at any time, never gated behind a wizard. This is the single structural guarantee `FamilyPlanningDesign.md` Part 3's onboarding-brevity decision depends on: onboarding can stay short only because the Family workspace is always available afterward, not a one-time setup step.
