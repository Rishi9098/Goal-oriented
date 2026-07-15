# PR Report — Milestone 2 Task 12: Family Dashboard Integration

**Date:** 2026-07-07

## Summary

Implements Task 12 per `Milestone2ImplementationContract.md` §12: the "who depends on me, and are we okay" view — six single-question cards plus the Task 11 recommendations feed on Family Home, and a quiet Family card on the main `/app` overview. The entire task is composition: the new backend layer contains zero financial arithmetic, no new business logic, and no writes. Its whole risk profile was integration-shaped, so a new **Integration Integrity Review** (card-by-card authoritative-source map) was the centerpiece pre-implementation review.

## Reviews Performed Before Implementation

- **Dependency Validation** (`DependencyValidation_Task12.md`): all reused services exist and are certified. Two findings, both resolved by this task's own constraints rather than judgment calls:
  - **Finding 1:** the Contract's "existing emergency-fund-months calculation" does not exist anywhere in the codebase. Inventing it would violate "no financial calculations during read operations" — so the backend passes through `get_dashboard()`'s authoritative figures and the frontend renders "X months covered" as display arithmetic (Task 9's exact precedent).
  - **Finding 2:** the Parents card's literal Contract condition would contradict the recommendations feed on the same screen (stale `has_own_insurance` vs. an on-file policy). Resolved by extracting `family_insurance_service.uncovered_parents()` from the recommendation logic — card and recommendation now share one authority and are structurally incapable of disagreeing.
- **Integration Integrity Review** (`IntegrationIntegrityReview_Task12.md`) — the centerpiece: a card-by-card table mapping every card to its authoritative source and naming exactly what "new logic" each involves (counting, set-union, min-by-date — nothing more), plus pre-defined loading/empty/error states per section.
- **Recommendation Integrity Review** (`RecommendationIntegrityReview_Task12.md`): the feed is a verbatim call to Task 11's aggregation — no re-filtering, re-ranking, or re-wording; also closes the cross-surface consistency question `RecommendationConsistencyReview_Task10.md` explicitly deferred to this task.
- **Data Integrity Review** (`DataIntegrityReview_Task12.md`): shared member snapshot for both counting cards; statelessness as the freshness mechanism; failed sections never fabricate zeros.
- **User Trust & Design Review** (`UserTrustAndDesignReview_Task12.md`): one question one answer per card; warnings only when actionable; cards are real links; the `/app` card renders nothing on error rather than breaking the money dashboard.

## Implementation

| File | Change |
|---|---|
| `backend/app/services/family_insurance_service.py` | Extracted `uncovered_parents()` + `_covered_member_ids()` (pure refactor; all 21 Task 10 tests pass unchanged). |
| `backend/app/schemas/family_dashboard.py` | New — six nullable card schemas + `FamilyDashboardResponse` with `recommendations_unavailable`. |
| `backend/app/services/family_dashboard_service.py` | New — read-only composition, per-section `_safe()` failure isolation. |
| `backend/app/routers/family.py` | New `GET /family/dashboard`. |
| `backend/tests/test_family_dashboard.py` | 14 new tests. |
| `code/src/routes/app.family.index.tsx` | New Family Dashboard section (six-card grid + compact feed). |
| `code/src/routes/app.index.tsx` | New quiet `FamilyCard` on the money dashboard. |
| `code/src/lib/api.ts` | `FamilyDashboard` type + `getFamilyDashboard()` (real + mock). |
| `docs/backend.md`, `docs/frontend.md` | Documented the composition design and both deviations. |

## Verifying the Dashboard Reuses Existing Services

Card-by-card source map in `IntegrationIntegrityReview_Task12.md`: members/goals/policies/uncovered-parents/recommendations/money-figures all come from `family_service`, `family_insurance_service`, `family_recommendations_service`, and `planning_service` as they already exist. The only service-layer change anywhere is the extraction refactor.

## Verifying No Recommendation Logic Is Duplicated

The feed calls `get_family_recommendations()` verbatim. Permanent test `test_feed_identical_to_recommendations_endpoint` asserts byte-identical output with `GET /family/recommendations`; live-verified word-for-word identical recommendation text on both surfaces.

## Verifying No Financial Calculations Occur During Read Operations

The new service contains only counting, set membership, and min-by-date selection — grep-verifiable, and `calculate_goal_probability` is never imported. Live-verified at the database: both test goals' persisted probabilities byte-identical (21.2 / 3.9) after many dashboard loads. The one figure that needed arithmetic (months covered) is frontend display arithmetic per Task 9's precedent.

## Verifying the Dashboard Remains a Read-Only Composition Layer

No INSERT/UPDATE/DELETE anywhere in the new code; the `recommendations` table confirmed at zero rows across the entire database after the live walkthrough; no dashboard-state or cache table exists (per instruction: dashboard state is never persisted).

## Verifying Every Card Consumes Authoritative Data

Live-verified all five card-vs-source pairings (see `PRODUCT_CONSISTENCY_REVIEW.md` addendum): feed vs. Recommendations screen, Parents card vs. insurance recommendation, Coverage card vs. Insurance screen, Retirement card vs. persisted goal probability, Emergency card vs. the money dashboard's own figures — checkable by eye on the same visit (₹3,00,000 ÷ ₹40,000 = "7.5 months covered").

## Verifying Partial Failures Degrade Gracefully

Two permanent tests monkeypatch a section (`get_dashboard`) and the feed to raise: the endpoint returns 200 with that card `null` / `recommendations_unavailable: true` while every other section populates; the failure is logged with full context, never silently swallowed. The frontend renders "Temporarily unavailable" for null cards and "we couldn't check" for the flagged feed — never a fake zero, never "no recommendations" when the truth is "couldn't check."

## Verifying Loading, Empty, and Error States for Every Section

Defined per-section in the Integration Integrity Review **before** implementation: skeleton grid (existing pattern) / per-card honest empty states ("No upcoming education goals", "Add income & expenses to see this", "Just you right now") / per-card unavailable states + whole-query retry / feed unavailable state / `/app` card renders nothing on error.

## Testing

```
Backend tests:     317 passed (was 303 — 14 new), 97.50% coverage,
                    family_dashboard_service.py at 100%
Frontend tsc:      Clean, 0 errors
Frontend eslint:   Clean on every touched file
Live smoke test:   Full walkthrough with real financials (₹12L salary,
                    ₹40,000/mo expenses, ₹3,00,000 savings), a retirement
                    goal, an uninsured mother, an SSY-eligible daughter,
                    and a tagged education goal. All six cards correct and
                    cross-checkable. The Contract's central Acceptance
                    Criterion held: recording one policy covering the
                    mother updated the Parents card (warning cleared),
                    the Coverage card (0→1 of 3), and the feed (insurance
                    recommendation removed) simultaneously on the next
                    load. Card navigation verified. Database checks:
                    recommendations table at zero rows; goal probabilities
                    byte-identical after many loads. Test account fully
                    cleaned up.
```

## Documentation

`PROJECT_STATE.md` (Task 12 entry + honest milestone status), `DependencyValidation_Task12.md`, `IntegrationIntegrityReview_Task12.md` (with post-implementation live addendum), `RecommendationIntegrityReview_Task12.md`, `DataIntegrityReview_Task12.md`, `UserTrustAndDesignReview_Task12.md`, `CHANGELOG.md`, `docs/backend.md`, `docs/frontend.md`, `FIRST_TIME_USER_REVIEW.md` (addendum), `PRODUCT_CONSISTENCY_REVIEW.md` (addendum).

## Coverage

Backend: 97.50% (up from 97.41%; `family_dashboard_service.py` at 100%). No frontend coverage metric exists (no test runner, consistent with prior precedent).

## Known Risks

None new. Both integration risks (card-vs-source contradiction; cascading section failure) are closed structurally and regression-tested. One pre-existing item flagged honestly in `PROJECT_STATE.md`: the Contract's §11 Schemes *screen* remains unbuilt (the user redirected Task 11 to the aggregation layer) — the schemes engine is fully consumed elsewhere, but the dedicated three-bucket browsing screen is an open Contract item awaiting a user decision.

## Rollback

Revert the new endpoint, schema, and service files, the two-function extraction in `family_insurance_service.py` (behavior-identical either way), and the two frontend surfaces. No migration to reverse — no new tables, no persisted state.

## Future Dependencies

Milestone 4's Calculation Engine can upgrade any card's underlying figure (e.g., a real emergency-months model) and the dashboard inherits it automatically, since the dashboard computes nothing itself. Milestone 5's Recommendation Engine can replace the feed's source service without the dashboard changing.

---

## Definition of Done

- [x] Dashboard reuses existing services (card-by-card source map, verified)
- [x] No recommendation logic duplicated (feed byte-identical to source endpoint — permanent test)
- [x] No financial calculations during read operations (live DB verification + permanent test)
- [x] Dashboard remains a read-only composition layer (zero writes; zero persisted state)
- [x] Every card consumes authoritative data (all five pairings live-verified)
- [x] Partial failures degrade gracefully (two permanent monkeypatch tests; per-card null degradation)
- [x] Loading, empty, and error states defined for every section (pre-implementation, then built)
- [x] Reused Family Recommendation / Insurance / Scheme Eligibility / Goal / Household services
- [x] No parallel business logic (one extraction, zero new authorities)
- [x] Dashboard state never persisted
- [x] Live verification, First-Time User Review, Product Consistency Review, Integration Review all run
- [x] Documentation updated
- [x] Tests pass (317/317 backend; tsc/eslint clean)

**Stopping here per instruction. The next milestone has not been started and requires separate review/approval before beginning.**
