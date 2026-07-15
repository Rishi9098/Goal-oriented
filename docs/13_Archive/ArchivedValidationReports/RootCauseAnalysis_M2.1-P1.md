# Root Cause Analysis — Milestone 2.1-P1 (Government Schemes Screen)

**Date:** 2026-07-07

## Why this gap exists (not a defect — a scoped, documented deviation)

`Milestone2ImplementationContract.md` §11 always specified a dedicated "Family Government Schemes" screen (`/app/family/schemes`) as Task 11 of Milestone 2. During this milestone's actual implementation, the turn that would have built it was retitled "Task 11 (Family Recommendations)" and its content (aggregate multiple recommendation sources, detect conflicts) matched the Contract's **Task 12** concept instead of its own Task 11. This mismatch was surfaced to the user before implementation (`DependencyValidation_Task11.md`), and the user explicitly chose to build the recommendation-aggregation layer instead of the dedicated Schemes screen. That was the correct call given the instructions at the time — but it left the Contract's actual §11 deliverable unbuilt.

**Consequence:** `evaluate_household_eligibility()`'s `"eligible"` bucket is surfaced today (via the Recommendations feed and Dashboard), but its `"potentially_eligible"` and `"not_eligible"` buckets — a full two-thirds of the three-state design — have **zero UI surface anywhere in the product**. A household with a parent turning 60 next year (about to qualify for SCSS) gets no forward-looking signal today; `ProductConsistencyRoadmap.md`'s PCA-7 is therefore partially, not fully, resolved, as the Certification Report already stated.

## Is there a code-level bug to fix, or only a missing screen?

**Only a missing screen.** No backend logic is broken. `evaluate_household_eligibility()` was verified in the Milestone 2 Certification's Architecture Health review to be correct, singly-implemented, and already the sole source of eligibility truth for every existing consumer. This finding is additive (build the missing screen), not corrective (no existing behavior is wrong) — the closest precedent in this sprint's own framing is "a documented, honest gap being closed," not "a bug being fixed."

## Scope boundary (what this finding does NOT attempt to fix)

- The self-member eligibility gap (Task 3's own documented limitation) is **not** in scope for this finding — closing it would require joining `UserProfile` data into the eligibility evaluator, a change to Task 3's certified service, not a new screen consuming it as-is.
- The 6 schemes with no seeded eligibility rules (`PPF`/`EPF`/`NPS`/`NSC`/`KVP`/`APY`) will continue to show "criteria not yet configured" — correct, honest behavior per Rule 4, not something this finding fabricates a fix for.
