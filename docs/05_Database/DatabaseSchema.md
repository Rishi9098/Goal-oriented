# Database Schema Reference

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Companion doc:** `docs/05_Database/DatabaseArchitecture.md` — conceptual model, relationships, lifecycle, security posture. This document is the flat, lookup-style reference: every table, its migration, its owning service, and its CRUD surface.
**Supersedes:** `DatabaseSchemaBible.md` §3–4, 6, 8 (archived in full).

---

## 1. Table Inventory (36 tables)

| Table | Domain | Migration | Service | API | Status |
|---|---|---|---|---|---|
| `users` | Auth | 001 | `auth_service.py` | `/auth/*` | Active |
| `password_reset_tokens` | Auth | 004 | `routers/auth.py` | `/auth/forgot-password`, `/auth/reset-password` | Active |
| `goals` | Goals | 001, 007 (col) | `planning_service.py` | `/goals/*` | Active |
| `simulations` | Goals | 001 | `routers/simulate.py` | `/simulate` | Active (append-only, write-only — see DB-007) |
| `user_profiles` | Financial | 002 | `routers/profile.py` | `/profile` | Active (2 deprecated fields) |
| `income_sources` | Financial | 002, 006, 010 (col) | `routers/financials.py` | `/financials/income` | Active |
| `expenses` | Financial | 002, 006 | `routers/financials.py` | `/financials/expenses` | Active |
| `assets` | Financial | 002, 006, 010 (col) | `routers/financials.py` | `/financials/assets` | Active |
| `liabilities` | Financial | 002, 006, 010 (col) | `routers/financials.py` | `/financials/liabilities` | Active |
| `financial_assumptions` | Financial | 002 | `routers/assumptions.py` | `/assumptions` | Active, disconnected from Monte Carlo (known gap) |
| `households` | Family | 005 | `family_service.py` | `/family*` | Active |
| `household_members` | Family | 005, 008 | `family_service.py` | `/family/members*` | Active |
| `dependents` | Family | 005, 007, 008 | `family_service.py`, `scheme_eligibility_service.py` | `/family/members*` | Active |
| `goal_household_members` | Family | 007 | `family_service.py` | `/goals/{id}/family-tags` | Active |
| `schemes` | Schemes | 005 | `scheme_eligibility_service.py` | `/family/schemes` | Active (seeded, read-only) |
| `scheme_rates` | Schemes | 005 | none | none | **Zero consumer** |
| `scheme_eligibility_rules` | Schemes | 005 | `scheme_eligibility_service.py` | `/family/schemes` | Active |
| `tax_acts` | Schemes | 005 | none | none | **Zero consumer** |
| `tax_sections` | Schemes | 005 | `family_insurance_service.py` | `/family/insurance` | Active, narrow (one section code) |
| `tax_regimes` | Schemes | 005 | none | none | **Zero consumer** |
| `tax_slabs` | Schemes | 005 | none | none | **Zero consumer** |
| `policy_citations` | Schemes | 005 | none | none | **Zero consumer** |
| `health_policies` | Insurance | 005 | `family_insurance_service.py` | `/family/insurance*` | Active |
| `health_policy_coverage` | Insurance | 005 | `family_insurance_service.py` | `/family/insurance*` | Active |
| `recommendations` | Recommendations | 005 | none | none | **Zero consumer** (schema-only) |
| `recommendation_citations` | Recommendations | 005 | none | none | **Zero consumer** |
| **`life_events`** | Life Events | **010, 011 (col)** | `life_event_service.py` | `/life-events*` | **Active — new since the source Bible** |
| **`life_event_effects`** | Life Events | **010, 011 (col)** | `life_event_service.py` | `/life-events*` | **Active — new since the source Bible** |
| `notification_markers` | Notifications | 009 | `notification_service.py` | `/notifications*` | Active |
| `audit_logs` | Audit | 005 | `family_service.py`, `family_insurance_service.py` | none direct (write-only) | Active, no UI reader |
| `huf_entities` | Future | 005 | none | none | **Zero consumer** |
| `huf_coparceners` | Future | 005 | none | none | **Zero consumer** |
| `nominees` | Future | 005 | none | none | **Zero consumer** |
| `estate_documents` | Future | 005 | none | none | **Zero consumer** |
| `best_practice_rules` | Future | 006 | none | none | **Zero consumer** |
| `company_policies` | Future | 006 | none | none | **Zero consumer** |

---

## 2. Migration History (11 migrations)

| # | Title | What it added |
|---|---|---|
| 001 | Initial schema | `users`, `goals`, `simulations`, ENUM types |
| 002 | Financial profile | `user_profiles`, `income_sources`, `expenses`, `assets`, `liabilities`, `financial_assumptions` |
| 003 | Composite indexes | `(user_id, is_active)` indexes on 5 tables via `CREATE INDEX CONCURRENTLY` inside an `autocommit_block()` — the one migration requiring non-default Alembic handling |
| 004 | Password reset tokens | `password_reset_tokens` |
| 005 | Family/Policy/Estate/Insurance/Recommendation/Audit foundation | **20 tables in one migration** — the full Government Policy Engine, Estate/Nominee, Insurance, Recommendation schemas, `audit_logs` |
| 006 | Foundation reconciliation | `huf_entity_id` (`ON DELETE SET NULL`) on the 4 financial tables; `best_practice_rules`, `company_policies` |
| 007 | Family goal tagging | `goals.custom_inflation_rate`; `dependents.has_own_insurance`; `goal_household_members` |
| 008 | Household member identity fields | `household_members.name`; `dependents.gender`, `.relationship_detail` |
| 009 | Notification markers | `notification_markers` |
| **010** | **Life Events** | **`life_events`, `life_event_effects`** |
| **011** | **Life Event hardening** | **`life_events.idempotency_key` + unique constraint; `life_event_effects.after_updated_at`** — see `docs/02_Architecture/LifeEventEngine.md` §8 for why |

**Verified across every migration:** every one is purely additive; every `downgrade()` is the exact structural inverse of its `upgrade()`; a three-migration column build-up (`005`→`007`→`008`) is a real pattern for `dependents` specifically, worth knowing before assuming any single migration tells a table's complete current shape.

---

## 3. CRUD Matrix (abridged — see archived Bible for the exhaustive per-table version)

| Table | C | R | U | D | Soft Delete | Audit Logged |
|---|---|---|---|---|---|---|
| `goals` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `simulations` | ✅ | ❌ (never listed back) | ❌ | ❌ | N/A | ❌ |
| `income_sources`/`expenses` | ✅ | ✅ | ❌ (no PATCH — DB-008) | ❌ | ✅ | ❌ |
| `assets`/`liabilities` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `household_members` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3 actions) |
| `health_policies` | ✅ | ✅ | ✅ (coverage only) | ❌ | ✅ (flag exists, **never set — no delete endpoint**) | ✅ (2 actions) |
| `life_events` | ✅ | ✅ | ❌ (undo, not edit — see LifeEventEngine.md §6) | ❌ | ✅ (`status="undone"`) | ✅ (`AuditLog` pointer) |
| `notification_markers` | ✅ (on read/dismiss) | ✅ | ✅ | ❌ | N/A | ❌ |
| Every zero-consumer table (12 total) | ❌ | ❌ | ❌ | ❌ | N/A | ❌ |

---

## 4. Known Risks (Verified Findings, DB-001 through DB-011)

| ID | Severity | Finding |
|---|---|---|
| DB-001 | Medium | 12 tables fully migrated, zero application consumers — real schema-comprehension overhead, no functional impact. |
| DB-002 | Medium | `financial_assumptions.expected_return_*`/`tax_rate`/`retirement_age`/`social_security_monthly` are stored and user-editable with zero calculation readers — a user-facing trust gap (settings imply an effect they don't have). |
| DB-003 | Low | `tax_sections`' one real consumer doesn't filter by `effective_from`/`effective_to` despite the table's entire purpose being effective-dating — low risk today (only one seeded 80D row), a real risk the moment a second row is seeded. |
| DB-004 | Low | `household_members.role` is migrated, defaulted, never read — dead column, positive-by-absence forward-compatible schema for a future permissions feature. |
| DB-005 | Low | `health_policy_coverage` has no `UNIQUE` constraint, unlike its sibling `goal_household_members`. |
| DB-006 | Low | `health_policies.is_active` exists but no endpoint ever sets it — no delete route exists for this table. |
| DB-007 | Low | `simulations` is fully write-only — no endpoint ever lists a user's past simulation runs. |
| DB-008 | Info | `income_sources`/`expenses` have no `PATCH` endpoint, unlike `assets`/`liabilities` in the same domain — a user must delete-and-recreate to correct an entry. |
| DB-009 | Info | Every FK has an explicit `ON DELETE` clause (positive finding — no undefined delete behavior exists anywhere). |
| DB-010 | Info | `nominees.percentage_share`'s `CHECK` constraint is the only database-level numeric `CHECK` in this entire schema. |
| DB-011 | Info | The test suite documents a SQLite-vs-Postgres cascade/`SET NULL` enforcement gap; two specific behaviors were manually verified once against real Postgres rather than continuously re-verified by CI. |

---

## Related Documents
`docs/05_Database/DatabaseArchitecture.md` (conceptual model, relationships, lifecycle) · `docs/02_Architecture/LifeEventEngine.md` (`life_events`/`life_event_effects` detail) · `docs/02_Architecture/RecommendationEngine.md` (Government Schemes/Insurance domain tables)

## Related Database Tables
All 36 (this document's own subject).


## Related Tests
`test_household_policy_models.py`, `test_foundation_reconciliation.py`, plus every domain's own test file for the tables it owns.

---

*Archived original: `docs/13_Archive/ArchivedReports/DatabaseSchemaBible.md` (full column-by-column table chapters, complete ER diagram, and exhaustive per-table CRUD matrix preserved there in full).*
