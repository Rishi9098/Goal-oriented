# Recommendation Integrity Review — Task 10 (Family Insurance)

**Date:** 2026-07-07
**Performed before implementation**, per instruction. This is the first task in this engagement to produce a genuine, user-facing financial recommendation (as opposed to a fixed eligibility callout like SSY) — the bar for this review is correspondingly higher.

---

## 1. Insurance recommendations come only from verified rules

The recommendation is a **calculation-lite fact application**, not a model: it applies exactly two verified figures —

- **₹25,000** — the base 80D health-insurance-premium deduction ceiling for a self/spouse/children floater. Sourced from the seeded `tax_sections` table (`section_number='80D'`, live-queried, not hardcoded) — verified present in this dev DB before writing any code.
- **₹50,000** — the senior-citizen-enhanced ceiling for a standalone parent policy, derived as `base_limit × 2`, per `FamilyHUFPlanningReport.md` line 24 and `GovernmentPolicyReport.md` line 45 (both independently confirm the 2× relationship). Not a second hardcoded literal — computed structurally from the one verified base figure.

No other number, threshold, or claim in this recommendation is invented. The recommendation's *existence* (whether it fires at all) is driven entirely by the household's actual, stored data (`has_own_insurance`, existing `health_policies`/`health_policy_coverage`) — never by a heuristic, a model score, or an assumed default.

## 2. No recommendation is presented without an explanation

Every recommendation the service can return carries four mandatory fields, always populated (never optional or silently blank):

- **`why`** — the concrete financial fact (the deduction opportunity), naming the specific parent(s) it applies to.
- **`why_now`** — the specific trigger condition that fired *for this household, today* (which parent, what their recorded status is, whether they're currently covered by any policy on file).
- **`what_information_was_used`** — an explicit list of the exact data points consulted (each parent's `has_own_insurance` answer, their age if known, the count of existing policies checked).
- **`what_information_is_missing`** — an explicit list of any gaps that limit the recommendation's precision (see §3).

There is no code path that returns a recommendation object with any of these fields empty, null, or omitted. If the underlying data can't support a recommendation at all (no eligible parent, or the verified `TaxSection` figure can't be found), the response's `recommendation` field is `null` — never a partially-explained recommendation.

## 3. Missing information never produces fabricated advice

Two specific missing-information cases are handled explicitly, not silently guessed:

- **Parent's date of birth unknown → senior-citizen status unknown.** The recommendation still fires (the base ₹25,000 opportunity is real regardless of age), but cites only the **base** ₹25,000 figure, explicitly lists "date of birth" under `what_information_is_missing`, and states in `why` that the ceiling *could* be as high as ₹50,000 once age is confirmed — phrased as a possibility, never asserted as fact. `confidence_score` is set lower (0.7) than the fully-known case (1.0) specifically to reflect this genuine uncertainty in the *figure*, not the underlying recommendation.
- **The verified `TaxSection` row itself is missing** (e.g., an environment where the seed script hasn't run). The service returns `recommendation: null` rather than fabricating a figure from memory — no hardcoded fallback number exists anywhere in the code for this case.

Neither case invents a number, rounds a real one differently, or presents a guess as a verified fact.

## 4. Existing calculation lifecycle remains unchanged

This recommendation is **read-only and computed fresh on every `GET`**, deliberately **not** persisted to the `recommendations` table on every view. This is a considered decision, not an oversight:

- The underlying computation is a pure, deterministic function of current household state (unlike Monte Carlo probability, it has no RNG, no stochastic element, no reason to drift between identical inputs) — recomputing on read carries none of the risk ADR-001 was written to eliminate.
- Writing a `Recommendation` row on every `GET` would itself reintroduce exactly the "reads mutate stored data" anti-pattern this whole engagement's Stabilization Sprint (ADR-001, PCA-3) was built to remove. A read endpoint with a write side-effect is precisely the shape of bug PCA-3 found.
- `Milestone2ImplementationContract.md` §10's own Data Sources section never lists `recommendations`/`recommendation_citations` as read or write targets for this screen — only `health_policies`/`health_policy_coverage`/`household_members`.

"Reusing existing recommendation infrastructure" is satisfied by reusing the **shape** the `Recommendation` model was designed around (reasoning + confidence + alternatives + assumptions, extended here to the four explicit WHY/WHY NOW/USED/MISSING fields this task requires) as a plain, computed response schema — not by writing a new DB row per page view. `goal.probability`/`on_track` (the actual Calculation Lifecycle ADR-001 governs) are untouched by anything in this task; this service never calls `calculate_goal_probability()`.

## 5. Government schemes and insurance remain separate concepts

Confirmed no shared table, no shared evaluation function, no shared response schema between `scheme_eligibility_service.py` (SSY/SCSS/PMVVY, Task 3/11) and the new `family_insurance_service.py` (80D, Task 10). The only crossing point is the pure `age_years()` arithmetic helper (promoted from private to public) — domain-agnostic date math, not scheme-evaluation logic. `Scheme`/`SchemeEligibilityRule`/`SchemeRate` are never read by this task; `TaxSection`/`health_policies`/`health_policy_coverage` are never read by scheme evaluation. The two concepts remain exactly as distinct as they were before this task.

---

## Conclusion

No blocker. All five verification points hold under the design described above. Proceeding to Data Integrity Review, User Trust Review, and Design Review.
