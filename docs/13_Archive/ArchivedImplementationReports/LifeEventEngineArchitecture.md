# LIFE EVENT ENGINE — MILESTONE 2 ARCHITECTURE

**Role:** Principal Product Architect
**Status:** Design only. No code in this document is implemented; every reference to an existing file, model, field, or function has been verified against the current codebase as of Milestone 1's completion, not assumed.
**Scope:** Design a system that lets a user record one real-world life event and have Northstar make every resulting financial-record change atomically, consistently, and reversibly — instead of the user manually opening Financials, Family, and Goals in turn and editing each by hand.

---

## 1. WHY THIS IS NEEDED (grounded in the current product, not a generic pitch)

Today, a user who gets a raise, has a child, or pays off a mortgage must:
1. Know which of Financials' four sections (Income, Expenses, Assets, Liabilities), Family, and Goals are affected.
2. Open each one separately and edit the right row correctly.
3. Trust that they didn't forget one (e.g., adding a mortgage `Liability` without also recording the `Asset` it bought).

`UXValidationReport.md` already demonstrated how fragile manual multi-field entry is in this exact product (P0-1: a single typed amount silently discarded because the user clicked the wrong button). A **Life Event** is not a new calculation engine — every number a life event produces is computed by machinery that already exists (`planning_service.get_financial_context`, `calculate_goal_probability`, `family_recommendations_service`, `notification_service`). A Life Event is an **orchestration and narration layer**: it asks the user one real-world question ("What happened?"), and translates the answer into the same writes a careful user would have made by hand across Financials/Family/Goals — atomically, previewed before committing, and reversibly.

This is a direct continuation of this codebase's own strongest, most consistently reapplied principle, verified in `ArchitectureDecisionRecordBible.md`: **compute live, never persist a derived value, and centralize every write path in one service.** The Life Event Engine adds no exception to that rule. It is a fifth application of it, not a departure.

---

## 2. CORE ARCHITECTURAL PRINCIPLE

**A Life Event is a named, versioned recipe that writes to existing entities through existing service functions. It never computes anything a service doesn't already compute, and it never introduces a second path to a calculation that ADR-001 or ADR-005 already centralized.**

Concretely:
- Writing a `Goal`'s `current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, or `target_amount` inside a life event still goes through the exact same trigger `routers/goals.py` already uses: checking the field name against `CALCULATION_CONTEXT_FIELDS` and calling `planning_service.calculate_goal_probability`. The Life Event Engine does not duplicate this check — it calls the same `update_goal` code path Financials/Goals already call, so the trigger fires by construction, not by a second copy of the rule.
- Writing an `IncomeSource`, `Expense`, `Asset`, or `Liability` triggers **nothing** directly, because nothing needs to: `get_dashboard`, `get_financial_context`, and every rule in `family_recommendations_service._financial_health_recommendations` are computed fresh on every read (ADR-001/ADR-005). The instant a life event commits, the next `GET /dashboard` or `GET /family/recommendations` already reflects it. This is a genuine architectural gift this milestone inherits for free — no cache to invalidate, no event bus, no staleness window.
- Writing a `HouseholdMember`/`Dependent` reuses `family_service.create_member`/`update_member`/`remove_member` exactly as `routers/family.py` already does, including the `family_member_added` `AuditLog` row that `notification_service._collect_family_member_added_facts` already reads. Several life events (Marriage, Birth of Child, Adoption) get their notification **for free**, with zero new notification code, purely by reusing the existing function.

The engine's only genuinely new responsibility is: (a) asking the user one coherent, real-world question instead of several disconnected ones, (b) writing to more than one entity **atomically** in a single transaction, and (c) recording what it did in a form that can be explained and undone.

---

## 3. NEW DATA MODEL (additive only — no existing table changes)

Two new tables, deliberately modeled as a **specialization of the existing `AuditLog` before/after pattern**, not a competing audit system — the same relationship `HealthPolicy`/`EstateDocument` already have to the generic `Asset` table (a specialized structure for a specialized concern).

```
life_events
  id                 UUID PK
  user_id            UUID FK -> users.id, indexed
  event_type         VARCHAR(50)   -- "salary_raise" | "job_change" | "marriage" | ... (15 values, §5)
  occurred_on        DATE          -- the real-world date the user reports (informational; see §4.3)
  recorded_at        TIMESTAMPTZ   -- system time the event was committed
  inputs             JSON          -- the exact form submission that produced this event (for re-display/audit)
  status             VARCHAR(20)   -- "applied" | "undone"
  undone_at          TIMESTAMPTZ NULL
  notes              TEXT NULL     -- optional free-text the user can attach
  is_active           BOOLEAN       -- soft-delete convention, matches every other table in this schema

life_event_effects
  id                 UUID PK
  life_event_id      UUID FK -> life_events.id, indexed, ON DELETE CASCADE
  entity_table       VARCHAR(50)   -- "income_sources" | "expenses" | "assets" | "liabilities" |
                                   -- "goals" | "household_members" | "dependents" | "user_profiles" |
                                   -- "financial_assumptions"
  entity_id          UUID          -- the row that was changed
  change_type        VARCHAR(20)   -- "create" | "update" | "soft_delete" | "reactivate"
  before_state       JSON NULL     -- exact prior column values (NULL for "create")
  after_state        JSON NULL     -- exact new column values (NULL for "soft_delete")
  created_at         TIMESTAMPTZ
```

**Why two tables, not one JSON blob on `life_events`:** a single life event routinely touches more than one entity (House Purchase creates an `Asset` *and* a `Liability`). Recording each touched row as its own `life_event_effects` entry is what makes **partial, guarded undo** possible (§7) — the engine can check, entity by entity, whether anything has changed since the event before allowing a reversal, rather than an all-or-nothing blob no later code could safely reason about.

**Relationship to the existing `AuditLog` table:** every life event also writes one lightweight `AuditLog` row (`action="life_event_recorded"`, `after_state={"life_event_id": ..., "event_type": ...}`), purely so any code that already scans `AuditLog` generically continues to have a hook. This is a two-line courtesy write, not a second source of truth — `life_events`/`life_event_effects` is the authoritative record; `AuditLog` gets a pointer to it, the same way `notification_service._collect_family_member_added_facts` already reads `AuditLog.after_state` for a `member_id` pointer today.

---

## 4. THE ORCHESTRATION SERVICE — `life_event_service.py`

A single new service module, structurally parallel to `family_recommendations_service.py`: it depends on the existing domain services (`financials_service`, `family_service`, `planning_service`, `assumptions` router logic) and adds no calculation of its own.

### 4.1 Shape

```
async def preview_life_event(db, user, event_type, inputs) -> LifeEventPreview
async def record_life_event(db, user, event_type, inputs) -> LifeEvent
async def undo_life_event(db, user, life_event_id) -> UndoResult
async def list_life_events(db, user) -> list[LifeEvent]
```

`preview_life_event` and `record_life_event` share one internal function per event type (§5's "Which entities change" column, made literal): the preview path runs the exact same entity-diff logic but inside a transaction that is always rolled back, never committed — this guarantees the preview a user sees is never a lie, because it is produced by the same code that would actually run.

### 4.2 Atomicity

Every `record_life_event` call runs inside one database transaction. If any sub-write fails (e.g., a validation error on the second of two entities), the whole event is rolled back — the user never ends up in a half-applied state (a `Liability` created with no matching `Asset` for a House Purchase that failed partway through). This is a stronger guarantee than the current Financials editing flow gives today (each `PATCH` is already its own transaction, but a user manually editing four sections has no atomicity across them at all — this is a genuine reliability improvement the Life Event Engine adds).

### 4.3 `occurred_on` is metadata, not a time machine

The user-reported real-world date (e.g., "we got married on March 3rd") is stored and displayed, but **no calculation in this codebase is date-of-event-aware** — `calculate_goal_probability` always computes from `date.today()` (see `planning_service.py`'s `years_to_goal = ... (goal.target_date - date.today()).days ...`). A life event recorded today with an `occurred_on` of six months ago does not retroactively recompute anything as of that past date. This is stated explicitly here so a future implementer does not accidentally promise backdated recalculation the Monte Carlo engine was never designed to do — a real, honest limitation, not an oversight.

---

## 5. THE FIFTEEN LIFE EVENTS

Every event below follows the same nine-part template the brief requested. "Which calculations rerun" and "Which recommendations update" are answered precisely — where the honest answer is **"nothing reruns, because the read path is already live,"** that is stated as such rather than invented.

---

### 5.1 Salary Raise

| | |
|---|---|
| **Trigger** | User selects "Salary Raise" from the Life Event picker. |
| **Required inputs** | Which existing `IncomeSource` this applies to (dropdown of the user's active income rows; "add as a new source" if none fits), new `annual_amount`, `occurred_on`. Optional: "Put some of this toward a goal?" — if yes, pick a goal + new `monthly_contribution`. |
| **Entities changed** | `income_sources.annual_amount` (update, reusing the existing income-update path Financials already calls). If the optional goal step is taken: `goals.monthly_contribution` (update). |
| **Calculations rerun** | None automatically for the income change (`get_financial_context` is always live — the next `GET /dashboard` already reflects the new `monthly_income`/`savings_rate`). **If** the optional goal contribution was changed: `calculate_goal_probability` reruns for that one goal, because `monthly_contribution` is in `CALCULATION_CONTEXT_FIELDS` — same trigger `routers/goals.py` already uses. |
| **Recommendations that update** | `family_recommendations_service`'s `low_savings_rate` and `income_concentration` rules re-evaluate on next read (higher income → less likely to fire); Dashboard's own `_generate_suggestions` savings-rate suggestion likewise. |
| **Notifications** | New life-event notification ("Recorded: raise to $X/yr"). If the optional goal step pushed a formerly at-risk goal's probability above 70%, the existing `goal_at_risk` notification simply stops appearing on the next read — no new notification code needed. |
| **Undo/edit** | Undo reverts `annual_amount` (and the goal's `monthly_contribution`, if changed) to the `before_state` captured in `life_event_effects`, **guarded**: if the income row's `annual_amount` has been independently edited since (via Financials) the guard blocks a silent overwrite and asks the user to confirm. Edit = undo + re-record with corrected inputs (no separate "edit" code path — see §7). |
| **Audit trail** | One `life_events` row (`event_type="salary_raise"`), one or two `life_event_effects` rows. |
| **UI flow** | Single-screen form → review ("Monthly income: $X → $Y") → confirm. |

---

### 5.2 Job Change

| | |
|---|---|
| **Trigger** | User selects "Job Change." |
| **Required inputs** | New `employer`, new `occupation`, new `annual_amount` for the replacement role, `occurred_on`. The prior income row to close (dropdown). |
| **Entities changed** | `user_profiles.employer`, `user_profiles.occupation` (update); the prior `income_sources` row is **soft-deleted** (`is_active=false`) rather than edited in place, and a **new** `income_sources` row is created — this models a real job change honestly (a new employer relationship, not a renamed old one) and preserves the old row's history, consistent with the soft-delete convention already used everywhere else in this schema. |
| **Calculations rerun** | None automatically — same live-read reasoning as Salary Raise. |
| **Recommendations that update** | Same set as Salary Raise, re-evaluated against the new income figure. |
| **Notifications** | New life-event notification. |
| **Undo/edit** | Reactivate the old `income_sources` row, soft-delete the new one, revert the two `user_profiles` fields — guarded the same way as §5.1 if any of the three rows changed independently since. |
| **Audit trail** | One `life_events` row, three `life_event_effects` rows (profile update, old income soft-delete, new income create). |
| **UI flow** | Single-screen form with two sub-sections ("Old role" / "New role") → review → confirm. Optional follow-up prompt (not an automatic write): "Did your health insurance change with this job?" — links to the existing Family → Insurance page rather than inventing a new insurance-editing surface inside this flow. |

---

### 5.3 Marriage

| | |
|---|---|
| **Trigger** | User selects "Marriage." |
| **Required inputs** | Spouse's name, date of birth (optional), `occurred_on`. |
| **Entities changed** | `household_members` create (`relationship_type="spouse"`) via the existing `family_service.create_member` — the exact function `routers/family.py`'s add-member endpoint already calls, so its existing validation is reused, not re-implemented. `dependents` create (`dependent_type="spouse"`) with the given date of birth, per the same function's existing behavior (every non-self `HouseholdMember` already gets exactly one `Dependent` row, including spouses, per `household.py`'s own comment). **`user_profiles.marital_status` is deliberately not written** — that field is explicitly deprecated in the current schema (`household_members.relationship_type` is the authoritative source per `FoundationReconciliationReport.md`), and this design does not resurrect a deprecated field. |
| **Calculations rerun** | None. Marriage alone moves no money; `CALCULATION_CONTEXT_FIELDS` is untouched. (The spouse's own separate income/assets are **not** captured — `HouseholdMember.user_id` stays `NULL` for a spouse with no login, per the current data model's own explicit design. This is a real, stated limitation of today's schema, not something this design invents a workaround for.) |
| **Recommendations that update** | `family_insurance_service` and `scheme_eligibility_service` both read `household_members` live, so the new spouse is automatically considered in the next insurance-gap and scheme-eligibility computation — no new logic needed. |
| **Notifications** | **Free.** `family_service.create_member` already writes the `family_member_added` `AuditLog` row, and `notification_service._collect_family_member_added_facts` already turns that into a notification within its existing 30-day window. Zero new notification code for this event. |
| **Undo/edit** | Soft-delete the spouse `HouseholdMember` (+ cascading `Dependent`) via the existing `family_service.remove_member`, guarded: blocked if anything now references the spouse (a `HealthPolicyCoverage` row, a goal tagged to them via `set_goal_household_tags`) — those must be resolved first, surfaced to the user as a specific list, not a generic error. |
| **Audit trail** | One `life_events` row, two `life_event_effects` rows (member create, dependent create). |
| **UI flow** | Single-screen form → review ("New household member: [spouse name]") → confirm. Links to Family page afterward for completing the spouse's profile, matching the existing "+ Add details" placeholder-member pattern already on that page. |

---

### 5.4 Divorce

| | |
|---|---|
| **Trigger** | User selects "Divorce" and picks the existing spouse `HouseholdMember` from their household. |
| **Required inputs** | The spouse to remove (dropdown, defaults to the one active spouse), `occurred_on`. |
| **Entities changed** | The spouse's `household_members` row soft-deleted (`is_active=false`) via `family_service.remove_member`; the cascading `dependents` row soft-deleted with it. |
| **Calculations rerun** | None automatically. |
| **Recommendations that update** | `family_insurance_service`/`scheme_eligibility_service` reflect the smaller household on next read. |
| **Notifications** | New life-event notification. **Two new, purely-live "review" prompts are added to `notification_service`** (no persistence, following the exact same pattern already used for every other notification source): (1) any active `health_policy_coverage` row still referencing the now-inactive member's `household_member_id` — "Review insurance coverage for [name]"; (2) any active `Nominee` row (via `Asset` ownership) whose `relationship_type` was "spouse" — "Review beneficiary/nominee designations." Both are plain reads of already-existing tables, computed fresh on every call, exactly matching this codebase's established notification philosophy — no new write, no new stored fact. |
| **Undo/edit** | Reactivate the member + dependent rows, **guarded**: blocked if any `HealthPolicyCoverage` or `Nominee` row referencing them was independently changed after the divorce was recorded (the two review prompts above exist specifically so a user resolves these before they'd become an undo obstacle). |
| **Audit trail** | One `life_events` row, two `life_event_effects` rows (member soft-delete, dependent soft-delete). |
| **UI flow** | Confirm the spouse to remove → review (explicitly lists any goals currently tagged to them, via the existing `list_goals_with_tags`, as an FYI, not an automatic re-tag) → confirm. |

---

### 5.5 Birth of Child

| | |
|---|---|
| **Trigger** | User selects "Birth of Child." |
| **Required inputs** | Child's name, date of birth, gender (optional — drives scheme eligibility, see below), `occurred_on`. Optional: "Start a college fund?" |
| **Entities changed** | `household_members` create (`relationship_type="child"`) + `dependents` create (`dependent_type="minor_child"`, `is_tax_dependent=true` by default, `gender` if given) via `family_service.create_member`. If the optional goal step is taken: `goals` create (`category="education"`), using the same creation path `routers/goals.py` already exposes, which means `calculate_goal_probability` runs once for it exactly as any new goal creation already does today. |
| **Calculations rerun** | None for the family-member write. One fresh Monte Carlo run only if the optional education goal is created — the same, already-existing goal-creation trigger, not a new one. |
| **Recommendations that update** | `family_insurance_service` (new dependent → coverage gap), `scheme_eligibility_service` — if `gender="female"` and the child is under 10, the existing Sukanya Samriddhi Yojana eligibility check (driven by `Dependent.gender`, per that field's own code comment) will surface it on the next read, with zero new eligibility logic. |
| **Notifications** | **Free**, same mechanism as Marriage (`family_member_added`). |
| **Undo/edit** | Soft-delete the child + dependent rows, guarded if the education goal (if created) has since received contributions or been tagged elsewhere — surfaced to the user rather than silently blocked. |
| **Audit trail** | One `life_events` row; two or three `life_event_effects` rows (member, dependent, optionally goal). |
| **UI flow** | Single-screen form → optional goal sub-step (target amount / timeline pre-filled with a sensible default the user can change, same pattern as onboarding's Goal step) → review → confirm. |

---

### 5.6 Adoption

| | |
|---|---|
| **Trigger** | User selects "Adoption." |
| **Required inputs** | Identical to Birth of Child: child's name, date of birth, gender (optional), `occurred_on`. |
| **Entities changed** | Identical to Birth of Child — `household_members`/`dependents` create with `dependent_type="minor_child"`. **Honest schema note:** the current data model has no field distinguishing "born into the family" from "adopted into the family" on the `Dependent` row itself. This design does not invent one speculatively. The distinction is preserved at the `life_events.event_type` level (`"adoption"` vs `"birth_of_child"`) for history and reporting, even though the resulting household rows are identical in shape. A future milestone could add a nullable `Dependent.acquisition_type` column if a real downstream need for it emerges (e.g., adoption-specific tax credits) — flagged here as a possible future addition, not built now. |
| **Calculations rerun / Recommendations / Notifications / Undo / Audit** | Identical to Birth of Child in every respect. |
| **UI flow** | Same form as Birth of Child, with copy that says "Adoption" throughout instead of "Birth," and an optional "adoption finalized on" sub-field stored only in the `life_events.inputs` JSON (not a new column) for the user's own record-keeping. |

---

### 5.7 House Purchase

| | |
|---|---|
| **Trigger** | User selects "House Purchase." |
| **Required inputs** | Property value (→ `Asset.current_value`), mortgage balance, interest rate, monthly payment (→ `Liability` fields), `occurred_on`. Optional: "Cash used for down payment?" (reduces a chosen liquid `Asset`). Optional: "Does this fulfill a Home Purchase goal?" (goal picker). |
| **Entities changed** | `assets` create (`asset_type="real_estate"` — already a defined value in `INVESTMENT_TYPES`, no new enum needed); `liabilities` create (`liability_type="mortgage"`). Optional: an existing liquid `assets.current_value` reduced by the stated down payment; optional: `goals.current_amount` updated on the linked goal (in `CALCULATION_CONTEXT_FIELDS`, so `calculate_goal_probability` reruns for it). |
| **Calculations rerun** | None for the base Asset+Liability write (`get_financial_context` reflects it on next read: `net_worth`, `total_assets`, `total_liabilities`, `debt_ratio` all shift live). One Monte Carlo run only if the goal-linking step is taken. |
| **Recommendations that update** | `high_interest_debt` and `high_debt_to_income` (financial-health rules) re-evaluate against the new mortgage on next read; `low_liquidity` re-evaluates if a down payment reduced a liquid asset. |
| **Notifications** | New life-event notification. If the mortgage rate happens to exceed the existing `_HIGH_INTEREST_THRESHOLD = 0.10` constant already defined in `family_recommendations_service.py`, the confirmation screen can surface that same recommendation inline immediately (reusing the constant, not inventing a second one) rather than waiting for the user to separately visit Family Recommendations. |
| **Undo/edit** | Reverse the Asset create, the Liability create, and the down-payment reduction (restore the liquid asset's prior value) and the goal's `current_amount` if changed — each guarded independently: e.g., if the user has since made a regular mortgage payment through ordinary Financials editing, undoing would be offered only with an explicit "this will discard the balance update you made on [date]" confirmation, never silently. |
| **Audit trail** | One `life_events` row; two to four `life_event_effects` rows depending on which optional steps were taken. |
| **UI flow** | Multi-field single screen (property + mortgage terms) → optional down-payment/goal sub-steps → review (explicit before/after net worth line) → confirm. |

---

### 5.8 Home Sale

| | |
|---|---|
| **Trigger** | User selects "Home Sale" and picks the existing home `Asset`. |
| **Required inputs** | Sale price, whether the linked mortgage `Liability` is paid off by the sale (checkbox, defaults to yes if one exists), net proceeds destination (add to an existing liquid `Asset`, or create a new one), `occurred_on`. |
| **Entities changed** | The home `assets` row soft-deleted; the mortgage `liabilities` row soft-deleted (if paid off) or left as-is (if not, e.g. an assumable loan — rare, but the option exists rather than forcing an inaccurate payoff); a liquid `Asset` created or updated (`current_value` increased) for net proceeds. |
| **Calculations rerun** | None directly; `get_financial_context` reflects the changes live. |
| **Recommendations that update** | `high_interest_debt`/`high_debt_to_income` stop firing for the paid-off mortgage; `low_liquidity` may stop firing given the proceeds. |
| **Notifications** | New life-event notification, styled positively if debt was eliminated (mirroring the existing "✓ [Goal] is fully funded" tone already used in `notification_service._collect_goal_facts`). |
| **Undo/edit** | Reactivate the home Asset and mortgage Liability at their prior values; reverse the proceeds Asset create/update — guarded identically to House Purchase. |
| **Audit trail** | One `life_events` row; two to three `life_event_effects` rows. |
| **UI flow** | Select home → sale terms → review (shows the mortgage disappearing and the new cash appearing side by side) → confirm. |

---

### 5.9 New Loan

| | |
|---|---|
| **Trigger** | User selects "New Loan." |
| **Required inputs** | Loan type (`auto_loan` / `student_loan` / `personal_loan` / `credit_card` / `other` — the existing `LIABILITY_TYPES` set, no new enum needed for anything except a genuine business loan, see §5.14's honest gap note), balance, interest rate, monthly payment, `occurred_on`. Optional: "What did this loan fund?" — an optional linked `Asset` create (e.g. a car) for symmetry with House Purchase, never mandatory. |
| **Entities changed** | `liabilities` create; optionally `assets` create. |
| **Calculations rerun** | None directly. |
| **Recommendations that update** | `high_interest_debt` fires immediately on the confirmation screen if the entered rate exceeds the existing `0.10` threshold (same reuse pattern as House Purchase) — this is the one event where showing that recommendation *before* the user even finishes the flow is genuinely useful (e.g. a credit card at 24% APR), so the preview step should surface it, not just the post-commit read. |
| **Notifications** | New life-event notification. |
| **Undo/edit** | Reverse the Liability (and Asset, if created) — guarded the same way as every other create-based event. |
| **Audit trail** | One `life_events` row; one or two `life_event_effects` rows. |
| **UI flow** | Loan terms form → optional linked-purchase sub-step → review (surfaces the high-interest warning inline if applicable) → confirm. |

---

### 5.10 Loan Payoff

**Deliberately scoped to full closure only** — a partial balance reduction is already well-served by ordinary Financials editing (`PATCH /financials/liabilities/{id}`) and does not need a life event; building one for partial payoffs would duplicate an already-solved case rather than closing a real gap (the same "narrowest correct shape" discipline this codebase already applies elsewhere, e.g. the Scheme Engine's deliberately narrow rule-type scope).

| | |
|---|---|
| **Trigger** | User selects "Loan Payoff" and picks the `Liability` being closed. |
| **Required inputs** | The liability to close (dropdown), `occurred_on`. |
| **Entities changed** | The `liabilities` row soft-deleted (`is_active=false`). |
| **Calculations rerun** | None directly. |
| **Recommendations that update** | Whichever of `high_interest_debt`/`high_debt_to_income` were firing for this specific liability stop firing on next read. |
| **Notifications** | New life-event notification, celebratory tone: "✓ [Liability description] paid off" — directly mirroring the existing `_collect_goal_facts`' "✓ [Goal] is fully funded" pattern already in `notification_service.py`, applied to a second, structurally identical case rather than inventing new copy conventions. |
| **Undo/edit** | Reactivate the liability at its prior balance — guarded if it was independently re-created or edited since (rare, but the same discipline applies uniformly). |
| **Audit trail** | One `life_events` row; one `life_event_effects` row. |
| **UI flow** | Pick liability → confirm → done (the shortest flow of all fifteen — a one-click event, deliberately, since there is nothing else to ask). |

---

### 5.11 Inheritance

| | |
|---|---|
| **Trigger** | User selects "Inheritance." |
| **Required inputs** | Form received (cash / investment / property — informs `Asset.asset_type`), amount/value, `occurred_on`. Optional: "Does this generate ongoing income?" (e.g. inherited rental property) → creates an `IncomeSource` (`source_type="rental"` or `"investment"`, from the existing `INCOME_TYPES` set). |
| **Entities changed** | `assets` create; optionally `income_sources` create. |
| **Calculations rerun** | None directly. |
| **Recommendations that update** | `negative_net_worth_trend` and `low_liquidity` may stop firing; if income was added, `income_concentration` re-evaluates against the larger number of sources. |
| **Notifications** | New life-event notification. The confirmation screen also surfaces a **UI-only prompt** (not a write) to review `EstateDocument` status — a natural moment to nudge estate planning, using the existing `estate_documents` table's own `status` field (`"not_started"`/etc.), without this event ever writing to it itself; the user's own estate-planning-review action remains theirs to take on the existing Family/Estate surface. |
| **Undo/edit** | Reverse the Asset create (and IncomeSource, if created) — guarded as usual. |
| **Audit trail** | One `life_events` row; one or two `life_event_effects` rows. |
| **UI flow** | Form-received + value → optional income sub-step → review → confirm, with the estate-document nudge shown on the success screen, not blocking commit. |

---

### 5.12 Retirement

The most structurally distinct event — a status transition rather than a single transaction, touching Profile, Income, and Assumptions together.

| | |
|---|---|
| **Trigger** | User selects "Retirement." |
| **Required inputs** | `occurred_on` (retirement date). Which active salary `income_sources` row(s) to deactivate. Optional: new pension/annuity income amount (creates an `IncomeSource`, `source_type="pension"`). Optional: confirm/update `FinancialAssumptions.retirement_age` and `.social_security_monthly` if the actual figures differ from the planning assumptions already on file. Optional, explicitly opt-in per goal: for each active `category="retirement"` goal, offer to update its `monthly_contribution` (commonly to `$0`, or to a pension-funded figure). |
| **Entities changed** | `user_profiles.employment_status → "retired"`; salary `income_sources` soft-deleted; optionally a new pension `income_sources` row created; optionally `financial_assumptions.retirement_age`/`.social_security_monthly` updated; optionally one or more `goals.monthly_contribution` updated. |
| **Calculations rerun** | None for the profile/income/assumptions writes (`get_financial_context` and `get_dashboard` are always live). `calculate_goal_probability` reruns **only** for each goal whose `monthly_contribution` was explicitly changed in the opt-in step — using the exact same existing trigger, never a bespoke "recompute every goal on retirement" pass that would sit outside `CALCULATION_CONTEXT_FIELDS`'s established contract. |
| **Recommendations that update** | Dashboard's `low_savings_rate` suggestion and `family_recommendations_service`'s `low_savings_rate`/`income_concentration`/`high_debt_to_income` rules all re-evaluate against the new income picture on next read. |
| **Notifications** | New life-event notification, milestone-toned. |
| **Undo/edit** | Reactivate the deactivated income source(s); soft-delete the pension source if created; revert `employment_status` and the two `financial_assumptions` fields; revert any goal `monthly_contribution` changes — each captured as its own `life_event_effects` row, so a user can, for example, keep the profile status change but undo just one goal's contribution edit if that turns out to be the only thing they got wrong. |
| **Audit trail** | One `life_events` row; three to seven `life_event_effects` rows depending on how many optional steps were taken. |
| **UI flow** | The longest flow of the fifteen, deliberately broken into clearly labeled sub-sections (Income → Assumptions → Goals) rather than one dense form, each with its own "skip this section" affordance — matching this app's existing onboarding pattern of optional, clearly-scoped sub-steps rather than one overwhelming page. |

---

### 5.13 Major Medical Event

| | |
|---|---|
| **Trigger** | User selects "Major Medical Event." |
| **Required inputs** | New or increased monthly healthcare cost (→ `Expense`), `occurred_on`. Optional: "Paid a lump sum from savings?" (reduces a chosen liquid `Asset`). Optional: "Financed with a loan?" (creates a `Liability`). |
| **Entities changed** | `expenses` create or update (`category="healthcare"`); optionally a liquid `assets.current_value` reduced; optionally `liabilities` create. |
| **Entities NOT changed, with an honest reason why** | The `Expense` model has no "one-time" flag — `monthly_amount` is inherently recurring. This design does not invent a one-time-expense concept the schema doesn't support. The confirmation screen explicitly tells the user: *"We've recorded this as an ongoing monthly expense. Once it's resolved, edit or remove it from Financials."* This is the same transparency standard the rest of this app's copy already holds itself to (e.g. the Assumptions step's "these are the exact return figures we use"). |
| **Calculations rerun** | None directly. |
| **Recommendations that update** | `low_liquidity` and `low_savings_rate` re-evaluate against the new/increased expense and any asset reduction. |
| **Notifications** | New life-event notification. |
| **Undo/edit** | Reverse whichever of the three optional sub-effects were actually recorded, independently. |
| **Audit trail** | One `life_events` row; one to three `life_event_effects` rows. |
| **UI flow** | Expense entry → optional lump-sum/financing sub-steps → review (with the "this is an ongoing expense until you edit it" notice shown plainly, not buried) → confirm. |

---

### 5.14 Business Start

| | |
|---|---|
| **Trigger** | User selects "Business Start." |
| **Required inputs** | `occurred_on`. Optional: startup costs paid from savings (reduces a liquid `Asset`, or creates an `Expense` if ongoing). Optional: startup debt (creates a `Liability`). |
| **Entities changed** | `user_profiles.employment_status → "self_employed"`; optionally an `Asset` reduction or `Expense` create; optionally a `Liability` create. **No `income_sources` row is created at this event** — a business start commonly precedes any revenue, and inventing a $0 income row would misrepresent the household's actual finances. Income is recorded later, either via ordinary Financials editing once revenue exists, or (once revenue is real and recurring) as a natural follow-up life event of its own kind — this design does not force a premature entity into existence to make the event "feel complete." |
| **Honest schema gap, flagged not silently worked around** | The current `liabilities.liability_type` enum (`mortgage`/`auto_loan`/`student_loan`/`credit_card`/`personal_loan`/`other`) has no dedicated `business_loan` value. Until implementation adds one (a small, additive enum change, consistent with how this codebase has handled every prior gap — e.g. `custom_inflation_rate`'s own additive-nullable-column precedent), a business loan is recorded as `"other"` with the description field carrying the specific label. This is named here explicitly so the implementation phase treats it as a known, deliberate placeholder, not a bug discovered later. |
| **Calculations rerun** | None. |
| **Recommendations that update** | None currently — `family_recommendations_service` has no employment-status-aware rule today. This is named as a natural **future** rule (e.g., "newly self-employed — consider quarterly estimated tax planning") rather than invented and claimed as existing. |
| **Notifications** | New life-event notification only. |
| **Undo/edit** | Revert `employment_status`; reverse the optional asset/expense/liability effects. |
| **Audit trail** | One `life_events` row; one to three `life_event_effects` rows. |
| **UI flow** | Single screen, mostly optional fields, explicitly low-friction since the common case (no financial entities yet) is "just record that this happened." |

---

### 5.15 Business Sale

| | |
|---|---|
| **Trigger** | User selects "Business Sale." |
| **Required inputs** | Sale proceeds, destination (existing or new liquid `Asset`), whether any business `Liability` is paid off, whether an installment/ongoing payout creates new `income_sources` (`source_type="other"`), whether `employment_status` should revert (e.g. from `"self_employed"` back to `"employed"`/`"retired"` if this was the sole income source), `occurred_on`. |
| **Entities changed** | Liquid `Asset` create/update for proceeds; optional `Liability` soft-delete; optional `IncomeSource` create; optional `user_profiles.employment_status` update. |
| **Calculations rerun** | None directly. |
| **Recommendations that update** | `negative_net_worth_trend`/`low_liquidity` may stop firing (proceeds); `high_interest_debt`/`high_debt_to_income` may stop firing if business debt was cleared. |
| **Notifications** | New life-event notification. |
| **Undo/edit** | Mirrors Home Sale's undo shape exactly — reverse whichever of the (up to four) optional effects were recorded. |
| **Audit trail** | One `life_events` row; one to four `life_event_effects` rows. |
| **UI flow** | Proceeds + destination → optional debt/income/status sub-steps → review → confirm. |

---

## 6. CROSS-CUTTING: NOTIFICATIONS

**No per-event notification code is written.** Exactly one new collector function is added to `notification_service.py`, structurally identical to the existing `_collect_family_member_added_facts`:

```
async def _collect_life_event_facts(db, user) -> list[_Fact]:
    # reads life_events where user_id = user.id, status = "applied",
    # recorded_at within a recency window (mirroring the existing
    # _FAMILY_MEMBER_ADDED_WINDOW_DAYS = 30 pattern), and turns each into
    # one _Fact using event_type-specific title/body templates.
```

Every one of the fifteen events' "Notifications" row above reduces to either (a) this one generic collector, or (b) an existing collector that already fires for free because the underlying write (`family_service.create_member`, a goal reaching `current_amount >= target_amount`, a liability's `high_interest_debt` rule) is one this codebase's live-computation model already covers. The only genuinely new notification logic in this entire design is the two small, live, read-only "review" checks added for Divorce (§5.4) — and even those follow the exact same `_Fact`-producing shape as every other collector, wired into the same `_collect_facts` aggregator, deduped through the same `NotificationMarker` table.

---

## 7. CROSS-CUTTING: UNDO AND EDIT

**There is one generic undo mechanism, not fifteen bespoke ones.**

```
async def undo_life_event(db, user, life_event_id):
    event = load life_events row, verify ownership and status == "applied"
    for effect in event.life_event_effects (in reverse order):
        current = load the live row named by effect.entity_table/entity_id
        if current's mutable fields != effect.after_state:
            # someone/something changed this row after the life event —
            # block this one effect, collect it as a conflict
            conflicts.append(effect)
            continue
        apply effect.before_state back onto the row (or reactivate/soft-delete
        as the inverse of effect.change_type)
    if conflicts and not force:
        return UndoResult(blocked=True, conflicts=[...])  # 409, explicit list
    event.status = "undone"; event.undone_at = now()
    commit
```

- **Full, clean undo** is possible whenever nothing the event touched has been independently modified since — the common case, especially soon after recording.
- **Partial/blocked undo** surfaces the *specific* rows that changed since (e.g. "the mortgage balance was updated on [date] — undoing this event would discard that update") rather than a generic "cannot undo" — the same specificity standard the rest of this app's error/validation copy already holds itself to (`FinancialsE2EValidationReport.md`/`UXValidationReport.md` both praised this app's existing validation-message quality; this design extends that standard here).
- A `force=true` override is available for a user who explicitly wants to discard the intervening change too, requiring an explicit confirmation naming what will be lost — never a silent default.

**Edit is not a separate code path.** "Editing" a recorded life event is presented to the user as **undo, then re-record with corrected inputs** — using the exact same guarded undo above, followed by a normal `record_life_event` call with the corrected form. This avoids building and maintaining a second, parallel "amend in place" mutation path for fifteen different entity-shapes, at the cost of nothing a user would notice (the flow is: open the event from history → "Edit" → the form re-opens pre-filled → change what's wrong → the same guarded-undo-then-re-record happens under the hood).

---

## 8. CROSS-CUTTING: AUDIT TRAIL

Already fully specified by §3's `life_events`/`life_event_effects` tables. To summarize the guarantee: **for any past life event, the system can answer, precisely and without inference, (a) what the user said happened, (b) exactly which rows changed and how, (c) whether it has since been undone, and (d) whether undoing it now would be safe.** This is a strictly stronger audit guarantee than the generic `AuditLog` table alone provides today (which records a single action's before/after, not a *group* of related changes with per-row undo safety) — appropriate, since a life event is deliberately a bigger, more consequential unit of change than the actions `AuditLog` was originally built for (HUF creation, nominee changes).

A **Life Events history page** (new, under Profile or its own nav entry — see §9) is the user-facing view of this same table: a reverse-chronological timeline, each entry showing its `event_type`, `occurred_on`, a plain-language summary of its effects (reusing the same diff-rendering the preview/review screen already uses), and an "Undo" action gated exactly as above.

---

## 9. FRONTEND ARCHITECTURE

### 9.1 Entry points
- A primary, persistently discoverable action — "Record a life event" — placed with the same prominence as "New goal" today (sidebar or a Dashboard card), so it is not buried.
- Secondary, contextual entry points on pages where a relevant event is a natural next action (e.g., a "Record a life event" link on the Family page's empty state, on the Goals page next to an at-risk retirement goal, on Financials near a liability someone might be paying off) — all routing to the same canonical flow, never a page-specific variant.

### 9.2 The flow (four steps, every event)
1. **Pick a category, then an event** — the fifteen events grouped into five scannable categories (Income & Career, Family, Property & Debt, Assets & Windfalls, Health & Business), reusing the card-with-real-information pattern already proven in onboarding's Risk Profile step (informative cards, not a bare dropdown).
2. **Guided form** — the event-specific fields from §5, built from the same `InputField`/`SelectField` components already shared across onboarding and the list-based Financials steps, for visual and interaction consistency.
3. **Review ("Here's what will change")** — a plain-language diff of every entity effect (new/changed rows, before → after values, e.g. "Net worth: -$45,000 → -$355,000"), with every optional sub-step shown as an explicit, unchecked-by-default opt-in the user must actively select — never auto-applied. This step is the direct, deliberate fix for the exact class of problem `UXValidationReport.md`'s P0-1 identified: the user sees precisely what is about to happen **before** it happens, with no ambiguous button that means two different things depending on unsaved state.
4. **Confirm & Record** — commits via `record_life_event`; the success screen shows the same diff already reviewed (now as fact, not preview), a link to the updated Dashboard, and an immediate, no-navigation-required "Undo" affordance for the next few minutes — directly answering "can users recover from mistakes," this time by construction rather than by accident.

### 9.3 History
A **Life Events** page — reverse-chronological list, each entry expandable to its full effect diff, each with a guarded "Undo" action per §7 and an "Edit" action that opens the same guided form pre-filled with the original inputs.

---

## 10. API SURFACE (design only — shapes, not implementation)

```
POST /api/v1/life-events/preview     { event_type, inputs }  -> diff, no commit, transaction always rolled back
POST /api/v1/life-events             { event_type, inputs }  -> the committed LifeEvent + its effects
GET  /api/v1/life-events                                      -> paginated history
POST /api/v1/life-events/{id}/undo   { force?: bool }         -> UndoResult (200 ok, or 409 with conflicts)
```

No new endpoint is added to `financials`, `family`, or `goals` — this feature is additive, sitting above them, exactly as `family_recommendations_service` sits above `family_insurance_service`/`scheme_eligibility_service` without either of those needing to change.

---

## 11. NON-GOALS (explicitly out of scope for this design)

Matching this codebase's own consistent discipline (its own words, on the Scheme Engine and the Family module's placeholder members): **the narrowest correct shape, not the most general one.**

- **No automatic event detection** from bank statement imports, calendar integrations, or AI-inferred life changes. Every life event is user-initiated and user-confirmed.
- **No multi-user approval workflow.** A household has no shared login today (per `HouseholdMember.user_id`'s own nullable, no-login design) — a life event is recorded by the one logged-in user, exactly as every other write in this schema already is.
- **No retroactive recalculation** as of a past `occurred_on` date (§4.3) — this would require date-aware Monte Carlo the engine doesn't have, and is not invented here to make this feature seem more complete than it is.
- **No new recommendation rules invented to fill perceived gaps** (e.g., Business Start's missing employment-status-aware recommendation, §5.14) — every such gap is named explicitly as a candidate for the recommendation engine's own future roadmap, not built speculatively inside this milestone.
- **No new `Dependent.acquisition_type` column** for Adoption (§5.6) unless a real downstream consumer (e.g. an adoption-specific tax rule) is confirmed to need it.
- **No `business_loan` liability-type enum addition** committed by this document (§5.14) — flagged as a small, likely, additive change for the implementation phase to make, not decided here.

---

## 12. IMPLEMENTATION PHASING (for a future planning pass — not started here)

1. **Phase A — Core engine + audit.** `life_events`/`life_event_effects` tables, `life_event_service.py`'s `preview`/`record`/`undo`/`list`, and the single simplest event (Loan Payoff, §5.10 — one entity, one effect) as the proof of the whole mechanism.
2. **Phase B — Single-entity events.** Salary Raise, New Loan, Inheritance, Business Start — each touching one primary entity plus at most one optional secondary effect.
3. **Phase C — Family events.** Marriage, Divorce, Birth of Child, Adoption — exercising the `family_service` reuse and the free-notification path.
4. **Phase D — Compound events.** House Purchase, Home Sale, Business Sale, Job Change, Major Medical Event — exercising multi-entity atomicity and guarded undo across more than one row.
5. **Phase E — Retirement.** Deliberately last: the most structurally distinct event, and the only one touching Profile, Income, Assumptions, and (optionally) multiple goals in one transaction.
6. **Phase F — Frontend.** The four-step flow (§9), built once against whichever events Phases A–E have shipped, not per-event bespoke UI.

This phasing is offered as a starting point for the eventual planning document — not itself the plan.
