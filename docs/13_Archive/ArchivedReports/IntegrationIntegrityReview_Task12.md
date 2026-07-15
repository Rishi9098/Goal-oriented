# Integration Integrity Review — Task 12 (Family Dashboard Integration)

**Date:** 2026-07-07
**Performed before implementation**, per instruction. New review type for this engagement — the centerpiece of Task 12, since this task's entire risk profile is integration-shaped: it writes no new business logic, so the only ways it can go wrong are duplicating logic it should reuse, contradicting a source screen, or failing badly when one source fails.

## The dashboard reuses existing services — mapped card by card, before writing code

| Card / section | Authoritative source (reused) | New logic in the dashboard layer |
|---|---|---|
| Who depends on me? | `family_service.list_members_with_completeness()` | Counting rows by `relationship_type` — tallying, not business logic. |
| Education costs ahead | `family_service.list_goals_with_tags()` (Task 8) — persisted `target_date`, tagged member names | Picking the education-category goal with the nearest future `target_date` — a `min()` over persisted dates. |
| Insurance coverage | `family_insurance_service.list_policies_with_coverage()` (Task 10) + the member list above | Set-union of covered member IDs → "N of M" — counting, not logic. |
| Parents | `family_insurance_service.uncovered_parents()` — **extracted from** `compute_insurance_recommendation()`, now shared by both | None — the exact same function the recommendation uses. |
| Retirement readiness | The retirement-category goal's **persisted** `probability`/`on_track` (from the same `list_goals_with_tags` call) | None — persisted values read out verbatim, never recomputed (ADR-001). |
| Emergency readiness | `planning_service.get_dashboard()`'s `liquid_assets` + `monthly_expenses`, passed through verbatim | None on the backend; the months figure is frontend display arithmetic per Task 9's precedent (see `DependencyValidation_Task12.md` Finding 1). |
| Recommendations feed | `family_recommendations_service.get_family_recommendations()` (Task 11) — called verbatim | None — not a new recommendation type, not a second aggregation; the feed is byte-identical to `/app/family/recommendations`. |

## No financial calculations occur during read operations

The dashboard service contains zero arithmetic beyond counting and `min()`-by-date selection. Every financial number it returns (`probability`, `target_amount`, `liquid_assets`, deduction limits inside recommendations) is a persisted value or an already-computed figure from an existing certified service. `calculate_goal_probability()` is never imported. This will be enforced by a permanent test mirroring Tasks 10/11's `test_calculation_lifecycle_untouched`.

## The dashboard remains a read-only composition layer

`GET /family/dashboard` performs no INSERT/UPDATE/DELETE on any table, persists no dashboard state (no cache rows, no snapshot rows), and calls only functions that are themselves documented read-only. Nothing about a dashboard visit changes what a subsequent visit — or any other screen — sees.

## Every card consumes authoritative data

No card computes its own version of a fact another screen owns. The two places this could have silently gone wrong were caught in Dependency Validation: the Parents card (Finding 2 — resolved by extraction, so card and feed share one function) and Emergency readiness (Finding 1 — resolved by passthrough, so the dashboard can never disagree with `/app`'s money dashboard about the underlying figures).

## Partial failures degrade gracefully

Each card's payload is independently nullable in the response schema. The service computes each section under its own `try/except`: a failure in one section logs the full error server-side (never silently swallowed — per coding standards) and returns `null` for that card while every other section still populates. The recommendations feed likewise degrades to an empty list with an explicit `recommendations_unavailable: true` flag — distinguishable from the honest "no recommendations" state, so the frontend never renders "you're all set" when the truth is "we couldn't check." The frontend renders a per-card unavailable state for `null` cards and keeps the rest of the screen fully functional.

## Loading, empty, and error states are defined for every section — before implementation

| Section | Loading | Empty | Error |
|---|---|---|---|
| Six-card grid | Skeleton cards (existing `StatSkeleton` pattern) | Per-card honest empty state (e.g., "No education goals yet", "Add income & expenses to see this") | Per-card "unavailable" state when that card is `null`; whole-query error state with retry if the request itself fails |
| Recommendations feed | Covered by the same skeleton block | "No recommendations right now" (same copy as `/app/family/recommendations`) | "We couldn't check for recommendations" when `recommendations_unavailable` — never conflated with empty |
| `/app` family card | Rendered only after data resolves (dashboard already has its own skeletons) | "It's just you right now" count of 1 renders normally | Card simply not rendered on error — the main dashboard never breaks because the family aggregate failed |

---

## Post-Implementation Integration Review (live verification addendum, 2026-07-07)

Every claim above was re-checked against the built feature, live against the running backend and Postgres:

- **All six cards rendered with real, cross-checkable data** for a household with a salary, expenses, savings, a retirement goal, a tagged education goal, an uninsured mother, and an SSY-eligible daughter: "1 kid · 1 parent" / "Riya Shah: Riya's college, ₹25,00,000 by 2038" / "0 of 3 people covered" / "⚠ Kamla Shah: no own insurance" / "4% — needs attention" / "7.5 months covered" (₹3,00,000 ÷ ₹40,000 — verifiable against the money dashboard's own stats shown on the same visit).
- **The freshness Acceptance Criterion held with one action updating three surfaces:** recording a policy covering the mother flipped the Parents card to "No insurance gaps we know of," the Coverage card to "1 of 3 people covered," and removed the insurance recommendation from the feed — all on the very next load, no manual refresh.
- **Card navigation:** tapping the Parents card landed on Family Insurance, showing the identical recommendation the feed had shown.
- **Read-only, verified at the database:** after many dashboard loads, the `recommendations` table remained at zero rows across the entire database, and both goals' persisted probabilities were byte-identical to their creation values (21.2 / 3.9) — no financial calculation, no write, occurred on any read.
- **Partial-failure degradation** is covered by two permanent tests (`test_partial_failure_degrades_gracefully`, `test_recommendations_unavailable_flag` — monkeypatching a section/the feed to raise and asserting a 200 with a null card / an explicit flag while every other section populates). Not re-induced live against the dev database, since forcing a real mid-request failure would have required corrupting shared dev state; the tests exercise the exact code path.
- **The `/app` family card** rendered quietly between the stats and cash-flow strip ("Family — 3 people · 2 suggestions to review") and navigated correctly.
