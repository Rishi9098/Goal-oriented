# UX Principles

**Purpose:** How Northstar should feel, in every screen, forever — the durable standard `UX_REVIEW.md`-style critiques get measured against. Pairs with `docs/PRODUCT_PRINCIPLES.md` (what to build) and `docs/ENGINEERING_CONSTITUTION.md` (how it's built).

---

## 1. One primary action per screen.

If a screen has two buttons competing for the user's attention, one of them is wrong. The Family "Add a person" flow has exactly one primary action (Save & continue) per step — never a form with five equally-weighted buttons at the bottom.

## 2. Progressive disclosure instead of long forms.

Never ask for more than a person can comfortably give in one breath. Onboarding's family step is three yes/no questions, not a full household census — depth is deferred to the Family workspace, reached on the user's own schedule, exactly as designed in `FamilyPlanningDesign.md`.

## 3. Every financial term has an explanation, inline, at the moment it matters.

"Sukanya Samriddhi Yojana" is never shown without a plain-language one-liner beside it the first time. A user should never have to leave the screen they're on to understand the screen they're on.

## 4. Every chart answers a specific question — never a vanity metric.

"Insurance coverage: 2 of 4 people covered" is a chart that answers "who's exposed?" A raw premium total is not — it answers nothing actionable. If a card can't be phrased as an answer to a question a real user would ask, it doesn't belong on the dashboard.

## 5. Every recommendation explains why it was generated.

Reason, supporting calculation, policy cited, confidence, alternatives — every time, no exceptions, per `docs/PRODUCT_PRINCIPLES.md` #2. A recommendation that can't show its work isn't a recommendation, it's a guess wearing a recommendation's UI.

## 6. Users always know what to do next.

Every screen answers three questions, implicitly or explicitly: what should I do here, why does it matter, and what happens after. An empty state is never a dead end — "it's just you right now" is immediately paired with "add a family member anytime," never left as an unexplained blank.

## 7. Honesty over polish when the two conflict.

If a feature has a real limitation (a "joint goal" that can't yet track individual contributions), the UI says so in plain language rather than hiding the gap behind confident-looking copy. A limitation stated clearly builds more trust than a capability implied and later found missing.

## 8. Color is never the only signal.

Every status indicator (eligible / potentially eligible / not eligible; complete / incomplete household member) pairs an icon or shape with a text label. A user with color-vision deficiency, or a screen reader user for whom color doesn't exist at all, gets the same information everyone else does.

## 9. Motion clarifies; it never decorates for its own sake.

A probability bar animating from 61% to 82% helps a user feel the improvement a recommendation would produce — that's motion with a job. Motion without a job respects `prefers-reduced-motion` and simply doesn't happen.

## 10. Errors are scoped and reassuring, especially for emotionally-loaded data.

"We couldn't save Priya's details — your other family information is safe" is the standard, not "something went wrong." Family and financial data carry more emotional weight than most software data ever does; error copy should reflect that, every time.

## 11. Empty states are normal states, not apologies.

Being a single person with no dependents, or a household with no goals yet, is a complete, valid state — never presented as something missing or broken. The product's job is to make the next step obvious, not to make the user feel behind.
