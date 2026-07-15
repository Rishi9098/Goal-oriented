# Life Event Engine

**Status:** Canonical · **Last verified against code:** 2026-07-13 (router, hardening migration, and idempotency/locking code paths directly re-inspected this pass)
**Supersedes:** `LifeEventEngineArchitecture.md` (design, archived), `LifeEventArchitectureValidation.md`, `LifeEventEngine_FinalReleaseAudit.md`, `LifeEventEngine_PhaseA_ImplementationReport.md`, `LifeEventEngine_BackendHardeningReport.md`, `LifeEventAPI_ImplementationReport.md`, `LifeEventEngine_ProgressMatrix.md`, `TransactionConsistencyImplementationPlan.md`, `LifeEventIntegrationReview.md`, `LifeEventIntegrationReport.md`, and 16 per-event-type implementation reports (kept as a linked appendix, §7, rather than dissolved into this document's prose — each retains standalone reference value for its own event type's field/effect contract).
**Method:** every claim below was checked against the live codebase this pass, not inherited from any single prior report on faith — in particular, this document resolves a real, serious discrepancy between two prior reports (§8) by re-reading the current source directly.

---

## 1. Why This Exists

A user who gets a raise, has a child, or pays off a mortgage previously had to know which of Financials' four sections, Family, and Goals were affected, open each separately, and trust they didn't forget one. A Life Event is **not a new calculation engine** — every number it produces is computed by machinery that already exists (`get_financial_context`, `calculate_goal_probability`, `family_recommendations_service`, `notification_service`). It is an **orchestration and narration layer**: it asks one real-world question ("What happened?") and translates the answer into the same writes a careful user would have made by hand across Financials/Family/Goals — atomically, previewed before committing, and reversibly.

This is a direct, fifth application of this codebase's own most consistently reapplied principle: **compute live, never persist a derived value, and centralize every write path in one service.**

---

## 2. Core Architectural Principle

**A Life Event is a named, versioned recipe that writes to existing entities through existing service functions.** It never computes anything a service doesn't already compute, and never introduces a second path to a calculation ADR-001/ADR-005 already centralized:

- Writing a `Goal`'s calculation-context field still goes through the exact same `CALCULATION_CONTEXT_FIELDS` trigger `routers/goals.py` already uses — the engine calls the same `update_goal` code path, so the trigger fires by construction, not a second copy of the rule.
- Writing an `IncomeSource`/`Expense`/`Asset`/`Liability` triggers **nothing** directly — `get_dashboard`/`get_financial_context`/every recommendation rule is computed fresh on every read (ADR-001/ADR-005), so the next `GET /dashboard` already reflects it with zero cache to invalidate.
- Writing a `HouseholdMember`/`Dependent` reuses `family_service.create_member`/`update_member`/`remove_member` exactly as `routers/family.py` already does — several events (Marriage, Birth of Child, Adoption) get their notification **for free**, zero new notification code, purely by reusing the existing `family_member_added` `AuditLog` write.

---

## 3. Data Model (additive only)

```
life_events
  id, user_id, event_type, occurred_on, recorded_at, inputs (JSON),
  status ("applied"|"undone"), undone_at, notes, is_active,
  idempotency_key (nullable, UNIQUE(user_id, idempotency_key) — added in the hardening pass, §8)

life_event_effects
  id, life_event_id FK CASCADE, entity_table, entity_id, change_type ("create"|"update"|"soft_delete"|"reactivate"),
  before_state (JSON), after_state (JSON), created_at,
  after_updated_at (nullable — the row-level fingerprint added in the hardening pass, §8)
```

**Why two tables, not one JSON blob:** a single event routinely touches more than one entity (House Purchase creates an `Asset` *and* a `Liability`). Recording each touched row as its own effect is what makes **partial, guarded undo** possible.

**Relationship to `AuditLog`:** every life event also writes one lightweight `AuditLog` row (`action="life_event_recorded"`) so generic `AuditLog` scanners keep a hook — a two-line courtesy pointer, not a second source of truth.

---

## 4. The Orchestration Service — `life_event_service.py`

```
async def preview_life_event(db, user, event_type, inputs) -> LifeEventPreview
async def record_life_event(db, user, event_type, inputs, idempotency_key=None) -> LifeEvent
async def undo_life_event(db, user, life_event_id, force=False) -> UndoResult
async def list_life_events(db, user) -> list[LifeEvent]
```

`preview` and `record` share the identical entity-diff logic — the preview path runs inside a transaction that is always rolled back, never committed, so the preview a user sees is never a lie. Every `record_life_event` call runs inside one database transaction: any sub-write failure rolls back the whole event, so a user never ends up half-applied (e.g. a `Liability` with no matching `Asset` for a failed House Purchase) — a stronger atomicity guarantee than manually editing four sections by hand ever gave.

**Handler registry:** `_HANDLERS: dict[str, LifeEventHandler]`. Adding a new event type is a two-line diff (one handler class, one registration) with zero changes to the generic engine — confirmed genuinely good architecture by the release audit (§8); three of the 17 originally-implemented events (Adoption, Business Start, Business Sale) required **zero new service code**, composing exclusively from prior extractions.

**`occurred_on` is metadata, not a time machine:** no calculation in this codebase is date-of-event-aware — a life event backdated six months does not retroactively recompute anything as of that past date. Stated explicitly so no future implementer promises backdated recalculation the Monte Carlo engine was never built to do.

---

## 5. The 18 Event Types

**Originally designed: 15.** Three were added later without a design-doc update (Bonus, Caring for a Parent/"Dependent Parent", Education Planning) — confirmed present today via the frontend picker and their own implementation reports. **18 total, all implemented and all reachable via the API (§8).**

| Category | Events |
|---|---|
| Income & Career | Salary Raise, Job Change, Bonus, Retirement |
| Family | Marriage, Divorce, Birth of Child, Adoption, Caring for a Parent |
| Housing | House Purchase, Home Sale, New Loan |
| Major Purchases & Windfalls | Inheritance, Business Start, Business Sale, Major Medical Event |
| Debt | Loan Payoff |
| Planning | Education Planning |

Every event follows the same shape: **Trigger → Required/optional inputs → Entities changed → Calculations rerun (usually none directly — the live-read model means only a genuine `CALCULATION_CONTEXT_FIELDS` touch reruns Monte Carlo) → Recommendations that update (on next read, zero new logic) → Notifications (usually free, via the existing `family_member_added`/`goal_at_risk`/`goal_completed` collectors, or the one new generic `_collect_life_event_facts` collector, §6) → Undo/edit → Audit trail → UI flow.**

**Representative examples** (full per-event detail in the archived reports, §7):

- **Loan Payoff** — the simplest: one entity (`liabilities`, soft-deleted), one effect, a one-click flow, celebratory notification tone mirroring the existing "✓ [Goal] fully funded" pattern. Deliberately scoped to full closure only — a partial payoff is already well-served by ordinary Financials editing.
- **House Purchase** — the most structurally involved of the "compound" events: `Asset` + `Liability` create, optional down-payment reduction on a liquid asset, optional goal-linking (which reruns Monte Carlo, since `current_amount` is a calculation-context field).
- **Retirement** — the most structurally distinct: a status transition rather than a single write, touching Profile, Income, Assumptions, and optionally multiple goals in one transaction; the longest UI flow of the eighteen, deliberately broken into labeled sub-sections.
- **Business Start** — deliberately creates **no** `income_sources` row (a business commonly precedes any revenue; inventing a $0 income row would misrepresent the household's actual finances) — a documented non-goal, not an oversight.
- **Adoption** — identical household-model effects to Birth of Child; the current schema has no field distinguishing "born into" vs. "adopted into" the family, and this design does not invent one speculatively — the distinction lives only at the `life_events.event_type` level for history/reporting.

**Notably out of scope by design (§9 of the original architecture, still true today):** no automatic event detection from bank imports or AI inference — every event is user-initiated and user-confirmed; no multi-user approval workflow (no shared household login exists); no retroactive recalculation as of a past date; no new recommendation rules invented to fill perceived gaps (e.g. Business Start has no employment-status-aware recommendation — named as a future candidate, not built speculatively).

---

## 6. Cross-Cutting: Notifications, Undo, Audit

**Notifications:** exactly one new collector (`_collect_life_event_facts`), structurally identical to the pre-existing `_collect_family_member_added_facts` — every event's notification reduces to either this one generic collector or an existing collector that already fires for free (a member add, a goal reaching its target, a liability's high-interest rule). The only genuinely new *logic* is two small, live, read-only "review" checks added for Divorce (coverage/nominee review prompts) — following the identical `_Fact`-producing shape as every other collector.

**Undo — one generic mechanism, not eighteen bespoke ones:**
```
for effect in event.effects (reverse order):
    current = load the live row
    if current's state doesn't match effect.after_state OR the row's updated_at has changed since (§8):
        conflict — block this effect, list it
    else: apply effect.before_state back (or reactivate/soft-delete as the inverse)
if conflicts and not force: return blocked, with the specific conflicting rows named
else: mark undone, commit
```
**Edit is not a separate code path** — presented to the user as undo-then-re-record with corrected inputs, avoiding a second parallel "amend in place" mutation path for 18 different entity shapes.

**Audit trail:** for any past life event, the system can answer precisely (a) what the user said happened, (b) exactly which rows changed and how, (c) whether it's since been undone, (d) whether undoing it now would be safe — a strictly stronger guarantee than the generic `AuditLog` table alone provides.

---

## 7. Per-Event Implementation Reports (linked appendix)

Full field-level detail, entity effects, and test coverage for each event type is preserved in its own archived report rather than dissolved into this document — each remains a genuine, standalone reference for that event type's specific contract:

`docs/13_Archive/ArchivedImplementationReports/LifeEvent_{Adoption,BirthOfChild,Bonus,BusinessSale,BusinessStart,DependentParent,Divorce,EducationPlanning,HomeSale,HousePurchase,Inheritance,JobChange,MajorMedicalEvent,Marriage,NewLoan,PhaseB1(LoanPayoff),Retirement,SalaryRaise}_ImplementationReport.md`

---

## 8. Validation Summary — including a real NO-GO and its since-verified remediation

**This is the one place in this documentation system where "never lose information" matters most concretely** — the engine's own history includes a full release rejection, and this document preserves that rejection in full rather than only reporting the eventual success.

| Checkpoint | Date | Verdict | What it found |
|---|---|---|---|
| Architecture design | pre-implementation | — | 15-event design, `LifeEventEngineArchitecture.md` |
| Phase A–F implementation | — | — | 17 handlers built (3 more than designed at the time), generic engine, 636 tests, 97.90% coverage, `ruff`/`mypy --strict` clean |
| **Final Release Audit** | — | **NO GO — Overall Release Score 4/10** | **Critical:** zero API surface existed — no router, no schema, no frontend, `grep` for any caller of `record_life_event`/`undo_life_event` outside the service and test files returned nothing. Engineering internals were genuinely strong (Architecture 8/10) but the *feature* was unreachable by any user (Product 2/10, UX 1/10). Also found: a field-scoped (not row-scoped) undo conflict guard that could silently apply a stale partial write across two events touching the same row on different fields (HIGH); no idempotency protection, meaning a duplicate submission would double-count money for delta-based effects like a down payment (HIGH); no row locking on read-then-write mutations (MEDIUM); an untracked household-bootstrap side effect (MEDIUM); zero mention of the engine anywhere in `CHANGELOG.md`/`docs/backend.md`/`docs/architecture.md`, in direct violation of this project's own checklist (documentation debt); and a genuinely absent "Death of a Family Member" event, surfaced by the audit's own customer-journey replay. |
| API Implementation | — | — | Built `POST /life-events`, `GET /life-events`, `GET /life-events/{id}`, `POST /life-events/{id}/undo`, `POST /life-events/preview` — resolving the CRITICAL finding. Explicitly deferred idempotency and row-locking per its own scoped brief ("Do NOT fix idempotency" — a deliberate, stated sequencing choice, not an oversight). |
| Backend Hardening | — | — | Fixed all three remaining HIGH/MEDIUM findings: added `idempotency_key` with a `UNIQUE(user_id, idempotency_key)` constraint and flush-time race recovery; replaced the field-scoped undo guard with a row-level `updated_at` fingerprint (`after_updated_at`), re-tested against the audit's own exact reproduction scenario; added `with_for_update()` locking to `adjust_asset_value` and every effect-row load in `undo_life_event`. |
| **This document's own re-verification (2026-07-13)** | current | **All three release-blocking findings confirmed fixed in live code** | `grep` confirms: `app/routers/life_events.py` exists and is registered in `main.py`; `LifeEvent.idempotency_key` and its unique constraint exist in `models/life_event.py`; `with_for_update()` appears in both `financials_service.adjust_asset_value` and `life_event_service`'s effect-row loads, the latter citing the audit by name in its own code comment. |

**What remains genuinely open** (carried forward honestly, not re-litigated as fixed):
1. **No "Death of a Family Member" event** — a real, named product-completeness gap from the audit's own customer-journey replay, not yet built. Likely legitimately out of scope for this milestone (a user cannot report their own death; a "reported by survivor" flow is a materially different product shape, though `Nominee`/`EstateDocument` already exist as infrastructure a future milestone could build on).
2. **Untracked household-bootstrap side effect** (§1.4 of the audit) — creating a `Household`/`self` member as a side effect of a user's first family-domain life event is not itself wrapped in an `EntityEffect`. Almost certainly the *correct* behavior (a household shouldn't vanish because one event was undone), but means the effects list is not a literally complete picture of every row a transaction touched.
3. **Unbounded list-input loop in Retirement** — no max-length validation on its optional `income_source_ids`/`goal_contributions` lists; a malformed request with hundreds of entries would perform hundreds of sequential Monte Carlo recalculations in one request. A real, if edge-case, cost center once real-world traffic exists.
4. **Documentation debt** (the audit's finding #11-13) — this restructuring effort (the v2 documentation system this very document is part of) is the direct remediation of that specific finding.

---

## 9. Known Strengths (verified, stated plainly rather than only finding fault)

- **Zero raw SQL** across all 18 handlers, confirmed by grep — every write goes through a service function.
- **Ownership/IDOR protection is structural**, not a router-level check that could be forgotten — every handler's `apply(db, user, inputs)` signature takes the authenticated user as a parameter never sourced from the inputs dict.
- **No N+1** in the notification/recommendation fan-out — each collector issues one query, not one per row of a prior result set.
- **Rollback correctness independently re-verified**, not just re-asserted — the highest-effect-count event (Business Sale, 4 effects across 4 tables) was traced end to end confirming every touched row reverts after `db.rollback()`.

---

## Related Documents
`docs/02_Architecture/SystemArchitecture.md` §2.6, §2.9, §7.3 · `docs/02_Architecture/CalculationEngine.md` (the calculation-context trigger this engine reuses, never duplicates) · `docs/02_Architecture/RecommendationEngine.md` (the family-domain services this engine's handlers call into) · `docs/03_Engineering/ArchitectureDecisionRecords.md` (ADR-001, ADR-005) · `docs/08_Testing/ValidationStrategy.md` (full test-suite detail)

## Related ADRs
ADR-001 (Calculation Lifecycle — reused, never duplicated, by every goal-touching handler), ADR-005 (Recommendation Freshness — the reason no life-event effect needs to invalidate a cache).

## Related APIs
`POST /life-events`, `POST /life-events/preview`, `GET /life-events`, `GET /life-events/{id}`, `POST /life-events/{id}/undo`.

## Related Database Tables
`life_events`, `life_event_effects`, plus every table an event type can touch: `income_sources`, `expenses`, `assets`, `liabilities`, `goals`, `household_members`, `dependents`, `user_profiles`, `financial_assumptions`.

## Related Services
`life_event_service.py` and the 18 handler modules (`salary_raise_handler.py`, `job_change_handler.py`, `marriage_handler.py`, `divorce` logic, `retirement_handler.py`, `house_purchase_handler.py`, `home_sale_handler.py`, `new_loan_handler.py`, `loan_payoff_handler.py`, `inheritance_handler.py`, `major_medical_event_handler.py`, and others per §7's appendix), plus `financials_service.py` (`adjust_asset_value`), `family_service.py`, `notification_service.py`.

## Related Frontend Components
`app.life-events.tsx`, `RecordLifeEventDialog.tsx`, `life-event-field-inputs.tsx`, `life-events.ts`, `life-events-form.ts`.


## Related Tests
`test_life_event_hardening.py` (idempotency, row-fingerprint undo, row locking), plus one dedicated test file per handler (18 event types) — see the archived per-event implementation reports for each handler's own specific test list.

## Related Validation Reports
`LifeEventEngine_FinalReleaseAudit.md` (the NO-GO audit) — the single most consequential validation document in this codebase's history, archived in full and summarized in this document's own §8.

## Related Implementation Reports
16 per-event-type implementation reports, `LifeEventEngine_PhaseA_ImplementationReport.md`, `LifeEventAPI_ImplementationReport.md`, `LifeEventEngine_BackendHardeningReport.md` — all archived, all linked from this document's own §7 appendix.

## Related Future Work
A "Death of a Family Member" event (named, deferred, infrastructure — `Nominee`/`EstateDocument` — already exists) · resolving the untracked household-bootstrap side effect · a max-length validation on Retirement's optional list inputs.
---

*Archived originals: `docs/13_Archive/ArchivedReports/LifeEventEngineArchitecture.md`, `LifeEventArchitectureValidation.md`, `LifeEventEngine_FinalReleaseAudit.md`, `LifeEventEngine_PhaseA_ImplementationReport.md`, `LifeEventEngine_BackendHardeningReport.md`, `LifeEventAPI_ImplementationReport.md`, `LifeEventEngine_ProgressMatrix.md`, `TransactionConsistencyImplementationPlan.md`; `docs/13_Archive/ArchivedImplementationReports/LifeEvent_*_ImplementationReport.md` (16 files); `docs/13_Archive/ArchivedReports/LifeEventIntegrationReview.md`, `LifeEventIntegrationReport.md`.*
