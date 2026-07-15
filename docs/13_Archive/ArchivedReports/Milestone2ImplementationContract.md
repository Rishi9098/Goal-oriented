# Milestone 2 Implementation Contract — Family Financial Planning

**Date:** 2026-07-06
**Status:** Specification only. No code, no migrations, no APIs implemented. This document is the sole architectural authority for Milestone 2 implementation — an engineering team should not need to ask an architectural question this document doesn't already answer.
**Traces to:** `FamilyPlanningDesign.md` (approved UX), `UX_REVIEW.md` (approved, with its two required revisions incorporated throughout this contract), `DatabaseDesignReport.md`/`FoundationReconciliationReport.md` (certified schema), `GovernmentPolicyReport.md`/`FamilyHUFPlanningReport.md`/`CalculationEngineReport.md`/`PolicyEngineReport.md` (domain rules), `docs/ENGINEERING_CONSTITUTION.md`/`docs/PRODUCT_PRINCIPLES.md`/`docs/UX_PRINCIPLES.md` (standing rules every screen below is checked against).

---

## 0. Verified Blockers Requiring New Milestone-2-Owned Schema

Per instruction, the certified Foundation schema is not changed. Two gaps, both already flagged in `FutureCompatibilityAuditReport_v2.md`, require small, additive, **Milestone-2-owned** tables/columns — created in Milestone 2's own migration, not a retroactive change to Foundation's migrations 001–006. Both are specified here precisely so implementation doesn't have to make a design decision mid-build.

### 0.1 `goal_household_members` (new table)

**Why:** `FamilyPlanningDesign.md` Part 5 requires a goal to display "who this affects" and to list goals grouped by household member. `goals` remains single-`user_id`-owned (Finding E, deliberately not resolved at the Foundation level). This is a purely descriptive tagging table, not an ownership change — `goals.user_id` remains the sole owner of record for every purpose (tax attribution, contribution tracking, access control).

```sql
CREATE TABLE goal_household_members (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id               UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    household_member_id   UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (goal_id, household_member_id)
);
CREATE INDEX ix_goal_household_members_goal_id ON goal_household_members(goal_id);
CREATE INDEX ix_goal_household_members_household_member_id ON goal_household_members(household_member_id);
```

**Explicitly not a joint-ownership model** — see UX_REVIEW.md's required revision, Section 8 below (Family Goals screen) for the mandatory disclosure copy this table's data must be paired with.

### 0.2 `goals.custom_inflation_rate` (new nullable column on the existing `goals` table)

**Why:** `CalculationEngineReport.md` #10 established that a single flat inflation rate (`financial_assumptions.inflation_rate`) systematically understates education- and medical-category goals, which run 2.5-3x general inflation. Rather than a new table, this reuses the exact pattern `goals.risk_profile` already establishes (a per-goal override of an otherwise-global assumption).

```sql
ALTER TABLE goals ADD COLUMN custom_inflation_rate FLOAT NULL;
```

Nullable and additive: every existing goal gets `NULL`, meaning "use the global `financial_assumptions.inflation_rate` exactly as today" — zero behavior change for any goal that doesn't opt in.

### 0.3 `dependents.has_own_insurance` (new nullable column on the existing `dependents` table)

**Why:** discovered while specifying §10 (Family Insurance) below, not anticipated at the start of this document — an honest example of "verified blocker discovered during implementation planning," not a pre-existing known gap. The Family Insurance screen's entire recommendation (separate policy for a dependent parent, doubling the deduction) depends on knowing whether that parent already has their own coverage — captured during the Add Parent flow (§3-6) — but no field in the certified `dependents` table holds a yes/no/not-sure answer to this specific question. `dependent_type='elderly_parent'` identifies *who* the parent is; it says nothing about their insurance status.

```sql
ALTER TABLE dependents ADD COLUMN has_own_insurance VARCHAR(10) NULL;
-- 'yes' | 'no' | 'not_sure' | NULL (not yet asked / not applicable to this dependent_type)
```

**All three additions (§0.1-0.3) are the only schema changes this milestone requires.** Everything else (spouse/child/parent data, insurance, government-scheme eligibility, recommendations) reads and writes tables that already exist and are already certified.

---

## Shared Baselines (referenced by every screen below, not repeated per-screen)

### Standard Accessibility Baseline
Semantic HTML landmarks and heading levels (never a styled `<div>` standing in for a heading); every icon-only or color-only status indicator pairs with a text label (`UX_PRINCIPLES.md` #8); full keyboard operability with a visible focus ring on every interactive element; form fields associated with their label via `<label for>` and their help text via `aria-describedby`; `prefers-reduced-motion` respected on every animated element; minimum 4.5:1 text contrast; touch targets ≥ 44×44px on mobile viewports (320/768/1024/1440 per this project's own testing rules).

### Standard Security Baseline
Every endpoint requires a valid access-token bearer (existing `get_current_user` dependency, unchanged); every query scoped to `current_user.id` (directly, or via a household the user is confirmed a member of — see §per-screen ownership checks below, since Family introduces the first case in this codebase where a user can legitimately act on data that isn't directly their own `user_id`); no endpoint returns another household member's data unless the requesting user is confirmed to belong to the same household; all financial figures validated server-side with the same upper-bound pattern already established in `schemas/financials.py` (AUDIT.md #10); every mutation writes an `audit_logs` row (`action` in `family_member_added`, `family_member_updated`, `family_member_removed`, `family_goal_tag_changed`, `health_policy_created`, etc.).

### Standard Performance Baseline
Every list screen (Family Home, Family Goals, Family Insurance) paginates or, given realistic household sizes (2-8 members), simply loads in full with no pagination UI shown — pagination is explicitly **not** built for Milestone 2 given the bounded fan-out already confirmed safe in `DatabaseDesignReport.md`'s Scalability Review; revisit only if real usage data ever shows otherwise. Every aggregate calculation (family net worth, family cash flow) is computed server-side in one request, not assembled from N client-side calls. Optimistic UI is used for add/remove-member actions (per `UX_PRINCIPLES.md`'s "users always know what to do next" — an added family member should appear instantly, reconciled against the server response, with a rollback-and-toast on failure, matching this codebase's existing goal-creation pattern in `app.goals.tsx`).

---

## 1. Onboarding — Family Step (Revised)

### Purpose
Seed the household with minimal friction during account creation, per `FamilyPlanningDesign.md` Part 3's explicit decision to keep onboarding light and defer depth to the Family workspace. Incorporates **UX_REVIEW.md's required revision #1**: the children question must not silently under-register a multi-child household.

### User Story
As a new user creating my financial plan, I want to tell the app who's in my life in under 30 seconds, so that I get relevant recommendations later without filling out a census on day one.

### Business Rules
No financial calculation happens on this screen. The only rule: answering "Yes" to children requires a count (minimum 1), and the app creates exactly that many placeholder `household_members` rows (`relationship_type = 'child'`), each linked to an empty `dependents` row the user completes later. Answering "Yes" to spouse or parents creates exactly one placeholder row each (a household has at most one recorded spouse relationship-type row and, per `FamilyHUFPlanningReport.md`, at most two parent-type rows are the realistic common case, but the schema doesn't hard-limit this — no artificial cap is enforced here).

### Data Sources
**Writes:** `households` (created once, `created_by_user_id = current_user.id`, `name` defaulted to e.g. "My Household," editable later), `household_members` (one row for self with `relationship_type='self'`, plus one row per Yes answer — N rows for children, matching the entered count).
**Reads:** none (this is the first time this data is created for the user).

### API Contract
`POST /api/v1/family/onboarding-seed`
Request:
```json
{
  "has_spouse": true,
  "has_children": true,
  "children_count": 3,
  "has_dependent_parents": false
}
```
Response: `201 Created`, returns the created `Household` + all `HouseholdMember` rows (ids only needed for the Family Home screen's placeholder cards).
Validation: `children_count` required and `>= 1` only if `has_children` is `true`; rejected with `422` otherwise. Idempotency: this endpoint is called exactly once per user, at the end of onboarding's family step — if a household already exists for the user (re-entering onboarding after a partial completion), it returns the existing household unchanged (`200`) rather than duplicating rows.
Auth: existing bearer token from the in-progress registration session (same pattern as every other onboarding step's authenticated calls).

### UI Components
Three toggle/yes-no question groups; a numeric stepper (1-10, reasonable upper bound) that only renders when "children: yes" is selected; a single "Continue" primary action button (`UX_PRINCIPLES.md` #1); no cards, no tables, no charts on this screen.

### User Actions
Toggle each yes/no; adjust the children stepper; tap Continue. No back-navigation data loss — answers persist in the onboarding wizard's existing local state pattern (`onboarding.tsx`'s `useState`) until the final submit.

### Validation Rules
`children_count`: required only if `has_children=true`; integer, 1-10 inclusive (a count above 10 is vanishingly unlikely and more likely a fat-fingered input — the UI should confirm rather than silently accept). No other field is independently required; a user answering "No" to all three proceeds with just a "self" household member row, per `FamilyPlanningDesign.md`'s empty-state design (single-person household is a normal, complete state).

### Accessibility
Standard Baseline. The stepper is a real `<input type="number">` with `aria-label="Number of children"`, not a custom div-based counter — keyboard up/down arrows must work natively.

### Performance
Standard Baseline. Single API call, expected round-trip well under 500ms (row creation only, no calculation).

### Security
Standard Baseline. This is the one endpoint in Milestone 2 that creates a household rather than acting on an existing one — `created_by_user_id` is set server-side from the authenticated session, never accepted from the request body.

### Acceptance Criteria
- A user answering "children: yes, count: 3" has exactly 3 `household_members` rows with `relationship_type='child'` after onboarding completes.
- Re-running the onboarding flow for a user who already has a household does not create a duplicate household.
- A user answering "No" to all three questions completes onboarding with exactly one household member (self) and sees the Family Home empty state on first visit to `/app/family`.

---

## 2. Family Home (`/app/family`)

### Purpose
The single "building your family's financial profile" screen — a list of people, each showing completeness, per `FamilyPlanningDesign.md` Part 4.1. Benefits every persona with any household composition (married, family, senior-with-dependents per `UserPersonasReport.md`); for a single-professional persona, this screen's job is to make clear that adding anyone is optional, never pushed.

### User Story
As a user with a family, I want to see everyone in my household at a glance and know exactly who still needs details filled in, so that I never wonder whether the app "knows about" someone I already told it about.

### Business Rules
A household member is "Complete" once its relationship-type-specific required fields are filled (spouse: name + DOB; child: name + DOB; parent: name + relationship + insurance-status answer; other: name + relationship). No financial calculation on this screen — it's a status/navigation hub.

### Data Sources
**Reads:** `households` (one, via `created_by_user_id = current_user.id` OR membership — see ownership note below), `household_members` (all, `WHERE household_id = ? AND is_active = true`), `dependents` (joined, for child/parent completeness check).
**Writes:** none directly (all mutations happen on the Add/Detail screens).

**Ownership check (new pattern for this codebase):** a user may view a household if `households.created_by_user_id = current_user.id` **or** a `household_members` row exists with `household_id = this household AND user_id = current_user.id`. Milestone 2 ships with every household having exactly one adult creator (no shared-login multi-adult access yet — per `FamilyPlanningDesign.md`, the second adult, e.g. a spouse, is recorded as data, not given their own login/access this milestone) — so in practice this check simplifies to `created_by_user_id = current_user.id` for Milestone 2, but the query is written against the general rule so it doesn't need rewriting when a future milestone adds shared household access.

### API Contract
`GET /api/v1/family`
Response `200`:
```json
{
  "household": { "id": "...", "name": "My Household" },
  "members": [
    { "id": "...", "relationship_type": "self", "name": "You", "is_complete": true },
    { "id": "...", "relationship_type": "spouse", "name": "Priya", "is_complete": true },
    { "id": "...", "relationship_type": "child", "name": null, "is_complete": false }
  ]
}
```
`404` if the user has no household yet (should not happen post-onboarding, but a user who registered before Milestone 2 shipped has no household row — see Acceptance Criteria).
Auth: standard bearer.

### UI Components
Vertical list of cards (one per member); a dashed-border variant for incomplete placeholders with a "+ Add details" CTA; solid-card variant with a completeness checkmark for finished entries; two persistent "+ Add a parent" / "+ Add someone else" cards at the list's end (always visible, not conditional, so the user can always add more later — per `FamilyPlanningDesign.md` 4.1); empty state per Part 9.

### User Actions
Tap any card to navigate to that member's detail page (or directly into the Add flow if incomplete); tap "+ Add a parent" / "+ Add someone else" to start those flows.

### Validation Rules
N/A (read-only aggregation screen).

### Accessibility
Standard Baseline. The member list is a semantic `<ul>`/`<li>` structure; each card's completeness state is announced via visually-hidden text ("Priya, Spouse, complete") in addition to the checkmark icon.

### Performance
Standard Baseline. One request, one join across `household_members`+`dependents` — bounded by realistic household size (2-8 rows), no pagination.

### Security
Standard Baseline. 404 (not 403) for a user with no household — avoids confirming/denying existence of data that isn't theirs in a way that would matter here (there's nothing to leak; every user's household is 1:1 with their own account at this milestone), but returning "not found" rather than an empty list is more honest about the actual state (no household exists yet) than pretending an empty one does.

### Acceptance Criteria
- A user who completed onboarding after Milestone 2 shipped sees their pre-seeded members immediately.
- A user who registered before Milestone 2 shipped and visits `/app/family` for the first time sees a clear "Set up your family" entry point (a one-time backfill prompt, not a 404 error page) — **implementation note:** this requires a lazy-creation fallback (create an empty household + self-only member on first `/app/family` visit if none exists) rather than a hard 404, since a raw 404 would fail `UX_PRINCIPLES.md` #11 ("empty states are normal states, not apologies") for existing users. This supersedes the literal `404` response above for that specific case — the endpoint should lazily provision rather than error for an authenticated user with zero household rows.
- Tapping an incomplete placeholder navigates directly into that member's Add flow, not the (empty) detail page.

---

## 3–6. Add Family Member (Spouse / Child / Parent / Other) — one route family, four data shapes

### Purpose
Let the user add real depth about one person at a time, per `FamilyPlanningDesign.md` Part 4.2 — never a combined form. Directly serves the Married Couple, Family, and Senior-citizen-dependent personas.

### User Story
As a user, I want to tell the app about my spouse (or child, or parent) in a short, focused form that explains why each question matters, so that I never feel like I'm filling out a tax document.

### Business Rules (per relationship type)

**Spouse:** name + DOB required. DOB drives future retirement-timing and health-premium calculations (Milestone 4+, not this milestone) — the "why we ask" copy states this per the approved design.

**Child:** name + DOB required; gender optional, explicitly framed per **UX_REVIEW.md's required revision** — the softened copy ("this helps us find scholarships and schemes that might apply," not a mechanical scheme name-drop) is mandatory microcopy, not a suggestion. If gender = female and computed age < 10 (from DOB), the SSY inline callout renders immediately, citing `scheme_rates`/`scheme_eligibility_rules` for `code='SSY'` (live policy data, not a hardcoded string — per `docs/ENGINEERING_CONSTITUTION.md` Rule 2).

**Parent:** name + relationship (mother/father) + "own health insurance?" (yes/no/not-sure) required. A "No" or "Not sure" answer triggers the family-floater-vs-standalone-policy recommendation surfaced on the Family Insurance screen (§10), per `FamilyHUFPlanningReport.md`'s verified doubled-80D/123-deduction finding — this screen only captures the fact; the recommendation itself renders elsewhere.

**Other dependent:** name + relationship (free text) + optional DOB; no scheme logic attached (disabled dependents' specific tax provisions were explicitly flagged as unresearched in `FamilyHUFPlanningReport.md` — this milestone captures the person, not a tax treatment it hasn't verified yet).

### Data Sources
**Writes:** `household_members` (update the placeholder row created at onboarding, or insert a new row if added directly from Family Home's "+ Add" CTAs — both paths converge on the same upsert), `dependents` (insert/update, for child/parent/other; not created for spouse, since `dependents` per `DatabaseDesignReport.md` Group A models minors/elderly-dependents/disabled-dependents specifically, and a spouse is never a "dependent" in that schema sense).
**Reads:** `scheme_rates`/`scheme_eligibility_rules` for `code='SSY'` (child flow's inline eligibility check only).

### API Contract
`PUT /api/v1/family/members/{member_id}`
Request (child example):
```json
{
  "name": "Ananya",
  "date_of_birth": "2019-03-15",
  "gender": "female",
  "dependent_type": "minor_child",
  "is_tax_dependent": true
}
```
Response `200`: the updated member + dependent record, plus (child flow only) an `eligible_schemes` array if the SSY check passes:
```json
{ "member": {...}, "dependent": {...}, "eligible_schemes": [{"code": "SSY", "reason": "Daughter under 10"}] }
```
`POST /api/v1/family/members` — for adding a person not seeded at onboarding (e.g., "+ Add a parent" from Family Home when the user answered "No" at onboarding but later has a parent to add). Same request/response shape, `relationship_type` included in the body.
Validation: `name` required, 1-255 chars; `date_of_birth` must not be in the future; `gender` optional enum (`female`/`male`/`other`/unset); parent's insurance-status field is a required enum (`yes`/`no`/`not_sure`) when `relationship_type in ('parent')`.
Error responses: `422` for validation failures (field-level detail, matching this codebase's existing FastAPI/Pydantic error shape); `404` if `member_id` doesn't belong to the caller's household; `409` never applies here (upsert, not create-only).
Auth: standard bearer + household-ownership check (§Family Home).

### UI Components
Single-column form, one relationship-type-specific field set; inline "why we ask" text under each field (never a tooltip-only explanation — per `UX_PRINCIPLES.md` #3, the explanation is always visible, not hidden behind a hover/tap); the SSY callout card (child flow, conditional); a single "Save & continue" primary action.

### User Actions
Fill fields, toggle gender/insurance-status where applicable, tap Save & continue (returns to Family Home); back-navigation preserves entered data in the wizard's local state.

### Validation Rules
| Field | Required? | Rule |
|---|---|---|
| name | Yes (all types) | 1-255 chars, non-empty after trim |
| date_of_birth | Yes (spouse, child); optional (other) | Not in the future; not more than 130 years in the past (sanity bound) |
| gender | No (child only) | enum, unset is valid and does not block SSY re-evaluation later if added |
| relationship (parent) | Yes | "mother" \| "father" |
| insurance-status (parent) | Yes | "yes" \| "no" \| "not_sure" |
| relationship (other) | Yes | free text, 1-100 chars |

**Duplicate detection:** no hard uniqueness constraint (two children could plausibly share a name); the UI does not block a duplicate name, since false-positive blocking (twins with similar names, e.g.) would be worse than allowing it.

### Accessibility
Standard Baseline. The SSY callout is `role="status"` (announced to screen readers when it appears, since it's a dynamically-inserted, non-error informational panel) — not `role="alert"` (reserved for errors/warnings per WAI-ARIA authoring practices, and an eligibility callout is positive news, not a warning).

### Performance
Standard Baseline. The SSY eligibility check is a single indexed query (`scheme_eligibility_rules WHERE scheme_id = ?`) evaluated inline, not a separate round-trip — the save response includes the eligibility result directly.

### Security
Standard Baseline + household-ownership check on every `member_id` path parameter (a user must never be able to `PUT` another household's member by guessing a UUID — enforced by the ownership check joining through `household_members.household_id`).

### Acceptance Criteria
- Adding a daughter under 10 immediately surfaces the SSY callout, sourced from live `scheme_rates` data, not a hardcoded string in frontend code.
- Adding a daughter age 10 or older does not surface the callout.
- A parent marked "no own insurance" surfaces the separate-policy recommendation on the Family Insurance screen (§10) on the very next visit, without requiring a page refresh workaround.
- Attempting to `PUT` a `member_id` belonging to another user's household returns `404`.

---

## 7. Family Member Detail (`/app/family/members/:id`)

### Purpose
A single person's consolidated view — their goals, coverage, and edit access — per `FamilyPlanningDesign.md` Part 4.3. Serves every persona as the "drill into one person" screen reached from Family Home.

### User Story
As a user, I want to see everything the app knows about my spouse in one place, so that I can update her details or see what goals and coverage already involve her without hunting across the app.

### Business Rules
Read-only aggregation except for the Edit/Remove actions. "Goals involving [name]" reads `goal_household_members` (§0.1) joined to `goals`. "Remove from household" soft-deletes (`is_active=false`) the `household_members` row and cascades the same soft-delete intent to its `dependents` row if present — it does **not** hard-delete, consistent with `docs/ENGINEERING_CONSTITUTION.md` and this codebase's universal soft-delete convention.

### Data Sources
**Reads:** `household_members` + `dependents` (this person), `goal_household_members` joined to `goals` (their tagged goals), `health_policy_coverage` joined to `health_policies` (their coverage).
**Writes:** `household_members.is_active = false` (Remove action only); all other writes route through the Add/Edit flow (§3-6), reused here as an edit entry point, not duplicated.

### API Contract
`GET /api/v1/family/members/{member_id}` → full detail payload (member + dependent + tagged goals + coverage).
`DELETE /api/v1/family/members/{member_id}` → `204`, soft-delete only.
Auth: standard bearer + household-ownership check.

### UI Components
Header (name, relationship, DOB); "Goals involving X" list (empty state: "No goals tagged yet"); "Health coverage" summary (empty state: "Not yet covered under any policy — see Insurance"); Edit button (routes to §3-6's form, pre-filled); Remove button (opens a confirm dialog, per Standard Baseline's irreversible-action pattern already established elsewhere in this codebase, e.g. Settings' account-deletion flow).

### User Actions
Tap Edit (→ pre-filled Add/Edit form); tap Remove (→ confirm dialog → soft-delete → back to Family Home).

### Validation Rules
Remove requires explicit confirmation (typed confirmation not required here, unlike account deletion — removing a family member is reversible-in-spirit via re-adding, unlike deleting one's own account, so a lighter "Are you sure?" dialog is proportionate, not the heavier typed-DELETE pattern).

### Accessibility
Standard Baseline. The confirm dialog traps focus and returns focus to the Remove button on cancel, matching this codebase's existing dialog pattern (`GoalSimPanel.tsx`'s delete-confirmation flow).

### Performance
Standard Baseline. Single request, three small joins.

### Security
Standard Baseline + household-ownership check. Removing oneself ("self" relationship_type) is explicitly disallowed (`400`) — a household must always retain its creator.

### Acceptance Criteria
- Removing a household member soft-deletes, never hard-deletes (verifiable: the row still exists in the database with `is_active=false` after the action).
- A removed member's previously-tagged goals no longer show that member in "who this affects," but the goal itself is untouched.
- Attempting to remove "self" returns `400` with a clear error message.

---

## 8. Family Goals (`/app/family/goals`)

### Purpose
List every goal grouped by who it affects, and create new goals with the "who this affects" tag — the screen where **UX_REVIEW.md's required revision #2** (honest joint-goal disclosure) is mandatory, not optional.

### User Story
As a married user, I want to tag a goal as affecting both me and my spouse, while understanding clearly that it's still my account's goal, so that I'm never surprised later that her contributions aren't tracked separately.

### Business Rules
A goal's owner (`goals.user_id`) is unchanged and unchangeable from this screen — only the existing goal-creation flow (already shipped, `app.goals.tsx`) sets it, implicitly to the current user. This screen adds exactly one new capability: tagging a goal with 0-N household members via `goal_household_members`. **Mandatory disclosure text, verbatim intent (copy may be refined, meaning may not):** *"This goal belongs to your account. [Name] can see it if you share access, but their own contributions aren't tracked separately yet."* This text must render on every goal that has at least one tag, every time — not a one-time dismissible tooltip.

### Data Sources
**Reads:** `goals` (existing, `WHERE user_id = current_user.id`), `goal_household_members` joined to `household_members` (tags).
**Writes:** `goal_household_members` (insert/delete rows on tag/untag) — the existing `goals` table itself is untouched by this screen beyond what the pre-existing goal-creation flow already does.

### API Contract
`GET /api/v1/family/goals` → existing goals, each with a `tagged_members: [{id, name, relationship_type}]` array.
`PUT /api/v1/goals/{goal_id}/family-tags` — new endpoint, replaces the full tag set for a goal in one call:
```json
{ "household_member_ids": ["uuid1", "uuid2"] }
```
Response `200`: updated tag list. `404` if `goal_id` doesn't belong to the caller; `422` if any `household_member_id` doesn't belong to the caller's household.
Auth: standard bearer + goal-ownership check (existing pattern, unchanged) + household-membership check on each tagged id (new).

### UI Components
Goal list grouped by tagged member (a goal with 2 tags appears under both groups — this is a display grouping, not a data duplication); "who this affects" multi-select `<fieldset>` (checkbox group, per `FamilyPlanningDesign.md` Part 5 and the Accessibility Expert's review note); the mandatory disclosure banner on any tagged goal's detail view.

### User Actions
Create a goal (routes to the existing goal-creation flow, then prompts for tags); tag/untag members on an existing goal; view goals grouped by member.

### Validation Rules
`household_member_ids`: each must reference an active member of the caller's own household; empty array is valid (untagging everyone, goal reverts to showing only under "You").

### Accessibility
Standard Baseline. The multi-select is a real fieldset/legend with checkboxes (per `UX_REVIEW.md`'s Accessibility Expert finding), not a custom chip-picker.

### Performance
Standard Baseline. Tag list bounded by household size; no pagination needed.

### Security
Standard Baseline. The `422` check on `household_member_ids` prevents a user from tagging a goal with a UUID belonging to someone else's household member (which would otherwise leak that such an id exists, even if it couldn't be viewed).

### Acceptance Criteria
- Tagging a goal with a spouse displays the mandatory disclosure text on that goal's detail view.
- Untagging removes the display grouping but never deletes the underlying goal.
- Attempting to tag a goal with a household_member_id from a different household returns `422`, not a silent no-op.

---

## 9. Education Planning (goal-detail extension, education-category goals)

### Purpose
Give an education-category goal family-aware context: whose education, what the cost inflation assumption is, and whether a government scheme (SSY) already covers part of the plan — per `FamilyPlanningDesign.md` Part 8's recommendation example and the Family persona's explicit need in `UserPersonasReport.md`.

### User Story
As a parent, I want to see my daughter's college goal show a realistic, education-specific cost projection and know if a government scheme already helps, so that I'm not relying on a generic inflation number that understates the real cost.

### Business Rules
Only renders for goals where `category = 'education'`. If `custom_inflation_rate` (§0.2) is unset, the screen surfaces a one-time prompt: *"Education costs typically rise faster than general inflation — want to use a more accurate estimate?"* with a suggested rate (a specific verified figure, not invented — **implementation note: the exact education-cost-inflation multiplier was flagged as unverified in `CalculationEngineReport.md` #12; this milestone must not invent one. Either (a) source and verify a specific rate before this prompt ships, or (b) ship the prompt with a neutral, user-supplied rate only (no suggested default) until verified.** This is a real open item, not a rounding error — flagged here so it isn't silently guessed at during implementation.). If the goal is tagged (§8) with a daughter under 10, the SSY eligibility callout (§3-6) reappears here contextually, reusing the same live-data-sourced check, not a duplicated hardcoded copy.

### Data Sources
**Reads:** the tagged goal (`goals` + `goal_household_members`), `scheme_eligibility_rules`/`scheme_rates` for SSY, `financial_assumptions.inflation_rate` (fallback) or `goals.custom_inflation_rate` (override).
**Writes:** `goals.custom_inflation_rate` (only field this screen can set).

### API Contract
`PATCH /api/v1/goals/{goal_id}` — existing endpoint, extended with one new optional field, `custom_inflation_rate` (nullable float). No new endpoint required beyond §8's tagging endpoint.
Validation: `custom_inflation_rate`, if provided, must be `>= 0` and `<= 0.5` (50%), matching the existing `FinancialAssumptions.inflation_rate` field's own bound (`ge=0, le=0.5` per its Pydantic schema) for consistency.

### UI Components
Inflation-override prompt (dismissible, reappears only if the user hasn't set a value); cost-projection chart (reuses the existing `NetWorthProjection`-style chart component, re-themed for a single goal rather than total net worth); SSY callout (conditional).

### User Actions
Accept or dismiss the inflation-override prompt; enter a custom rate; view the projection.

### Validation Rules
See Business Rules — `custom_inflation_rate` bound `[0, 0.5]`.

### Accessibility
Standard Baseline. The projection chart provides a text-equivalent summary above or below it (e.g., "Projected cost in 11 years: ₹X, using a Y% annual inflation assumption") so the information isn't chart-only.

### Performance
Standard Baseline. No new calculation engine work required this milestone beyond applying whichever inflation rate is in scope to the existing FV formula (`CalculationEngineReport.md` #10) — the Monte Carlo re-run this would ideally trigger is a Calculation Engine milestone (4) concern; Milestone 2 surfaces the *inputs*, not a new simulation pipeline.

### Security
Standard Baseline + existing goal-ownership check (unchanged).

### Acceptance Criteria
- An education-category goal with no custom rate shows the standard, global inflation-based projection and the override prompt.
- Setting a custom rate persists and is reflected on next load.
- The SSY callout only appears when the goal is tagged with an eligible member, never unconditionally on every education goal.

---

## 10. Family Insurance (`/app/family/insurance`)

### Purpose
Surface the family-floater-vs-standalone-parent-policy recommendation concretely, and let the user record real policies — per `FamilyHUFPlanningReport.md`'s verified doubled-deduction finding and `FamilyPlanningDesign.md` Part 6's dashboard card.

### User Story
As a user with a dependent parent, I want to know whether a separate health policy for my parent actually saves me money, so that I can make an informed choice instead of guessing.

### Business Rules
If any parent-type household member has `insurance-status = 'no'` or `'not_sure'` (captured in §3-6), this screen surfaces a recommendation comparing (a) adding them to an existing/new family floater vs. (b) a standalone parent policy, citing the verified ₹25,000+₹25,000(or ₹50,000 senior)-doubled-deduction fact from `GovernmentPolicyReport.md`/`FamilyHUFPlanningReport.md`. This is a **calculation-lite** recommendation (a fixed, cited fact applied to the user's specific household composition), not a full Recommendation Engine (Milestone 5) output — it does not require `best_practice_rules`/`company_policies` (those remain empty per the Foundation Reconciliation) and should not be over-built to anticipate that milestone.

### Data Sources
**Reads:** `health_policies` + `health_policy_coverage` (existing coverage), `household_members` (parent insurance-status field, captured via the `dependents`-adjacent flow in §3-6 — **implementation note:** the parent's "own insurance?" answer needs a place to live; `dependents.dependent_type='elderly_parent'` exists but there's no dedicated field for this yes/no/not-sure answer in the certified schema. This is a **third small schema need**, missed in §0's initial two — add `dependents.has_own_insurance: VARCHAR(10) NULL` (`'yes'|'no'|'not_sure'`), same additive pattern as §0.1/0.2, owned by Milestone 2's migration, not Foundation.).
**Writes:** `health_policies`, `health_policy_coverage` (creating/editing a policy and its covered members).

### API Contract
`GET /api/v1/family/insurance` → existing policies + coverage + the computed recommendation (if applicable).
`POST /api/v1/family/insurance/policies` → create a `HealthPolicy` + initial `HealthPolicyCoverage` rows.
`PUT /api/v1/family/insurance/policies/{id}/coverage` → replace the covered-member set for a policy.
Validation: `sum_insured > 0`, `annual_premium >= 0`; `policy_type` enum (`family_floater`|`individual`|`senior_citizen_standalone`); at least one covered member required per policy.

### UI Components
Recommendation card (conditional, per Business Rules); policy list (cards, one per `HealthPolicy`, showing covered members' names); Add Policy form.

### User Actions
Dismiss or act on the recommendation (acting navigates to Add Policy, pre-selecting "standalone" if that's what was recommended); add/edit a policy; add/remove covered members from a policy.

### Validation Rules
Per Business Rules and API Contract above; a policy must cover at least one active household member.

### Accessibility
Standard Baseline.

### Performance
Standard Baseline.

### Security
Standard Baseline + household-ownership check on every covered `household_member_id`.

### Acceptance Criteria
- A household with a parent marked "no own insurance" sees the recommendation; a household with no such parent, or where all parents are marked "yes," does not.
- The recommendation's cited deduction figures match `GovernmentPolicyReport.md`'s verified numbers exactly (₹25,000 base, doubled for a separate parent policy, ₹50,000 if the parent is a senior citizen) — no invented or rounded-differently figures.
- Creating a policy with zero covered members is rejected with a clear validation message.

---

## 11. Family Government Schemes (`/app/family/schemes`)

### Purpose
Personalize the entire scheme catalog against the household's actual composition — Eligible / Potentially Eligible / Not Eligible, never a flat list — per `FamilyPlanningDesign.md` Part 7 and `docs/PRODUCT_PRINCIPLES.md` #6.

### User Story
As a user, I want to see only the government schemes that actually apply to my family, with a plain-language reason each one does, so that I don't have to research nine schemes myself.

### Business Rules
For each `scheme` in the certified `schemes` table, evaluate its `scheme_eligibility_rules` against every household member's recorded data (age derived from `date_of_birth`, `relationship_type`, and — where relevant — the user's own tax-filing status from `user_profiles`/`income_sources`). A scheme with `status='closed_to_new'` (e.g., PMVVY) is **never** shown in the Eligible or Potentially Eligible buckets regardless of rule match — this is a hard, non-negotiable filter per `docs/ENGINEERING_CONSTITUTION.md`'s own Rule 2 illustration and the PMVVY lesson from `GovernmentPolicyReport.md`. Rule evaluation logic (parsing `scheme_eligibility_rules.value` by `rule_type`) is a **Government Policy Engine (Milestone 3)** concern in its full generality; Milestone 2 implements only the specific rule types already proven necessary by the seeded data (`min_age`, `max_age`, `residency_status` — see `backend/scripts/seed_policy_data.py`) and explicitly does not attempt a fully generic rule interpreter ahead of need, per `docs/ENGINEERING_CONSTITUTION.md` Rule 7.

### Data Sources
**Reads:** `schemes`, `scheme_rates`, `scheme_eligibility_rules` (all certified Foundation data), `household_members`+`dependents` (for age/relationship facts).
**Writes:** none — this screen is read-only.

### API Contract
`GET /api/v1/family/schemes` → three buckets:
```json
{
  "eligible": [{"scheme_code": "SSY", "member_name": "Ananya", "reason": "She's 7 — this scheme is only available for girls under 10."}],
  "potentially_eligible": [{"scheme_code": "SCSS", "member_name": "Mother", "reason": "She turns 60 next year and would qualify."}],
  "not_eligible": [{"scheme_code": "APY", "reason": "..."}]
}
```
Auth: standard bearer.

### UI Components
Three sections (Eligible expanded by default, Potentially Eligible expanded, Not Eligible collapsed behind a "Show N more" disclosure per `FamilyPlanningDesign.md` Part 7); each item a card with scheme name, affected member, and plain-language reason; "Learn more" link (expands the full scheme profile inline, reusing citation data from `policy_citations`).

### User Actions
Expand/collapse the Not Eligible section; tap "Learn more" on any scheme.

### Validation Rules
N/A (read-only).

### Accessibility
Standard Baseline. The collapsed "Not Eligible" section is a native `<details>`/`<summary>` element or an ARIA-compliant disclosure widget — never a purely visual collapse with no accessible expanded/collapsed state announced.

### Performance
Standard Baseline. Rule evaluation is a small, in-memory computation over already-fetched rows (household size × scheme count is a tiny cross-product, e.g., 5 members × 9 schemes = 45 rule checks) — no risk of this being a slow endpoint.

### Security
Standard Baseline. No PII beyond what the user already entered is exposed; scheme data itself is non-sensitive reference data.

### Acceptance Criteria
- PMVVY never appears in Eligible or Potentially Eligible for any household composition.
- A household with a daughter under 10 sees SSY in Eligible with the correct, live-sourced interest rate mentioned if expanded.
- A household with no members over 55 sees SCSS in Not Eligible (collapsed), not Potentially Eligible.

---

## 12. Family Dashboard (`/app/family` summary + `/app` card)

### Purpose
The "financial command center" view for the household — six single-question cards plus a recommendations feed, per `FamilyPlanningDesign.md` Part 6.

### User Story
As a user, I want one screen that answers "who depends on me, and are we okay," so that I don't have to mentally assemble that picture from six different app sections myself.

### Business Rules
Six cards, each answering exactly one question (per `UX_PRINCIPLES.md` #4): **Who depends on me?** (count of dependents by type); **Education costs ahead** (nearest education-category goal's target date + tagged member); **Insurance coverage** (N of M household members covered by any policy); **Parents** (any parent-type member with `has_own_insurance != 'yes'`, surfaced as a warning state); **Retirement readiness** (existing `plan_health_score`-adjacent figure, reused, not recalculated); **Emergency readiness** (existing emergency-fund-months calculation, reused). The Recommendations feed below the cards surfaces the Insurance (§10) and Schemes (§11) recommendations already computed elsewhere on this screen — **not a new recommendation type**, a consolidated feed of what those two screens already produce, avoiding duplicate logic per `docs/ENGINEERING_CONSTITUTION.md`.

### Data Sources
**Reads:** aggregates across `household_members`, `dependents`, `goals` (via `goal_household_members`), `health_policies`/`health_policy_coverage`, the existing dashboard's plan-health and emergency-fund figures (reused via the existing `planning_service.get_dashboard()` call, not reimplemented).
**Writes:** none.

### API Contract
`GET /api/v1/family/dashboard` → the six card payloads + a `recommendations` array (each item tagged with its source screen: `insurance` | `schemes`).
Auth: standard bearer.

### UI Components
Six-card grid (matching the existing dashboard's `Stat`/`StatSkeleton` component pattern, reused, not reinvented); recommendation cards below, matching `FamilyPlanningDesign.md` Part 8's format exactly (reason, current/projected numbers, confidence, alternatives — even though full confidence-scoring/citation infrastructure is Milestone 5's job, this milestone's two recommendation *sources* — Insurance and Schemes — already have enough concrete, cited data to populate this format honestly without needing the full Recommendation Engine).

### User Actions
Tap any card to navigate to its source screen (Insurance card → §10, Schemes-derived recommendations → §11, Education card → the relevant goal's §9 view).

### Validation Rules
N/A (read-only).

### Accessibility
Standard Baseline. Each card is a `<button>` or a properly-labeled link, not a bare clickable `<div>` (an existing, already-flagged-elsewhere pattern this codebase should apply consistently).

### Performance
Standard Baseline. One aggregate request; reuses existing dashboard computation rather than duplicating it, keeping this endpoint's cost close to the existing `/api/v1/dashboard`'s already-acceptable cost.

### Security
Standard Baseline.

### Acceptance Criteria
- Every card's number changes correctly and immediately (next load, not requiring a manual refresh workaround) after a relevant action elsewhere (e.g., adding a dependent parent with no insurance updates the "Parents" card to a warning state).
- The Recommendations feed never shows a recommendation whose source screen (Insurance/Schemes) wouldn't independently justify it — no orphaned or stale recommendation text.
