# LIFE EVENT ENGINE — ARCHITECTURE VALIDATION

**Role:** Technical Design Authority / Principal Software Architect
**Question being answered:** is `LifeEventEngineArchitecture.md` implementable against the codebase as it exists today?
**Method:** every conclusion below is backed by a fresh read of current source during this validation pass — `family_service.py`, `financials_service.py`, `routers/financials.py`, `routers/goals.py`, `routers/family.py`, `routers/profile.py`, `routers/assumptions.py`, `routers/copilot.py`, `database.py`, and the model files for every entity a life event touches — not by re-trusting the design document's own claims about that source. One critical, evidence-based defect was found that the design document did not surface (§6), which is why the final verdict is what it is.

---

## ARCHITECTURE SCORE: 6/10

## PASS / FAIL: **FAIL** (one Critical Blocker; fixable without a redesign)

The orchestration principle itself (§2 below) is sound and, event-by-event, correctly reuses existing services rather than duplicating calculation, recommendation, or notification logic. ADR-001 is respected precisely (§4). Where this design fails is a claim it makes about itself that the current codebase does not actually support: **"every `record_life_event` call runs inside one database transaction... the whole event is rolled back"** (`LifeEventEngineArchitecture.md` §4.2). This is false for 10 of the 15 events, proven directly from `routers/financials.py`'s actual commit pattern (§6). This is a Critical Blocker, not a redesign trigger — the fix is a small, well-understood refactor (defer financials' commits to the request-scoped session, exactly as `routers/goals.py` and `family_service.py` already do), not a change to the architecture's shape.

---

## 1. VERIFY EVERY ONE OF THE 15 LIFE EVENTS

Each event assessed against: can it be implemented today, which tables actually change, which services/APIs are genuinely reused vs. missing, and which schema gaps are real.

### 5.1 Salary Raise
- **Implementable today:** Yes.
- **Tables:** `income_sources` (update `annual_amount`); optionally `goals` (update `monthly_contribution`).
- **Services reused:** the existing income-update code path (`financials_service.update_income_source` or equivalent field-set logic); `planning_service.calculate_goal_probability` via `routers/goals.py`'s existing `CALCULATION_CONTEXT_FIELDS` check, if the optional goal step is taken.
- **APIs reused:** `PATCH /financials/income/{id}` semantics (in-process, not necessarily the HTTP endpoint itself), `PATCH /goals/{id}` semantics.
- **Missing APIs:** none — this event needs no new capability, only orchestration.
- **Schema gaps:** none.
- **Transaction risk:** **Real.** `financials_service.update_income_source` calls `await db.commit()` internally (`financials_service.py:46`). If the optional goal step is also taken and *that* write fails validation, the income update is already durably committed. See §6.

### 5.2 Job Change
- **Implementable today:** Yes.
- **Tables:** `user_profiles` (`employer`, `occupation`); `income_sources` (soft-delete old row, create new row).
- **Services reused:** the profile-update path (`routers/profile.py`); the income create/soft-delete paths (`routers/financials.py`).
- **APIs reused:** profile update, income create, income delete — all exist today.
- **Missing APIs:** none.
- **Schema gaps:** none.
- **Transaction risk:** **Real, and the worst 2-write case among the "simple" events.** `routers/profile.py:51` commits, then the old-income soft-delete commits (`routers/financials.py:87`), then the new-income create commits (`routers/financials.py:56`) — three independent commit points, no shared transaction. A failure on the third write leaves the user with **no income source at all** (the old one already deactivated, the new one never created) — a materially worse state than before the event was attempted.

### 5.3 Marriage
- **Implementable today:** Yes.
- **Tables:** `household_members` (create, `relationship_type="spouse"`), `dependents` (create, `dependent_type="spouse"`).
- **Services reused:** `family_service.create_member` — confirmed by direct read to perform exactly this two-row create and write the `family_member_added` `AuditLog` row the design doc claims it does (`family_service.py:163-196`).
- **APIs reused:** `POST /family/members` semantics.
- **Missing APIs:** none.
- **Schema gaps:** none for the write itself. **One real gap the design doc did not surface:** `create_member` (and the whole `household_members` table) has **no uniqueness constraint or application-level check preventing a second active `relationship_type="spouse"` row.** Confirmed by direct read of `household.py` (no `UniqueConstraint`/`CheckConstraint` on `relationship_type`) and `family_service.validate_member_fields` (validates required *fields* per type, never *cardinality*). See §5 (event ordering).
- **Transaction risk:** **None.** `family_service.create_member` never calls `db.commit()` — confirmed by direct read of the full file. This event is genuinely atomic today via the request-scoped session (`database.py`'s `get_db`).

### 5.4 Divorce
- **Implementable today:** Yes.
- **Tables:** `household_members` (soft-delete the spouse row), `dependents` (soft-delete, cascades in application logic since `remove_member` only flips the member's `is_active`; confirmed the `Dependent` row is *not* separately soft-deleted by `remove_member` today — see gap below).
- **Services reused:** `family_service.remove_member`.
- **APIs reused:** `DELETE /family/members/{id}` semantics.
- **Missing APIs:** none for the base operation.
- **Schema gaps / real defect found:** `family_service.remove_member` (`family_service.py:278-288`) sets **only** `member.is_active = False` — it does **not** touch the associated `Dependent` row's `is_active` at all. This means after a Divorce, the `HouseholdMember` row is correctly inactive, but its `Dependent` row (carrying `date_of_birth`, `has_own_insurance`, etc.) is left `is_active=True` and orphaned from any UI that filters on the member. This is a **pre-existing gap in `family_service.py` itself**, not something the Life Event Engine introduces — but the Life Event Engine's Divorce handler cannot honestly claim "the dependent row soft-deleted with it" (as `LifeEventEngineArchitecture.md` §5.4 states) without either (a) `remove_member` being fixed first, or (b) the Life Event Engine adding its own extra write to the `Dependent` row — the latter is a small, scoped, justifiable addition (not a duplicate of any calculation), but it is **new code**, not pure reuse, and the design doc should say so rather than imply `remove_member` already handles it.
- **Also missing:** the two "review" notification checks (health policy coverage, nominee designation) the design proposes are **net-new read-only functions** — nothing in `notification_service.py` today reads `HealthPolicyCoverage`/`Nominee` at all. Correctly scoped as small and consistent with the existing pattern, but they do not exist yet and must be built, not merely wired.
- **Transaction risk:** Low in isolation (`remove_member` doesn't commit), but the Divorce handler's own extra `Dependent` write (needed to fix the gap above) would need to happen in the same uncommitted session, which is fine as long as it's added directly to `life_event_service.py` rather than assumed to already happen inside `remove_member`.

### 5.5 Birth of Child
- **Implementable today:** Yes.
- **Tables:** `household_members` + `dependents` (create, `relationship_type="child"` / `dependent_type="minor_child"`); optionally `goals` (create, `category="education"`).
- **Services reused:** `family_service.create_member`; `routers/goals.py`'s goal-creation logic (which **unconditionally** calls `calculate_goal_probability` for every new goal — confirmed at `routers/goals.py:45`, not gated by `CALCULATION_CONTEXT_FIELDS` at all, since a brand-new goal has no "before" state to compare against).
- **APIs reused:** `POST /family/members`, `POST /goals`.
- **Missing APIs:** none.
- **Schema gaps:** none.
- **Transaction risk:** **None**, provided the optional goal step is the *only* additional write (both `create_member` and goal creation defer commit to the request-scoped session — confirmed no `db.commit()` in either path). This is one of the two cleanest compound events in the entire catalog.

### 5.6 Adoption
- **Implementable today:** Yes — identical to Birth of Child in every table/service/API respect, confirmed by inspection (no distinguishing field exists on `Dependent`, exactly as the design doc itself already states). No additional finding beyond what §5.5 covers and what the design doc already self-flags.
- **Transaction risk:** Same as Birth of Child — none.

### 5.7 House Purchase
- **Implementable today:** Yes, as a set of writes — **not** atomically, today.
- **Tables:** `assets` (create, `asset_type="real_estate"`), `liabilities` (create, `liability_type="mortgage"`); optionally an existing liquid `assets.current_value` (update); optionally `goals.current_amount` (update).
- **Services reused:** the asset-create and liability-create paths in `routers/financials.py`.
- **APIs reused:** `POST /financials/assets`, `POST /financials/liabilities`.
- **Missing APIs:** none for the writes themselves.
- **Schema gaps:** none (`real_estate` is already a valid `asset_type` used by the existing Investments onboarding step).
- **Transaction risk:** **Critical, direct evidence.** `routers/financials.py:176` (`create_asset`) and `:252` (`create_liability`) each call `await db.commit()` independently. If the `Asset` create succeeds and commits, and the `Liability` create then fails (a validation error, a constraint violation, a dropped connection), **the user is left with a house and no mortgage recorded — a permanently half-applied event**, exactly the failure mode `LifeEventEngineArchitecture.md` §4.2 claims cannot happen. This is the flagship counter-example for §6.

### 5.8 Home Sale
- **Implementable today:** Yes, as a set of writes — not atomically.
- **Tables:** `assets` (soft-delete the home), `liabilities` (soft-delete the mortgage, if paid off), `assets` (create or update for proceeds).
- **Services/APIs reused:** the asset/liability delete and asset create/update paths in `routers/financials.py`.
- **Missing APIs:** none.
- **Schema gaps:** none.
- **Transaction risk:** **Critical, worse than House Purchase** — three independent commit points (`routers/financials.py:223` asset soft-delete, a liability soft-delete at the equivalent line, `:176` or `:202` for the proceeds asset). A failure on the third write can leave a user with **no home, a still-active mortgage on a home they no longer own, and no proceeds recorded** — the single worst partial-failure outcome in the entire catalog.

### 5.9 New Loan
- **Implementable today:** Yes.
- **Tables:** `liabilities` (create); optionally `assets` (create, for the linked purchase).
- **Services/APIs reused:** liability-create and asset-create paths.
- **Missing APIs:** none.
- **Schema gaps:** none for the enumerated types the design uses (`auto_loan`/`student_loan`/`personal_loan`/`credit_card`/`other` all exist in the current `LIABILITY_TYPES` set, confirmed against `code/src/components/onboarding/list-steps.tsx`).
- **Transaction risk:** **Real only when the optional linked-Asset step is taken** (two eager-commit financials writes). The mandatory-only case (Liability alone) is a single write and is trivially atomic (it either fully succeeds and commits, or fails before ever reaching `db.commit()`).

### 5.10 Loan Payoff
- **Implementable today:** Yes.
- **Tables:** `liabilities` (soft-delete only).
- **Services/APIs reused:** the liability-delete path.
- **Missing APIs:** none.
- **Schema gaps:** none.
- **Transaction risk:** **None.** Single entity, single write, deliberately scoped to closure-only exactly as the design specifies — this is the one financials-touching event that is genuinely atomic today, purely because it never combines with a second write.

### 5.11 Inheritance
- **Implementable today:** Yes.
- **Tables:** `assets` (create); optionally `income_sources` (create).
- **Services/APIs reused:** asset-create, income-create paths.
- **Missing APIs:** none.
- **Schema gaps:** none.
- **Minor completeness gap (not a defect):** unlike House Purchase and Birth of Child, Inheritance's design does not offer an optional "apply this toward an existing goal's `current_amount`" step, even though a cash inheritance is a natural candidate for exactly that. Flagged in §Minor Issues, not a blocker.
- **Transaction risk:** **Real only when the optional income step is taken** (two eager-commit writes); atomic in the base case (Asset only).

### 5.12 Retirement
- **Implementable today:** Yes, as a set of writes — **the least atomic event in the entire catalog.**
- **Tables:** `user_profiles.employment_status`, one-or-more `income_sources` (soft-delete), optionally a new `income_sources` (pension), optionally `financial_assumptions.retirement_age`/`.social_security_monthly`, optionally one-or-more `goals.monthly_contribution`.
- **Services/APIs reused:** profile update (`routers/profile.py`), income soft-delete/create (`routers/financials.py`), assumptions update (`routers/assumptions.py`), goal update (`routers/goals.py`).
- **Missing APIs:** none — every sub-write already has an existing path.
- **Schema gaps:** none.
- **Transaction risk:** **Critical, and structurally guaranteed to occur** — this event is *designed* (correctly, from a product standpoint) to touch Profile, Income, Assumptions, and Goals together, and three of those four domains (`profile.py:51`, `financials.py`'s income paths, `assumptions.py:57`/`:84`) each commit eagerly and independently, while only the goal-contribution updates defer commit. A failure partway through Retirement's flow (e.g., the third of four goal-contribution updates fails validation) can leave a user retired-on-paper, with their salary already deactivated, but only some of their goals reflecting the change — the single most damaging partial-failure scenario this design catalog contains, given how consequential and irreversible-feeling "I am now retired" is to a real user.

### 5.13 Major Medical Event
- **Implementable today:** Yes, as a set of writes — not atomically once more than one optional step is taken.
- **Tables:** `expenses` (create/update); optionally `assets` (update, lump sum); optionally `liabilities` (create, financing).
- **Services/APIs reused:** expense create/update, asset update, liability create paths.
- **Missing APIs:** none.
- **Schema gaps:** correctly self-identified by the design doc — `Expense` has no one-time-transaction concept; the design's stated workaround (record as ongoing, tell the user plainly) is honest and requires no schema change. No further gap found.
- **Transaction risk:** **Real** whenever two or more of the three possible writes are combined — the realistic case the design itself anticipates (an expense increase *and* a lump-sum payment, or *and* new financing).

### 5.14 Business Start
- **Implementable today:** Yes.
- **Tables:** `user_profiles.employment_status`; optionally `assets`/`expenses`; optionally `liabilities`.
- **Services/APIs reused:** profile update, expense/asset/liability creation paths.
- **Missing APIs:** none.
- **Schema gaps:** correctly self-identified — no `business_loan` `liability_type` value exists yet; the design's own stated `"other"` fallback is honest and requires no schema change to ship. No further gap found.
- **Transaction risk:** **Real** whenever the profile update is combined with any financials write (`profile.py:51` commits independently of `financials.py`'s eager commits).

### 5.15 Business Sale
- **Implementable today:** Yes, as a set of writes — not atomically in the realistic (2+ effect) case.
- **Tables:** `assets` (create/update, proceeds); optionally `liabilities` (soft-delete); optionally `income_sources` (create); optionally `user_profiles.employment_status`.
- **Services/APIs reused:** asset, liability, income, profile paths.
- **Missing APIs:** none.
- **Schema gaps:** none beyond the already-flagged `business_loan` note carried over from Business Start.
- **Transaction risk:** **Real**, essentially guaranteed — the minimum realistic case (proceeds asset + debt payoff) is already two eager-commit financials writes.

**Summary of Part 1:** every one of the 15 events is implementable using tables, fields, and service logic that already exist — **zero missing APIs, zero missing entities, zero invented schema required beyond two already-self-flagged, small, additive gaps** (`business_loan` enum value; `Dependent` has no adoption-vs-birth distinction). This is a genuine strength of the design: it was scoped tightly against the real schema, not against a wished-for one. The defect is entirely in the transaction layer (§6), not in the entity model.

---

## 2. VERIFY THE ORCHESTRATION PRINCIPLE

**PASS.** Traced every event's "which calculations rerun" and "which recommendations update" claims against the actual code, not the design document's own restatement of it:

- **Financial calculations:** confirmed `get_financial_context`/`get_dashboard` (`planning_service.py`) are computed fresh on every call with no memoization — the design's claim that no life event needs to "invalidate" anything holds, because there is nothing cached to invalidate. No life event in the catalog re-implements net worth, savings rate, or debt-ratio math; every one simply writes to the entities that math already reads.
- **Recommendation logic:** confirmed `family_recommendations_service._financial_health_recommendations` (Recommendation Engine v2, verified live and shipped per `RecommendationEngineV2.md` and the follow-up `RecommendationEngineV2_E2EValidation.md`) reads only `FinancialContext`, never `income_sources`/`expenses`/`assets`/`liabilities` directly. No life event in the catalog computes a threshold comparison itself (e.g., no event checks `interest_rate > 0.10` — that check exists exactly once, in `family_recommendations_service.py`'s `_HIGH_INTEREST_THRESHOLD` constant, and the design doc explicitly reuses that same constant name rather than restating the number, at §5.7/§5.9).
- **Notification logic:** confirmed `notification_service.py`'s `_Fact`-based collector pattern is the only notification-producing mechanism in the codebase, and the design's one new collector (`_collect_life_event_facts`) is structurally identical to the existing `_collect_family_member_added_facts` (same dedupe-key convention, same recency-window convention, same read-only guarantee). No event invents a second notification pathway.
- **Monte Carlo:** confirmed `monte_carlo.quick_probability_async`/`run_simulation_async` are called from exactly one place, `planning_service.calculate_goal_probability`, and every life event that touches a goal field routes through the *existing* `routers/goals.py` create/update code (or an identical call to `calculate_goal_probability`), never a second Monte Carlo entry point.

**No event in the catalog duplicates a calculation, a recommendation rule, or a notification collector.** This part of the design is correctly disciplined and required no correction.

---

## 3. VERIFY ADR-001

**PASS**, verified against `CALCULATION_CONTEXT_FIELDS = {"current_amount", "monthly_contribution", "target_date", "risk_profile", "target_amount"}` (`planning_service.py:36-38`) and `routers/goals.py`'s exact conditional (`if CALCULATION_CONTEXT_FIELDS & updates.keys(): await calculate_goal_probability(goal)` at line 91-92).

Exactly four of the fifteen events can trigger a Monte Carlo recalculation, and only in their optional branches:

| Event | Goal field touched | Trigger mechanism |
|---|---|---|
| Salary Raise | `monthly_contribution` (optional) | Existing conditional check in `update_goal` |
| Birth of Child | new goal's full field set (if created) | `create_goal`'s **unconditional** call — every new goal always gets one Monte Carlo run, this is not special-cased |
| Adoption | same as Birth of Child | same |
| House Purchase | `current_amount` (optional) | Existing conditional check in `update_goal` |
| Retirement | `monthly_contribution`, per goal (optional, possibly multiple goals) | Existing conditional check, called once per goal touched — never a batch "recompute every goal" pass |

The remaining 10 events correctly trigger **zero** Monte Carlo runs, because none of their entity writes (`income_sources`, `expenses`, `assets`, `liabilities`, `household_members`, `dependents`, `user_profiles`, `financial_assumptions`) are members of `CALCULATION_CONTEXT_FIELDS` — and `CALCULATION_CONTEXT_FIELDS` is, by design, a set of `Goal` columns only. The design never proposes recalculating a goal because a life event changed a non-goal field, which would have been a direct ADR-001 violation. It does not.

---

## 4. VALIDATE UNDO

| Event | Classification | Why |
|---|---|---|
| Salary Raise | **Conditionally reversible** | Income revert always safe alone; blocked if the linked goal's contribution was independently re-edited since. |
| Job Change | **Conditionally reversible** | Three rows involved; blocked if any one was independently touched since — genuinely more fragile than most, given the compound old/new income swap. |
| Marriage | **Conditionally reversible** | Blocked if anything now references the spouse (a goal tag, a `HealthPolicyCoverage` row) — this guard does not exist in `family_service` today and must be built new in the orchestration layer (see §1, §5.3). |
| Divorce | **Conditionally reversible, weaker than the design assumes** | Reactivating the member is straightforward; reactivating the `Dependent` row requires the orchestration layer to touch it directly, since `remove_member` never deactivated it in the first place (§1, §5.4 gap) — meaning "undo" and "the original soft-delete" are not perfectly symmetric today without this fix. |
| Birth of Child | **Conditionally reversible** | Blocked if the optional education goal received contributions or tags since. |
| Adoption | Same as Birth of Child. |
| House Purchase | **Conditionally reversible** | Blocked if the mortgage balance was independently edited (a normal, expected occurrence — mortgages get paid down) — this is likely to become blocked-by-default fairly quickly after the event, which the design correctly anticipates with its explicit "this will discard your update" confirmation. |
| Home Sale | **Conditionally reversible** | Three effects, each guarded independently. |
| New Loan | **Conditionally reversible** | Straightforward unless the linked asset was independently edited. |
| Loan Payoff | **Fully reversible** | Single entity, single field flip (`is_active`), no realistic independent-edit race in the interim for a *closed* liability. |
| Inheritance | **Conditionally reversible** | Blocked if the asset's value was independently adjusted (e.g., a brokerage-held inheritance whose value the user later corrected). |
| Retirement | **Conditionally reversible, but in practice the least likely to cleanly undo** | Four-to-seven effect rows; the more optional sub-steps taken, the higher the chance at least one has independently drifted by the time undo is attempted — genuinely the hardest event to fully reverse in the catalog, compounding its transaction risk (§1, §6). |
| Major Medical Event | **Conditionally reversible** | Up to three independent effects. |
| Business Start | **Conditionally reversible** | Profile field plus up to two financial effects. |
| Business Sale | **Conditionally reversible** | Up to four independent effects — the second-hardest event to cleanly undo after Retirement. |

**No event in the catalog is "never reversible"** — every write, including soft-deletes, preserves the prior row's data (soft-delete, not hard-delete, is the schema-wide convention, confirmed on every table involved). The generic guarded-undo mechanism (§7 of the design) is structurally sound. Its correctness, however, depends entirely on `life_event_effects.before_state`/`after_state` being captured **before any commit happens** — which is only safe today for the four events that are already atomic (§1: Marriage, Divorce, Birth of Child, Adoption). For every other event, if a mid-event write already committed and a later write then fails, the recorded `life_event_effects` rows for the *committed* portion are real and undoable, but the event as a whole is left in the exact half-applied state §6 describes — undo can clean up the mess, but only after the fact, and only if the user notices something is wrong and asks for it.

---

## 5. VALIDATE EVENT ORDERING

**The engine cannot prevent invalid sequences today, and for good reason in most cases — but one real, fixable gap exists.**

- **Divorce before Marriage:** effectively prevented today, but only as a side effect of UI scoping, not a real guard — the Divorce flow's spouse-picker (§9.2 of the design) queries only active `household_members` with `relationship_type="spouse"`; if none exists, there is nothing to select. This is adequate, but it is worth naming precisely as *incidental* prevention, not a designed constraint, since a direct API call (bypassing the picker) would hit no server-side check at all — `family_service.remove_member` takes any `HouseholdMember` row and does not verify `relationship_type` matches anything.
- **Two simultaneous Marriages (bigamy-shaped data):** **not prevented, and this is a real gap.** Nothing in `household_members`, `family_service.create_member`, or `family_service.validate_member_fields` stops a second `relationship_type="spouse"` row being created while a first is still `is_active=True`. This is the one ordering case that is unambiguously invalid in every real-world reading (unlike remarriage-after-divorce, which is legitimate and must **not** be blocked). The Life Event Engine's Marriage handler must add this specific guard itself — it cannot inherit it from `family_service`, because `family_service` was never asked to enforce it (correctly, for Milestone 1/2's scope — this is a new requirement this milestone introduces).
- **Remarriage after Divorce, multiple Business Starts, multiple House Purchases, "un-retiring" after Retirement:** all real-world-valid sequences that must **not** be blocked, and nothing in the current schema blocks them. This is correct behavior, not a gap — the design does not need a fix here, only the explicit acknowledgment (given here) that "prevent invalid sequences" is not the same goal as "prevent all repetition."
- **Retirement recorded with zero prior income history:** technically possible (a user could record Retirement as their very first life event), producing a `user_profiles.employment_status = "retired"` with no salary ever deactivated. Not harmful, not worth guarding — the event's own inputs form already only offers to deactivate income sources that exist, so this degrades gracefully to "just a profile/assumptions update," not an error.

**Conclusion:** the engine can and should add exactly one new ordering guard (at-most-one-active-spouse) at the orchestration layer. Every other sequencing question the brief's example (Marriage → Birth → Divorce → Retirement) raises is either already handled by data availability (you cannot act on a person/entity that doesn't exist) or should remain unconstrained because the real world does not follow a fixed order either.

---

## 6. VALIDATE TRANSACTION BOUNDARIES — **CRITICAL BLOCKER**

This is the headline finding of this validation.

**Claim in `LifeEventEngineArchitecture.md` §4.2:** *"Every `record_life_event` call runs inside one database transaction. If any sub-write fails... the whole event is rolled back."*

**Verified against actual code:**

```
app/routers/financials.py:56   await db.commit()   (create_income)
app/routers/financials.py:87   await db.commit()   (delete_income)
app/routers/financials.py:116  await db.commit()   (create_expense)
app/routers/financials.py:147  await db.commit()   (delete_expense)
app/routers/financials.py:176  await db.commit()   (create_asset)
app/routers/financials.py:202  await db.commit()   (update_asset)
app/routers/financials.py:223  await db.commit()   (delete_asset)
app/routers/financials.py:252  await db.commit()   (create_liability)
app/routers/financials.py:278  await db.commit()   (update_liability)
app/routers/financials.py:299  await db.commit()   (delete_liability)
app/services/financials_service.py:46  await db.commit()   (update_income_source)
app/services/financials_service.py:71  await db.commit()   (update_expense)
app/routers/profile.py:51      await db.commit()
app/routers/assumptions.py:57, 84   await db.commit()
```

versus:

```
app/database.py's get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()      # commits ONCE, at the end of the request
        except Exception:
            await session.rollback()
            raise
```

`routers/goals.py` and `family_service.py` contain **zero** explicit `db.commit()` calls anywhere — confirmed by direct grep of both files. They rely entirely on `get_db`'s single end-of-request commit, which is exactly what makes a multi-write event built purely from goal/family writes (Marriage, Divorce, Birth of Child, Adoption) genuinely atomic today, with no changes needed.

**But `financials.py`, `financials_service.py`, `profile.py`, and `assumptions.py` each commit eagerly, per operation, independently of the request-scoped session.** This is a real, pre-existing inconsistency in the current codebase between two commit conventions that have never before needed to interoperate within a single logical operation — no feature before the Life Event Engine has ever needed one HTTP request to atomically span, say, both an Asset and a Liability write. Milestone 1's Financials editing was always single-entity, single-PATCH, single-commit by design, and that design was correct **for that scope**. It was never built to compose.

**Consequence:** any life event whose design combines two or more writes where at least one is a `financials.py`/`profile.py`/`assumptions.py` write is **not atomic today**, regardless of how the orchestration code is written, because the individual functions being reused each end their own transaction before the orchestrator can react to a later failure. **10 of the 15 events fall into this category** (§1's per-event "Transaction risk" line makes this explicit for each). House Purchase, Home Sale, and Retirement are the three most exposed — Home Sale can leave a user's mortgage still active on a home they no longer own; Retirement can leave a user's salary deactivated with only some goals updated.

**This is fixable without redesigning the architecture.** Three options, in order of preference:

1. **Refactor `financials_service.py`/`routers/financials.py`, `routers/profile.py`, and `routers/assumptions.py` to stop committing internally**, matching the pattern `goals.py`/`family_service.py` already use — a small, mechanical, low-risk change (remove one line per function, let `get_db` commit once at request end). This is the only option that actually delivers the atomicity the design document promises, and it improves the existing Financials/Profile/Assumptions code too (a `PATCH` that raises after a partial in-place mutation today already has a narrow window where `db.add()` happened but `commit()` hadn't — removing the internal commit and centralizing on `get_db` closes that window everywhere, not just for life events).
2. **Wrap the Life Event Engine's own DB operations in an explicit nested transaction/savepoint** (`async with db.begin_nested()`) that is independent of what the reused functions do internally — technically possible with SQLAlchemy, but fragile: if a reused function calls `db.commit()` on the *outer* session from inside a caller's `begin_nested()` block, the nested savepoint's guarantees are not what a reader would assume, and this requires careful, non-obvious session-lifecycle reasoning to get right. Not recommended as the primary fix.
3. **Accept non-atomic, compensating-transaction semantics** — let sub-writes commit as they do today, and have the Life Event Engine detect a partial failure and *undo* the already-committed portion via the same `life_event_effects`-driven undo mechanism, immediately, automatically, without waiting for the user to notice. This is weaker than true rollback (there is a real, if brief, window where the database is in a half-applied state visible to a concurrent read — e.g., a `GET /dashboard` racing between the Asset commit and the Liability failure would show a house with no mortgage), but it is a legitimate, honest fallback if option 1 is deferred.

**Recommendation: Option 1**, scheduled explicitly in the implementation phasing (§Implementation Order below), before any compound event (Phase D in the original design's own phasing) is built.

---

## 7. VALIDATE RECOMMENDATION INTEGRATION

**Rules that react** (verified against `family_recommendations_service._financial_health_recommendations`'s actual seven rules and `planning_service._generate_suggestions`):

| Rule | Reacts to which life events |
|---|---|
| `income_concentration` | Salary Raise (no), Job Change (source count unchanged, no), Inheritance (if income added, yes), Retirement (if income sources change, yes) |
| `expense_review_prompt` | Major Medical Event (yes — `updated_at` on the touched `Expense` row refreshes) |
| `low_liquidity` | House Purchase (down payment), Home Sale (proceeds), Inheritance, Major Medical Event (lump sum), all financials-touching events that move a liquid `Asset` |
| `high_interest_debt` | House Purchase, New Loan, Loan Payoff (stops firing), Home Sale (stops firing), Business Start/Sale |
| `low_savings_rate` | Salary Raise, Job Change, Retirement, Major Medical Event (expense increase) |
| `negative_net_worth_trend` | House Purchase, Home Sale, Inheritance, Business Sale |
| `high_debt_to_income` | House Purchase, New Loan, Loan Payoff (stops), Home Sale (stops), Business Start/Sale |

**Rules that remain unchanged, correctly:** none of the seven rules need any code change — every reaction above is a consequence of the rule reading `FinancialContext`, which is always recomputed live from the entities the life event wrote to. The design's claim that recommendations update "for free" is verified true. `family_insurance_service` and `scheme_eligibility_service` likewise react automatically to Marriage/Divorce/Birth of Child/Adoption's `household_members`/`dependents` writes, with zero new eligibility logic needed — confirmed both read `household_members`/`dependents` live on every call.

---

## 8. VALIDATE NOTIFICATION INTEGRATION

**Reused, confirmed free:** the `family_member_added` fact (`notification_service._collect_family_member_added_facts`, reading `AuditLog` rows written by `family_service.create_member`) already fires for Marriage, Birth of Child, and Adoption with zero new code — verified directly, since `create_member` is the exact function all three events call. The existing `goal_at_risk`/`goal_completed` facts (`_collect_goal_facts`) already react to any life event that changes a goal's `current_amount`/`monthly_contribution` (House Purchase, Retirement, Birth of Child/Adoption's optional goal, Salary Raise's optional step).

**New, genuinely required (do not exist today):**
1. `_collect_life_event_facts` — the one generic collector the design specifies, reading the new `life_events` table.
2. The two Divorce-specific "review" facts (health policy coverage, nominee designation) — confirmed nothing in `notification_service.py` reads `HealthPolicyCoverage` or `Nominee` today; these are net-new, small, read-only functions, correctly scoped in the same pattern as everything else in that file, but not free the way the family-event notification is.

Nothing else is required. Loan Payoff's proposed "✓ paid off" styling is copy, not new mechanism — it reuses the exact same collector as every other life event.

---

## 9. VALIDATE AI COPILOT READINESS

**Not ready today, and the design document does not claim it is** — this validation checked independently rather than against a claim.

Verified `routers/copilot.py`: the system prompt (`_SYSTEM_PROMPT`) is built from `{goals_json}` only — confirmed by direct read, no `FinancialContext`, no household/family state, no notification or recommendation data, and certainly no life event history, is fed into the prompt anywhere in the current router.

**Missing metadata for Life Events to become usable AI context:**
1. **A natural-language summary field.** `life_events.inputs` (as designed) is a raw form-submission JSON blob (e.g., `{"annual_amount": 156000, "income_source_id": "..."}`) — this is machine-shaped, not something a prompt builder should paste in front of an LLM as-is. A `life_events.summary` (plain-language, generated once at record time from the same copy the UI's review screen already renders — e.g., "Recorded a salary raise to $156,000/yr") would be a small, additive column and the natural bridge to Copilot context, but it is not in the current design.
2. **A copilot prompt-builder hook.** Even with a summary field, nothing in `routers/copilot.py` today reads any table besides `Goal`. Wiring life event history into the prompt is real, unbuilt integration work, not a configuration flag.
3. **Relevance/recency weighting.** A user's full life event history could grow large; the design does not specify how many recent events (or which ones) should ever reach a prompt, risking an unbounded, un-prioritized context dump if implemented naively.

**Recommendation:** treat AI Copilot integration as an explicit, separate follow-up milestone once life events exist and have accumulated real usage — consistent with this design's own, already-stated non-goal discipline (§11 of the design: "no new recommendation rules invented to fill perceived gaps"). Do not build Copilot wiring speculatively inside this milestone.

---

## 10. EVENT IMPACT MATRIX

| Event | Family | Financials | Goals | Recommendations | Notifications | Monte Carlo | Undo | Risk |
|---|---|---|---|---|---|---|---|---|
| Salary Raise | — | Income update | Optional contribution update | `income_concentration`, `low_savings_rate` | New (generic) + goal_at_risk may clear | Conditional (1 goal) | Conditional | Medium (2-write case) |
| Job Change | — | Income soft-delete + create | — | `income_concentration`, `low_savings_rate` | New (generic) | None | Conditional | **High** (3 commit points) |
| Marriage | Member + dependent create | — | — | Insurance/scheme (live) | Free (`family_member_added`) | None | Conditional (new guard needed) | Low (atomic today) |
| Divorce | Member soft-delete (+ dependent gap) | — | (goal tags reviewed, not changed) | Insurance/scheme (live) | Free + 2 new review facts | None | Conditional (weaker than assumed) | Medium (dependent-row gap) |
| Birth of Child | Member + dependent create | — | Optional education goal create | Insurance/scheme (live), `income_concentration` unaffected | Free | Conditional (1 new goal) | Conditional | Low (atomic today) |
| Adoption | Same as Birth of Child | — | Same | Same | Free | Conditional | Conditional | Low |
| House Purchase | — | Asset + Liability create | Optional current_amount update | `high_interest_debt`, `high_debt_to_income`, `low_liquidity` | New (generic) + inline high-interest surfacing | Conditional (1 goal) | Conditional (mortgage drifts fast) | **Critical** (2-write, flagship non-atomic case) |
| Home Sale | — | Asset soft-delete + Liability soft-delete + Asset create/update | — | `high_interest_debt`/`high_debt_to_income` clear, `low_liquidity` clears | New (generic) | None | Conditional | **Critical** (3-write, worst partial-failure state) |
| New Loan | — | Liability create (+ optional Asset) | — | `high_interest_debt` | New (generic) + inline warning | None | Conditional | Medium (only if linked asset used) |
| Loan Payoff | — | Liability soft-delete | — | `high_interest_debt`/`high_debt_to_income` clear | New (generic, celebratory) | None | **Fully reversible** | Low (single write, atomic) |
| Inheritance | — | Asset create (+ optional Income) | (no goal-link option — gap) | `negative_net_worth_trend`, `low_liquidity` clear | New (generic) + estate-doc UI nudge | None | Conditional | Medium (only if income added) |
| Retirement | — | Income soft-delete + create + Assumptions update | Optional multi-goal contribution update | `low_savings_rate`, `income_concentration`, `high_debt_to_income` | New (generic) | Conditional (N goals) | Conditional (hardest to fully undo) | **Critical** (4+ commit points, most exposed event) |
| Major Medical Event | — | Expense create/update (+ optional Asset/Liability) | — | `low_liquidity`, `low_savings_rate`, `expense_review_prompt` refresh | New (generic) | None | Conditional | High (up to 3 writes) |
| Business Start | — | Profile update (+ optional Expense/Asset/Liability) | — | None modeled today (gap, correctly not invented) | New (generic) | None | Conditional | Medium |
| Business Sale | — | Asset create/update (+ optional Liability/Income/Profile) | — | `negative_net_worth_trend`, `high_interest_debt`/`high_debt_to_income` clear | New (generic) | None | Conditional | High (up to 4 writes) |

---

## CRITICAL BLOCKERS (must be resolved before Phase D of the design's own phasing ships)

1. **Transaction atomicity is not real for 10 of 15 events** (§6). `financials.py`/`financials_service.py`/`profile.py`/`assumptions.py` each commit eagerly per operation; only `goals.py`/`family_service.py` defer to the request-scoped session. Fix: refactor the eager-commit paths to stop calling `db.commit()` internally, matching the pattern already proven correct elsewhere in this same codebase. This is a pre-existing inconsistency the Life Event Engine exposes, not one it creates — and fixing it also improves Milestone 1's existing Financials/Profile/Assumptions code, not just this milestone.
2. **No cardinality guard prevents a second active spouse** (§5). Must be added as new orchestration-layer logic in the Marriage handler — cannot be inherited from `family_service.create_member`, which was never asked to enforce this.
3. **`family_service.remove_member` does not deactivate the associated `Dependent` row** (§1, §4). The Divorce handler's claim that the dependent row is "soft-deleted with it" is not true of the reused function as it exists today; the orchestration layer must add this write itself, and the design document should say so explicitly rather than imply full reuse.

## MINOR ISSUES (do not block implementation)

- Inheritance has no optional goal-funding step, asymmetric with House Purchase and Birth of Child's analogous options — a completeness gap, not a defect.
- The two Divorce-specific notification checks (health policy coverage, nominee review) and the one generic `_collect_life_event_facts` collector are net-new code, correctly small and consistent in shape with existing collectors, but should not be described as "free" the way the family-member-added reuse genuinely is.
- AI Copilot readiness requires a new `life_events.summary` field and new prompt-builder wiring, neither of which the design specifies — correctly treated as a future milestone's concern, not a defect in this one, provided it is not silently assumed to already work.

## MIGRATION RISKS

- The `financials.py`/`profile.py`/`assumptions.py` commit-pattern refactor (Critical Blocker 1's fix) touches already-shipped, already-tested Milestone 1 code. It must ship with full regression coverage of the existing Financials/Profile/Assumptions test suites before any Life Event work depends on it, exactly the same rigor `RecommendationEngineV2Validation.md`'s own Phase A ("extraction, no behavior change, verified byte-identical before any new feature is added") already modeled successfully in this project.
- `life_event_effects`' `before_state`/`after_state` JSON snapshots are only as trustworthy as the transaction boundary they were captured inside — until Critical Blocker 1 is fixed, any `life_event_effects` row for a financials-touching event captures the state at snapshot time, which may not reflect what actually persisted if a later step in the same event failed. This is a direct, compounding consequence of Blocker 1, not a separate risk.

## IMPLEMENTATION ORDER (validated against the design's own phasing, §12)

The original design's phasing (A: core engine + Loan Payoff → B: single-entity events → C: family events → D: compound events → E: Retirement → F: frontend) is **directionally correct and should not be reordered**, with one addition: **Critical Blocker 1's transaction refactor must be inserted before Phase D**, not discovered during it. Concretely:

1. Phase A (core engine, `life_events`/`life_event_effects` tables, Loan Payoff) — no blocker, can start immediately.
2. Phase B (Salary Raise, New Loan, Inheritance, Business Start) — can start immediately in their single-effect forms; their optional multi-effect branches inherit Blocker 1 and should be flagged, not silently shipped as "atomic," until it lands.
3. Phase C (Marriage, Divorce, Birth of Child, Adoption) — can start immediately; must incorporate Critical Blockers 2 and 3 (spouse-cardinality guard, dependent-deactivation fix) as part of this phase's own scope, not deferred.
4. **New: Transaction refactor (Critical Blocker 1)** — inserted here, before Phase D, as its own scoped unit of work with full regression coverage of existing Financials/Profile/Assumptions tests.
5. Phase D (House Purchase, Home Sale, Business Sale, Job Change, Major Medical Event) — only after the transaction refactor lands; these are precisely the events for which atomicity actually matters most.
6. Phase E (Retirement) — last, exactly as originally designed, and only after Phase D's transaction guarantees are proven under real multi-write events.
7. Phase F (frontend) — unchanged.

---

## GO / NO-GO DECISION

### **GO WITH MINOR CHANGES**

The architecture's core principle — orchestrate existing services, compute nothing new, reuse the live-computation model this codebase has proven four times over (ADR-001 → ADR-005 → Recommendation Engine v2 → Life Events) — is sound, is correctly applied event-by-event, and requires no redesign. Every one of the fifteen events is implementable against real, already-existing tables and service functions, with only two small, already-self-identified, additive schema gaps (a `business_loan` enum value, an `acquisition_type` distinction not built). ADR-001 is respected exactly. No calculation, recommendation, or notification logic is duplicated anywhere in the catalog.

It is not a clean GO because this validation found one Critical Blocker the design document's own atomicity claim does not survive contact with the actual codebase (§6), plus two smaller, concrete gaps in the family-domain reuse it assumed was complete (§5.3, §5.4). None of the three requires touching the architecture's shape — the fix for the transaction blocker is a small, well-precedented refactor of already-existing code (removing internal `commit()` calls in favor of the request-scoped session this codebase already uses successfully elsewhere), and the two family-domain gaps are small, additive guards belonging in the new orchestration layer, not in `family_service.py` itself. Implementation should proceed directly against the Implementation Order above, with the transaction refactor treated as a mandatory, explicitly-scheduled prerequisite to Phase D — not discovered mid-phase, and not deferred as an afterthought.
