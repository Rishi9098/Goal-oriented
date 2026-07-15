# User Trust Review & Design Review — Task 10 (Family Insurance)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

---

## User Trust Review

Reviewed as: a user with a dependent parent (the primary persona this screen exists for), a financial planner (checking the figures are defensible), and a first-time user encountering a tax-adjacent recommendation for the first time in this product.

**Does the user understand why this is being recommended?** Yes — `why` names the specific parent(s) and the specific deduction opportunity in plain language before any number appears, matching the same "reason before number" pattern Task 9's inflation prompt already established as working well in the previous review.

**Does the user trust the number?** The figure is explicitly tied to a named tax section (80D) and a plain-language description ("a standalone health policy for your parent") rather than presented as an opaque "you could save more" claim. When age is unknown, the copy says the ceiling *could* be higher rather than asserting ₹50,000 as certain — a financial planner reviewing this would see calibrated confidence, not overreach.

**Does the user understand this doesn't replace their own judgment?** The recommendation explicitly frames itself as a comparison ("compare a family floater addition vs. a standalone policy") rather than a directive ("you must buy X") — matching the Contract's own User Story ("so that I can make an informed choice instead of guessing"), not a hard sell.

**First-time user, no dependent parents:** the screen shows no recommendation at all and no error — an honest, quiet absence, not a placeholder implying something is broken or "coming soon" (this feature already exists in full; it's simply not applicable to this household).

---

## Design Review

**Reuses the established recommendation-card pattern.** Same visual treatment as SSY's existing callout (Task 6/7/9) where the content genuinely fits (a bordered, tinted card with an icon) — but this recommendation is denser (four explanatory sections, not one sentence), so it uses **progressive disclosure**: the `why` sentence and headline figure are always visible; "what information was used" / "what information is missing" are available via a `<details>` disclosure, matching the exact accessible-disclosure pattern `Milestone2ImplementationContract.md` §11 already specifies for the Schemes screen (collapsed-by-default, not hidden entirely) — reused here rather than inventing a second disclosure pattern.

**Never overwhelms.** The policy list and Add Policy form are separated from the recommendation card, not interleaved — a user who only wants to record an existing policy never has to read the recommendation copy first.

**Explains the WHY/WHY NOW/WHAT USED/WHAT MISSING structure in the user's language, not the engineering label.** The UI never shows those four literal labels; it shows a natural sentence for "why/why now" and a short bulleted "Based on" / "We don't yet know" pair for the used/missing fields — the structure is what this task requires internally, not necessarily the user-facing heading text.

**Accessibility:** Standard Baseline (per Contract). The recommendation card is a real semantic region with a heading, not a bare styled `<div>`; the `<details>` disclosure is native, not a custom-built accordion (keyboard/screen-reader behavior comes free).
