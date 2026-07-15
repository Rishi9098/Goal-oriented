# Service Interactions

**Status:** Canonical · **Last verified against code:** 2026-07-09
**Supersedes:** `APIServiceInteractionBible.md` §4–6, §9–14 (archived in full).
**Companion doc:** `docs/04_API/RESTAPI.md` (endpoint inventory, auth, validation).

---

## 1. Cross-Service Calls (every one, verified exhaustively by reading every service's imports)

| Caller | Callee | Purpose |
|---|---|---|
| `planning_service.calculate_goal_probability` | `monte_carlo.quick_probability_async` | Compute and persist a goal's probability |
| `routers/simulate.py` (`optimize`) | `optimizer.generate_suggestions` | Ranked suggestions |
| `optimizer.generate_suggestions` | `monte_carlo.quick_probability` | Evaluate each candidate change |
| `family_insurance_service.compute_insurance_recommendation` | `family_service.resolve_member_name` | Resolve a subject's display name |
| `family_insurance_service` | `scheme_eligibility_service.age_years` | Senior-citizen (60+) determination — reused, not reimplemented |
| `family_recommendations_service._insurance_recommendations` | `family_insurance_service.compute_insurance_recommendation` | Source insurance recommendations |
| `family_recommendations_service._scheme_recommendations` | `scheme_eligibility_service.evaluate_household_eligibility`, `age_years` | Source scheme recommendations |
| `family_dashboard_service._parents_card` | `family_insurance_service.uncovered_parents` | Same authority as the insurance recommendation — never disagree |
| `family_dashboard_service._emergency_card` | `planning_service.get_dashboard` | Reuse the Dashboard's own figures verbatim |
| `family_dashboard_service.get_family_dashboard` | `family_recommendations_service.get_family_recommendations` | Compose the recommendations feed |
| `notification_service._collect_insurance_fact` | `family_insurance_service.compute_insurance_recommendation` | Same live call the Insurance page makes |
| `notification_service._collect_scheme_facts` | `scheme_eligibility_service.evaluate_household_eligibility` | Same live call the Schemes page makes |
| `notification_service._collect_family_member_added_facts` | `family_service.resolve_member_name` | Resolve the notification's display name |
| `routers/goals.py` (`set_goal_family_tags`) | `family_service.set_goal_household_tags` | The one place Goals calls into a different domain |
| `life_event_service.py`'s 18 handlers | `financials_service`, `family_service`, `planning_service`'s existing update paths | Every life-event effect reuses an existing write path — see `docs/02_Architecture/LifeEventEngine.md` §2 |

**What is verified to *never* happen, exhaustively, by grep:** `family_service.py`, `monte_carlo.py`, and `scheme_eligibility_service.py` never call any other service (true leaves). `planning_service.py` never calls any Family-domain service, despite `family_dashboard_service.py` calling *into* `planning_service` — the dependency is strictly one-directional.

---

## 2. Read vs. Write Classification

| Endpoint pattern | Classification | Why |
|---|---|---|
| `GET /goals`, `GET /goals/{id}` | Pure Read | Direct filtered `SELECT` |
| `POST /goals` | Write + Calculation | Insert + unconditional Monte Carlo |
| `PATCH /goals/{id}` | Write + conditional Calculation | Monte Carlo only if Calculation Context intersects |
| `DELETE /goals/{id}` | Pure Write | Soft-delete flag flip |
| `GET /dashboard`, `GET /reports/summary` | Read + Aggregation | Independent reads, summed/weighted in Python, zero persistence |
| `POST /simulate` | Write + Calculation | Full Monte Carlo + `INSERT simulations`, never touches `goals` |
| `POST /simulate/optimize` | Read + Calculation | Up to 6 Monte Carlo calls, zero persistence |
| `GET /family/insurance`, `/schemes` | Read + Calculation | Computed fresh every call, never persisted |
| `GET /family/recommendations`, `/dashboard` | Read + Aggregation | Composes already-live calculations, persists nothing |
| `GET /notifications` | Read + Aggregation | Unions 5 live sources against markers — verified, test-enforced, to never write |
| `POST /notifications/.../read`, `.../dismiss` | Pure Write | The only two writes in the Notifications domain |
| `POST /life-events`, `POST /life-events/{id}/undo` | Write + multi-entity, transactional | The one API surface where a single call routinely writes to more than one table |
| `POST /life-events/preview` | Read (transaction always rolled back) | Runs the identical diff logic as `record`, never commits |

**Why this classification matters:** every "Read + Calculation" row represents a deliberate trade — a small, repeated computation cost in exchange for never showing a stale number. The same trade-off was made independently, in the same direction, across four unrelated domains (Insurance, Schemes, Notifications, and later Life Events' preview step) by different phases of this project's history, none reusing code from the others, all arriving at the identical architectural answer.

---

## 3. Engineering Decisions

- **Why routers stay thin:** concentrating business logic in one layer means the Calculation Lifecycle rule can be *structurally* enforced — a router cannot contain the recalculation branch, because that branch lives in `planning_service.py`, referenced by name, not reimplemented per call site.
- **Why services own business logic:** every composition service (`family_recommendations_service.py`, `family_dashboard_service.py`) explicitly documents zero calculation of its own — possible only because the calculation-owning services are callable, reusable functions, not logic embedded in one endpoint handler.
- **Why recommendations aren't stored:** persisting recommendation content would require either a background job to keep it synchronized (infrastructure this codebase doesn't have) or accepting silent staleness — both worse than recomputing fresh.
- **Why calculations are centralized:** `planning_service.calculate_goal_probability` is the single point of truth specifically so `GET /dashboard` and `GET /reports/summary` can be *tested* to agree exactly — a guarantee only possible because both call the identical underlying function.
- **Why the Family domain has an audit trail and Goals/Financials don't:** Family was first to anticipate genuine compliance weight (HUF, nomination, estate concerns) — a scope decision made once, early, not yet revisited to extend to the other two domains. A real, open gap, not a permanent boundary.

---

## Related Documents
`docs/04_API/RESTAPI.md` · `docs/02_Architecture/CalculationEngine.md` · `docs/02_Architecture/RecommendationEngine.md` · `docs/02_Architecture/LifeEventEngine.md` · `docs/03_Engineering/ArchitectureDecisionRecords.md` (ADR-001, ADR-005)

## Related Services
Every service named above.


## Related Tests
One test file per service named in §1's table — e.g. `test_family_recommendations.py` for `family_recommendations_service.py`.

---

*Archived original: `docs/13_Archive/ArchivedReports/APIServiceInteractionBible.md`.*
