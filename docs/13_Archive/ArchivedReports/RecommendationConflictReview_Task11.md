# Recommendation Conflict Review — Task 11 (Family Recommendations)

**Date:** 2026-07-07
**Performed before implementation**, per instruction. This is a new review type for this engagement — the first task aggregating more than one recommendation source.

## What counts as a genuine conflict (defined before writing code)

Two recommendations are flagged as conflicting only if they (a) share at least one subject (household member) **and** (b) reference the same underlying deduction/scheme ceiling — i.e., they would compete for the same bounded resource if a user tried to act on both. This is deliberately **narrower** than "same person, multiple recommendations": Task 10's insurance recommendation (80D, health-premium deduction) and a scheme recommendation (SSY/SCSS, both 80C/123-linked, per `GovernmentPolicyReport.md`'s table) about the *same* person are **not** flagged — they're compatible, complementary advice about different tax sections, not competing claims on the same ceiling. Flagging that pairing as a "conflict" would be a false positive that confuses the user about a tension that doesn't exist.

Each `FamilyRecommendation` carries a `reference_code` ("80D" for insurance; "80C/123" for SSY/SCSS, both verified as drawing from the same combined ceiling per the cited report) — conflict detection groups by `(subject, reference_code)` and flags any group with more than one entry.

## Do the two current sources ever actually conflict?

**No, and this is confirmed by construction, not assumed.** SSY only ever matches a child under 10 (category `child`); SCSS only ever matches someone 60+ (category `senior`). A single household member cannot be both simultaneously, so two 80C/123-linked scheme recommendations can never target the same subject with the currently seeded data. The insurance recommendation (80D) never shares a `reference_code` with either scheme recommendation. **Verified conclusion: the conflict-detection function will correctly return an empty list for every realistic household composition today** — this is stated honestly here rather than fabricating a scenario to "prove" the feature does something. The mechanism itself is real, general, and would correctly catch a genuine future case (e.g., a third 80C-linked scheme being added later, or a data anomaly matching one person to both SSY and SCSS).

## How a real conflict would be resolved if one existed

**Never by silently picking a winner.** Per instruction ("do not hardcode recommendation priorities"), if a conflict were ever detected, both recommendations remain in the response — the conflict entry is additive metadata (which subject, which sources, why they overlap), not a suppression mechanism. The user always sees every recommendation a source legitimately produced; the conflict note exists to add context, not to hide one option in favor of another.

## Recommendation engines remain independent — verified by construction

`family_recommendations_service.py` (new, aggregation-only) calls `family_insurance_service.compute_insurance_recommendation()` and `scheme_eligibility_service.evaluate_household_eligibility()` exactly as they already exist — neither function is modified to know about the other, and neither is modified to know about conflict detection. The aggregation layer sits strictly above both, converting each source's own native output into a shared `FamilyRecommendation` envelope after the fact. A source can be added or removed without either existing engine changing.

## Aggregation does not duplicate logic

The aggregation service performs zero eligibility math and zero deduction-figure computation of its own — every `why`/`why_now`/`what_used`/`what_missing`/`confidence_score` value is read directly from what the underlying engine already computed (Task 10's `InsuranceRecommendation`, Task 3's `EligibilityResult.reason`), reformatted into the shared envelope, never recomputed.

## Live-verification addendum (post-implementation, 2026-07-07)

Ran the actual scenario predicted above: a household with a parent (Meera Kapoor, no recorded insurance, no DOB) and a 7-year-old daughter (Priya Kapoor, gender female — SSY-eligible). `GET /family/recommendations` returned both recommendations simultaneously (`source: "insurance"` and `source: "schemes"`), and **`conflicts` was correctly empty** — confirmed live, not just by the 4 automated `TestConflictDetection` unit tests. This is the exact "same household, two sources, different people, different reference codes" case the design predicted would never conflict, and it didn't.
