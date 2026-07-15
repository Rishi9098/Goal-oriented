# API Reference — Quick Lookup

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Purpose:** a fast, single-table lookup from endpoint → owning service → primary table(s) → frontend consumer, for an engineer who already knows roughly what they're looking for. For narrative detail, see `docs/04_API/RESTAPI.md` (the full endpoint contract) and `docs/04_API/ServiceInteractions.md` (cross-service call graph).
**Supersedes:** the API/Service/Database Index sections of `EngineeringKnowledgeIndex.md` (archived in full — that document's other sections feed `docs/03_Engineering/EngineeringHandbook.md`).

---

## Quick Lookup Table

| Domain | Router | Primary Service | Primary Table(s) | Frontend |
|---|---|---|---|---|
| Auth | `auth.py` | `auth_service.py` | `users`, `password_reset_tokens` | `routes/auth.*.tsx` |
| Goals | `goals.py` | `planning_service.py` | `goals` | `app.goals.tsx`, `GoalSimPanel.tsx` |
| Dashboard | `dashboard.py` | `planning_service.py` | reads goals/assets/liabilities/income/expenses | `app.index.tsx` |
| Simulation | `simulate.py` | `monte_carlo.py`, `optimizer.py` | `simulations` | `GoalSimPanel.tsx` |
| Financials | `financials.py` | inline | `income_sources`, `expenses`, `assets`, `liabilities` | `app.financials.tsx` |
| Assumptions | `assumptions.py` | inline | `financial_assumptions` | Onboarding, Settings |
| Profile | `profile.py` | inline | `user_profiles` | `app.profile.tsx` |
| Family core | `family.py` | `family_service.py` | `households`, `household_members`, `dependents` | `app.family.*.tsx` |
| Schemes | `family.py` | `scheme_eligibility_service.py` | `schemes`, `scheme_eligibility_rules`, `scheme_rates` | `app.family.schemes.tsx` |
| Insurance | `family.py` | `family_insurance_service.py` | `health_policies`, `health_policy_coverage`, `tax_sections` | `app.family.insurance.tsx` |
| Recommendations | `family.py` | `family_recommendations_service.py` | reads only | `app.family.recommendations.tsx` |
| Family Dashboard | `family.py` | `family_dashboard_service.py` | reads only | `app.family.index.tsx` |
| Notifications | `notifications.py` | `notification_service.py` | `notification_markers` | `notification-center.tsx` |
| **Life Events** | **`life_events.py`** | **`life_event_service.py`** | **`life_events`, `life_event_effects`** | `app.life-events.tsx`, `RecordLifeEventDialog.tsx` |
| AI Copilot | `copilot.py` | inline (no service file — deliberate exception) | reads `goals` | `app.copilot.tsx` |
| Reports | `reports.py` | reuses `planning_service.get_dashboard` | reads only | `app.reports.tsx` |

## Zero-Consumer Tables (schema exists, no router/service reads or writes them)

`scheme_rates`, `tax_acts`, `tax_regimes`, `tax_slabs`, `policy_citations`, `recommendations`, `recommendation_citations`, `huf_entities`, `huf_coparceners`, `nominees`, `estate_documents`, `best_practice_rules`, `company_policies` — see `docs/05_Database/DatabaseSchema.md` §1 and `docs/05_Database/DatabaseArchitecture.md` §5 for why each exists ahead of its own milestone.

---

## Related Documents
`docs/04_API/RESTAPI.md`, `docs/04_API/ServiceInteractions.md`, `docs/05_Database/DatabaseSchema.md`, `docs/03_Engineering/EngineeringHandbook.md`.


## Related Tests
See `04_API/RESTAPI.md` and `04_API/ServiceInteractions.md` — this document is a lookup table, not an independent claim needing its own test cross-reference.

---

*Archived original: `docs/13_Archive/ArchivedReports/EngineeringKnowledgeIndex.md` (full 96KB file/service/API/database/frontend index preserved there — sections §2–4, §11 feed the Engineering Handbook; §5–10 fed this document and `RESTAPI.md`/`ServiceInteractions.md`).*
