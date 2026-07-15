# Blocker Report — Task 5 (Family Home Screen)

**Date:** 2026-07-07
**Purpose:** Dependency validation performed before writing any code, per instruction. Distinguishes Task 5's own certified scope (not blocked) from the expanded 8-section "Family Financial Dashboard" this turn's brief describes (partially blocked on unbuilt future tasks).

---

## Dependency Validation Results

| Dependency | Status |
|---|---|
| Task 2 APIs exist | ✅ Confirmed. `GET /api/v1/family`, `POST/PUT/GET/DELETE /api/v1/family/members[/{id}]` all present in `backend/app/routers/family.py`, certified and tested (26 tests, Task 2). |
| Task 4 onboarding produces compatible data | ✅ Confirmed. `POST /family/onboarding-seed` creates `self` + one row per "Yes" answer, matching `GET /family`'s response shape exactly. Live-verified twice already this session (PCA-2, and again during this review's own dependency checks). |
| Stabilization Sprint changes respected | ✅ Confirmed. `api.getFamilyHome()` (added during PCA-2) already wraps `GET /api/v1/family` with the exact shape Task 5 needs — will be reused, not reimplemented. |
| No deprecated fields consumed | ✅ Confirmed. Task 5's certified data sources (`households`, `household_members`, `dependents`) never touch `marital_status`/`dependents`(profile)/`tax_rate`. |

**Task 5's own certified scope (per `Milestone2ImplementationContract.md` §2 and `FamilyPlanningDesign.md` Part 4.1) is NOT blocked.** It proceeds below.

## Genuine Blockers — Sections Requested This Turn That Exceed Task 5's Certified Scope

This turn's brief asks for 8 sections framed as a full "Family Financial Dashboard": Family Members, Household Summary, Upcoming Family Goals, Insurance Status, Government Scheme Eligibility, AI Recommendations, Recent Changes, Quick Actions. Cross-checked each against the actual current backend (`grep` across `backend/app/routers/`, not assumption):

| Requested section | Backing API | Status |
|---|---|---|
| Family Members | `GET /api/v1/family` | ✅ Exists (Task 2, certified) |
| Household Summary | `GET /api/v1/family` (same payload) | ✅ Exists — a presentation of the same data, not a new source |
| Upcoming Family Goals | `PUT /goals/{id}/family-tags`, `GET /family/goals` | ❌ **Does not exist.** This is Task 8's scope, not yet implemented. `grep` for `family-tags` across `backend/app/routers/` returns zero matches. |
| Insurance Status | `GET /family/insurance` | ❌ **Does not exist.** Task 10's scope. Zero matches for `family/insurance`. |
| Government Scheme Eligibility | `GET /family/schemes` | ❌ **Does not exist as a callable endpoint.** Task 3's `scheme_eligibility_service` exists and is certified, but it is only invoked today from inside the member-add/update flow (the inline SSY callout) — no standalone route exposes household-wide eligibility yet. That route is Task 11's scope. Zero matches for `family/schemes`. |
| AI Recommendations | `GET /family/dashboard` (or Milestone 5's Recommendation Engine) | ❌ **Does not exist.** Confirmed no `recommendations` are populated anywhere for Family — `best_practice_rules`/`company_policies` remain empty per the Foundation Reconciliation, by design. This is explicitly a Milestone 5 concern per `Milestone2ImplementationContract.md` §12's own text. |
| Recent Changes | *(no equivalent endpoint)* | ❌ **No certified data source exists at all.** `audit_logs` is an internal table with no user-facing read endpoint anywhere in the certified API surface. Not part of any Task 1-12 spec. |
| Quick Actions | Navigation only (no new API needed) | ✅ Buildable, with one nuance: the Contract's own Task 5 Acceptance Criteria say tapping an incomplete card should "navigate directly into that member's Add flow" — that flow is Task 6's scope, not yet built. |

## Resolution

Per this turn's own instruction ("No backend work unless a verified blocker is discovered" and "Do not begin Task 6") and the explicit Data Rules ("Consume ONLY certified APIs," "Do not infer relationships," "Display exactly what the backend returns"), building Upcoming Family Goals, Insurance Status, Government Scheme Eligibility, AI Recommendations, or Recent Changes with real data is not possible without either (a) writing new backend endpoints — forbidden, since that is Tasks 8/10/11/12's work, not Task 5's — or (b) fabricating/inferring data on the frontend — forbidden by this turn's own Data Rules and the exact principle (`PRODUCT_PRINCIPLES.md` #7) the entire Stabilization Sprint was just built around.

**Decision:** implement Task 5's full certified scope (Family Members, Household Summary, Quick Actions, all real, all from certified APIs) to the highest possible quality — this is not a reduced or partial delivery of Task 5 itself, Task 5 was never specified to include the other five sections. For the five sections that belong to later tasks, render an honest, clearly-labeled "coming soon" teaser card per section — stating plainly what it will show and which task builds it — rather than either fabricating content or silently omitting five of the eight sections this turn asked for without explanation. This is the same "state the real limitation in plain language" pattern this product's own voice already established during PCA-1 and PCA-2, applied here to a forward-looking capability gap rather than a backward-looking inconsistency.

This is not a hard stop. Implementation proceeds below with this scope understood and documented.
