# Design Review — Scheme Eligibility Evaluation Service (Milestone 2, Task 3)

**Date:** 2026-07-06
**What's being reviewed:** Not a screen (none exists yet) — the *output contract* of the eligibility service: the reason-string wording and categorization boundaries that Task 6 (inline SSY callout) and Task 11 (Schemes screen) will render verbatim without further design work. This is the one place in a backend-only task where real product design decisions get made, so it gets a real review, not a rubber stamp.

---

## Persona Reviews

**Apple Designer:** Reason strings must never leak implementation vocabulary (`rule_type`, `operator`, `max_age`) into user-facing text. The service should return plain-language sentences, not rule metadata — "She's 7 — this scheme is only available for girls under 10" (already the Contract's own example), not "max_age: 10, actual_age: 7." Confirmed as a hard requirement, not a suggestion.

**Linear Designer:** Pushed on whether SCSS's unmodeled special cases (55+ for VRS retirees, 50+ for defense personnel) should be surfaced as an on-screen caveat. Decision: **no** — surfacing an edge-case disclaimer to the ~95% of users it doesn't affect would itself violate `UX_PRINCIPLES.md` #4 ("never overwhelm users") for the sake of transparency that matters to a narrow population. The honest disclosure belongs in code (docstring) and `docs/database.md`, where an engineer extending this later will find it — not on every SCSS card. This is Linear's own instinct (surface system state honestly) balanced against the equally real "don't overwhelm" principle; where the two trade off, this review sides with not overwhelming, since the gap is a false-negative for a narrow, identifiable population (retired government/defense personnel under 60) rather than a wrong answer for anyone else.

**Financial Planner:** The reason string should be specific enough to be *useful*, not just accurate — naming the exact scheme, the exact member, and the exact threshold ("turns 60 next year," not "not yet eligible"). Also flagged: the SCSS gap above is a real limitation for a real (if narrow) population a planner would actually serve — worth a prominent code-level flag so it's the first thing a future engineer adding retirement-status data sees, not a footnote.

**Accessibility Expert:** Reason strings are plain text, self-contained, and don't depend on visual context (color, icon) to be understood — confirmed compatible with `FamilyPlanningDesign.md` Part 10's existing accessibility baseline (color is never the only signal). No new concerns; this service produces text, and text is inherently accessible if it's not visually load-bearing on its own.

**First-time user:** Wants to understand *instantly* why a scheme does or doesn't apply. Confirmed: every reason string names the specific fact that decided it (an age, a status), never a generic "criteria not met."

**Parent:** Cares specifically about SSY. Confirmed the reason string names the child (`member_name`) wherever the eligibility check resolves to a specific person, not just "a household member."

**Senior citizen:** Cares specifically about SCSS. Confirmed the "potentially eligible" reason string for someone approaching 60 reads encouragingly ("turns 60 next year") rather than clinically ("not yet 60") — small wording choice, real emotional difference for a screen that's fundamentally about aging and dependency.

---

## Design Decisions Made This Review

### 1. "Potentially Eligible" window: within 5 years of an age threshold

Neither the Contract nor any research report specified an exact window for the "Potentially Eligible" bucket (it only gave one illustrative example: "she turns 60 next year"). This review sets a concrete, documented rule: **an age-gated scheme is "Potentially Eligible" if the relevant household member is within 5 years of the threshold, on the side that hasn't reached it yet; "Not Eligible" beyond that.** 5 years is a reasonable planning horizon (matches this app's own goal-planning timeframes elsewhere) and avoids the alternative of either no "potentially eligible" bucket ever populating (window too narrow) or nearly everyone showing as "potentially eligible" (window too wide, defeating the bucket's purpose). This is an implementation-level product decision, not a financial or policy fact, so it doesn't fall under "never invent financial rules" — but it's recorded here so it's traceable, not buried in code.

### 2. SSY has no "Potentially Eligible" case in practice

Since SSY's eligibility depends on a child who already exists in the household (age and gender both concretely known, never "expected"), a household either has an eligible girl under 10 or doesn't — there's no meaningful "approaching eligibility" state for SSY the way there is for SCSS's approaching-60 case. This asymmetry is correct and expected, not a bug to fix.

### 3. SCSS's unmodeled special-case routes: code/docs disclosure only, not user-facing

Per the Linear Designer/Financial Planner notes above — documented in the service's docstring and `docs/database.md`, not surfaced as in-product caveat text.

---

## Verdict

No blocking issues. Two concrete decisions (the 5-year window, the SCSS disclosure placement) are now explicit and traceable rather than left to whoever wrote the code that day. Proceed to Implementation Contract Validation (Step 5).
