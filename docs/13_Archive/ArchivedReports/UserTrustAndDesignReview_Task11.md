# User Trust Review & Design Review — Task 11 (Family Recommendations)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

---

## User Trust Review

**Does the user understand these come from two different, independent checks?** Each recommendation card is labeled by its own source context (an insurance-shaped card vs. a scheme-shaped card, matching Task 10's and the SSY callout's existing visual language respectively) rather than merged into one generic, unattributed list — a user who already trusts the insurance card from Task 10 recognizes the same shape here, not a new unfamiliar format.

**Does the user understand why there's no "conflict" notice, given two recommendations might be about the same person?** Since a genuine conflict never fires with the current two sources (per `RecommendationConflictReview_Task11.md`), there is nothing to reassure the user about in the common case — two independent, compatible recommendations about the same parent (e.g., an insurance suggestion and a scheme match) simply appear as two separate, clearly-labeled cards. Nothing in the copy implies they're in tension, because they aren't.

**If a conflict were ever shown:** it would read as a plain, factual note ("both of these concern the same combined tax ceiling — you may not be able to claim both in full"), never a warning that either recommendation is wrong. Neither is suppressed.

---

## Design Review

**Reuses each source's own established visual language**, not a new generic "recommendation" template — the insurance card looks like Task 10's; the scheme card reuses the same icon/tone the existing SSY callout (Task 6/7/9/10) already established. A user who has seen either before recognizes it immediately here.

**Progressive disclosure carried forward from Task 10** — the same collapsed `<details>` "what we used / what we don't know yet" pattern is reused verbatim for both source types, not reinvented per-source.

**Never overwhelms:** if a household has neither an insurance nor a scheme match, the screen shows a single, honest empty state — not two separate empty sections stacked, which would read as noisier than the actual "nothing to show yet" reality.

**Accessibility:** Standard Baseline, matching every prior Family screen. Each recommendation card is a semantic region (`role="status"`), consistent with Task 10.
