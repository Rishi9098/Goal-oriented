# MILESTONE 1 — FINANCIAL PROFILE MANAGEMENT
## Implementation Specification — v2

**Role:** Lead Architect
**Supersedes:** `Milestone1ImplementationSpecification.md` (v1)
**Produced from:** a full re-read of v1, `DesignReview_Milestone1.md`'s 14 findings (DR-01–DR-14), and a fresh, independent re-verification of every changed claim against current source — not against v1's or the review's own prior assertions. Section 0 states, for each finding, whether this revision agrees, and cites the exact evidence either way. No claim in this document rests on "the previous document said so."
**Scope discipline:** This revision resolves review findings only. It adds no feature, endpoint, table, or screen beyond what v1 already scoped for PLA-001/PLA-002. Every change below either fixes something v1 got wrong or removes something v1 over-specified — nothing is added that expands what Milestone 1 builds. One exception is disclosed and justified in §0.6a: a field (`tax_rate`) is *removed* from the Assumptions form's scope, which narrows rather than expands the milestone.

---

## PART 0 — REVIEW RESOLUTION (read this before anything else)

Each entry: the review's claim, whether this revision agrees, the evidence checked, and the resulting change.

### 0.1 — DR-01: Nav placement contradicts the documented Family-position rule
**Agree.** Re-verified `code/src/components/app-shell.tsx` lines 30-43 directly: the comment above the `nav` array states *"Order matches `FamilyPlanningDesign.md`'s concrete nav diagram (Family directly after Goals, before AI Copilot)."* v1's placement ("immediately after `/app/goals` and before `/app/family`") breaks this.
**Resolution:** New desktop order: `Dashboard, Goals, Family, AI Copilot, Financials, Reports, Profile, Settings`. Financials sits immediately before Reports. Rationale, evidence-based rather than asserted: `MOBILE_PRIMARY`/`MOBILE_MORE` (see §0.14 below) already group Reports, Profile, and Settings together as the "occasional, not daily" surfaces, distinct from Dashboard/Goals/Family/Copilot's "daily-use" grouping (`app-shell.tsx` line 45-47's own comment: *"Dashboard, Goals, Family, Copilot stay primary; Reports/Profile/Settings move behind 'More'"*). Financials is, by the same cadence logic the codebase already applies, an occasional-update surface — placing it adjacent to Reports on desktop keeps the desktop order legible against that existing grouping rather than inventing a new one.

### 0.2 — DR-02: Testing strategy assumed non-existent infrastructure
**Agree.** Re-verified `code/package.json`: `devDependencies` contains no test runner (no Playwright, Vitest, Jest, React Testing Library, Cypress); no `*.test.*`/`*.spec.*`/`playwright.config.*`/`e2e/` exists anywhere under `code/`.
**Resolution, and explicit scope call:** Per this revision's "do not expand scope" mandate, Milestone 1 does **not** install or configure a frontend test framework — doing so is real, unscoped infrastructure work with its own risk surface, not a Milestone 1 feature. Frontend verification for this milestone is manual (a QA checklist, §Part 1.10 below) plus backend integration tests (which do have a real, working `pytest` setup — unchanged from v1). Introducing frontend test tooling is named as a candidate follow-up in Outstanding Risks, not as part of this milestone.

### 0.3 — DR-03: Mobile nav placement unaddressed
**Agree.** Re-verified `app-shell.tsx` lines 286-288: the mobile bottom nav is `grid-cols-5`, filled by exactly `MOBILE_PRIMARY`'s 4 routes plus the "More" button — 5 of 5 slots already in use, zero free slots, confirmed by reading the render loop directly, not inferred from the comment alone.
**Resolution:** `MOBILE_MORE` gains a fourth entry: `/app/financials`, placed alongside `/app/reports`, `/app/profile`, `/app/settings`. `MOBILE_PRIMARY` is **not** changed — displacing Dashboard, Goals, Family, or Copilot from the primary row would itself be an undocumented product decision this milestone has no mandate to make, and the existing 5-slot hard limit (`grid-cols-5`, unchanged since first commit per the file's own comment) is a structural constraint this milestone should not break. This mirrors the desktop decision in §0.1: Financials groups with Reports/Profile/Settings on both surfaces, consistently.

### 0.4 — DR-04: `extra="forbid"` proposal introduces API inconsistency and touches shipped endpoints unnecessarily
**Agree.** Re-verified: no schema in `backend/app/schemas/{goal,financials,assumptions}.py` sets `model_config = {"extra": "forbid"}` anywhere — every existing `Update`/`Create` schema uses Pydantic's default (silently ignore unrecognized fields). Re-verified `code/src/lib/api.ts`: no call site spreads a full entity object into a patch payload for any of `updateAsset`/`updateLiability` — both `patch` parameter types are narrow, hand-declared shapes (`{ current_value?, institution?, description? }`, etc.), meaning the concern the `extra="forbid"` proposal defended against is already prevented at the TypeScript layer.
**Resolution:** The `extra="forbid"` proposal is dropped entirely. `IncomeSourceUpdate`/`ExpenseUpdate` (new, below) use the same undecorated `BaseModel` convention as every other Update schema in this codebase. `AssetUpdate`/`LiabilityUpdate` are not touched. Immutability of `source_type`/`category` is enforced the same way `asset_type`/`liability_type`'s immutability already is today — by omission from the Update schema's field list, plus a disabled field in the edit UI — not by a new validation mode.

### 0.5 — DR-05: Generic form-component design lacked a concrete config schema
**Agree.** v1 asserted a single, entity-parameterized component set without defining the parameter. Left to an implementing engineer, this is exactly the kind of interface design this document is supposed to have already resolved.
**Resolution:** §Part 1.1 below now defines the field-config shape explicitly, applied to all four entities in a table, so no field-by-field decision is left open.

### 0.6 — DR-06: Assumptions get-or-create race condition understated as a hedge
**Agree.** Re-verified `backend/app/models/assumptions.py`: `user_id` carries `unique=True` at the DB level, confirmed directly in the column definition, not inferred. Re-verified `backend/app/routers/assumptions.py`'s `get_assumptions`: the insert-if-missing path has no `try/except` around `db.commit()` and no `ON CONFLICT` handling. Two concurrent requests for a user with no existing row can both pass the `scalar_one_or_none() is None` check before either commits, and the second commit raises an uncaught `IntegrityError`.
**Resolution:** §Part 3.9/3.12 below specify a required fix: wrap the insert path in `try/except IntegrityError`, `await db.rollback()`, then re-`SELECT` and return the row the other concurrent request created. Disclosed honestly: **no existing code in this repository already does this** (`grep -rn "IntegrityError" backend/app/` returns zero matches) — this is not "matching an existing pattern," it is the first instance of this handling in the codebase, and is specified as new, necessary logic, not inherited convention.

### 0.6a — NEW (found during this revision's re-verification, not in the original review): `tax_rate` is explicitly deprecated and must not gain a new UI writer
**Discovered by this revision, independent of the Design Review.** Re-reading `backend/app/models/assumptions.py` in full (not just the fields v1 already quoted) surfaces a comment v1 did not act on:
> `tax_rate`: *"DEPRECATED (2026-07-06, `FutureCompatibilityAuditReport.md` Finding C / `FoundationReconciliationReport.md`): a flat, single-rate approximation that predates the versioned `tax_regimes`/`tax_slabs` engine... Confirmed unread by any service/router as of this reconciliation — grep shows it is only ever set to its default, never computed against... do NOT wire new logic to this field."*
v1's §0.6 decided the Settings Assumptions card should expose "all seven fields" including `tax_rate`, to fully resolve onboarding's claim that assumptions "can be refined... in Settings." Building a new, second UI write-path to a field the codebase has explicitly marked deprecated and instructed against wiring new logic to is a direct conflict with `docs/ENGINEERING_CONSTITUTION.md` Rule 11 (Deprecation Completion) — adding a consumer to a deprecated field moves the codebase backward on that rule, not forward.
**Resolution:** The Settings Assumptions card exposes **six** fields, not seven: `inflation_rate`, `expected_return_conservative`, `expected_return_balanced`, `expected_return_aggressive`, `retirement_age`, `social_security_monthly`. `tax_rate` is excluded. This is a narrowing of v1's scope, not an expansion, and is consistent with this revision's "do not introduce new features" mandate — declining to build new UI around a field flagged deprecated is the conservative choice, not a speculative one.
**Residual gap, disclosed, not fixed here:** Onboarding's existing `StepAssumptions` form (`code/src/components/onboarding/wizard-steps.tsx`) still collects `tax_rate` today and still writes it via `upsertAssumptions` — that is pre-existing behavior, unrelated to and unchanged by Milestone 1, and fixing it (either removing the field from onboarding or wiring it to the real `tax_slabs` engine) is out of scope for this milestone. Onboarding's general claim ("refine them any time in Settings") remains imperfectly true specifically for `tax_rate` after this milestone ships — tracked in Outstanding Risks, not silently absorbed into this document's Definition of Done.

### 0.7 — DR-07: Percentage conversion lacked explicit rounding
**Agree.** No rounding step existed anywhere in v1's conversion description; IEEE-754 double-precision division (e.g., `3.5 / 100` in JavaScript) can produce a non-exact result.
**Resolution:** §Part 3.9 specifies rounding to 4 decimal places on the stored fraction at both conversion points (submit and load) — sufficient precision for any of these fields (a tax or return rate specified finer than 0.01% has no real-world meaning here) while eliminating floating-point drift on round-trip.

### 0.8 — DR-08: Delete confirmation copy unchanged from Goals despite different stakes and no restore path
**Agree.** No restore UI exists in Milestone 1 (confirmed unchanged — restore is Milestone 5 per `ImplementationRoadmap.md`, not touched by this revision), and `UX_PRINCIPLES.md` #10 sets an explicit bar for emotionally-loaded data that a generic "Are you sure?" doesn't meet for a $310,000 liability record.
**Resolution:** §Part 1.4 and §Part 2 now specify entity-specific confirm copy naming what's being deleted and stating plainly that Milestone 1 has no in-app undo, rather than reusing Goals' generic copy verbatim.

### 0.9 — DR-09: Bundling the full service-layer extraction with the two new endpoints increased regression blast radius
**Agree.** v1 directed extracting all 14 existing + 2 new endpoints' logic into `financials_service.py` in one pass — a full-file refactor of already-shipped, already-tested code riding along with a small additive change.
**Resolution:** Narrowed. `financials_service.py` is created in this milestone containing **only** the two new functions (`update_income_source`, `update_expense`). The 12 existing endpoints' inline logic in `backend/app/routers/financials.py` is **not touched** — it remains exactly as it is today. This means the router is only partially thin after this milestone (new code follows Engineering Constitution Rule 1; old code doesn't yet) — disclosed explicitly as intentional, tracked debt in Outstanding Risks, not silently implied as fully resolved. This is the smaller of the two options the review offered, chosen specifically because it satisfies "do not expand scope."

### 0.10 — DR-10: Reduced-motion claim assumed a convention that doesn't exist
**Agree.** Re-verified: `grep -rln "prefers-reduced-motion\|useReducedMotion" code/src/` returns zero files. `GoalSimPanel.tsx`, cited by v1 as the pattern to reuse, does not itself handle reduced motion.
**Resolution:** §Part 1.9 now states plainly that no existing convention exists, and explicitly defers reduced-motion handling to Milestone 6 (Accessibility) rather than instructing an implementing engineer to "match" something that isn't there. New components in this milestone use the same unguarded `motion/react` transitions every other screen in this app already uses — consistent with existing app-wide behavior, not a regression relative to it, and not a new gap Milestone 1 is introducing.

### 0.11 — DR-11: Wireframes were desktop-only despite a stated 320px testing requirement
**Agree, with a scope-consistent adjustment.** Since §0.2 above descopes automated screenshot testing at specific breakpoints (no test framework installed in this milestone), the "committed to 320/768/1024/1440 screenshot coverage" premise DR-11 was reacting to no longer applies as stated. The underlying design problem is still real, independent of testing: a dense multi-column row does not fit a narrow viewport.
**Resolution:** §Part 1.3 now includes a mobile layout description, reusing the exact collapse pattern already verified in `code/src/routes/app.goals.tsx` (`grid md:grid-cols-2 xl:grid-cols-3` — single-column stacked cards below the `md` breakpoint) rather than inventing a new one.

### 0.12 — DR-12: Factual error — claimed `test_assumptions.py` "confirmed absent"
**Agree, this was simply wrong.** Re-verified `backend/tests/test_financials.py` directly (257 lines, read in full): it already contains a `TestAssumptions` class with `test_get_assumptions_creates_defaults`, `test_get_assumptions_idempotent`, `test_update_assumptions`, `test_assumptions_requires_auth` — real, working coverage of exactly the behavior this milestone touches. v1's claim was based on a filename-only search, not a content check.
**Resolution:** §Part 3.13 now instructs extending the existing `TestAssumptions` class (adding the §0.6 concurrency-fix regression test and the six-field, not seven-field, scope) rather than creating a new file.

### 0.13 — DR-13: No pagination noted as a deliberate decision
**Agree it should be stated, not silently absent.** Adding pagination itself would be scope expansion this revision's mandate forbids introducing.
**Resolution:** One line added here: pagination on the four list endpoints is considered and explicitly deferred, on the basis of realistic cardinality (a personal finance user accumulates a handful to a few dozen rows across a lifetime, not thousands) — Engineering Constitution Rule 7 (no premature abstraction) applies directly. Not revisited unless real usage data says otherwise.

### 0.14 — DR-14: Liability `interest_rate` frontend bound unstated
**Agree.** Minor completeness gap.
**Resolution:** §Part 2.D now states the bound explicitly: `max="100"` on the percentage-displayed input, distinct from the Assumptions return-rate fields' `max="50"` (different backend bounds: `le=1` vs. `le=0.5`, both re-verified against `backend/app/schemas/{financials,assumptions}.py` directly).

---

## PART 1 — CROSS-CUTTING SPECIFICATION (Income, Expenses, Assets, Liabilities)

### 1.1 Component Hierarchy and Field-Config Schema (resolves DR-05)

```
app.financials.tsx (route component, new)
 └── FinancialsPage
      ├── FinancialsSection (config=INCOME_CONFIG)
      │    ├── AddRowForm (config)
      │    └── FinancialRow[] → EditRowForm (config, row) when editing
      ├── FinancialsSection (config=EXPENSE_CONFIG)
      ├── FinancialsSection (config=ASSET_CONFIG)
      └── FinancialsSection (config=LIABILITY_CONFIG)
```

Each entity's config is an ordered list of field descriptors. This is the concrete shape DR-05 found missing — stated here so no field-level decision is left to the implementing engineer:

| Field descriptor property | Meaning |
|---|---|
| `key` | matches the backend schema's field name exactly (e.g. `source_type`, `annual_amount`) |
| `label` | UI label text |
| `kind` | one of `text`, `select`, `currency`, `percentage` |
| `editableOnCreate` | always `true` for every field in this milestone |
| `editableOnUpdate` | `false` for the type-discriminator field of each entity (§0.4/DR-04's immutability rule), `true` for everything else |
| `required` | matches the backend schema's required/optional status |
| `maxLength` | `50` for type fields, `255` for description/institution, per `backend/app/schemas/financials.py` |
| `min` / `max` | matches the backend `Field(ge=..., le=...)` bound exactly, converted to the UI's display units (percentage fields show ×100 of the backend bound) |
| `percentageConversion` | `true` only for `interest_rate` in this milestone; the ×100/÷100 + 4-decimal rounding logic from §0.7 applies only where this is `true` |
| `options` | populated only for `kind: "select"` fields, reusing the existing fixed option lists already defined for onboarding where one exists (e.g., asset/liability type lists) |

**Per-entity configs:**

| Entity | Fields (`key`: `kind`, editableOnUpdate, notes) |
|---|---|
| Income | `source_type`: select, **not editable on update**; `description`: text, editable, optional; `annual_amount`: currency, editable, required, `min=0.01` (backend `gt=0`), `max=100000000` |
| Expense | `category`: select, **not editable on update**; `description`: text, editable, optional; `monthly_amount`: currency, editable, required, `min=0`, `max=10000000` |
| Asset | `asset_type`: select, **not editable on update** (pre-existing, unchanged); `institution`: text, editable, optional; `description`: text, editable, optional; `current_value`: currency, editable, required, `min=0`, `max=1000000000` |
| Liability | `liability_type`: select, **not editable on update** (pre-existing, unchanged); `institution`: text, editable, optional; `description`: text, editable, optional; `balance`: currency, editable, required, `min=0`, `max=1000000000`; `interest_rate`: percentage, editable, optional, `min=0`, `max=100` (§0.14); `monthly_payment`: currency, editable, required, `min=0`, `max=10000000`, defaults `0` |

This table is the single source of truth for what `AddRowForm`/`EditRowForm` render per entity — no additional design decision is needed to implement them.

### 1.2 Design Tokens — unchanged from v1
`surface-card`, `field-input`, `font-display`, `text-muted-foreground`, `border-border`/`border-border-strong`, `bg-gradient-to-r from-primary to-cyan` + `shadow-glow`, `text-destructive`/`bg-destructive/10 border-destructive/30`. No new token. `code/src/styles.css` is not touched. (Re-verified: these are the same classes read directly from `GoalSimPanel.tsx` and `wizard-steps.tsx` in the original spec pass; no change on review.)

### 1.3 Screen Wireframe — desktop and mobile (resolves DR-11)

**Desktop (`md` and above):** unchanged from v1 — stacked `surface-card` sections, each row rendered as an inline multi-column row (type · description · amount · edit · delete).

**Mobile (below `md`):** re-verified against `code/src/routes/app.goals.tsx`'s existing collapse pattern (`grid md:grid-cols-2 xl:grid-cols-3`, i.e., single column below `md`) — reused directly, not reinvented:
```
┌─────────────────────────────┐
│  Salary                 ✎ 🗑  │
│  Acme Corp                    │
│  $145,000/yr                  │
├─────────────────────────────┤
│  Freelance               ✎ 🗑  │
│  $12,000/yr                   │
└─────────────────────────────┘
```
Each row becomes a stacked mini-card (label line, secondary detail line, amount line) instead of an inline row, with the edit/delete icons pinned top-right — the same information, vertically arranged instead of horizontally, matching how `/app/goals`' own cards already respond to viewport width. No new responsive pattern is introduced.

### 1.4 Shared UX Flow (delete-copy strengthened, resolves DR-08)
Unchanged from v1 for add/edit (§1.4 steps 1-4 in v1 stand as written — re-verified against `GoalSimPanel.tsx`'s edit-toggle and `wizard-steps.tsx`'s `InputField`/`SelectField`, no change needed). Delete step revised:

> User clicks 🗑 on a row → confirm step now reads, entity-specifically: *"Delete [row's identifying text, e.g. 'Acme Corp salary' or 'Wells Fargo mortgage']? This can't be undone from here."* / "Yes, delete" / "Cancel" — not the generic "Are you sure?" v1 specified. On confirm, `DELETE` fires, the row is removed on success.

### 1.5-1.8 Error Handling / Loading / Success / Edge Cases — unchanged from v1
Re-verified against `GoalSimPanel.tsx`'s existing `editError`/`deleting`/`confirmDelete` state machine and found no error in v1's description of these patterns; no change.

### 1.9 Accessibility Requirements (reduced-motion claim corrected, resolves DR-10)
Unchanged: labeled inputs via `InputField`/`SelectField` reuse, `aria-label` per icon button naming its row, full keyboard operability.
**Changed:** the reduced-motion bullet no longer instructs "match the existing convention." Re-verified: no such convention exists anywhere in `code/src/` (§0.10). New components in this milestone use the same unguarded `motion/react` transitions as every other screen in the app today — this is consistent with, not a regression from, current app-wide behavior. Building a `prefers-reduced-motion` guard that nothing else in the app has is explicitly deferred to Milestone 6, not built here as an unscoped addition.

### 1.10 Testing Strategy (rewritten, resolves DR-02)
- **Backend:** extend `backend/tests/test_financials.py`'s existing `TestIncome`/`TestExpenses` classes (both already exist, confirmed by direct read) with cases for the two new `PATCH` endpoints, mirroring the existing `test_update_asset`/`test_update_liability_balance` shape exactly. Add the §0.6 concurrency regression test to `TestAssumptions` (already exists — §0.12).
- **Frontend:** **no new test framework is installed in this milestone** (§0.2). Verification is a manual QA checklist, executed against the running dev server before this milestone is called done:
  1. Add one row of each of the four entities; confirm each appears without a page reload.
  2. Edit a value on one row of each entity; confirm the new value persists across a page refresh (real backend round-trip, not just local state).
  3. Attempt to edit a type field (`source_type`/`category`/`asset_type`/`liability_type`) in the UI; confirm it renders disabled, not editable.
  4. Delete one row of each entity; confirm the entity-specific confirm copy from §1.4 appears, and the row disappears on confirm.
  5. Load the Financials page and Settings' Assumptions card at 375px width (a real narrow viewport, checked manually in devtools) and confirm no horizontal overflow, per §1.3's mobile layout.
  6. Confirm the new "Financials" item appears in the desktop sidebar between AI Copilot and Reports, and inside the mobile "More" menu alongside Reports/Profile/Settings — not in the primary mobile row.
  7. Open Settings' Assumptions card, change the inflation rate to `3.5`, save, refresh the page, and confirm the field still reads `3.5` (not `3.4999999999999996` or `35`) — the specific DR-07 regression check.
- **Regression guard, unchanged from v1 and still the most important test in this milestone:** a backend test asserting that creating/editing/deleting any of the four entities, or updating Assumptions, does not change any existing goal's stored `probability`.

### 1.11 Rollback Strategy — unchanged from v1
Every backend change is additive (two new endpoints, one new service file containing only new functions) or entirely unmodified (all 12 existing endpoints, `AssetUpdate`/`LiabilityUpdate`, the whole Assumptions router). The frontend route and nav entries are net-new and independently removable. No feature flag required for the backend; optional for staged frontend rollout.

---

## PART 2 — PER-ENTITY DELTAS FROM v1

Only what changed is restated here; everything else in v1's Part 2 (functional requirements, API contracts for Asset/Liability's already-existing endpoints, DB interactions, calculation-trigger analysis) was re-verified against current source during this revision and found accurate — no change.

### 2.A Income Sources
- **API contract:** `PATCH /api/v1/financials/income/{income_id}` — `IncomeSourceUpdate` schema, plain `BaseModel` (no `extra="forbid"`, per §0.4). `source_type` is omitted from the schema's fields, not rejected via a validation mode — sending it is silently ignored, identical to how `AssetUpdate` already behaves for `asset_type` today (re-verified, unchanged behavior).
- **Service:** `financials_service.update_income_source(db, current_user, income_id, patch) -> IncomeSource` — the only function in the new `financials_service.py` alongside `update_expense` (§0.9's narrowed scope).
- **Delete copy:** per §1.4.

### 2.B Expenses
- **API contract:** `PATCH /api/v1/financials/expenses/{expense_id}` — `ExpenseUpdate`, same plain-`BaseModel` convention.
- **Service:** `financials_service.update_expense(...)`, second and last function in the new service file.
- **Delete copy:** per §1.4.

### 2.C Assets
- **No backend change** (re-confirmed: `PATCH /api/v1/financials/assets/{id}` already exists, already excludes `asset_type` from `AssetUpdate`, already filters `is_active.is_(True)` in its lookup — all unchanged from v1's original, accurate description).
- **Delete copy:** per §1.4.
- Estate-module FK note from v1 (`estate.py`'s `ForeignKey("assets.id", ondelete="CASCADE")` is dormant because delete is soft, never a hard row delete) re-verified unchanged, still accurate.

### 2.D Liabilities
- **No backend change** (re-confirmed unchanged).
- **`interest_rate` frontend bound now explicit:** `max="100"` (§0.14), distinct from Assumptions' return-rate fields.
- **Delete copy:** per §1.4.

---

## PART 3 — PLANNING ASSUMPTIONS (Settings) — revised

**1. Functional requirements:** View and edit **six** fields (not seven — `tax_rate` excluded, §0.6a): `inflation_rate`, `expected_return_conservative`, `expected_return_balanced`, `expected_return_aggressive`, `retirement_age`, `social_security_monthly`.
**2-5 (non-functional, UX flow, wireframe, component hierarchy):** unchanged from v1's Part 3 in structure; wireframe below reflects six fields instead of seven.
```
┌───────────────────────────────────────────────────────────┐
│  Planning assumptions                            [Saved ✓]  │
│  These power every goal projection. Changes apply the next   │
│  time you edit or create a goal.                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ Inflation rate (%)   │  │ Target retirement age│          │
│  └─────────────────────┘  └─────────────────────┘          │
│  ┌─────────────────────┐                                     │
│  │ Social Security ($/mo)│                                    │
│  └─────────────────────┘                                     │
│  Expected annual returns                                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                  │
│  │Conservative│ │ Balanced  │ │Aggressive │                  │
│  │    (%)    │ │    (%)    │ │    (%)    │                  │
│  └───────────┘ └───────────┘ └───────────┘                  │
│                                        [Discard] [Save changes]│
└───────────────────────────────────────────────────────────┘
```
**6. API contract:** `GET`/`PUT /api/v1/assumptions` — unchanged endpoints, **but the `PUT` request body from this UI never includes `tax_rate`**, relying on the endpoint's existing partial-update (`exclude_unset`) semantics (re-verified in `backend/app/routers/assumptions.py`'s `upsert_assumptions`, unchanged) to leave that field exactly as it is. Backend requires **one addition**, resolving §0.6/DR-06:

```
get_assumptions (revised):
  SELECT ... WHERE user_id = current_user.id
  IF found: return it
  ELSE:
    TRY:
      INSERT with defaults; commit
    EXCEPT IntegrityError:
      rollback
      SELECT ... WHERE user_id = current_user.id  (the row the concurrent request just created)
      return it
```
This is new logic, not a pre-existing pattern being reused — disclosed explicitly per §0.6, since no other endpoint in this codebase currently does this (`grep` confirmed zero existing `IntegrityError` handling anywhere in `backend/app/`).

**7. Request/response examples:**
```
GET /api/v1/assumptions
→ 200 { "id": "…", "inflation_rate": 0.03, "expected_return_conservative": 0.05,
        "expected_return_balanced": 0.07, "expected_return_aggressive": 0.09,
        "tax_rate": 0.22, "retirement_age": 65, "social_security_monthly": 0.0 }
        (response still includes tax_rate — the field isn't removed from the schema
        or the table, only from this UI's rendered form and its PUT payload)

PUT /api/v1/assumptions
{ "inflation_rate": 0.035 }
        ← user typed "3.5"; frontend computed round(3.5 / 100, 4) = 0.035, per §0.7
→ 200 { ... "inflation_rate": 0.035, "tax_rate": 0.22 (untouched), ... }
```
**8. Validation rules:** unchanged bounds for the six remaining fields, re-verified against `backend/app/schemas/assumptions.py` directly: `inflation_rate`/`expected_return_*`: `ge=0, le=0.5` (UI: 0-50%); `retirement_age`: `ge=40, le=80`; `social_security_monthly`: `ge=0, le=10_000_000`.
**9. Database interactions:** `financial_assumptions` table; `tax_rate` column is untouched by any write this milestone introduces.
**10. Service interactions:** the concurrency fix lives in the existing `backend/app/routers/assumptions.py` (the file is small enough that Engineering Constitution Rule 1's thin-router bar isn't in tension with keeping this fix there — re-verified file size, ~65 lines, unchanged assessment from v1).
**11. Calculation triggers:** unchanged from v1 — no retroactive recompute, per ADR-001, re-verified against `backend/app/services/planning_service.py`'s `calculate_goal_probability` (fires only on goal create/update).
**12. Recommendation triggers:** unchanged hedge from v1 (verify `tax_rate`'s role in `family_insurance_service.py` during implementation) — **now more clearly moot for this milestone specifically**, since this UI never writes `tax_rate` at all; the hedge only matters if some future milestone re-opens that field.
**13. Error handling:** unchanged from v1 — inline error on `PUT` failure, matching `app.profile.tsx`'s pattern, values preserved not reverted.
**14-15 (loading/success states):** unchanged from v1.
**16. Edge cases:** unchanged from v1's blank-field handling, plus: the concurrency fix (§0.6) is itself an edge case now explicitly covered rather than left as a hedge.
**17. Accessibility:** unchanged, per §1.9's corrected reduced-motion honesty.
**18. Test plan:** extend the **existing** `TestAssumptions` class in `backend/tests/test_financials.py` (§0.12) — not a new file — with: a concurrency test simulating two near-simultaneous first-time `GET` calls and asserting both succeed with no uncaught `IntegrityError` (the DR-06 fix's regression test); a boundary test at each of the six fields' `ge`/`le` limits; a test asserting a `PUT` payload never containing `tax_rate` leaves that field unchanged (protects §0.6a's exclusion from silently regressing later). Frontend: manual QA checklist item 7 in §1.10 covers the rounding behavior.
**19. Acceptance criteria:** unchanged core criterion from v1 (change inflation rate, see "Saved ✓", refresh, see it persisted), **narrowed**: the onboarding-copy-truthfulness criterion now explicitly excludes `tax_rate` (§0.6a's disclosed residual gap) rather than claiming full resolution.
**20. Rollback strategy:** unchanged — additive frontend card, one additive backend concurrency fix with no effect on any existing caller (the fix only changes behavior in the previously-uncaught-exception race case, which had no defined "correct" behavior before this fix — 500 with no fallback was never intentional API contract).

---

## PART 4 — MILESTONE 1 DEFINITION OF DONE (revised)

- [ ] `PATCH /api/v1/financials/income/{id}` and `PATCH /api/v1/financials/expenses/{id}` exist, tested, using the plain-`BaseModel` convention (no `extra="forbid"`) consistent with every other Update schema in the codebase.
- [ ] `backend/app/services/financials_service.py` exists containing exactly `update_income_source` and `update_expense` — the other 12 financials endpoints are explicitly, intentionally left unmoved (tracked in Outstanding Risks, not silently implied as refactored).
- [ ] `GET /api/v1/assumptions`'s get-or-create path is race-safe (§0.6/§Part 3.6), with a passing concurrency test.
- [ ] `code/src/routes/app.financials.tsx` exists; desktop nav shows "Financials" between AI Copilot and Reports; mobile "More" menu shows it alongside Reports/Profile/Settings; mobile primary row is unchanged (still exactly Dashboard/Goals/Family/Copilot).
- [ ] All four sections support add/edit/delete end-to-end against the real backend, using the field-config table in §1.1 as the implementation's source of truth; type fields render disabled in edit mode.
- [ ] Delete confirmations use entity-specific copy naming the row and disclosing no in-app undo exists yet (§1.4).
- [ ] Settings' Assumptions card exposes exactly six fields (`tax_rate` excluded, §0.6a); percentage fields round to 4 decimal places on both conversion directions (§0.7), verified by the manual QA checklist's item 7 and the corresponding backend/frontend logic.
- [ ] The manual QA checklist in §1.10 has been run and passed in full — no automated frontend test suite is claimed or required for this milestone (§0.2).
- [ ] `ruff check app/` and `mypy --strict app/` both clean (Engineering Constitution Rule 5, unchanged requirement).
- [ ] `docs/backend.md`, `docs/architecture.md`, and `CHANGELOG.md`'s `[Unreleased]` section updated, including an explicit note that `tax_rate` remains deprecated and was deliberately excluded from this milestone's new UI.

---

## CHANGE LOG (v1 → v2)

| # | Change | Driven by |
|---|---|---|
| 1 | Desktop nav order: Financials moved from "between Goals and Family" to "between AI Copilot and Reports" | DR-01 |
| 2 | Frontend test framework installation removed from scope; replaced with a manual QA checklist | DR-02 |
| 3 | `MOBILE_MORE` gains `/app/financials`; `MOBILE_PRIMARY` explicitly left unchanged | DR-03 |
| 4 | `extra="forbid"` proposal dropped entirely; new Update schemas use the codebase's existing plain-`BaseModel` convention | DR-04 |
| 5 | Concrete field-config schema and per-entity config table added | DR-05 |
| 6 | `GET /assumptions` get-or-create path gets a required `IntegrityError`-safe fix, explicitly disclosed as new (not pre-existing) logic | DR-06 |
| 6a | `tax_rate` removed from the Assumptions Settings form (6 fields, not 7) — deprecated-field conflict found during this revision's own re-verification, not in the original review | new, this revision |
| 7 | Percentage conversion now specifies 4-decimal rounding on both directions | DR-07 |
| 8 | Delete confirmation copy made entity-specific, discloses no undo | DR-08 |
| 9 | `financials_service.py` scope narrowed to the two new functions only; the other 12 endpoints explicitly left untouched | DR-09 |
| 10 | Reduced-motion requirement corrected to state no existing convention exists; deferred to Milestone 6 rather than falsely described as "matching" something | DR-10 |
| 11 | Mobile wireframe added, reusing `/app/goals`' existing responsive collapse pattern | DR-11 |
| 12 | Assumptions test-plan corrected to extend the existing `TestAssumptions` class in `test_financials.py`, not create a new file | DR-12 |
| 13 | Pagination deferral stated explicitly as a considered-and-rejected decision | DR-13 |
| 14 | Liability `interest_rate` frontend `max="100"` stated explicitly | DR-14 |

---

## REVIEW RESOLUTION MATRIX

| Finding | Severity | Agree? | Evidence checked | Resolution |
|---|---|---|---|---|
| DR-01 | High | Yes | `app-shell.tsx` nav comment, lines 30-34 | Nav order changed |
| DR-02 | High | Yes | `code/package.json` devDependencies, no e2e/test dirs found | Testing scope narrowed to manual QA + backend tests |
| DR-03 | High | Yes | `app-shell.tsx` `grid-cols-5`, render loop, lines 286-352 | `MOBILE_MORE` updated |
| DR-04 | Medium-High | Yes | No `extra="forbid"` anywhere in `schemas/`; no unsafe spread in `api.ts` | Proposal dropped |
| DR-05 | Medium | Yes | v1 text itself, no config schema present | Config table added |
| DR-06 | Medium | Yes | `assumptions.py` model `unique=True`; router has no exception handling | Fix specified |
| DR-07 | Medium | Yes | No rounding step in v1's §0.9 | Rounding specified |
| DR-08 | Medium | Yes | `UX_PRINCIPLES.md` #10; no Milestone 5 restore in this milestone's scope | Copy revised |
| DR-09 | Medium | Yes | Roadmap's own "Low risk" framing depends on diff size v1 didn't preserve | Extraction narrowed |
| DR-10 | Medium | Yes | Zero matches for reduced-motion handling anywhere in `code/src/` | Claim corrected, deferred to M6 |
| DR-11 | Medium | Yes | `app.goals.tsx`'s real responsive classes found and reused | Mobile wireframe added |
| DR-12 | Low | Yes | `test_financials.py` read in full — `TestAssumptions` already exists | Test plan corrected |
| DR-13 | Low | Yes | No pagination present, no stated reason in v1 | One-line deferral note added |
| DR-14 | Low | Yes | `LiabilityUpdate`'s `interest_rate` bound vs. Assumptions' bounds, both re-checked | Bound stated |

Every finding was accepted. None were disputed — each was independently re-verified against source during this revision (not merely re-asserted from the review document), and every piece of evidence the review cited held up under a fresh check, with one additional problem (§0.6a) found in the same area during that re-verification that the original review did not catch.

---

## OUTSTANDING RISKS (not resolved by this revision, disclosed deliberately)

1. **Partial service-layer migration.** After this milestone, `financials_service.py` exists but only handles 2 of 14 financials endpoints; the router remains "thin" for new code and not-yet-thin for old code. A future cleanup pass should either finish the extraction or explicitly accept the split permanently — currently undecided.
2. **`tax_rate` remains a live, deprecated, still-written field.** Onboarding still collects and writes it; this milestone declines to build new UI around it but does not fix the underlying inconsistency (a deprecated field with an active writer). A future decision is needed: remove it from onboarding, or complete its replacement by the `tax_slabs` engine.
3. **No frontend automated test coverage for the four new CRUD sections or the Assumptions card.** The manual QA checklist is a real but weaker substitute. If a frontend test framework is adopted project-wide later, this milestone's components should be the first backfilled.
4. **Mobile placement of Financials in "More," not the primary row, is a judgment call based on assumed usage cadence (occasional vs. daily), not measured data.** If real usage shows users need frequent access, this should be revisited — explicitly not a permanent architectural commitment.
5. **The `IntegrityError`-handling pattern introduced for Assumptions (§0.6) has no precedent elsewhere in the codebase.** If other get-or-create patterns exist elsewhere with the same latent race (not audited in this pass), they remain unfixed.

---

## DESIGN FREEZE CHECKLIST

Before implementation begins, confirm each of the following is true — if any is not, this specification is not ready to freeze:

- [ ] Every item in the Review Resolution Matrix above shows a concrete change in this document (not just a stated intention) — spot-check §0.1-§0.14 and §0.6a against Parts 1-3.
- [ ] `MOBILE_PRIMARY`/`MOBILE_MORE`/`nav` changes in §0.1/§0.3 are the only `app-shell.tsx` changes required — no other file in that component needs modification for Milestone 1.
- [ ] The field-config table in §1.1 accounts for every field in every one of the four entities' `Create`/`Update`/`Response` schemas (re-checked: yes — 3 Income fields, 3 Expense fields, 4 Asset fields, 6 Liability fields, all accounted for).
- [ ] The Assumptions form's six-field scope (§Part 3) is reflected consistently in the wireframe, the API examples, and the test plan — no remaining reference to a seventh field anywhere in this document.
- [ ] No new npm package, Python package, database table, or API prefix is introduced anywhere in this document.
- [ ] Every "unchanged from v1" claim in Parts 1-3 was re-verified against source during this revision, not carried forward from v1 by assumption — confirmed per this document's own citations throughout Part 0 and Part 2.
- [ ] Outstanding Risks are acknowledged by whoever approves this document for implementation, not silently accepted by omission.

If every box above is true, this specification is frozen and ready for implementation to begin.
