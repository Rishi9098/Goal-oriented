# Product Consistency Audit

**Date:** 2026-07-06
**Last updated:** 2026-07-07 — PCA-1, PCA-2, and PCA-3 (all three Critical findings) resolved during the Stabilization Sprint; see `PROJECT_STATE.md`'s Stabilization Sprint section and `PR_REPORT.md` for each fix record. This document's original findings are left otherwise unmodified below so the audit remains a historical record, not a moving target.
**Method:** Full application walkthrough as a first-time Indian user (continuing from `FIRST_TIME_USER_REVIEW.md`), across every screen — Onboarding, Dashboard, Goals, Profile, Reports, AI Copilot, Settings — combined with targeted code verification to establish exact root causes (this task, unlike the prior first-time-user review, does not restrict code inspection). Every finding below is either directly observed in the running UI or confirmed against the actual source file and line — nothing is speculative.
**Scope:** Audit only. No code changed. No new features implemented.

---

## Issue Index

| ID | Title | Severity | Category(ies) | Status |
|---|---|---|---|---|
| PCA-1 | Onboarding promises a "Family" destination that does not exist | Critical | 3, 8, 9 | ✅ Resolved 2026-07-07 |
| PCA-2 | Profile's "Household" field contradicts the family data the user just entered | Critical | 1, 2, 9, 14, 15 | ✅ Resolved 2026-07-07 |
| PCA-3 | Goal success probability changes depending on which screen was visited last | Critical | 2, 9, 13, 14 | ✅ Resolved 2026-07-07 |
| PCA-4 | U.S.-only financial account types shown to every user regardless of country | High | 4, 11 | Open |
| PCA-5 | Currency symbol never follows the selected country | High | 5 | Open |
| PCA-6 | Onboarding's flat "Tax Rate" field bypasses the certified tax-slab engine | High | 6, 14, 15 | Open |
| PCA-7 | Zero government-scheme information visible anywhere in the product | Medium | 7, 10 | Open |
| PCA-8 | AI Copilot's fallback answer never cites the actual number it's talking about | Medium | 9, 10, 11 | Open |
| PCA-9 | "Linked accounts via Plaid" advertises a feature that cannot work for Indian banks | Medium | 3, 4 | Open |
| PCA-10 | Plan health score shown with no explanation anywhere in the product | Medium | 10, 11 | Open |
| PCA-11 | Net Worth Projection card's headline number contradicts its own chart | Medium/High | 1, 12 | Open |
| PCA-12 | Plan health duplicated across three surfaces with no shared fetch, can disagree | Medium | 2, 13 | Open |
| PCA-13 | Delete-account copy is internally contradictory | Low | 9 | Open |
| PCA-14 | Two competing, unlabeled primary CTAs on the landing page | Low | 8 | Open |
| PCA-15 | Children-count placeholder looks like a real value, causes an avoidable form error | Low/Medium | 8, 11 | Open |
| PCA-16 | Financial jargon used throughout with no glossary or inline explanation | Medium | 11 | Open |

---

## PCA-1 — Onboarding promises a "Family" destination that does not exist

**Status: ✅ Resolved 2026-07-07.** Fixed during the Stabilization Sprint by removing the specific "Family" destination reference from the onboarding copy (a scope-appropriate fix, since building the actual Family Home screen would be new-feature work, forbidden during the sprint). Full record: `PROJECT_STATE.md`'s Stabilization Sprint section, `PR_REPORT.md`. The findings below are preserved as originally written, for the historical record.

**Severity:** Critical
**Evidence:** The onboarding Family step's own copy states: *"you can add full details anytime from Family"* and, for children specifically, *"You'll be able to add each child's name and details afterward in Family."* The application's actual navigation (`code/src/components/app-shell.tsx:17-24`) is: `Dashboard, Goals, AI Copilot, Reports, Profile, Settings`. There is no "Family" entry, route, or screen anywhere in the running application.
**Root cause:** Milestone 2 Task 4 (the onboarding Family step) shipped ahead of Task 5 (Family Home screen) and Tasks 6-12, per the approved `ImplementationChecklist.md`'s "one feature at a time" sequencing. The copy was written referencing the *planned* destination, which is correct per the approved design (`FamilyPlanningDesign.md`) but is currently a dead reference in the shipped product.
**User impact:** A first-time user is told, twice, in the very screen that asks the most personal questions in the whole flow, that they can act on this later — and then cannot find where. This is the single clearest broken promise in the product today.
**Recommended fix:** Not a code fix — a sequencing fact. Resolves automatically once Milestone 2 Task 5 (Family Home) ships and is added to the nav. Until then, this should be tracked as a known, temporary, and now-documented gap, not fixed in isolation (fixing the copy to remove the promise would be a worse regression once Task 5 ships days later).
**Owning milestone:** Milestone 2, Task 5 (already the next approved task).

---

## PCA-2 — Profile's "Household" field contradicts the family data the user just entered

**Status: ✅ Resolved 2026-07-07.** Investigation (`DataSourceMigrationReport.md`) found the problem extended to the write side too — saving the Profile form also wrote to the deprecated fields via a regex-parsed canned dropdown. Fixed by sourcing the Household display from the certified `GET /api/v1/family` endpoint (read-only for this sprint) and removing both the read and write dependency on the deprecated fields entirely. Full record: `PROJECT_STATE.md`, `PR_REPORT.md`. Findings below preserved for the historical record.

**Severity:** Critical
**Evidence:** Live walkthrough: answered Yes/Yes(1 child)/Yes to spouse/children/dependent-parents during onboarding. Profile page's "Household" field subsequently reads **"2 adults"** — no child, no parent. Root-caused in code: `code/src/routes/app.profile.tsx:48-58`, function `householdFromProfile(maritalStatus, dependents)`, called at line 77 as `householdFromProfile(profile?.marital_status ?? null, profile?.dependents ?? 0)`.
**Root cause:** `householdFromProfile` reads exclusively from `user_profiles.marital_status`/`dependents` — the exact two fields the Foundation Reconciliation (2026-07-06) marked deprecated in favor of the new `household_members`/`dependents` entities. Milestone 2 Task 4 correctly stopped *writing* to these deprecated fields (per its own scope), but nothing reads the *new* household data on the Profile page instead — so `marital_status` stays `null` and `dependents` stays `0` for every user who onboards through the new flow, and the function falls through to its "2 adults" default branch regardless of what the user actually entered.
**User impact:** This is precisely the failure mode `docs/ENGINEERING_CONSTITUTION.md` and the Foundation Reconciliation's own decision log warned about: two representations of the same fact, one now silently wrong. A user who told the product about a spouse, a child, and a dependent parent sees a summary that describes none of them. This is the most damaging kind of inconsistency for a financial product specifically — it's not a cosmetic bug, it's the product visibly not knowing its own data.
**Recommended fix:** Point `app.profile.tsx`'s Household display at the real household data (`GET /api/v1/family`, shipped in Milestone 2 Task 2) instead of the deprecated profile fields. This is a small, scoped frontend change, not a new feature — the backend endpoint already exists and is tested.
**Owning milestone:** Milestone 2 (a follow-up task on top of Task 5, since it needs the Family Home screen's data-fetching pattern to exist first — or can be done standalone as a small Profile-page fix).

---

## PCA-3 — Goal success probability changes depending on which screen was visited last

**Status: ✅ Resolved 2026-07-07.** Investigation (`MonteCarloConsistencyReport.md`) traced the full execution path and produced a decision record (`ArchitectureDecisionRecord.md`, ADR-001) before any code changed, per this finding's special pre-implementation rule. Fixed by establishing and enforcing a new architectural rule — read operations never perform or persist financial calculations — with Monte Carlo execution centralized behind the goal's actual inputs changing (create/update) instead of behind any page view. Full record: `PROJECT_STATE.md`, `PR_REPORT.md`. Findings below preserved for the historical record.

**Severity:** Critical
**Evidence:** Live walkthrough: the "Retirement corpus" goal showed **"3.8% Monte Carlo"** on the Goals page and **"5%"** on the Reports page, for the same goal, within the same session, without the user changing anything. Root-caused in code:
- `backend/app/services/planning_service.py:18-45` (`refresh_goal_probabilities`) re-runs a fresh Monte Carlo simulation for every active goal and **persists the result** (`goal.probability = round(prob, 1)`, `session.add(goal)`) every single time it's called.
- `backend/app/services/planning_service.py:113` (`get_dashboard`) calls `refresh_goal_probabilities` on every Dashboard load.
- `backend/app/routers/reports.py:25` calls `get_dashboard` again on every Reports load — a second independent recomputation.
- `MONTE_CARLO_SEED` is blank in this environment's `.env` (confirmed), so each recomputation uses fresh, unseeded randomness — there is no reason to expect two runs to agree.
- `GET /goals` (the Goals page's data source) does **not** call `refresh_goal_probabilities` — it just returns whatever was last stored, which could be from goal creation, or from whichever of Dashboard/Reports was visited most recently.
**Root cause:** A read-only page view (Dashboard, and transitively Reports) has a **write side effect** on core financial data — the stored success probability — using non-deterministic simulation. This violates this project's own Engineering Rule ("Every calculation has ONE source") at a structural level: there effectively is no single stored truth for a goal's probability, only whatever the last viewer happened to trigger.
**User impact:** For a financial planning product specifically, a number that changes every time you look at a different page is close to the worst possible trust signal — worse than being wrong consistently, because the user can't even tell which number (if either) to believe, and reloading either page could change it again.
**Recommended fix:** Decide once, explicitly, whether probability recomputation should be (a) triggered only on goal create/update (already done) and never again on a passive page view, or (b) recomputed on view but cached with a stable seed per goal-state so repeated views agree. Either fix removes the write-on-read side effect from `get_dashboard`. This is a real engineering decision, not a copy fix — flagging it here rather than silently resolving it.
**Owning milestone:** Milestone 4 (Calculation Engine) — this is squarely a Monte Carlo engine architecture question, and Milestone 4 is this roadmap's designated owner of calculation correctness. Recommend treating as a priority item within that milestone rather than a general bug-tracker entry, given the severity.

---

## PCA-4 — U.S.-only financial account types shown to every user regardless of country

**Severity:** High
**Evidence:** Onboarding's Investments step subtitle reads: *"Brokerage accounts, 401(k), IRA, and other investment holdings."* (`code/src/components/onboarding/list-steps.tsx`). 401(k) and IRA are U.S.-specific tax-advantaged account types with no Indian equivalent. Selecting India as the onboarding country (Personal Info step) does not change this copy.
**Root cause:** The onboarding wizard's financial-category copy was written once, generically, and never branched by country — despite the backend's entire Government Policy Engine (`schemes`, `scheme_rates`, `scheme_eligibility_rules`, seeded with PPF/EPF/NPS/SSY/SCSS/etc.) being built specifically for India. The frontend and backend have diverged on which country this product is for.
**User impact:** An Indian user is asked to categorize their investments using account types that don't exist in their country, with no Indian equivalent offered (no PPF, EPF, NPS mentioned anywhere in this step). This actively signals the product wasn't built for them, directly undercutting the country-specific research and backend work already completed.
**Recommended fix:** Replace or branch the investment-category copy and dropdown options to reflect India-specific instruments (PPF, EPF, NPS, mutual funds, fixed deposits, etc.), sourced from the same verified data already in `GovernmentPolicyReport.md`/`schemes`.
**Owning milestone:** Milestone 4 (Calculation Engine) or Milestone 2/3, whichever is designated to own onboarding-copy localization — flagging that no milestone in the current roadmap explicitly owns "make onboarding India-specific," which is itself a gap worth a product decision.

---

## PCA-5 — Currency symbol never follows the selected country

**Severity:** High
**Evidence:** Every amount field across the entire onboarding wizard and app (Income, Expenses, Cash & savings, Investments, Debts, Goal target amount, Dashboard, Reports) is labeled with **"$"**. Selecting India as the onboarding country does not change any of these. Confirmed via `grep` — `code/src/components/onboarding/wizard-steps.tsx`, `list-steps.tsx`, `GoalSimPanel.tsx`, and `app.goals.tsx` all hardcode `($)` in their field labels.
**Root cause:** Currency display was never made a function of the user's selected country — it's a hardcoded literal in every component that shows a monetary field, not a shared, country-aware formatting utility.
**User impact:** A user enters real rupee figures into fields explicitly labeled in dollars, on every single screen, for the entire session. This is the most visible, most repeated inconsistency in the whole product — it appears on nearly every screen a user will ever see.
**Recommended fix:** Introduce a single shared currency-formatting utility keyed off the user's profile country (or a dedicated currency preference), and route every amount label/value display through it. This is a moderate-sized, cross-cutting frontend change, not a quick patch, given how many components hardcode the symbol.
**Owning milestone:** Milestone 4 (Calculation Engine) is the natural technical owner (it already owns India-specific financial calculations), though this could also be scoped as its own small cross-cutting localization effort given how many files it touches.

---

## PCA-6 — Onboarding's flat "Tax Rate" field bypasses the certified tax-slab engine

**Severity:** High
**Evidence:** Onboarding's Assumptions step (10/10) shows a bare **"Tax Rate (%)"** field defaulting to **22**, with no explanation, no mention of old vs. new tax regime, and no connection visible to the user at all. Root-caused in code: this field maps directly to `financial_assumptions.tax_rate` (`backend/app/models/assumptions.py`), which carries this exact inline comment (added in the Foundation Reconciliation, 2026-07-06): *"DEPRECATED... a flat, single-rate approximation that predates the versioned tax_regimes/tax_slabs engine... Confirmed unread by any service/router... do NOT wire new logic to this field."*
**Root cause:** The onboarding wizard was built before (and has not been updated since) the certified `tax_regimes`/`tax_slabs` engine was seeded with real Indian old-regime/new-regime data (Milestone 1). The UI still collects and displays a field the backend has already, formally, marked as superseded and unused.
**User impact:** The user is asked to guess or confirm a number ("22%") that the system doesn't actually use for anything, while the real, verified, India-specific tax calculation engine sits fully built and silent. This is a direct, visible instance of deprecated logic still driving a user-facing screen.
**Recommended fix:** Remove or replace the onboarding Tax Rate field once Tax Planning (Milestone 4) has a real regime-election UI to replace it with — do not simply delete it without a replacement, since some downstream code may still read the field even if it's not load-bearing for tax computation.
**Owning milestone:** Milestone 4 (Calculation Engine / Tax Planning).

---

## PCA-7 — Zero government-scheme information visible anywhere in the product

**Severity:** Medium
**Evidence:** `grep` across the entire frontend (`code/src/`) for any of PPF, SSY, EPF, NPS, SCSS, "Sukanya," "Provident" returns **zero matches**. The backend has a fully seeded, tested, verified Government Policy Engine (9 schemes, rates, and — as of Milestone 2 Task 3 — eligibility rules) that is completely invisible to any user today.
**Root cause:** Milestone 2's Family Government Schemes screen (Task 11) and Milestone 3 (Government Policy Engine logic/lookup UI) have not been built yet — this is expected sequencing, not a defect, but worth stating plainly since a first-time user experiences it as "this product doesn't know about Indian schemes" when in fact the backend already does.
**User impact:** None of the product's most distinctive, India-specific research and backend investment is visible to a user yet. Not a trust problem (nothing is wrong), but a missed-value problem worth tracking explicitly so it isn't mistaken for "not built" when it's actually "built but not surfaced."
**Recommended fix:** N/A — this resolves as scheduled.
**Owning milestone:** Milestone 2, Task 11 (Family Government Schemes screen), which already calls the certified `evaluate_household_eligibility()` service built in Task 3.

---

## PCA-8 — AI Copilot's fallback answer never cites the actual number it's talking about

**Severity:** Medium
**Evidence:** Asking "Review my goal probabilities" returned: *"Based on your plan, Retirement corpus is below 70% confidence. I can run an optimization..."* — never stating the actual stored probability (3.8% or 5%, whichever was current). Root-caused in code: `backend/app/routers/copilot.py:61-68`, `_fallback_response()`, explicitly documented as *"Rule-based fallback when no OpenAI key is configured"* — confirmed `OPENAI_API_KEY=` is blank in this environment.
**Root cause:** The documented, deliberate no-API-key fallback path is a template that names the goal and a threshold ("below 70%") but doesn't interpolate the specific number, unlike the Goals/Reports pages which do show a specific (if inconsistent, see PCA-3) figure.
**User impact:** A tool that introduces itself as "your AI financial planner" and is asked specifically to "review probabilities" gives a vaguer answer than the static dashboard already provides. This is a real explainability gap in the *current, deployed* fallback experience — not a defect in the eventual GPT-backed path, but a gap in what most evaluators/testers will actually see, since this environment has no API key configured.
**Recommended fix:** Have the fallback template interpolate the actual stored `goal.probability` value, matching the specificity already shown elsewhere in the product.
**Owning milestone:** Milestone 6 (AI Financial Advisor) — though this is a small, self-contained fix to existing fallback code, not new scope.

---

## PCA-9 — "Linked accounts via Plaid" advertises a feature that cannot work for Indian banks

**Severity:** Medium
**Evidence:** Settings page: *"Linked accounts — Institution connections via Plaid — coming in a future release."* Plaid does not support Indian banks (a fact already established in this project's own research — `FeatureGapAnalysisReport.md`/`PrivateProductReport.md` evaluated and scoped account aggregation for India specifically, and Plaid was never the chosen vendor for that reason).
**Root cause:** This Settings copy appears to be inherited from a generic/template SaaS settings page rather than written against this product's own research findings.
**User impact:** A specific, named promise ("coming in a future release") that references a vendor incompatible with the product's own target market — the kind of detail that erodes trust specifically with the more financially sophisticated segment of users who would recognize the name.
**Recommended fix:** Update the copy to either name the actual planned account-aggregation approach for India (if one is decided) or use vendor-neutral language ("Institution connections — coming in a future release") until that decision is made.
**Owning milestone:** No milestone in the current 8-milestone roadmap explicitly owns account aggregation — this needs a product decision before it can be assigned. Flagging rather than guessing.

---

## PCA-10 — Plan health score shown with no explanation anywhere in the product

**Severity:** Medium
**Evidence:** "Plan health: 4/100" (later "5/100") appears in the persistent sidebar widget, the Dashboard, and the Reports page. No screen — including Reports, which is otherwise the most detail-dense page — explains what the score measures, what a good score looks like, or what specifically to do to improve it beyond generic dashboard suggestions.
**Root cause:** `compute_plan_health()` (`backend/app/services/planning_service.py`) is a real, computed metric, but its methodology is never surfaced to the user anywhere in the UI.
**User impact:** A prominent, alarming-looking number ("4 out of 100") shown immediately after onboarding, with zero context, reads as bad news the user has no way to interpret or act on — directly working against `PRODUCT_PRINCIPLES.md`'s "reduce financial anxiety" goal.
**Recommended fix:** Add a plain-language explanation (tooltip, expandable detail, or dedicated section) of what feeds the plan health score and what would move it.
**Owning milestone:** Milestone 5 (Recommendation Engine) or Milestone 6 (AI Advisor) — whichever is designated to own "explain this number to the user."

---

## PCA-11 — Net Worth Projection card's headline number contradicts its own chart

**Severity:** Medium/High
**Evidence:** Dashboard's "Net Worth Projection" card showed a headline figure of **"$0"** directly above a chart whose curve clearly rises to roughly $120M over the displayed horizon.
**Root cause:** Not confirmed from the UI alone whether this is a loading-state race (headline number renders before the chart's own async data resolves) or a genuine calculation mismatch — flagging as observed, unresolved.
**User impact:** Looks like a broken page at first glance — the single most "is this app buggy" moment in the whole walkthrough.
**Recommended fix:** Investigate whether the headline figure and the chart data come from the same fetch/state, and ensure they render in sync (e.g., both show a loading skeleton until both are ready, rather than one populating before the other).
**Owning milestone:** Not milestone-gated — recommend as an immediate, standalone bug investigation, independent of the Family Planning roadmap.

---

## PCA-12 — Plan health duplicated across three surfaces with no shared fetch, can disagree

**Severity:** Medium
**Evidence:** The sidebar widget (`app-shell.tsx`), the Dashboard card, and the Reports card each independently fetch and display "Plan health." Given PCA-3's finding that the underlying goal probabilities (which feed plan health) are recomputed with fresh randomness on each Dashboard/Reports load, these three surfaces have no structural guarantee of agreeing at any given moment.
**Root cause:** Same root cause as PCA-3 (unseeded recomputation-on-read) plus the added structural issue of three independent fetches with no shared cache or single source screen.
**User impact:** Compounds PCA-3 — the same instability is now visible in three places instead of one, tripling the chance a user notices numbers disagreeing during a single session.
**Recommended fix:** Resolves once PCA-3's underlying recomputation issue is fixed; no separate fix needed beyond that.
**Owning milestone:** Milestone 4 (tied to PCA-3).

---

## PCA-13 — Delete-account copy is internally contradictory

**Severity:** Low
**Evidence:** Settings page: *"Permanently deactivates your account. Your data will not be recoverable."* "Deactivates" implies a reversible state; "not be recoverable" implies the opposite.
**Root cause:** Copy-level ambiguity, likely trying to describe a soft-delete (`is_active=false`, consistent with this project's universal soft-delete convention) using language that also tries to warn the user it's final from their perspective — the two goals conflict in one sentence.
**User impact:** Minor — a careful reader pauses on the phrase, but it doesn't block or mislead action.
**Recommended fix:** Clarify to something like "Deactivates your account immediately. You won't be able to sign back in, and we won't offer a way to restore access" — precise about what's true (soft-delete internally) without contradicting itself in user-facing language.
**Owning milestone:** General copy polish, no milestone dependency.

---

## PCA-14 — Two competing, unlabeled primary CTAs on the landing page

**Severity:** Low
**Evidence:** Landing page shows both "Build your plan" (hero) and "Get started" (nav header) as equally-weighted primary actions, both leading to the same registration flow.
**Root cause:** Marketing-page copy written independently of the nav header, with no de-duplication pass.
**User impact:** Momentary hesitation only ("are these different?") — low stakes, but avoidable per this project's own "one primary action" principle applied to the marketing surface as well as the app itself.
**Recommended fix:** Keep one as primary, demote the other to a secondary/text-link style, or merge.
**Owning milestone:** General copy/design polish, no milestone dependency.

---

## PCA-15 — Children-count placeholder looks like a real value, causes an avoidable form error

**Severity:** Low/Medium
**Evidence:** Onboarding Family step's "How many?" field shows "1" as placeholder text (not a real value) when "Do you have children?" is answered Yes. Submitting without typing a number produces: *"Please enter how many children (1-10)."*
**Root cause:** The placeholder value ("1") is also the single most likely real answer, making it unusually easy to mistake for a pre-filled default — worse than a typical empty-placeholder situation.
**User impact:** One extra, avoidable submit-error-fix-resubmit cycle for a step that was otherwise designed specifically to be frictionless.
**Recommended fix:** Either default the field to a real value of 1 (removing the ambiguity) or use a placeholder that can't be mistaken for a real answer (e.g., "Enter a number").
**Owning milestone:** Milestone 2, Task 4 (already shipped) — a small follow-up polish item, not a new task.

---

## PCA-16 — Financial jargon used throughout with no glossary or inline explanation

**Severity:** Medium
**Evidence:** "Monte Carlo" (Goals, AI Copilot suggested prompts), "confidence" vs. "probability" vs. "on track" used interchangeably for what appears to be the same underlying metric, "risk profile" (Conservative/Balanced/Aggressive) shown with a return-mix subtitle but no explanation of what "risk" means in practice.
**Root cause:** No shared glossary or inline-explanation pattern exists across the app; each screen was built independently.
**User impact:** Compounds across every screen — a first-time, non-finance user encounters unexplained technical vocabulary repeatedly rather than once, with no consistent place to learn it.
**Recommended fix:** Establish one consistent term ("probability of success," used everywhere) and one lightweight, reusable explanation pattern (tooltip or inline "what's this?") applied everywhere that term appears.
**Owning milestone:** Cross-cutting — recommend Milestone 6 (AI Advisor/explainability) as the natural owner, since explainability is that milestone's core mandate, but the fix itself doesn't require AI.

---

## Note on Test Data

This audit's live walkthrough reused the account created during `FIRST_TIME_USER_REVIEW.md` (`jamie.carter.firstuser@example.com`) plus targeted `grep`/file reads against the actual source tree (no database queries were run this session). No cleanup was performed, consistent with this being a read-only audit.
