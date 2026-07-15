# MILESTONE 1 — FINANCIAL PROFILE MANAGEMENT
## Implementation Specification

**Role:** Lead Software Architect
**Inputs read in full for this specification:** `ImplementationRoadmap.md`, `PreLaunchProductAudit.md`, `ArchitectureDecisionRecordBible.md` (ADR-001 in particular), `docs/architecture.md`, `docs/backend.md`, `docs/database.md`, `docs/frontend.md`, `docs/ENGINEERING_CONSTITUTION.md`, `docs/PRODUCT_PRINCIPLES.md`, `docs/UX_PRINCIPLES.md`, plus direct re-verification of current source: `backend/app/models/financials.py`, `backend/app/schemas/financials.py`, `backend/app/routers/financials.py`, `backend/app/schemas/assumptions.py`, `backend/app/routers/assumptions.py`, `code/src/lib/api.ts`, `code/src/components/onboarding/wizard-steps.tsx`, `code/src/routes/onboarding.tsx`, `code/src/components/dashboard/GoalSimPanel.tsx`, `code/src/components/app-shell.tsx`, `code/src/routes/app.family.tsx`, `backend/tests/conftest.py`.
**Scope:** Milestone 1 only — PLA-001 (Income / Expenses / Assets / Liabilities CRUD) and PLA-002 (Planning Assumptions). No other milestone's work is specified here.
**Out of scope, explicitly:** bulk actions (Milestone 2), dashboard staleness indicators (Milestone 3), email-field fix (Milestone 4), restore/undo (Milestone 5), accessibility audit findings beyond the baseline requirements stated per-feature below (Milestone 6). Do not implement any of these while building Milestone 1.

An engineer building from this document needs no other source to make a structural decision. Every open question the roadmap left unresolved is closed in Part 0 below, with the evidence that closed it.

---

## PART 0 — RESOLVED AMBIGUITIES (read this before anything else)

### 0.1 — Soft-delete is not a decision to make. It already exists.
`ImplementationRoadmap.md` (PLA-006) asked whether Milestone 1 should adopt soft-delete for the four financials entities. **It already has, in the current codebase, for all four.** `backend/app/models/financials.py` defines `is_active: Mapped[bool]` on `IncomeSource`, `Expense`, `Asset`, and `Liability`, and every existing `DELETE` handler in `backend/app/routers/financials.py` sets `is_active = False` — never a hard `db.delete()`. Every `list_*` query already filters `.is_active.is_(True)`. **No schema change, no behavior change, and no decision is needed here.** Both prior documents overstated this as open; treat it as closed. The only real gap is that no *restore* UI exists yet — that is Milestone 5, not this one.

### 0.2 — `created_at`/`updated_at` already exist at the database and backend-schema level.
All four tables already have `created_at` and `updated_at` columns (server-defaulted, `updated_at` auto-updates via `onupdate=func.now()`), and `IncomeSourceResponse`/`ExpenseResponse`/`AssetResponse`/`LiabilityResponse` in `backend/app/schemas/financials.py` already return both fields. **The gap is frontend-only:** `code/src/lib/api.ts`'s `IncomeSource`/`Expense`/`Asset`/`Liability` TypeScript types do not currently declare `created_at`/`updated_at`. **Decision: add both fields to all four frontend types as part of Milestone 1.** This is free (the backend already sends them) and removes a dependency Milestone 3 would otherwise have to re-open this same file for.

### 0.3 — Route and navigation placement.
**Decision: a single new top-level route, `code/src/routes/app.financials.tsx`, with a new top-level nav item in `code/src/components/app-shell.tsx`'s `NAV_ITEMS` array, positioned immediately after `"/app/goals"` and before `"/app/family"`.**
Rationale: `NAV_ITEMS` today is `Dashboard, Goals, Family, AI Copilot, Reports, Profile, Settings`. Financial facts are the second most foundational data surface after Goals — Dashboard, Reports, and (per Volume 5) Insurance/Scheme recommendations all read from them. Family earned a top-level slot for a comparable reason (`docs/PRODUCT_PRINCIPLES.md` #5: "Family is a first-class navigation item, not a settings sub-page, precisely because it's a defensible product position"). The same logic applies here with more force: Financials is not a settings sub-page candidate, because Settings already establishes a single-record-form pattern (Change Password, Delete Account) that does not fit a four-entity list-CRUD surface. This route needs **no nested children** — unlike `app.family.tsx` (which has `app.family.add.tsx` and `app.family.members.$id.tsx` as sibling full-page routes because a household member has enough fields to warrant its own page), none of the four financial-fact entities here have enough fields to justify leaving the list page. `app.financials.tsx` is a leaf route, not a layout route — do not add an `<Outlet/>` wrapper file.

### 0.4 — Page layout: stacked cards, not tabs.
**Decision: one scrollable page with four stacked `surface-card` sections — Income, Expenses, Assets, Liabilities, in that order — never tab panels that hide data behind a click.**
Rationale: `docs/UX_PRINCIPLES.md` #6 ("Users always know what to do next... an empty state is never a dead end") and the existing convention on `/app` (Dashboard) and `/app/goals`, both of which use stacked, always-visible cards, not tabs. Hiding Assets behind a tab click when a user is trying to understand their whole financial picture works against the product's own stated purpose. Each section is independently collapsible is *not* required for Milestone 1 — keep it simple per Engineering Constitution Rule 7 (no premature abstraction); add collapse only if real usage shows the page is too long, which is not yet known.

### 0.5 — Planning Assumptions location: a new Settings card, not a new route.
**Decision: a fifth card in `code/src/routes/app.settings.tsx`, alongside `ChangePasswordSection` and `DeleteAccountSection`, not a standalone route.**
Rationale: Assumptions is a single record per user (the backend's own `GET /assumptions` get-or-creates exactly one row), which matches the single-form-with-Save pattern Settings and Profile already use — not the list-of-many-rows pattern the other four entities need. This also directly satisfies the onboarding copy's own claim ("refine them any time in Settings") literally, not just in spirit.

### 0.6 — Planning Assumptions scope: all seven fields, not onboarding's subset of four.
Onboarding's `AssumptionsFormState` (`wizard-steps.tsx`) only collects `inflation_rate`, `tax_rate`, `retirement_age`, `social_security_monthly` — it never lets the user set `expected_return_conservative`/`balanced`/`aggressive`, and its own copy says explicitly: *"Expected returns use built-in defaults... These can be adjusted in Settings after onboarding."* **Decision: the Settings Assumptions card exposes all seven fields defined in `FinancialAssumptionsUpdate`.** Shipping only the four onboarding-familiar fields would leave one of the two false claims in the onboarding copy (PLA-002) still false after "launch." Both claims must resolve together.

### 0.7 — `source_type`/`category`/`asset_type`/`liability_type` are immutable after creation.
`AssetUpdate` and `LiabilityUpdate` (`backend/app/schemas/financials.py`) already exclude `asset_type`/`liability_type` from their editable fields — only value/institution/description fields are updatable. **Decision: the new `IncomeSourceUpdate` and `ExpenseUpdate` schemas follow the identical precedent** — `source_type`/`category` are not included. To change an entry's type, the user deletes it and creates a new one. **This must be visually explicit in the edit UI** (the type field renders disabled/read-only in edit mode, not simply absent) so it reads as a deliberate constraint, not a bug — consistent with `UX_PRINCIPLES.md` #7, "honesty over polish."

### 0.8 — HUF assignment (`huf_entity_id`) is out of scope for Milestone 1.
All four models carry a nullable `huf_entity_id` column, but **no existing Pydantic schema (Create, Update, or Response) exposes it**, and no frontend type includes it. This is pre-existing, deliberate scope from the Foundation Reconciliation work (per the model file's own header comment) — not a gap Milestone 1 introduces or is responsible for closing. Do not add `huf_entity_id` to any new schema or form in this milestone.

### 0.9 — Percentage fields: display convention vs. storage convention.
Backend storage and the `FinancialAssumptions` Pydantic schema use **decimal fractions** (`0.03` = 3%, bounded `ge=0, le=0.5` for `inflation_rate`/`expected_return_*`, `ge=0, le=1` for `tax_rate`). The existing onboarding form displays **whole-number percentages** ("3" for 3%) and converts with `parseFloat(value) / 100` on submit (verified at `code/src/routes/onboarding.tsx`, `handleAssumptions`). **Decision: the Settings Assumptions form uses the identical whole-number-percentage display convention and the identical ÷100 (submit) / ×100 (load) conversion**, for `inflation_rate`, `tax_rate`, `expected_return_conservative`, `expected_return_balanced`, `expected_return_aggressive`. `retirement_age` (integer years) and `social_security_monthly` (currency) are not percentages and need no conversion. Getting this conversion backwards silently corrupts a user's projections by a factor of 100 — flagged explicitly because it is the single easiest mistake to make in this milestone.

### 0.10 — Error response shape.
No custom global exception handler exists in `backend/app/main.py` beyond `RateLimitMiddleware`/`RequestIDMiddleware` — every error response is FastAPI's default `{"detail": "<message>"}` JSON body with the corresponding HTTP status code. All new endpoints in this milestone must raise `HTTPException(status_code=..., detail=...)` exactly as the existing `financials.py` handlers already do. Do not introduce a different error envelope for the two new endpoints.

### 0.11 — Rate limiting.
`RateLimitMiddleware` is already global to every route; it requires no per-endpoint configuration. The two new `PATCH` endpoints need no special treatment — they carry the same authenticated, per-user-scoped profile as the existing `PATCH /financials/assets/{id}`, which has no dedicated throttle beyond the global middleware. Do not add one.

### 0.12 — Mock-mode parity is mandatory, not optional.
Per `CLAUDE.md`: *"Mock fallback must always work... Never remove or break the mock path."* Every new or modified function in `code/src/lib/api.ts` must retain the existing `BASE_URL ? apiFetch(...) : delay(...)` branching pattern with a realistic mock return value, matching every other function in this file. This is stated once here and applies to every API contract section below without being repeated.

### 0.13 — Settings save errors must be visible, unlike onboarding's fire-and-forget pattern.
`onboarding.tsx`'s `handleAssumptions` deliberately swallows save failures (`catch { advance(); }` — "proceed even if save fails") because blocking onboarding completion on a non-critical save is the right call *there*. **This is not the right pattern for Settings.** A user who explicitly clicks "Save" on the Assumptions card and gets no feedback on failure violates `UX_PRINCIPLES.md` #10 ("errors are scoped and reassuring") and directly reproduces the PLA-011 class of bug (a save that silently doesn't happen). The Settings Assumptions card must show a visible error state on failure — see §6.13 below.

---

## PART 1 — CROSS-CUTTING SPECIFICATION (applies to Income, Expenses, Assets, Liabilities)

This part is written once and referenced by all four entity sections in Part 2 to avoid restating identical mechanics four times (Engineering Constitution Rule 7). Each entity section in Part 2 states only what differs.

### 1.1 Component Hierarchy

```
app.financials.tsx                              (route component, new)
 └── FinancialsPage                              (new, code/src/routes/app.financials.tsx or co-located)
      ├── FinancialsSection (title="Income", ...)          (new, code/src/components/financials/FinancialsSection.tsx)
      │    ├── AddRowForm (entity="income")                (new, code/src/components/financials/AddRowForm.tsx)
      │    └── FinancialRow[] (one per income source)       (new, code/src/components/financials/FinancialRow.tsx)
      │         └── EditRowForm (inline, shown when editing) (new, code/src/components/financials/EditRowForm.tsx)
      ├── FinancialsSection (title="Expenses", ...)
      │    ├── AddRowForm (entity="expense")
      │    └── FinancialRow[] (one per expense)
      ├── FinancialsSection (title="Assets", ...)
      │    ├── AddRowForm (entity="asset")
      │    └── FinancialRow[] (one per asset)
      └── FinancialsSection (title="Liabilities", ...)
           ├── AddRowForm (entity="liability")
           └── FinancialRow[] (one per liability)
```

`FinancialsSection`, `AddRowForm`, `FinancialRow`, and `EditRowForm` are generic, entity-parameterized components (four field-config objects, not four copy-pasted component sets) — this is the one place in this milestone where a shared abstraction is justified, because the fourth near-identical case (Liabilities) already exists at spec time, satisfying Engineering Constitution Rule 7's own bar ("a shared helper built for a fourth case that doesn't exist yet" is the thing to avoid — here the fourth case is already in front of us).

Reused, not rebuilt: `InputField` and `SelectField` from `code/src/components/onboarding/wizard-steps.tsx` (import directly — do not fork a second copy). Reused visual/interaction pattern: `GoalSimPanel.tsx`'s inline edit-toggle (pencil icon → form expands in place) and two-step delete confirm (`Trash2` icon → "Are you sure?" / "Yes, delete" / "Cancel").

### 1.2 Design Tokens / Classes (frozen system — do not introduce new ones)

`surface-card` (section container), `field-input` (all inputs/selects), `font-display` (headings), `text-muted-foreground` (labels/secondary text), `border-border` / `border-border-strong` (dividers, hover), `bg-gradient-to-r from-primary to-cyan` + `shadow-glow` (primary buttons, matches every other primary action in the app), `text-destructive` / `bg-destructive/10 border-destructive/30` (delete confirm), `bg-success/15 text-success` / `bg-warning/15 text-warning` (status pills, reused for over-budget or negative-net indicators if used — see §2.16). No new color, font, or spacing token is introduced anywhere in this milestone — `code/src/styles.css` is not touched.

### 1.3 Screen Wireframe Description (shared shape, all four sections)

```
┌─────────────────────────────────────────────────────────────┐
│  Financials                                    [nav: active]  │
│  Keep your income, expenses, assets, and liabilities current   │
│  so every number on your Dashboard reflects real life.         │
├─────────────────────────────────────────────────────────────┤
│  ▸ INCOME                                                       │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ [Source type ▾] [Description______] [Annual $______] [+Add]│
│  ├───────────────────────────────────────────────────────┤   │
│  │ Salary · Acme Corp              $145,000/yr    ✎  🗑    │   │
│  │ Freelance                        $12,000/yr    ✎  🗑    │   │
│  │ (empty state if none: "No income sources yet — add your │   │
│  │  first one above." — never a blank silent card)          │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                                 │
│  ▸ EXPENSES  (same shape)                                       │
│  ▸ ASSETS    (same shape, + institution column)                 │
│  ▸ LIABILITIES (same shape, + interest rate / monthly payment)  │
└─────────────────────────────────────────────────────────────┘
```
Each row's edit affordance (✎) expands an `EditRowForm` inline directly below that row (matching `GoalSimPanel`'s `AnimatePresence`/`motion.form` height-animation pattern), pushing later rows down rather than opening a modal or a slide-over — a slide-over is right for a single goal's full detail (Monte Carlo, optimizer, education planning) but wrong here, where the point is comparing multiple rows in the same section at once.

### 1.4 Shared UX Flow

1. Page loads → four independent `GET` calls fire in parallel (`getIncome`, `getExpenses`, `getAssets`, `getLiabilities`) — each section renders its own loading/empty/error/loaded state independently; one section's failure must never block another's (same failure-isolation principle already documented for the Family dashboard's per-card queries).
2. User fills the inline `AddRowForm` at the top of a section and submits → optimistic-free, waits for the `POST` response, appends the returned row to that section's list, clears the form.
3. User clicks ✎ on a row → `EditRowForm` expands inline, pre-filled from that row's current values, type field shown but disabled (§0.7).
4. User edits a value and clicks "Save changes" → `PATCH` fires with only the changed, defined fields; on success the row updates in place and the form collapses; on failure an inline error shows inside the still-open form (matching `GoalSimPanel`'s `editError` pattern) and the form stays open so the user doesn't lose their edits.
5. User clicks 🗑 on a row → two-step confirm ("Are you sure?" / "Yes, delete" / "Cancel") exactly matching `GoalSimPanel`; on confirm, `DELETE` fires, the row is removed from the list on success.
6. No page-level "Save" button anywhere — every action (add/edit/delete) is committed independently and immediately, matching the existing Goals and Family patterns. There is no unsaved-changes state to lose track of.

### 1.5 Shared Error Handling
- Section-level `GET` failure: the section renders an inline error card ("Couldn't load your income sources — try refreshing this section.") with a retry button, while the other three sections remain fully interactive — one section's backend failure must never blank the whole page.
- `POST`/`PATCH` failure (validation or network): inline error text inside the open form, form stays open, submitted values are preserved so the user does not have to re-type. Matches `GoalSimPanel.editError`.
- `DELETE` failure: the confirm step collapses back to the un-confirmed state with a brief inline error ("Couldn't delete — try again."), matching `GoalSimPanel.handleDelete`'s existing `catch` behavior (`setDeleting(false); setConfirmDelete(false);`), extended with a visible message per `UX_PRINCIPLES.md` #10 (the existing goal-delete pattern is silent on failure today — this milestone should not carry that silence into new code, since the audit already flagged silent failures as a trust problem in PLA-011).
- 404 on `PATCH`/`DELETE` (row deleted in another tab/session): treat identically to a generic failure — inline error, no special-cased copy, since this project has no realtime sync and this is an acceptably rare edge case (see §1.8).

### 1.6 Shared Loading States
- Section skeleton: three placeholder rows at reduced opacity while the initial `GET` is in flight (consistent with `Loader2` spinner usage elsewhere, but a skeleton is preferred here since it communicates *shape*, not just "something is happening," reducing layout shift when real data arrives).
- Per-row action loading: the acted-on row's icon buttons show `Loader2` in place of the icon (matching `GoalSimPanel`'s `deleting`/`saving` boolean-gated spinner swap) — other rows remain interactive during that one row's in-flight request.

### 1.7 Shared Success States
- New row: appends with a brief `motion` fade/slide-in (matching the existing `motion/react` usage in `GoalSimPanel`), no toast — the row appearing *is* the confirmation, consistent with how Goals and Family already work.
- Edit: the form collapses and the updated value is visible immediately in the row — again, no separate toast; the changed number *is* the confirmation.
- Delete: the row is removed with a brief fade-out, not an abrupt disappearance (respect `prefers-reduced-motion` — see §1.9).

### 1.8 Shared Edge Cases
- Empty section (zero rows): render the empty-state copy specified per entity in Part 2, never a bare blank card — per `UX_PRINCIPLES.md` #11, "empty states are normal states, not apologies."
- Concurrent edit from two tabs: last write wins, no optimistic-locking/version check is implemented in this milestone (no evidence any other entity in this codebase does this either — do not introduce it here as a one-off).
- Extremely long `description`/`institution` strings: backend already enforces `max_length=255`; the frontend input must carry a matching `maxLength={255}` so the failure is prevented, not just handled after a 422.
- Values at or beyond the `_MAX_BALANCE`/`_MAX_ANNUAL_AMOUNT`/`_MAX_MONTHLY_AMOUNT` ceilings (§2 per entity): backend returns 422; frontend must surface the specific rejected value and bound in the inline error, not a generic "invalid input."
- Deleting the only row in a section: section transitions directly to its empty state, no special-cased "last one" confirmation beyond the normal two-step delete confirm.
- Rapid double-submit on Add: disable the Add button for the duration of the in-flight `POST` (`disabled={submitting}`), matching every other submit button in this codebase.

### 1.9 Shared Accessibility Requirements
- Every icon-only button (✎ edit, 🗑 delete) carries a `title`/`aria-label` naming the row it acts on (e.g. `aria-label="Edit Salary income source"`), not just a bare icon — matching `GoalSimPanel`'s existing `title={editing ? "Cancel edit" : "Edit goal"}` pattern, extended to include the row's own identifying text since a screen reader user navigating a list of six income rows needs to distinguish which edit/delete button belongs to which row.
- Every `AddRowForm`/`EditRowForm` field has a associated `<label>` (already guaranteed by reusing `InputField`/`SelectField`, which both render a real `<label>` — do not replace them with bare `placeholder`-only inputs anywhere in this milestone).
- Status/empty-state text must not rely on color alone (`UX_PRINCIPLES.md` #8) — none of the four sections currently need a color-coded status pill in Milestone 1's base scope (that's a Milestone 3/dashboard concern), so this mainly constrains any future addition, not a new requirement to build now.
- All `motion`/`AnimatePresence` transitions (row add/remove, edit-form expand) must respect `prefers-reduced-motion` — reuse whatever pattern `GoalSimPanel`'s existing animations already follow (confirm the project's existing reduced-motion handling convention during implementation and match it; do not invent a second convention).
- Keyboard: every action (add, edit-toggle, save, cancel, delete-confirm, delete-cancel) must be reachable and operable via `Tab`/`Enter`/`Space` with no mouse-only affordance — this is a baseline requirement inherited from every other interactive surface in this codebase, not a new bar.

### 1.10 Shared Test Strategy
- Backend: extend `backend/tests/test_financials.py` (already exists; confirm current coverage during implementation rather than assuming) with cases for every new endpoint, mirroring the existing Asset/Liability `PATCH` test shape for the two new Income/Expense `PATCH` endpoints.
- Frontend: component-level tests for `AddRowForm`/`EditRowForm`/`FinancialRow` (generic, so one test suite covers all four entities via the field-config parameter) plus one Playwright end-to-end journey per this project's web-testing convention: add → edit → delete one row of each of the four entities in a single flow, screenshotted at 320/768/1024/1440 per the frozen design system's responsive requirement.
- Regression guard (critical, explicit): a test asserting that creating/editing/deleting any of the four entities **does not** change any existing goal's `probability` field — this is the one thing that must never regress, since the audit and roadmap both rely on the verified fact that Monte Carlo's Calculation Context never reads these tables.

### 1.11 Shared Rollback Strategy
Every backend change in Part 2 is additive (two new endpoints, two new schemas) or already-existing (Asset/Liability `PATCH`, all four `DELETE`s) — reverting the two new endpoints has zero effect on any existing caller, since nothing existing calls them yet. The frontend route is net-new; removing the nav item and route file fully reverts the user-facing surface with no effect on any other screen (Dashboard, Goals, Family, Reports all read the same tables independently and unconditionally — none of them import anything from `app.financials.tsx`). No feature flag is required for the backend. A frontend feature flag around the new nav item is optional and recommended only for staged rollout, not for safety.

---

## PART 2 — PER-ENTITY SPECIFICATION

### 2.A INCOME SOURCES

**1. Functional requirements:** A user can view all their active income sources; add a new one (type + optional description + annual amount); edit description and/or annual amount on an existing one; delete one (soft-delete).
**2. Non-functional requirements:** List load completes within the same latency budget as any other authenticated `GET` in this app (no new SLA introduced); form submission round-trip must disable the submit control for its duration to prevent duplicate rows.
**3. UX flow:** Per §1.4, unmodified.
**4. Wireframe:** Per §1.3's Income section.
**5. Component hierarchy:** Per §1.1, `entity="income"`.
**6. API contract:**
- `GET /api/v1/financials/income` → `200 OK`, `list[IncomeSourceResponse]` — **already implemented, no change.**
- `POST /api/v1/financials/income` → `201 Created`, `IncomeSourceResponse` — **already implemented, no change.**
- `PATCH /api/v1/financials/income/{income_id}` → `200 OK`, `IncomeSourceResponse` — **new**, mirrors `PATCH /financials/assets/{asset_id}` exactly: 404 if not found or not owned by `current_user`, 404 if `is_active` is false (soft-deleted rows are not editable — matches the existing Asset/Liability `PATCH` precedent, which filters `Asset.is_active.is_(True)` in its lookup query).
- `DELETE /api/v1/financials/income/{income_id}` → `204 No Content` — **already implemented, no change.**
**7. Request/response examples:**
```
POST /api/v1/financials/income
{ "source_type": "salary", "description": "Acme Corp", "annual_amount": 145000 }
→ 201
{ "id": "…", "user_id": "…", "source_type": "salary", "description": "Acme Corp",
  "annual_amount": 145000.0, "is_active": true,
  "created_at": "2026-07-10T00:00:00Z", "updated_at": "2026-07-10T00:00:00Z" }

PATCH /api/v1/financials/income/{id}
{ "annual_amount": 152000 }
→ 200
{ "id": "…", ... "annual_amount": 152000.0, "updated_at": "2026-07-10T00:05:00Z" }

PATCH /api/v1/financials/income/{id}   (attempting to change source_type — not accepted)
{ "source_type": "bonus" }
→ 200, unchanged — IncomeSourceUpdate has no source_type field, so FastAPI/Pydantic silently
  ignores an extra key unless `model_config = {"extra": "forbid"}` is set. Decision: set
  `extra="forbid"` on IncomeSourceUpdate (and ExpenseUpdate) so an attempt to change an
  immutable field returns 422, not a silent no-op — silent no-ops on requests the frontend
  should never send anyway are still worth rejecting loudly, per Engineering Constitution
  Rule 6 ("tests prove behavior") — this is testable, unambiguous behavior, not a silent
  swallow. (Note: verify AssetUpdate/LiabilityUpdate's current `extra` behavior during
  implementation — if they do not already forbid extras, apply the same fix there too for
  consistency, as a one-line addition, not a new pattern.)
```
**8. Validation rules:** `source_type`: required, `max_length=50` (frontend: use the same fixed option list the onboarding wizard already offers — do not invent new categories here). `description`: optional, `max_length=255`. `annual_amount`: required, `gt=0` (strictly positive — zero is rejected, matching the existing `IncomeSourceCreate` bound exactly), `le=100_000_000`. `IncomeSourceUpdate` (new): all fields optional (partial update), same per-field bounds as Create, `source_type` excluded per §0.7.
**9. Database interactions:** `income_sources` table only; no joins, no FK writes beyond the existing `user_id`.
**10. Service interactions:** New `financials_service.py` function `update_income_source(db, current_user, income_id, patch) -> IncomeSource`, extracted alongside the rest of the router's logic per the roadmap's Engineering-Constitution-Rule-1 correction (§ preamble of `ImplementationRoadmap.md`).
**11. Calculation triggers:** **None.** `annual_amount` is not in the Monte Carlo Calculation Context. Do not add a trigger here — this is a load-bearing negative requirement, not an oversight to "fix."
**12. Recommendation triggers:** None verified — `family_recommendations_service.py` does not read `income_sources` per the audit's grep. No new trigger to build.
**13. Error handling:** Per §1.5.
**14. Loading states:** Per §1.6.
**15. Success states:** Per §1.7.
**16. Edge cases:** Per §1.8, plus: an `annual_amount` of exactly `100_000_000` is valid (inclusive bound `le`); `100_000_000.01` is rejected.
**17. Accessibility requirements:** Per §1.9.
**18. Test plan:** Per §1.10, plus a specific case: `PATCH` with `source_type` in the payload returns `422`, confirming §0.7/§2.A.7's immutability is enforced, not just UI-suggested.
**19. Acceptance criteria:** A user can add an income source, see it appear in the list without a page reload; edit its amount and see the new amount persist across a page refresh; delete it and confirm it no longer appears (and confirm via direct DB query in a test that the row still exists with `is_active=false`, not gone).
**20. Rollback strategy:** Per §1.11.

### 2.B EXPENSES

Identical to §2.A in every respect except the following deltas.
**1. Functional requirements:** Same shape, entity is Expense (`category` instead of `source_type`, `monthly_amount` instead of `annual_amount`).
**6. API contract:** `GET/POST/DELETE /api/v1/financials/expenses` already implemented; **new** `PATCH /api/v1/financials/expenses/{expense_id}`, identical shape to Income's new `PATCH`.
**7. Request/response example delta:** `{ "category": "housing", "description": "Rent", "monthly_amount": 2400 }`.
**8. Validation rules delta:** `category`: required, `max_length=50`, immutable on update per §0.7. `monthly_amount`: `ge=0` (zero is valid here — unlike income, a $0 expense category is a legitimate state, e.g. a paid-off subscription kept for record-keeping), `le=10_000_000`. New `ExpenseUpdate`: `description`/`monthly_amount` optional, `category` excluded, `extra="forbid"` per §2.A.7's reasoning.
**11. Calculation triggers:** None — same negative requirement as Income.
**Everything else (2-5, 9-10, 12-20):** identical to §2.A, substituting "expense"/"Expense"/`expenses` throughout.

### 2.C ASSETS

Backend CRUD (`GET/POST/PATCH/DELETE`) **already fully exists** — this entity's Milestone 1 work is **frontend-only**.
**1. Functional requirements:** View, add (`asset_type`, optional `institution`/`description`, `current_value`), edit (`current_value`/`institution`/`description`), delete.
**6. API contract:** No backend change. `GET/POST/PATCH/DELETE /api/v1/financials/assets[/{id}]` all already implemented exactly as needed.
**7. Request/response example:**
```
POST /api/v1/financials/assets
{ "asset_type": "checking", "institution": "Chase", "description": null, "current_value": 8500 }
→ 201 { "id": "…", "asset_type": "checking", "institution": "Chase", "description": null,
        "current_value": 8500.0, "is_active": true, "created_at": "…", "updated_at": "…" }

PATCH /api/v1/financials/assets/{id}
{ "current_value": 9200 }
→ 200 { ... "current_value": 9200.0, "updated_at": "…" }
```
**8. Validation rules:** `asset_type`: required, `max_length=50`, immutable on update (already enforced — `AssetUpdate` already excludes it). `institution`/`description`: optional, `max_length=255`. `current_value`: `ge=0` (an asset can legitimately be worth $0, e.g. a fully depreciated item still tracked), `le=1_000_000_000`.
**9. Database interactions:** `assets` table only. Note for the implementing engineer: `backend/app/models/estate.py` has a `ForeignKey("assets.id", ondelete="CASCADE")` from an estate-planning entity — this is dormant with respect to this milestone, since delete is soft (`is_active=False`), never a hard row delete, so that cascade path is never actually triggered by anything built in Milestone 1. Do not treat it as a blocker; it is noted here only so the implementing engineer doesn't have to re-discover it.
**10. Service interactions:** Extract into `financials_service.py` alongside Income/Expense/Liability — no new logic, pure relocation of the existing router body.
**11. Calculation triggers:** None (not in the Calculation Context).
**12. Recommendation triggers:** None verified in scope for this milestone; the classification into `_LIQUID_ASSET_TYPES`/`_INVESTED_ASSET_TYPES` sets used by `planning_service.get_dashboard` already exists and needs no change — it will simply start reflecting live data once this screen ships (that visible effect is PLA-003/Milestone 3's concern, not something to build here).
**13-20:** Per §1.5-§1.11 and §2.A's pattern, substituting "asset."
**19. Acceptance criteria delta:** Additionally confirm editing `current_value` on an asset does **not** trigger any Monte Carlo recomputation for any goal (regression test per §1.10), and does not itself change the asset's `asset_type`.

### 2.D LIABILITIES

Backend CRUD (`GET/POST/PATCH/DELETE`) **already fully exists** — frontend-only, mirroring §2.C.
**1. Functional requirements:** View, add (`liability_type`, optional `institution`/`description`, `balance`, optional `interest_rate`, `monthly_payment`), edit (`balance`/`interest_rate`/`monthly_payment`/`institution`/`description`), delete.
**6. API contract:** No backend change. `GET/POST/PATCH/DELETE /api/v1/financials/liabilities[/{id}]` already implemented.
**7. Request/response example:**
```
POST /api/v1/financials/liabilities
{ "liability_type": "mortgage", "institution": "Wells Fargo", "balance": 310000,
  "interest_rate": 0.0625, "monthly_payment": 1850 }
→ 201 { "id": "…", ... "balance": 310000.0, "interest_rate": 0.0625,
        "monthly_payment": 1850.0, "is_active": true, "created_at": "…", "updated_at": "…" }
```
**8. Validation rules:** `liability_type`: required, `max_length=50`, immutable on update (already enforced). `balance`: `ge=0`, `le=1_000_000_000`. `interest_rate`: optional, `ge=0, le=1` (a decimal fraction — the frontend must display this as a percentage input with the same ×100/÷100 convention as §0.9's assumptions fields, since `0.0625` stored means "6.25%" shown). `monthly_payment`: `ge=0, le=10_000_000`, defaults to `0.0` if omitted on create.
**9. Database interactions:** `liabilities` table only.
**10. Service interactions:** Same extraction as the other three.
**11. Calculation triggers:** None.
**12. Recommendation triggers:** None in scope for this milestone.
**13-20:** Per §1.5-§1.11 and §2.A's pattern, substituting "liability," plus: the `interest_rate` percentage-conversion requirement from §0.9 must be applied consistently — flag this explicitly in the frontend form's field label ("Interest rate (%)") to avoid the same class of silent-corruption risk called out for Assumptions.
**19. Acceptance criteria delta:** A liability created with no `interest_rate` shows as blank/"—" in the row, not `0%` (distinguish "unknown/not applicable" from "literally zero interest," since `interest_rate` is nullable and these are not the same fact).

---

## PART 3 — PLANNING ASSUMPTIONS (Settings)

**1. Functional requirements:** A user can view their current planning assumptions (auto-created with system defaults on first `GET` if none exist yet — already true server-side) and edit any subset of the seven fields, saved via a single "Save changes" action on one Settings card.
**2. Non-functional requirements:** Because `inflation_rate` has a verified real effect on Monte Carlo's real-return math (per Volume 2), a save here must be a synchronous, confirmed write before the user navigates away — no fire-and-forget (§0.13). No new SLA otherwise.
**3. UX flow:**
1. Settings page loads → `GET /api/v1/assumptions` fires once, on mount, alongside the page's other cards (Change Password, Delete Account already load independently — this follows the same pattern, not a new one).
2. Card renders pre-filled with current values (converted to whole-number percentages per §0.9 for the four percentage fields).
3. User edits one or more fields.
4. "Save changes" button is disabled until at least one field differs from the loaded values (`isDirty`, matching `app.profile.tsx`'s existing pattern exactly — reuse that pattern, do not invent a new dirty-tracking approach).
5. On submit: `PUT /api/v1/assumptions` with only the changed fields (partial update — the endpoint already supports `exclude_unset` semantics server-side); on success, values are re-synced from the response and a brief "Saved ✓" indicator shows (matching `app.profile.tsx`'s `Check` icon + "Saved" text convention, with a 3-second auto-clear via `setTimeout`, exactly as that file already does); on failure, an inline error shows and the form's edited values are preserved, not reverted (§0.13).
**4. Wireframe:**
```
┌───────────────────────────────────────────────────────────┐
│  Planning assumptions                            [Saved ✓]  │
│  These power every goal projection. Changes apply the next   │
│  time you edit or create a goal.                              │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ Inflation rate (%)   │  │ Tax rate (%)         │          │
│  └─────────────────────┘  └─────────────────────┘          │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ Target retirement age│  │ Social Security ($/mo)│         │
│  └─────────────────────┘  └─────────────────────┘          │
│  Expected annual returns                                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                  │
│  │Conservative│ │ Balanced  │ │Aggressive │                  │
│  │    (%)    │ │    (%)    │ │    (%)    │                  │
│  └───────────┘ └───────────┘ └───────────┘                  │
│                                        [Discard] [Save changes]│
└───────────────────────────────────────────────────────────┘
```
**5. Component hierarchy:**
```
app.settings.tsx
 ├── ChangePasswordSection   (existing, unchanged)
 ├── AssumptionsSection      (new, code/src/routes/app.settings.tsx or extracted to
 │                             code/src/components/settings/AssumptionsSection.tsx)
 │    └── InputField × 7     (reused from wizard-steps.tsx)
 ├── ComingSoonCard × 2      (existing, unchanged — Notifications, Linked accounts)
 └── DeleteAccountSection    (existing, unchanged)
```
**6. API contract:**
- `GET /api/v1/assumptions` → `200 OK`, `FinancialAssumptionsResponse` — **already implemented, no change**, including its get-or-create-with-defaults behavior.
- `PUT /api/v1/assumptions` → `200 OK`, `FinancialAssumptionsResponse` — **already implemented, no change.**
**7. Request/response examples:**
```
GET /api/v1/assumptions
→ 200 { "id": "…", "inflation_rate": 0.03, "expected_return_conservative": 0.05,
        "expected_return_balanced": 0.07, "expected_return_aggressive": 0.09,
        "tax_rate": 0.22, "retirement_age": 65, "social_security_monthly": 0.0 }
        (frontend displays inflation_rate as "3", tax_rate as "22", the three
        expected_return_* fields as "5"/"7"/"9" — whole-number percentages, per §0.9)

PUT /api/v1/assumptions
{ "inflation_rate": 0.035 }      ← user typed "3.5" in the Inflation rate field; the
                                    frontend divided by 100 before sending, per §0.9
→ 200 { ... "inflation_rate": 0.035, ...unchanged fields... }
```
**8. Validation rules:** `inflation_rate`, `expected_return_conservative`, `expected_return_balanced`, `expected_return_aggressive`: `ge=0, le=0.5` (i.e., the frontend field accepts 0-50 as a whole-number percentage). `tax_rate`: `ge=0, le=1` (0-100 as a whole-number percentage). `retirement_age`: `ge=40, le=80`, integer. `social_security_monthly`: `ge=0, le=10_000_000` (currency, no conversion). All fields optional on `PUT` (partial update already supported).
**9. Database interactions:** `financial_assumptions` table, single row per `user_id`, already unique-constrained by the existing get-or-create logic (verify the uniqueness constraint exists at the DB level during implementation — if it does not, that is a pre-existing gap outside Milestone 1's scope to fix, but flag it if found).
**10. Service interactions:** No new service — the existing router-level `upsert_assumptions` logic in `backend/app/routers/assumptions.py` is already complete and correctly scoped; no change needed here (this router is small enough that the thin-router rule is not in tension with leaving the logic where it is — re-evaluate only if this file grows past its current size).
**11. Calculation triggers:** Saving new assumptions does **not** retroactively recompute any existing goal's stored `probability` — per ADR-001, probability is computed only on goal create/update, never triggered by an unrelated write. **This is correct, expected behavior, not a bug to fix in this milestone**: a user's next goal edit will pick up the new inflation rate on that goal's next Monte Carlo run. State this explicitly in the card's UI copy ("Changes apply the next time you edit or create a goal" — already reflected in §3.4's wireframe) so it is not mistaken for a bug.
**12. Recommendation triggers:** `tax_rate` is a plausible input to insurance/scheme recommendation math — **verify this against `family_insurance_service.py` during implementation** (not re-derived in this document; flagged in the roadmap as an open spot-check, not resolved by the roadmap or this spec, because it requires reading that service's current logic, which was out of scope for this pass). If `tax_rate` does feed a live-computed recommendation, no code change is needed (recommendations are already always live-recomputed) — this note exists only so the implementing engineer confirms the assumption rather than assuming it.
**13. Error handling:** Inline error on the card (not a toast, matching `app.profile.tsx`'s existing `status === "error"` branch exactly) on `PUT` failure; per §0.13, do not silently discard the failure the way onboarding does.
**14. Loading states:** Card shows a centered spinner (matching `app.profile.tsx`'s existing `Loader2` full-card loading state) until the initial `GET` resolves; "Save changes" button shows `Loader2` + "Saving…" during the `PUT`, matching every other submit button in this codebase.
**15. Success states:** "Saved ✓" with `Check` icon, auto-clearing after 3 seconds — copy `app.profile.tsx`'s existing implementation exactly, do not design a new success-indicator pattern.
**16. Edge cases:** First-ever `GET` for a brand-new user with no assumptions row yet still returns `200` with system defaults (already true, get-or-create) — the form must not show a loading error or an empty state in this case, since a valid, fully-populated record is always returned. A user who clears a field entirely (empty string) and submits: the frontend must not send an empty string for a numeric field (would fail Pydantic's `float`/`int` coercion with a 422) — either block submission client-side until the field is refilled, or omit the field from the `PUT` payload entirely if left blank, falling back to its last-saved value (recommended: treat blank as "no change," matching the partial-update semantics already used everywhere else in this spec).
**17. Accessibility requirements:** Same baseline as §1.9 — labeled inputs (guaranteed via reused `InputField`), keyboard-operable Save/Discard, `prefers-reduced-motion`-respecting success indicator animation (`app.profile.tsx`'s existing `Check` fade-in, confirm it already respects this during implementation).
**18. Test plan:** Backend: new `backend/tests/test_assumptions.py` if one does not already exist (confirmed absent from the current test directory listing) — cover get-or-create-on-first-access, partial update, and boundary values at each field's `ge`/`le` limits. Frontend: component test for the ×100/÷100 conversion specifically (submit "3.5" in the Inflation rate field, assert the network payload contains `0.035`, not `3.5` or `35`) — this is the single highest-value test in this entire milestone given §0.9's flagged risk.
**19. Acceptance criteria:** A user can change their inflation rate from Settings, see "Saved ✓," refresh the page, and see the new value still shown (not reverted to the default); the onboarding copy's two claims ("refine them any time in Settings" and "these can be adjusted in Settings after onboarding" for expected returns) are both now literally true.
**20. Rollback strategy:** Purely additive frontend card on top of an already-complete, unchanged backend — revert by removing the card from `app.settings.tsx`; zero effect on any other Settings section or any other screen.

---

## PART 4 — MILESTONE 1 DEFINITION OF DONE

- [ ] `PATCH /api/v1/financials/income/{id}` and `PATCH /api/v1/financials/expenses/{id}` exist, tested, with `extra="forbid"` on both new `Update` schemas (and confirmed/aligned on `AssetUpdate`/`LiabilityUpdate` per §2.A.7).
- [ ] `backend/app/services/financials_service.py` exists; `backend/app/routers/financials.py` contains only request validation and calls into it — Engineering Constitution Rule 1 restored for this router.
- [ ] `code/src/routes/app.financials.tsx` exists, reachable from a new "Financials" nav item positioned after "Goals."
- [ ] All four sections (Income, Expenses, Assets, Liabilities) support add/edit/delete end-to-end against the real backend, with mock-mode parity in `api.ts` for every function touched.
- [ ] `code/src/routes/app.settings.tsx` has a new Assumptions card exposing all seven fields with correct percentage conversion, verified by the specific test in §3.18.
- [ ] The onboarding copy's two claims about Settings are both true.
- [ ] Regression test confirms zero change to any existing goal's `probability` from any action in this milestone.
- [ ] `ruff check app/` and `mypy --strict app/` both clean (Engineering Constitution Rule 5).
- [ ] `docs/backend.md`, `docs/architecture.md`, and `CHANGELOG.md`'s `[Unreleased]` section updated per `CLAUDE.md`'s own "Adding an Endpoint" checklist.

Nothing in this document requires a decision the implementing engineer has to make alone. Every open question the roadmap surfaced is closed in Part 0, with the source evidence that closed it.
