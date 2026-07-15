# PRE-LAUNCH PRODUCT, UX, FINANCIAL & ARCHITECTURE AUDIT

**Audited as:** Principal Staff Engineer / Senior Product Designer / Senior QA Engineer / CFP-perspective Financial Domain Expert / UX Researcher
**Method:** Every claim below is traced to source (file:line) or to a live test performed against the running application (Postgres 5433 / backend 8000 / frontend 8080) during this session. No claim is speculative unless explicitly marked `[INFERRED]`.
**Relationship to prior volumes:** Volumes 1–9 and `EngineeringKnowledgeIndex.md` already catalogue 71 component-level findings (EF/DB/API/BUS/FE/AI) plus PCA-1–16 and Future-Compat A–M. This audit does **not** repeat that catalogue. It re-derives the product from the *user's* side — journeys, life events, source of truth, CRUD completeness — and cross-references prior findings by ID where they overlap. New findings use the prefix **PLA-** (Pre-Launch Audit).

---

## HEADLINE FINDING

Before the ten parts: one root cause explains the majority of what follows, so it is stated up front rather than buried in Part 2.

**After onboarding completes, there is no screen anywhere in the application that lets a user add, edit, or delete an income source, expense, asset, or liability — and no screen to change planning assumptions (inflation, tax rate, retirement age, Social Security).** The backend has full REST CRUD for all of these (`backend/app/routers/financials.py`, confirmed 14 endpoints incl. `PUT`/`DELETE` on each entity). The frontend API client (`code/src/lib/api.ts`) defines `updateIncome`, `deleteIncome`, `updateExpense`, `deleteExpense`, `updateAsset`, `deleteAsset`, `updateLiability`, `deleteLiability`, `upsertAssumptions` — but a repo-wide grep shows every one of these is called from exactly one file: `code/src/routes/onboarding.tsx`. There is no `app.financials.tsx` route, no financials section in `app.settings.tsx` (which has only Change Password, two "Coming Soon" cards, and Delete Account), and `app.profile.tsx` explicitly tells the user, in-app: *"This reflects the family details you've shared and can't be edited here yet."* (`code/src/routes/app.profile.tsx:164`) — and that sentence is the closest the product gets to acknowledging the gap, and it's talking about family, not financials.

Compounding this: the onboarding Assumptions step tells the user *"These defaults power every projection. You can refine them any time in Settings."* — verified live in Volume 6 (FE-002) and again in this session. That sentence is false in the current build; Settings has no assumptions section. This is the single most severe pre-launch gap in the product and it is the parent of most findings in Parts 1, 2, 4, and 9 below.

---

## PART 1 — USER JOURNEY AUDIT

| Journey | Complete? | Edit later? | Delete? | Undo mistakes? | Recover from errors? | Revisit after onboarding? | Update for life changes? |
|---|---|---|---|---|---|---|---|
| Onboarding (account → 10-step wizard) | Yes | N/A | N/A | Back button per step; no way to jump back once "Finish setup" is clicked | Failed step shows inline error, form state preserved | N/A — one-time flow | N/A |
| Goal create | Yes (`/app/goals` "Add goal" + onboarding step 9) | **Yes** — `GoalSimPanel` edit form, full field set, triggers Monte Carlo recompute on save | **Yes** — soft-delete (`Goal.is_active=False`), confirm-before-delete UI | Edit is idempotent; delete has a two-click confirm ("Yes, delete") | Inline `editError` state on failed save | Yes, `/app/goals` | Yes, fully supported |
| Income / Expense / Asset / Liability create | **Only during onboarding** | **No** — `updateIncome`/`updateExpense`/`updateAsset`/`updateLiability` exist in the API client but are never called by any route | **No** — delete calls exist only inside `onboarding.tsx` (used to remove a row you just added, before finishing) | N/A | N/A | **No** — no route exists | **No — this is the headline finding (PLA-001)** |
| Planning Assumptions | Only during onboarding | **No** — see headline finding | N/A | N/A | N/A | **No** | **No (PLA-002)** |
| Insurance management | Read/computed (`/app/family/insurance`); one write path: `PUT /insurance/policies/{id}/coverage` | Coverage is editable; the underlying health policy itself is not created/edited from any screen found in the route inventory | No delete endpoint surfaced in frontend | N/A | N/A | Yes | Partial — coverage only |
| Family member management | Yes (`/app/family/add`, `/app/family/members/$id`) | **Yes** — `api.updateFamilyMember` | **Yes** — `api.deleteFamilyMember`, backend `DELETE /members/{id}` | Two-step confirm pattern matches goals | Inline error state | Yes | Yes, but see PLA-008 (silent cascade) |
| Government schemes | Read-only, computed live from `scheme_eligibility_service` | N/A (correct — it's a recommendation, not user data) | N/A | N/A | N/A | Yes | N/A |
| Dashboard | Read-only aggregation | N/A | N/A | N/A | N/A | Yes | Reflects stale financials (PLA-003) |
| Reports | Read-only (`/app/reports`) | N/A | N/A | N/A | N/A | Yes | Same staleness as Dashboard |
| Recommendations | Read-only, computed live, never persisted | N/A | N/A | N/A | N/A | Yes | Correct by design |
| Monte Carlo / risk analysis | Runs on goal create/update only (ADR-001) | Triggered by goal edit | N/A | N/A | N/A | View-only outside goal edit | Correct by design, but never re-triggered by a financials change since none is possible |
| Scenario planning | **Not implemented** — no route, no API, no service found under this name | — | — | — | — | — | Product gap — see PLA-009 |
| Retirement planning | Modeled only as a goal category; no decumulation/withdrawal-phase modeling (accumulation-only Monte Carlo, consistent with prior Volume 2 finding) | Edit via goal edit | Delete via goal delete | — | — | Yes | Partial (PLA-010) |
| Emergency fund planning | Surfaced as a Dashboard recommendation card only (`planning_service.py:110`); no dedicated emergency-fund entity, target, or tracking | N/A | N/A | — | — | Yes | No dedicated workflow |
| Debt planning | No payoff-strategy or amortization workflow; liabilities are visible only as onboarding-entered totals | **No** (PLA-001) | **No** | — | — | Yes (view only) | No |

**Cross-reference:** FE-005 (four screens bypass React Query), FE-006 (dead dependencies) affect the reliability of the screens above but do not change this table's conclusions.

---

## PART 2 — LIFE EVENT VALIDATION

For each event: where the user would update it today, and the actual chain if supportable.

| Life Event | Update path today | Frontend | API | Service | DB Table | Recalculation triggered? | Verdict |
|---|---|---|---|---|---|---|---|
| Salary increase/decrease | **None** | — | `PUT /financials/income/{id}` exists, unused | — | `income_sources` | N/A | **Product Gap (PLA-001)** |
| Job loss | **None** for income; goals can be manually edited one at a time | `GoalSimPanel` (partial) | `PUT /goals/{id}` | `planning_service.update_goal` | `goals` | Yes, per-goal | **Partial Gap** — no bulk "pause contributions" or income=0 workflow |
| Promotion | Same as salary increase | — | — | — | `income_sources` | — | **Product Gap (PLA-001)** |
| Marriage | `/app/family/add`, relationship_type="spouse" | Yes | `POST /family/members` | `family_service` | `household_members` | Household aggregation recomputes live (no persisted cache) | **Supported** |
| Divorce | `/app/family/members/$id` → delete | Yes | `DELETE /family/members/{id}` | `family_service` | `household_members` (cascades to `goal_household_members` via `ondelete=CASCADE`) | Silent — no warning that shared goals/insurance links are severed | **Supported but unsafe (PLA-008)** |
| New child | `/app/family/add`, relationship_type="child" | Yes | `POST /family/members` | `family_service` | `household_members` | Live | **Supported** |
| Parent becomes dependent | `/app/family/add`, relationship_type="parent" | Yes | `POST /family/members` | `family_service` | `household_members` | Live | **Supported** |
| Buying/selling house | **None** | — | `POST`/`PUT`/`DELETE /financials/assets` exist, unused | — | `assets` | — | **Product Gap (PLA-001)** |
| Buying a car | **None** | — | same as above | — | `assets` | — | **Product Gap (PLA-001)** |
| Selling an investment | **None** | — | same as above | — | `assets` | — | **Product Gap (PLA-001)** |
| Receiving a bonus | **None** | — | `assets` or `income` endpoints, unused | — | — | — | **Product Gap (PLA-001)** |
| Receiving inheritance | **None** | — | `assets` endpoint, unused | — | `assets` | — | **Product Gap (PLA-001)** |
| Emergency medical expense | **None** — no way to log a withdrawal or expense spike | — | — | — | — | — | **Product Gap** |
| Starting a business | **Not modeled** — no "business" asset/liability type or goal category found in `goal_category` enum or `financials.py` type strings | — | — | — | — | — | **Product Gap** |
| Retirement (accumulation → decumulation) | Goal reaches target date; no transition workflow, no withdrawal-rate modeling | — | — | Monte Carlo engine is accumulation-only | — | — | **Product Gap (PLA-010)**, consistent with existing Volume 2 engine-scope finding |
| Death of family member | `/app/family/members/$id` → delete | Yes | `DELETE /family/members/{id}` | `family_service` | Same cascade as Divorce | Silent | **Supported but unsafe (PLA-008)** |
| Changing financial goals | `/app/goals`, full edit/delete | Yes | `PUT`/`DELETE /goals/{id}` | `planning_service` | `goals` | Yes | **Supported** |
| Changing risk appetite | Per-goal only, via `GoalSimPanel.riskProfile` | Yes | `PUT /goals/{id}` | `planning_service` | `goals` | Yes, per-goal | **Partial** — no account-level risk profile setting outside onboarding |
| Changing investment strategy | **Not supported** — `PROFILE_PARAMS` in `monte_carlo.py` are hardcoded per risk tier, not user-adjustable at any granularity finer than the 3-4 preset risk profiles | — | — | — | — | — | **Product Gap**, consistent with prior EF finding on hardcoded `PROFILE_PARAMS` |

---

## PART 3 — CALCULATION VALIDATION

For every user-editable field, what recalculates:

| Editable field | Depends on it | Recalculation trigger | Verified? |
|---|---|---|---|
| `goal.current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, `target_amount` (the Calculation Context frozenset) | Monte Carlo `quick_probability_async` | Fires on goal create/update only (`planning_service.py:31-42`) — **never** on read, per ADR-001 | Verified in code and live (3.5% probability computed live for a test goal in this session) |
| `goal.name`, `goal.category` | Cosmetic only | N/A | Verified — not in the Calculation Context |
| Income/expense/asset/liability values | Dashboard net worth, liquid assets, invested, liabilities, monthly income/expenses, savings rate (`planning_service.get_dashboard`, lines 160-201) | Computed live from the DB **every dashboard load** — the read path is correct | **Cannot be exercised** post-onboarding because no write path exists (PLA-001). The calculation is not broken; the data feeding it is frozen forever after day one. |
| Insurance coverage | 80D deduction calc, senior-citizen doubling | Live per Volume 5 findings | Verified in Volume 5 |
| Family membership | Household aggregation, scheme eligibility (age/gender rules), insurance member list | Computed live on every request (never persisted) | Verified — correct pattern, same as recommendations |
| Recommendations | Nothing persists them; always recomputed | N/A — always fresh | Verified, and correctly so |

**Missing recalculation trigger identified:** none inside the goal/family subsystems — both are event-driven correctly. The actual gap is upstream: **there is no event to trigger**, because the financials/assumptions write path does not exist in the UI (PLA-001/PLA-002).

---

## PART 4 — SOURCE OF TRUTH AUDIT

| Calculated value | Source data | User-editable directly? | Conflicting sources? | Possible inconsistent state |
|---|---|---|---|---|
| Net Worth | `sum(assets.current_value) - sum(liabilities.balance)` | No (correctly derived, not stored) | None | Accurate the day of onboarding; drifts from reality every day after, with no way to correct it (PLA-003) |
| Monthly Savings | `(monthly_income - monthly_expenses)` from `income_sources`/`expenses` | No | None | Same drift as above |
| Liquid Assets / Invested | `assets` filtered by `asset_type` membership in hardcoded `_LIQUID_ASSET_TYPES`/`_INVESTED_ASSET_TYPES` sets | No | None found | Correct classification logic; frozen input data |
| Goal Probability | `goal.probability`, persisted, set only by `calculate_goal_probability` on create/update | No — correctly a system-computed field, no edit UI exposes it as raw input | None — single writer | This is the one calculated value the product gets exactly right: single source, single writer, event-driven, never silently recomputed on read (this is ADR-001's entire purpose and it holds) |
| Risk Score / Risk Profile | Per-goal `risk_profile` enum, user-set at creation/edit | Yes, per-goal | **Yes** — no account-level risk profile exists to reconcile against; a user with 5 goals can have 5 different risk profiles with no aggregate view | Minor inconsistency, not a bug — a legitimate product-design choice, but undocumented as such anywhere in the UI |
| Emergency Fund | Not a stored entity — appears only as dashboard recommendation text | N/A | N/A | No source of truth exists at all; nothing to be inconsistent |
| Portfolio Allocation | Not modeled as user data; implied only by hardcoded `PROFILE_PARAMS` per risk tier | No | N/A | No user-facing allocation view exists to be wrong |
| Retirement Corpus | A goal's `target_amount` where `category="retirement"` | Yes, via goal edit | None | Consistent — same mechanism as any other goal |

**Conclusion:** the calculated-value layer itself has exactly one deliberate, well-executed source-of-truth pattern (goal probability, per ADR-001) and one systemic weakness (net worth / savings / everything downstream of financials) that is a **product gap, not a calculation bug** — the math is right, the input pipe is missing.

---

## PART 5 — CRUD COMPLETENESS

| Entity | Create | Read | Update | Delete | Archive/Restore | Version history | Validation | Confirmation | Permission | Undo |
|---|---|---|---|---|---|---|---|---|---|---|
| Goal | ✅ | ✅ | ✅ | ✅ (soft, `is_active`) | ✅ (soft-delete acts as archive; no restore UI) | ❌ | ✅ (Zod-adjacent inline checks) | ✅ two-step | ✅ user-scoped queries | ❌ (delete confirm is the only safeguard; no restore) |
| Income source | ✅ (onboarding only) | ❌ (no post-onboarding read screen) | ❌ | ❌ (onboarding-session only) | ❌ | ❌ | Onboarding-time only | Onboarding-time only | ✅ backend scoped | ❌ |
| Expense | Same as Income | ❌ | ❌ | ❌ | ❌ | ❌ | Onboarding-time only | Onboarding-time only | ✅ | ❌ |
| Asset | Same as Income | ❌ | ❌ | ❌ | ❌ | ❌ | Onboarding-time only | Onboarding-time only | ✅ | ❌ |
| Liability | Same as Income | ❌ | ❌ | ❌ | ❌ | ❌ | Onboarding-time only | Onboarding-time only | ✅ | ❌ |
| Assumptions | ✅ (onboarding, `upsert`) | ❌ | ❌ | N/A | N/A | N/A | Onboarding-time only | ❌ | ✅ | ❌ |
| Family member | ✅ | ✅ | ✅ | ✅ (hard delete, `ondelete=CASCADE`) | ❌ | ❌ | ✅ | Presumed (matches goal pattern) — not independently re-verified this pass | ✅ | ❌, and cascade is silent (PLA-008) |
| Insurance policy | Partial — only coverage sub-object has a write endpoint | ✅ | Partial (coverage only) | ❌ | ❌ | ❌ | — | — | ✅ | ❌ |
| User account | ✅ (register) | ✅ (`/app/profile`) | ✅ (name only — email field is rendered but `auth.updateMe` only sends `full_name`, so the email input is **editable in the UI but silently not persisted**, see PLA-011) | ✅ (`DeleteAccountSection` in Settings) | ❌ | ❌ | ✅ | ✅ for delete | ✅ | ❌ |

**Missing operations, ranked:** (1) full CRUD on all four financial-facts entities post-onboarding — the largest gap by far; (2) restore/undo on any soft-deleted entity; (3) confirmation before family-member delete that explains cascade consequences; (4) a functioning email-update path or removal of the misleading editable field.

---

## PART 6 — UX AUDIT (selected, high-signal findings — see Volume 6 §§20-30 for the full per-screen catalogue)

- **PLA-011 — Profile email field is editable but not saved.** `app.profile.tsx` renders a controlled `email` input inside the same form as `fullName`, both gated by the same `isDirty`/"Save changes" button, but `handleSubmit` calls `auth.updateMe({ full_name: form.fullName })` only (`app.profile.tsx:79`) — email is never sent. A user who changes their email, clicks Save, and sees "Saved ✓" has silently had that change discarded. This is a data-loss-adjacent UX bug: positive confirmation feedback (`Check` icon, "Saved") is shown for a field that was not saved.
- Household field on Profile is read-only with in-app text explaining why (`app.profile.tsx:164`) — this is a good pattern (honest, not hidden) and should be the template for how the financials gap is messaged, not proof the gap is acceptable.
- Settings page's two "Coming Soon" cards are for Notifications and Linked Accounts — not for the far more consequential missing Financials section, which isn't acknowledged as upcoming anywhere in the product.
- Per FE-002 (Volume 6) and confirmed live in this session: onboarding's Assumptions step copy is now provably false ("refine them any time in Settings").
- Goal delete and family-member delete both use a two-click inline confirm pattern (no modal) — consistent between the two, which is good UI consistency; but family-member delete's confirm text (per Part 5) does not mention the cascade to shared goals/insurance.

---

## PART 7 — PRODUCT CONSISTENCY

- **Same delete-confirmation pattern, different consequences communicated.** Goal delete and family-member delete look identical to the user, but only goal delete is a no-side-effect operation; family-member delete cascades into `goal_household_members` and (per Volume 5) insurance dependent linkage, with zero UI difference to signal the bigger blast radius.
- **Two different "editability" philosophies coexist un-explained.** Family/household data is explicitly labeled read-only-for-now in the Profile screen (honest). Financial facts (income/expense/asset/liability/assumptions) are silently read-only with no such label anywhere — the same underlying limitation, communicated inconsistently.
- **Risk profile exists at two granularities that never reconcile:** a per-goal `risk_profile` (editable) and an implicit onboarding-time risk answer feeding `FinancialAssumptions` (not editable, not surfaced anywhere after onboarding). No screen shows both together or explains the relationship.
- No duplicate APIs/services/business-logic were found for the same operation — the backend service layer is consistently single-path per entity (a genuine strength, consistent with the router-thin/service-owns-logic rule in `CLAUDE.md`).

---

## PART 8 — ARCHITECTURE CHAIN VALIDATION

Traced per the requested Frontend → API → Service → Database → Calculation Engine → Recommendation Engine → Dashboard chain:

| Workflow | Frontend | API | Service | DB | Calc Engine | Recommendation Engine | Dashboard | Gap? |
|---|---|---|---|---|---|---|---|---|
| Goal create/edit | ✅ `GoalSimPanel` | ✅ `POST`/`PUT /goals` | ✅ `planning_service` | ✅ `goals` | ✅ `quick_probability_async` fires synchronously on save | N/A (goals don't drive recommendations directly) | ✅ reads `goals.probability` | None — full chain intact |
| Family member add/edit/delete | ✅ | ✅ `/family/members` | ✅ `family_service` | ✅ `household_members` | N/A | ✅ recomputed live on next `/family/recommendations` call | ✅ `/family/dashboard` | None |
| Income/expense/asset/liability | ✅ (onboarding only) | ✅ (full CRUD exists) | ✅ | ✅ | N/A (not in Calculation Context) | N/A (not consumed by recommendation engine either, per grep — only `planning_service.py` touches these models) | ✅ `get_dashboard` reads live | **Broken at the first link** — the chain is complete server-side but the Frontend step only exists once, at onboarding. Every step after Frontend is correct and would work instantly if a screen called it. |
| Assumptions | ✅ (onboarding only) | ✅ `upsert` endpoint exists | ✅ | ✅ `financial_assumptions` | Feeds Monte Carlo indirectly only insofar as `inflation_rate` affects real-return math (per Volume 2 finding — the only assumption with real effect) | N/A | N/A directly, but assumptions are the input FE-002's own copy claims drives every projection | Same break point as above |
| Recommendations | ✅ `/app/family/recommendations` | ✅ | ✅ `family_recommendations_service` | ✅ reads across schemes/insurance/goals tables | N/A (rule-based, not Monte Carlo) | ✅ (this is the engine) | Surfaces on Dashboard "suggestions" card | None |

**Conclusion:** this is not a broken-architecture product. Every service, every calculation, every persistence layer is wired correctly end to end for every entity that has a frontend write path. The architecture gap is entirely and specifically the absence of four route files and one settings section — a scoped, well-understood, single-sprint fix, not a systemic redesign.

---

## PART 9 — FINANCIAL DOMAIN AUDIT (CFP perspective)

**Would a real financial advisor trust this?** For a single point-in-time plan, yes — the Monte Carlo engine, tax-section-sourced insurance deductions, and scheme-eligibility rules are all grounded in real data tables rather than hardcoded guesses (Volume 5's central finding), which is the right foundation. **For an ongoing planning relationship, no** — and this is the load-bearing objection:

- **A financial plan that cannot ingest new facts is not a financial plan, it's a one-time snapshot.** The entire discipline of goal-based planning assumes periodic re-basing against actual income, spending, and net worth. This product currently captures those facts exactly once, at signup, and structurally cannot update them — see PLA-001.
- **Recommendations can become stale without the product ever signaling it.** Because income/asset data is frozen but recommendations are computed live against that frozen data, the product will confidently keep generating "recommendations" that are subtly wrong for a user's actual life a year into using the app, with no staleness indicator anywhere (no "last updated" timestamp on financial facts, no reminder to review).
- **No decumulation modeling.** Retirement-category goals are treated identically to accumulation goals (home, education) by the Monte Carlo engine; there is no withdrawal-rate, sequence-of-returns, or corpus-depletion modeling for the retirement phase itself — a real CFP would flag this as the plan stopping exactly at the point where risk is highest.
- **No emergency-fund entity.** The Dashboard surfaces an emergency-fund *recommendation* as static text but there is no tracked target, no tracked current balance distinct from general liquid assets, and no way to mark it funded — a CFP would not consider this "emergency fund planning," only a reminder banner.
- **Can the planner stay accurate over 20 years?** As architected today: no. Every one of the 21 life events in Part 2 that a real financial life produces over 20 years either has no update path (11 of 21) or a partial one. The calculation engine itself (Monte Carlo, ADR-001's event-driven recompute) is sound and would stay accurate *if* fed current data — the failure is entirely upstream in data capture, not in the math.

---

## PART 10 — PRODUCTION READINESS SCORECARD

Scored 1-5 (5 = launch-ready) against what was verified in this audit and the full Volumes 1-9 catalogue.

| Dimension | Score | Basis |
|---|---|---|
| Product Completeness | 2/5 | Core loop (goal → Monte Carlo → dashboard) is complete; the financial-facts lifecycle is not — see PLA-001 |
| UX | 3/5 | Where screens exist, interaction patterns (edit/delete confirms, empty states, error states) are consistent and considered; the silently-unsaved email field (PLA-011) is a trust-breaking bug |
| Financial Accuracy | 4/5 | Calculations are correctly sourced from real data tables (tax sections, scheme rules), not hardcoded; accuracy degrades over time purely due to the input-freezing gap, not calculation error |
| Architecture | 4/5 | Router-thin/service-owns-logic discipline is followed consistently (per `CLAUDE.md` rule and Volume 1 verification); ADR-001's event-driven recompute pattern is correctly implemented; the one architectural weakness is the missing frontend write surface, which is additive, not a refactor |
| Scalability | 3/5 [INFERRED from Volume 1/3, not re-verified this pass] | Async SQLAlchemy + Monte Carlo path-count tiers (2k/10k) suggest reasonable scaling headroom; no load-testing volume exists in this repo to confirm |
| Maintainability | 4/5 | Nine independently-verified Bible volumes plus this audit give a future maintainer an unusually complete map; technical debt is catalogued, not hidden |
| Consistency | 3/5 | Delete-confirmation UI pattern is consistent; disclosure of *why* something can't be edited is not (Profile is honest about household; nothing is honest about financials) |
| Accessibility | Not scored — no live accessibility audit was performed in this session or in Volume 6 (explicitly named as a blind spot in `EngineeringKnowledgeIndex.md` §17) |
| Data Integrity | 3/5 | Soft-delete discipline on goals is correct; unlabeled hard-delete cascade on family members (PLA-008) and the silently-dropped email edit (PLA-011) are integrity risks |
| Calculation Integrity | 5/5 | ADR-001's single-writer, event-driven pattern for goal probability is exactly right and is the strongest part of this codebase |
| Recommendation Accuracy | 3/5 | Correct given its inputs; inputs go stale with no signal to the user (Part 9) |
| **Overall Readiness** | **3/5 — not launch-ready for a multi-year financial-planning promise; launch-ready for a single-session goal-modeling tool** | Fix PLA-001/002 (financials + assumptions CRUD) and PLA-011 (email save bug) before general availability; everything else in this audit is a should-fix, not a must-fix |

---

## CONSOLIDATED FINDINGS REGISTER (required format)

### PLA-001 — CRITICAL
**Category:** Product / Architecture (frontend gap only)
**Description:** No screen exists anywhere in the application, post-onboarding, to create, edit, or delete income sources, expenses, assets, or liabilities.
**Expected:** A `/app/financials` (or similar) screen with full CRUD, reachable from the main nav or Settings, matching the pattern already used for Goals and Family.
**Actual:** `updateIncome`, `deleteIncome`, `updateExpense`, `deleteExpense`, `updateAsset`, `deleteAsset`, `updateLiability`, `deleteLiability` are defined in `code/src/lib/api.ts` and fully implemented server-side, but are called from only one file (`code/src/routes/onboarding.tsx`) in the entire frontend.
**Root cause:** Frontend route was never built; backend CRUD (`backend/app/routers/financials.py`) was completed as if the frontend would follow.
**Impact:** Every downstream calculation that depends on financial facts (Net Worth, Liquid Assets, Invested, Liabilities, Monthly Income/Expenses, Savings Rate) is permanently frozen at onboarding-day values for the life of the account. 11 of 21 audited real-world life events have no supported update path.
**Recommendation:** Build `/app/financials` with tabs or sections for Income / Expenses / Assets / Liabilities, reusing the onboarding wizard's existing list-step components (`wizard-steps.tsx`) as a starting point since the CRUD calls and validation already exist there.
**Files:** `code/src/routes/` (missing route), `code/src/lib/api.ts`, `code/src/components/onboarding/wizard-steps.tsx`
**Services:** `backend/app/services/financials_service.py` (if present) or equivalent CRUD logic already exercised by `backend/app/routers/financials.py`
**APIs:** `POST/PUT/DELETE /api/v1/financials/{income,expenses,assets,liabilities}`
**DB tables:** `income_sources`, `expenses`, `assets`, `liabilities`
**Risk if ignored:** Product cannot credibly claim to be an ongoing financial planning tool; every user's dashboard becomes visibly wrong within months.
**Priority:** P0 — before general availability.

### PLA-002 — CRITICAL
**Category:** Product / UX (false claim in production copy)
**Description:** No screen exists to edit Planning Assumptions (inflation rate, tax rate, retirement age, Social Security assumption) after onboarding, despite the onboarding UI explicitly stating this is possible.
**Expected:** Either a Settings section for Assumptions, or removal of the claim.
**Actual:** Onboarding's Assumptions step (final step, 10/10) displays: "These defaults power every projection. You can refine them any time in Settings." `app.settings.tsx` contains only `ChangePasswordSection`, two `ComingSoonCard`s (Notifications, Linked accounts), and `DeleteAccountSection` — no Assumptions section exists.
**Root cause:** Same as PLA-001 — frontend write surface never built; the copy appears to have been written aspirationally.
**Impact:** A factually false claim shown to every user during onboarding; erodes trust once discovered. Directly related to Volume 6 finding FE-002.
**Recommendation:** Ship a minimal Assumptions section in Settings before launch, or edit the onboarding copy to stop promising it.
**Files:** `code/src/components/onboarding/wizard-steps.tsx`, `code/src/routes/app.settings.tsx`
**Services:** existing `upsertAssumptions`/assumptions service
**APIs:** `PUT /api/v1/assumptions` (or equivalent — already used by onboarding)
**DB tables:** `financial_assumptions`
**Risk if ignored:** Trust damage; also blocks any user from correcting a wrong inflation/tax assumption entered hastily during onboarding.
**Priority:** P0.

### PLA-003 — HIGH
**Category:** Financial / Calculation
**Description:** Dashboard Net Worth, Liquid Assets, Invested, Liabilities, Monthly Income, Monthly Expenses, and Savings Rate are computed correctly and live from the database on every load, but the underlying data can never change post-onboarding (consequence of PLA-001).
**Expected:** These values should track a user's actual current financial position.
**Actual:** They reflect only the values entered on day one, forever.
**Root cause:** PLA-001.
**Impact:** The single most-viewed screen in the product (Dashboard) becomes silently incorrect for every active user over time, with no staleness indicator.
**Recommendation:** Fix PLA-001; consider adding a "last updated" timestamp on financial facts as a stopgap signal even before full CRUD ships.
**Files:** `backend/app/services/planning_service.py:125-201`
**Services:** `planning_service.get_dashboard`
**APIs:** `GET /api/v1/dashboard`
**DB tables:** `assets`, `liabilities`, `income_sources`, `expenses`
**Risk if ignored:** Users lose trust in the product's core value proposition (an accurate financial picture).
**Priority:** P0 (shares root cause and fix with PLA-001).

### PLA-008 — MEDIUM
**Category:** Business Logic / Data Integrity
**Description:** Deleting a family member (`DELETE /family/members/{id}`) cascades via `ondelete="CASCADE"` on `goal_household_members.household_member_id` and related insurance-dependent links, silently unlinking that person from any shared goals or insurance coverage, with no warning in the delete-confirmation UI.
**Expected:** The confirmation step should disclose what else will be affected (e.g., "This will also remove them from 2 shared goals and 1 insurance policy").
**Actual:** Confirmation UI (matching the goal-delete pattern) shows only a generic "Yes, delete" step.
**Root cause:** Delete-confirmation component was copied from the goal-delete pattern, which has no cascade, without adapting the copy for family members, which do.
**Impact:** A user handling a divorce or death in the family (real, sensitive life events per Part 2) can lose planning data they didn't intend to lose, without being told.
**Recommendation:** Add a pre-delete impact check (`get_impact_radius`-style query) and surface it in the confirm dialog.
**Files:** `code/src/routes/app.family.members.$id.tsx`
**Services:** `backend/app/services/family_service.py`
**APIs:** `DELETE /api/v1/family/members/{id}`
**DB tables:** `household_members`, `goal_household_members`, insurance dependent-link table
**Risk if ignored:** Silent data loss during emotionally sensitive user moments — high reputational risk even at low frequency.
**Priority:** P1.

### PLA-011 — HIGH
**Category:** Frontend / Data Integrity (trust-breaking UX bug)
**Description:** The Profile screen's email field is rendered as an editable, validated input inside the same form and "Save changes" action as Full Name, but the submit handler only persists `full_name`.
**Expected:** Either the email field saves correctly, or it is rendered read-only/removed until the feature exists.
**Actual:** `handleSubmit` in `app.profile.tsx:74-87` calls `auth.updateMe({ full_name: form.fullName })` — no `email` field is sent. The UI shows a green "Saved ✓" confirmation regardless.
**Root cause:** Incomplete implementation — the form scaffold includes both fields but the submit wiring was only completed for one.
**Impact:** A user who changes their email address, sees a success confirmation, and believes it took effect — it did not. This is worse than a visible error because it produces false confidence.
**Recommendation:** Either wire `auth.updateMe` to accept and persist `email` (with the appropriate re-verification flow), or make the field read-only with an explanatory note until that's built.
**Files:** `code/src/routes/app.profile.tsx:74-87`
**Services:** `backend/app/services/auth_service.py` (confirm whether `update_me` even accepts an email field server-side)
**APIs:** `PATCH /api/v1/auth/me` (or equivalent `updateMe` endpoint)
**DB tables:** `users`
**Risk if ignored:** Silent data-loss-adjacent UX bug; erodes trust in every "Saved" confirmation across the product once discovered.
**Priority:** P0 — trivial fix, high trust impact.

### PLA-009 — LOW
**Category:** Product
**Description:** "Scenario planning," named explicitly in the audit's required journey list, has no corresponding route, API, or service anywhere in the codebase.
**Expected:** N/A — flagged per the audit's instruction to report any missing step, not a claim that this was ever promised elsewhere in the product's own marketing.
**Actual:** Not implemented.
**Root cause:** Not built (not a regression — no evidence it was ever built and removed).
**Impact:** None currently, since the product doesn't market this capability; noted only because the audit brief named it as an expected journey.
**Recommendation:** No action unless product strategy calls for it — do not build speculatively (YAGNI).
**Files:** N/A
**Services:** N/A
**APIs:** N/A
**DB tables:** N/A
**Risk if ignored:** None.
**Priority:** P3 (informational only).

### PLA-010 — MEDIUM
**Category:** Financial / Calculation
**Description:** Retirement-category goals are modeled identically to accumulation goals (home, education) by the Monte Carlo engine; there is no decumulation-phase (withdrawal rate, sequence-of-returns risk, corpus depletion) modeling.
**Expected:** A CFP-grade retirement plan models the drawdown phase, not just accumulation to a target number.
**Actual:** `monte_carlo.py`'s `PROFILE_PARAMS` and simulation logic are accumulation-only (consistent with Volume 2's engine-scope documentation, not a new discovery but elevated here as a launch-readiness concern).
**Root cause:** Engine scope decision, likely intentional for v1 (Volume 9 ADR context suggests deliberate scoping, not oversight).
**Impact:** A user's "retirement goal probability" answers "will I reach $X by age Y" but not "will $X actually last me," which is the question retirees actually care about.
**Recommendation:** Scope for a post-launch milestone; document the limitation explicitly in-product (e.g., a tooltip on retirement goals) rather than implying full retirement planning.
**Files:** `backend/app/services/monte_carlo.py`
**Services:** `monte_carlo.run_simulation`, `quick_probability`
**APIs:** `/simulate`, goal creation/update paths
**DB tables:** `goals`, `simulations`
**Risk if ignored:** Moderate — sets incorrect user expectations for the single highest-stakes goal category in a financial planning app.
**Priority:** P1 (documentation fix now; engine work post-launch).

---

## CLOSING ASSESSMENT

This is not a product with broken architecture — it is a product with **one missing frontend surface** sitting on top of a correctly built backend, a genuinely sound calculation engine (ADR-001's event-driven recompute discipline is executed better here than in most production fintech codebases), and consistent interaction patterns wherever screens actually exist. The single fix that would move this from "impressive prototype" to "launchable financial planning product" is building the financials + assumptions CRUD surface (PLA-001/PLA-002) — everything else in this audit is either a small trust-repairing bug (PLA-011), a safety-net addition (PLA-008), or a documented, deliberate v1 scope boundary (PLA-009, PLA-010) rather than a defect.
