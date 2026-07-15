# Product Consistency Review — Family Home Screen (Task 5) + Add Family Member Flows (Task 6)

**Date:** 2026-07-07 (Task 5 review), updated 2026-07-07 (Task 6 addendum below)
**Scope:** Compare Family Home / Add Family Member flows against Profile, Dashboard, Goals, and AI Copilot for contradictory data, duplicate summaries, deprecated terminology, and broken navigation.

---

## Family Home vs. Profile

Both read `GET /api/v1/family` via the same `api.getFamilyHome()` client function (Profile's usage added during PCA-2; Family Home reuses it, introducing no second implementation). Live-verified side by side for the same test account: both showed identical member counts, names, relationship labels, and completeness state. **No contradiction, no duplicate summary logic** — this was the exact failure mode PCA-2 fixed, and Task 5 was built to preserve that fix rather than reintroduce a second, independent household view.

## Family Home vs. Dashboard

Family Home does not read or display `plan_health_score`, net worth, or any goal-probability figure — it has no overlap with the main Dashboard's data at all. The two screens are complementary, not competing: Dashboard's "Plan health" widget (sidebar) is untouched by this task. No shared figure exists that could disagree.

## Family Home vs. Goals

Family Home's deferred "Upcoming family goals" section explicitly does not read from `/api/v1/goals` today (see `BlockerReport.md` — goal-to-member tagging is Task 8's scope) and makes no claim about goal data. No contradiction is possible because no goal data is displayed yet, honestly.

## Family Home vs. AI Copilot

No overlap — AI Copilot reads goal probabilities from stored `Goal` rows (confirmed in the PCA-3 investigation), unrelated to household/family data. No shared figure, no contradiction.

## Deprecated Terminology Check

Grepped every new/modified file (`app.family.tsx`, `app.family.index.tsx`, `app.family.add.tsx`, `app.family.members.$id.tsx`, `lib/family.ts`, `app-shell.tsx`) for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches. Family Home's data model is exclusively the certified `household_members`/`dependents` (Family) tables via `GET /api/v1/family`, never the deprecated `user_profiles` fields.

## Navigation Check

- Sidebar "Family" nav item added, correctly highlights active on `/app/family` and all its sub-routes (verified live).
- Mobile bottom nav restructured to `Dashboard · Goals · Family · Copilot · More`, with Reports/Profile/Settings reachable via "More" (verified live at 375px and 768px widths — both work, no dead ends).
- Every member card, and both Quick Action links, navigate to a real, rendering route (`/app/family/add`, `/app/family/members/:id`) — verified live after fixing a genuine routing bug (see `PR_REPORT.md`) where these initially resolved to blank/wrong content due to TanStack Router's automatic parent-layout nesting.
- No link in Family Home points to a route that 404s or renders nothing.

## Conclusion (Task 5)

No contradictory data, no duplicate summary logic, no deprecated terminology, no broken navigation. Family Home integrates cleanly with the rest of the product as it exists today, and is explicit (via the "Coming soon" section) about the parts of the product that don't exist yet rather than implying they do.

---

## Addendum — Task 6 (Add Family Member Flows)

### Add Family Member vs. Family Home

The add/edit forms write via `POST`/`PUT /api/v1/family/members[/{id}]`, and every successful save invalidates the `["family-home"]` query cache — live-verified: Family Home reflected each change (spouse completed, child completed, parent added) immediately on return navigation, with no stale data and no manual refresh needed.

### Deprecated Terminology / Duplicate Logic Check

Grepped `app.family.add.tsx`, `app.family.members.$id.tsx`, `components/family/FamilyMemberForm.tsx`, and the new `api.ts` additions for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches. Client-side field validation in `FamilyMemberForm.tsx` mirrors `backend/app/services/family_service.py`'s `validate_member_fields()` for UX purposes only (fail fast, clear message) — the server remains the sole real enforcement; no eligibility logic (SSY check) is duplicated client-side, confirmed by the callout's reason text coming verbatim from the API response.

### Audit Trail Check

Independently verified via a read-only database query that every mutation performed during the live walkthrough (household creation, two member updates, one member creation) wrote exactly the audit log row the certified backend service already produces (`household_created`, `family_member_updated` ×2, `family_member_added`) — no gaps, no duplicates, no new audit-logging code needed since Task 2/3's endpoints already handle this.

### Navigation Check

`/app/family/add` (both `?type=parent` and `?type=other`) and `/app/family/members/:id` (for spouse, child, and a self-guard case) all render correctly — the stub content Task 5 shipped is now fully replaced with working forms for every relationship type Task 6 covers. No broken links introduced.

### Conclusion (Task 6)

No contradictory data, no duplicated business/eligibility logic, no deprecated terminology, no broken navigation. The two stub destinations Task 5 intentionally left as placeholders are now real, and Family Home's data stays consistent with every change made through them.

---

## Addendum — Task 7 (Family Member Detail)

### Family Member Detail vs. Family Home

Removing a member via the detail page immediately updated Family Home's member list and household summary — live-verified (4 → 3 people, spouse gone from both the list and the breakdown). No stale state observed.

### Deprecated Terminology / Duplicate Logic Check

The one backend change this task required (`is_complete` on three existing response models) reuses `family_service.is_complete()` — the exact same function the Family Home list already called — rather than introducing a second completeness computation anywhere. Grepped the new/modified frontend file for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches.

### Identity Integrity Check

Live-verified and backed by two new automated tests: editing one child left its sibling completely untouched, and repeated edits of the same member never produced a duplicate row — confirmed via a direct database query showing exactly 4 member rows after all edits, matching the 4 distinct people actually created.

### Audit Trail Check

Independently verified via a read-only database query that the full sequence of actions performed (household creation, one member update, one member removal) wrote exactly the 3 corresponding audit log rows — no gaps, no duplicates.

### Navigation Check

Edit → Cancel returns to the same detail view. Remove → confirm → navigates back to Family Home. No broken links, no dead ends.

### Conclusion (Task 7)

No contradictory data, no duplicated logic (business or identity/completeness), no deprecated terminology, no broken navigation. The read-only detail view Task 6 deferred is now real and consistent with Family Home at every step.

---

## Addendum — Task 8 (Family Goal Tagging)

### Family Goals vs. Goals

`GET /family/goals` reads the caller's goals with the exact same filter/ordering `routers/goals.py`'s own `list_goals()` uses (`family_service.list_goals_with_tags` mirrors it, does not reimplement it independently) — live-verified the one goal created during onboarding appeared identically on both `/app/goals` and `/app/family/goals` (same name, target amount, probability). No contradiction possible since both read the same underlying rows.

### Family Goals vs. Family Member Detail (Task 7)

Tagging a goal on the Family Goals screen made it appear under "Goals involving [name]" on that member's detail page (Task 7) with zero changes to Task 7's code — that query was written against `goal_household_members` back in Task 2/7, ahead of Task 8 actually writing rows there. Live-verified: tagged a goal with the spouse on Family Goals, then opened the spouse's detail page directly and confirmed the goal appeared there immediately.

### Family Goals vs. Family Home

Family Home's "Upcoming family goals" Coming Soon card is now a real link to `/app/family/goals` — live-verified the click navigates correctly and the destination renders real data, not another placeholder.

### Goal Ownership Check

Confirmed via a direct database query that `goals.user_id` never changed across three separate tagging operations (tag both members, untag one, re-tag) — `goal_household_members` remains purely descriptive, never a second ownership record. No new "co-owner" concept exists anywhere in the schema or the API responses.

### Deprecated Terminology / Duplicate Logic Check

Grepped `app.family.goals.tsx` and the new backend files for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches. The household-membership validation in `family_service.set_goal_household_tags` reuses `get_or_create_household` (the same function every other Family endpoint uses) rather than a second household-scoping implementation.

### Audit Trail Check

Independently verified via a read-only database query that each save on the Family Goals screen wrote exactly one `family_goal_tag_changed` audit row — no gaps, no duplicates, no silent no-ops on the rejected cross-household case.

### Navigation Check

Family Home → Family Goals → tag/untag → Family Member Detail (Task 7) all interlink correctly with no dead ends. "+ Create a new goal" correctly routes to the existing, unmodified `/app/goals` flow rather than a duplicated goal-creation form.

### Conclusion (Task 8)

No contradictory data, no duplicated business/ownership/recommendation logic, no deprecated terminology, no broken navigation. Family Goals integrates cleanly with Goals (Task-agnostic, pre-existing), Family Member Detail (Task 7), and Family Home, and correctly reuses every certified piece it touches rather than reimplementing any of it.

---

## Addendum — Task 9 (Family Goals & Custom Inflation)

### Goals vs. Dashboard vs. Reports

Live-verified after setting a custom inflation rate on an education goal: Goals' detail panel, Dashboard, and Reports all showed the identical `100% current probability` / `100% likely` / `100%` figure — byte-identical, confirmed by reading each page's rendered text directly. No screen recomputes or diverges from what `calculate_goal_probability()` last persisted (unchanged by this task), exactly matching ADR-001's single-source-of-truth requirement.

### Goals vs. Family Member Detail (Task 7) vs. Family Goals (Task 8)

The education cost projection's SSY callout reuses the exact same `eligible_schemes` field and reason text Task 7's member-detail screen and Task 6's Add-Child flow already show — same wording, same icon, same visual treatment. No second SSY-eligibility copy was written for this task.

### Calculation Boundary Check

Confirmed via direct database query that `custom_inflation_rate` and `probability`/`on_track` are fully independent: setting the former never altered the latter, across the goal's full lifecycle (create → tag → set rate → re-verify). `goal_household_members` (Task 8) and `goals.custom_inflation_rate` (Task 9) are both purely descriptive/presentational — neither is a second ownership or calculation model.

### Deprecated Terminology / Duplicate Logic Check

Grepped `EducationPlanningSection.tsx` and the two modified backend files for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches. The future-cost projection formula is new (a simple, separate FV calculation, not present anywhere else in the codebase to duplicate) but is never fed into `calculate_goal_probability()` or any other stored figure.

### A Genuine Cross-Task Gap Found and Fixed

`GET /family/members/{id}` (Task 7) had never populated `eligible_schemes` — only Task 6's create/update responses did. This meant Task 7's own detail screen (which also displays `eligible_schemes` conceptually, via the same response model) was silently incomplete since it shipped, discovered only now because Task 9 was the first consumer to actually rely on that field from the GET path. Fixed with a minimal, narrowly-scoped addition mirroring the existing `dependent`-null-safety pattern already used elsewhere in the same function, backed by two new permanent tests.

### Navigation Check

No new route was introduced — the feature extends the existing goal-detail panel (`GoalSimPanel`), reachable exactly as it always was. No broken links, no new dead ends.

### Conclusion (Task 9)

No contradictory data, no duplicated calculation logic, no deprecated terminology, no broken navigation. Dashboard, Reports, and Goals were independently confirmed to show identical, unperturbed probabilities after this task's changes — the central requirement given this task sits directly adjacent to the Calculation Lifecycle (ADR-001).

---

## Addendum — Task 10 (Family Insurance)

### Insurance vs. Family Member Detail (Task 6/7)

The recommendation reads `has_own_insurance` exactly as captured by Task 6's Add Family Member form and displayed by Task 7's member detail — no second capture UI, no re-derivation. Live-verified: adding a parent with insurance status "No" immediately produced the recommendation on the next Family Insurance visit, with no manual refresh.

### Insurance vs. Calculation Lifecycle (ADR-001, Task 9)

Live-verified and backed by a permanent test (`test_calculation_lifecycle_untouched`): triggering the insurance recommendation never invokes `calculate_goal_probability()` and never changes a goal's stored `probability`/`on_track`. This task's read endpoint has no write side-effect on any table outside `health_policies`/`health_policy_coverage`.

### Insurance vs. Government Schemes (Task 3/6/11)

Confirmed no shared table, no shared evaluation function. `scheme_eligibility_service.py`'s `age_years()` (promoted to public) is reused for senior-citizen determination — pure date arithmetic, not scheme-evaluation logic — the only crossing point between the two domains, and it doesn't blur them.

### Avoiding a Stale Recommendation

Live-verified: adding a policy that covers the previously-flagged parent made the recommendation disappear on the very next load — no stale "you should get insurance for X" message persisted after X was actually insured. Confirmed via direct database query that the underlying `has_own_insurance` value (still `'no'`, unchanged) does not override the more current `health_policies` signal.

### Deprecated Terminology / Duplicate Logic Check

Grepped `app.family.insurance.tsx`, `family_insurance_service.py` for `marital_status`, `dependents` (profile field), `tax_rate` — zero matches. The base 80D figure is read once from `tax_sections` (reusing Task 1's existing seeded data), never re-declared as a second literal.

### Navigation Check

Family Home → Family Insurance → Add a policy / Edit coverage all interlink correctly. No broken links, no dead ends.

### Conclusion (Task 10)

No contradictory data, no duplicated calculation or recommendation logic, no deprecated terminology, no broken navigation, and no stale recommendation surfaced after the underlying facts changed.

---

## Addendum — Task 11 (Family Recommendations)

### Recommendations vs. Family Insurance (Task 10) and the eligibility engine (Task 3)

The aggregation layer never recomputes either source's figures or rule logic — live-verified: the insurance card on `/app/family/recommendations` cited the exact same ₹25,000/₹50,000 figures and the same why/why_now text the standalone `/app/family/insurance` screen shows for the same household member, because both read from the same `compute_insurance_recommendation()` call. No second, drifted copy of the insurance logic exists.

### "AI recommendations" renamed, not just relabeled

Family Home's Coming Soon card previously read "AI recommendations." This task's actual output is rule-based, calculation-lite logic — zero AI/ML involved — so the real link is titled "Family Recommendations," never "AI," to avoid misrepresenting what generates these suggestions. Grepped the new route and service for "AI"/"machine learning"/"GPT" — no matches.

### No false conflicts, verified live

Confirmed via live walkthrough (see `RecommendationConflictReview_Task11.md`'s live-verification addendum): a household with both an insurance-eligible parent and a scheme-eligible child showed both recommendations side by side with zero conflict entries — the two sources never contradict each other with the currently seeded data, and the UI never implies a tension that isn't there.

### Calculation Lifecycle (ADR-001)

`family_recommendations_service.py` imports neither `planning_service` nor any goal-related model — confirmed by grep, and backed by a permanent test (`test_calculation_lifecycle_untouched`) mirroring Task 10's.

### Navigation Check

Family Home → Family Recommendations → Back to Family all interlink correctly. No broken links.

### Conclusion (Task 11)

No contradictory data, no duplicated recommendation logic between the two underlying engines and the new aggregation layer, no misleading "AI" branding on rule-based logic, no false conflicts shown, no broken navigation.

---

## Addendum — Task 12 (Family Dashboard Integration)

### Dashboard vs. every source screen — the core consistency property, verified live

- **Feed vs. `/app/family/recommendations`:** byte-identical output from the same service call, enforced by a permanent test (`test_feed_identical_to_recommendations_endpoint`) and observed live (the Kamla Shah recommendation read word-for-word the same on the dashboard feed and the Insurance screen).
- **Parents card vs. insurance recommendation:** both consume the newly-extracted `family_insurance_service.uncovered_parents()` — live-verified that recording one policy cleared the card's warning AND removed the feed's recommendation on the same next load, with no intermediate state where one said "fixed" and the other said "act."
- **Coverage card vs. Insurance screen:** "1 of 3 people covered" derived from the same `list_policies_with_coverage()` data the Insurance screen renders — tapping the card lands on a screen showing the same one covered person.
- **Retirement card vs. Goals:** the persisted probability (3.9) read out verbatim; the card's "4%" is display rounding of the same number the Goals screen shows.
- **Emergency card vs. `/app` money dashboard:** `liquid_assets`/`monthly_expenses` passed through from the same `get_dashboard()` call — the "7.5 months covered" figure is arithmetically checkable against the money dashboard's own Liquid ($3,00,000) and Monthly expenses (₹40,000) stats displayed on the same visit.

### No parallel business logic

Grep-verified: `family_dashboard_service.py` imports no model directly except for type references via existing services, calls `calculate_goal_probability` nowhere, and contains no arithmetic beyond counting and min-by-date. The one piece of arithmetic the feature needed (months covered) lives on the frontend as display arithmetic, per Task 9's precedent.

### Calculation Lifecycle (ADR-001)

Live-verified: both goals' persisted probabilities byte-identical after many dashboard loads (21.2 / 3.9). Permanent test in place.

### Navigation Check

`/app` family card → Family Home; Parents/Coverage cards → Family Insurance; Education card → Family Goals; Retirement/Emergency cards → Goals; feed entries → Family Recommendations. All verified live or by route inspection; no dead ends.

### Conclusion (Task 12)

The dashboard never disagrees with any screen it summarizes — by construction (shared services, one extraction) and confirmed live across all five card-vs-source pairings. No duplicated logic, no persisted state, no stale warnings after user action.

---

## Addendum — Milestone 2.1-P1 (Government Schemes Screen)

### Schemes screen vs. Recommendations feed vs. Dashboard

Live-verified: the Schemes screen's "Eligible now" entry for SSY read byte-identical reason text to the Recommendations feed's scheme-sourced recommendation for the same person — both call `evaluate_household_eligibility()` directly with no caching layer between them, so they cannot drift. The Schemes screen legitimately shows *more* than the feed (all three buckets vs. only "eligible") — this is a scope difference, not a disagreement; the feed never claims to be exhaustive.

### No duplicated eligibility logic

The new `GET /family/schemes` endpoint is a single service call plus schema construction — confirmed via code review (`DesignReview_M2.1-P1.md`) and via a permanent test asserting reason-text identity with the Recommendations endpoint.

### Honest handling of unconfigured schemes and the self-member gap

6 of 9 seeded schemes have no eligibility rules configured and correctly read "criteria not yet configured" rather than a fabricated verdict — live-verified. The self-member eligibility gap (Task 3's own pre-existing, documented limitation — a user's own eligibility is never evaluated, only family members') is carried forward unchanged, not silently worked around or hidden.

### Navigation Check

Family Home → Government Schemes → Back to Family. No broken links. The "Government scheme eligibility" Coming Soon entry is removed now that the real screen exists.

### Conclusion (Milestone 2.1-P1)

No contradictory data between the new screen and any existing surface, no duplicated eligibility logic, honest handling of both known limitations (unconfigured schemes, self-member gap), no broken navigation. PCA-7 ("zero government-scheme information visible") is now substantively closed — the "Potentially Eligible" bucket, previously invisible everywhere in the product, has a real UI surface for the first time.
