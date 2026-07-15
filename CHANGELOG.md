# Changelog

All notable changes to Northstar are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Fixed (M2.6.1 — Global Shell overlay mutual exclusion, 2026-07-08)
- The Profile Menu no longer stays open when the Command Palette is opened via ⌘K/Ctrl+K (and vice versa) — the certification condition from `GlobalShellCertification.md`. Consolidated four independent overlay-open booleans (palette, notifications, profile menu, mobile "More" sheet) into one shared state, structurally guaranteeing only one can be open at a time. Zero changes to search, notification, or profile functionality.

### Added (Global Shell Phase 3 — Notification Center, 2026-07-08)
- The header bell is now a real notification center, surfacing insurance recommendations, government scheme eligibility, family members added, goals at risk, and goals completed — one new table (`notification_markers`) storing only read/dismissed state, never notification content, which is always read live from the same engines the Insurance/Schemes/Goals pages already call. Zero new calculation logic, zero recommendation-engine or dashboard changes.

### Added (Global Shell Phase 2 — Global Command Palette & Search, 2026-07-08)
- The header search bar is now a real, working command palette (`⌘K` / `Ctrl+K`), built entirely from the already-installed `cmdk` package and the previously-unused `command`/`dialog` components — zero new dependencies. Searches goals, family members, government schemes, and insurance policies by name; navigates to every real page in the app; and exposes two real quick actions (Create Goal, Add Family Member). Recent searches persist per-user. Zero backend changes.

### Added (Global Shell Phase 1 — Profile Avatar Menu & Mobile Sign-out, 2026-07-08)
- The header avatar is now a working account menu (My Profile, Settings, Sign Out) instead of a non-interactive decoration — built by reusing the existing, previously-unused `dropdown-menu` component, with zero new dependencies. Since the avatar lives in the shared header (not the desktop-only sidebar), this closes a real gap: mobile users previously had no way to sign out at all.

### Performance (Global Shell Phase 0 — Persistent AppShell Foundation, 2026-07-08)
- `AppShell` now mounts once, at the `/app` layout route, instead of independently by each of 13 leaf routes — it no longer fully unmounts and remounts on every navigation. Measured: `auth.me()` requests across a 6-navigation sequence dropped from 14 to 2 (residual attributed to an unrelated, pre-existing call in `app.copilot.tsx`); plan-health (`GET /dashboard`) requests dropped from 12 to 0, now served entirely from cache. No visual, UX, or routing change — purely an internal architecture fix, the prerequisite foundation for the upcoming Profile Menu, Global Search, and Notifications work.

### Performance (Milestone 2.1 — Dashboard Query Optimization, 2026-07-08)
- `GET /family/dashboard` reduced from 25 to 22 SQL queries (measured, not estimated) by sharing the household-members and goals-with-tags fetches between the card pairs that each independently re-fetched them, and by eliminating a redundant covered-member-ids query inside the insurance recommendation. `list_policies_with_coverage()`'s N+1 pattern (one query per policy) was batched into a single query across all policies. No business logic, API response shape, or authoritative data source changed; the dashboard's per-card failure-isolation behavior is unchanged. One remaining, deliberately-deferred duplication (a cross-service query shared between the Parents card and the Recommendations feed) is documented as non-blocking debt rather than fixed, since closing it would require coupling two services currently kept independent by design.

### Fixed (Milestone 2.1 — Accessibility Polish, 2026-07-08)
- Added visible keyboard-focus indicators to 24 interactive elements across 6 Family-module files (`app.family.insurance.tsx`, `app.family.recommendations.tsx`, `app.family.goals.tsx`, `app.family.members.$id.tsx`, `FamilyMemberForm.tsx`, `app.family.index.tsx`) — previously only Task 12's screens and the Schemes screen had this styling consistently. Purely additive CSS (the same existing `focus-visible:` utility string used elsewhere); no layout, logic, or component-API change. Verified live via keyboard-only navigation.

### Fixed (Milestone 2.1-P2 — Insurance Policy Audit Logging, 2026-07-07)
- Insurance policy creation and coverage updates are now audit-logged, matching the pattern every other Family write (member add/update/remove, goal tagging) has always used — closing the one gap the Certification's Security Review flagged. No new audit mechanism: reuses the existing `AuditLog` model and call pattern exactly. No delete/deactivate endpoint exists for policies today, so only the two real write actions (create, coverage-update) are logged.

### Added (Milestone 2.1-P1 — Government Schemes Screen, 2026-07-07)
- New `/app/family/schemes` screen: personalizes all 9 seeded government schemes against household composition into Eligible / Potentially Eligible / Not Eligible buckets, per `Milestone2ImplementationContract.md` §11 and `FamilyPlanningDesign.md` Part 7 — closing (substantively, not just partially) `ProductConsistencyAudit.md`'s PCA-7.
- Backend: `GET /api/v1/family/schemes` — a direct, zero-new-logic passthrough of the certified `scheme_eligibility_service.evaluate_household_eligibility()` (Task 3).
- The "Potentially Eligible" bucket is now visible in the product for the first time — previously, a household member approaching scheme eligibility (e.g., a parent turning 60 soon) had no forward-looking signal anywhere.
- Not Eligible reasons (including unconfigured schemes, honestly labeled "criteria not yet configured" rather than fabricated) are collapsed by default behind a native disclosure, never a wall of "no."
- Verified this screen and the existing Recommendations feed/Dashboard cannot disagree — both read the same live evaluation with no caching layer between them; a permanent test asserts reason-text identity for the overlapping "eligible" case.
- Family Home's "Government scheme eligibility" Coming Soon card replaced with a real link.
- 8 new backend tests.

### Fixed (Milestone 2.1-P0 — Risk Profile Persistence Bug, 2026-07-07)
- Removed Profile's "Risk Profile" field: it never had a backing account-level field anywhere in the backend, so changing it and seeing "✓ Saved" was a false confirmation — the value silently never persisted. No such account-level concept has ever existed in this product (risk profile is, and remains, a per-goal setting on `/app/goals`). Fixed by removing the misleading control rather than inventing new backend persistence under stabilization-sprint scope, per `DesignReview_M2.1-P0.md`.

### Added (Milestone 2 — Task 12: Family Dashboard Integration, 2026-07-07)
- Family Dashboard on `/app/family`: six single-question cards (Who depends on me / Education costs ahead / Insurance coverage / Parents / Retirement readiness / Emergency readiness) plus the Task 11 recommendations feed — every value read from an existing certified service or persisted goal state, zero financial arithmetic in the new layer.
- Backend: `GET /api/v1/family/dashboard` — read-only composition; each card is independently nullable so one failed section degrades to an "unavailable" card (logged server-side) instead of a 500, and a failed feed sets an explicit `recommendations_unavailable` flag rather than masquerading as "no recommendations."
- Extracted `family_insurance_service.uncovered_parents()` from the insurance recommendation so the dashboard's Parents warning and the recommendation share one authority — recording a policy clears both at once (live-verified).
- The Emergency card passes through the money dashboard's `liquid_assets`/`monthly_expenses`; "X months covered" is frontend display arithmetic (Task 9's precedent) because no backend emergency-months calculation exists and this task forbids inventing one.
- Quiet Family card on the main `/app` overview ("Family — N people · X suggestions to review") that renders nothing on error rather than breaking the money dashboard.
- 14 new backend tests, including feed-identity with the recommendations endpoint, warning-and-recommendation-move-together, two partial-failure degradation tests, nothing-persisted, and calculation-lifecycle regressions.

### Added (Milestone 2 — Task 11: Family Recommendations, 2026-07-07)
- New `/app/family/recommendations` screen: aggregates the insurance (Task 10) and government-scheme (Task 3) recommendation sources into one feed, each recommendation carrying why/why now/data used/missing information/confidence regardless of source.
- Backend: `GET /api/v1/family/recommendations`. Zero eligibility math or deduction-figure computation happens in the new aggregation layer — every value is read from the already-certified Task 3/Task 10 engines, never recomputed.
- Real conflict detection: two recommendations are flagged as conflicting only if they share a subject and a `reference_code` (the same bounded deduction/scheme ceiling) — never merely "same person, multiple recommendations." No recommendation is ever hidden to "resolve" a conflict; both remain visible with additive context.
- Family Home's "AI recommendations" Coming Soon card replaced with a real "Family Recommendations" link — deliberately renamed away from "AI," since this is rule-based, calculation-lite logic, not an AI/ML output.
- 13 new backend tests (9 integration, 4 unit tests against the conflict-detection helper directly).

### Added (Milestone 2 — Task 10: Family Insurance, 2026-07-07)
- New `/app/family/insurance` screen: a calculation-lite recommendation card (family-floater-vs-standalone-parent-policy tax opportunity, citing the verified 80D deduction figures), a policy list, and Add Policy / Edit Coverage forms.
- Backend: `GET /api/v1/family/insurance`, `POST /api/v1/family/insurance/policies`, `PUT /api/v1/family/insurance/policies/{id}/coverage`. The base ₹25,000 deduction figure is read from the seeded `tax_sections` table, not hardcoded; the ₹50,000 senior-citizen figure is derived (2× base), not a second literal.
- Every recommendation always explains why, why now, what information was used, and what information is missing — never partially populated. A missing date of birth shows the base figure only (with a lower confidence score) rather than guessing senior-citizen status either way.
- The recommendation is computed fresh on every read, never persisted — deliberately avoiding a "GET mutates stored data" anti-pattern (the same class of bug ADR-001/PCA-3 already eliminated elsewhere).
- A parent already covered by an active policy on file is excluded from the recommendation even if their recorded insurance-status answer is stale — verified live: adding a policy makes the recommendation disappear on the next load.
- Family Home's "Insurance status" Coming Soon card replaced with a real link now that the feature exists.
- 21 new backend tests, including permanent regressions for every Recommendation Integrity guarantee: verified-figures-only, always-explained, missing-information-never-fabricated, and the Calculation Lifecycle (goal probability) untouched.

### Added (Milestone 2 — Task 9: Family Goals & Custom Inflation, 2026-07-07)
- Education-category goals now show a future-cost projection ("Projected cost in N years: $X, using the standard/custom Y% annual inflation assumption"), reusing the goal-detail panel (`GoalSimPanel`) rather than a new route.
- `PATCH /api/v1/goals/{goal_id}` extended with an optional `custom_inflation_rate` field (bound `[0, 0.5]`) — a per-goal override of the global inflation rate. This is a display-only input this milestone: it never changes the goal's Monte Carlo probability/on_track (Milestone 4 will wire real inflation-aware Monte Carlo; see `CalculationContextReview.md`).
- Fixed a latent correctness gap: `update_goal()` previously recalculated probability on *any* field change (including the new field), which — with no seed configured — could silently perturb probability from RNG variance alone. Recalculation is now conditional on an actual Calculation Context field (current_amount, monthly_contribution, target_date, risk_profile, target_amount) being present in the request.
- No suggested default inflation rate is shown — education-cost inflation isn't independently verified yet, so the rate field starts empty rather than implying false precision.
- Fixed a real, pre-existing gap found during live testing: `GET /family/members/{id}` never populated `eligible_schemes` (only create/update did) — the goal's SSY callout is the first thing to have relied on it from a GET.
- 13 new backend tests, including permanent regressions for: probability never changes from setting `custom_inflation_rate` alone (even across repeated PATCHes), the override is scoped to exactly one goal, and cross-user access is rejected.

### Added (Milestone 2 — Task 8: Family Goal Tagging, 2026-07-07)
- New `/app/family/goals` screen: goals grouped by which family member they affect, with an honest "Not yet tagged" bucket for goals with no tags yet.
- Tagging/untagging uses a real `<fieldset>`/checkbox multi-select — no chip-picker. The mandatory joint-ownership disclosure ("This goal belongs to your account. [Name] can see it if you share access...") renders live as selections change, on every goal with at least one tag.
- Backend: new `PUT /api/v1/goals/{goal_id}/family-tags` (replaces a goal's full tag set in one call; 422 if any member id isn't in the caller's own household) and `GET /api/v1/family/goals` (goals with their tagged members). Goal ownership (`goals.user_id`) is never read or written by either endpoint — `goal_household_members` remains a purely descriptive tag, never a co-ownership mechanism.
- Family Home's "Upcoming family goals" Coming Soon card replaced with a real link now that the feature exists.
- 16 new backend tests, including permanent regressions for: goal ownership never changes, Monte Carlo probability/on_track never changes from tagging, repeated tagging never creates duplicate rows, and cross-household member ids are rejected with 422 rather than silently ignored.
- Fixed a live-caught frontend bug where a goal's tag checkboxes could show stale state after a tag change made elsewhere on the same page.

### Added (Milestone 2 — Task 7: Family Member Detail, 2026-07-07)
- `/app/family/members/:id` now shows a real read-only detail view for complete members — name/relationship/DOB header, "Goals involving X," "Health coverage," Edit and Remove actions. Incomplete placeholders still go straight to Task 6's form, per the Contract's own acceptance criteria.
- Remove uses an inline "Are you sure?" confirm (matching the codebase's existing `GoalSimPanel.tsx` pattern) — soft-deletes only (`is_active=false`), never hard-deletes.
- Backend: `family_service.is_complete()` (made public) is now returned on every family-member response (create/update/detail), not just the Family Home list — closes a gap that would otherwise have forced the frontend to duplicate completeness logic. No new backend endpoints.
- 2 new backend regression tests directly verifying editing never creates a duplicate member and never leaks into a different member's data.

### Added (Milestone 2 — Task 6: Add Family Member Flows, 2026-07-07)
- `/app/family/add` and `/app/family/members/:id` now do real work — a shared, relationship-branching form (`FamilyMemberForm`) for spouse/child/parent/other, wired to the existing, certified `POST`/`PUT /api/v1/family/members[/{id}]` endpoints. No new backend API.
- The Sukanya Samriddhi Yojana eligibility callout renders live from the backend's own eligibility service — never recomputed on the frontend.
- Completing a placeholder and editing an already-complete member share the same code path, matching Task 7's own plan to reuse this form for its future Edit button.

### Added (Milestone 2 — Task 5: Family Home Screen, 2026-07-07)
- `/app/family` — the household workspace: household summary, member list with completeness state, Quick Actions to add a parent or another person. Consumes only the certified `GET /api/v1/family` endpoint; no new backend API.
- "Family" added to the sidebar nav and the mobile bottom nav (now `Dashboard · Goals · Family · Copilot · More`, with Reports/Profile/Settings behind a new accessible "More" popover), per `FamilyPlanningDesign.md`.
- Five sections that depend on later tasks (Upcoming Family Goals, Insurance Status, Government Scheme Eligibility, AI Recommendations, Recent Changes) are shown as honest "Coming soon" cards rather than fabricated — see `BlockerReport.md`.
- `code/src/lib/family.ts` — shared `relationshipLabel`/`relationshipIcon` helpers, refactoring `app.profile.tsx` to reuse them instead of a second copy.
- Fixed a routing bug found during implementation: TanStack Router nests any `app.family.*` file under `app.family.tsx` as a parent layout; the real Family Home content moved to `app.family.index.tsx` and `app.family.tsx` became a thin `<Outlet/>` layout, matching the existing `app.tsx`/`app.index.tsx` split.
- Fixed a pluralization bug found during the live walkthrough ("3 Childs" → "3 Children").

### Fixed (Stabilization Sprint — PCA-3: Non-deterministic Monte Carlo recomputation on read, 2026-07-07)
- `GET /dashboard` and `GET /reports/summary` no longer recompute or persist a goal's Monte Carlo probability — they now read the already-persisted value. A goal's probability and `on_track` status are stable across every screen and every refresh, no longer dependent on which page was last opened.
- New architectural rule (ADR-001, `ArchitectureDecisionRecord.md`): read operations must never perform or persist financial calculations. Monte Carlo execution is centralized behind the goal's actual inputs changing (create/update) via a single new function, `planning_service.calculate_goal_probability()` — replacing two previously-separate, duplicate implementations (`planning_service.refresh_goal_probabilities()` and `routers/goals.py`'s `_refresh_probability()`).
- `quick_probability`/`quick_probability_async` now accept and use `MONTE_CARLO_SEED` (previously only the full 10k-path engine did), so the one remaining legitimate trigger is reproducible when a seed is configured.
- See `MonteCarloConsistencyReport.md` for the full investigation and `docs/architecture.md`'s new "Calculation Lifecycle" section.

### Fixed (Stabilization Sprint — PCA-2: Profile's deprecated Household field, 2026-07-07)
- Profile's "Household" field no longer reads or writes `user_profiles.marital_status`/`dependents` (deprecated). It now displays the certified household model directly (via a new `api.getFamilyHome()` client function wrapping the existing `GET /api/v1/family` endpoint — no new backend API), read-only for this sprint.
- Removed the now-empty `upsertProfile` write call and the now-unused `getProfile` read call from the Profile page.
- Added `docs/ENGINEERING_CONSTITUTION.md` Rule 11 (Deprecation Completion), citing this incident.

### Fixed (Stabilization Sprint — PCA-1: Broken Family promise, 2026-07-07)
- Onboarding's Family step no longer promises a specific "Family" destination that doesn't exist yet in the shipped product — copy now reassures without naming an unreachable place, per `ProductConsistencyAudit.md`.

### Changed (Milestone 2 — Task 4: Onboarding Family Step, 2026-07-06)
- Onboarding's Family step replaced: "Marital status" dropdown + "Number of dependents" field (writing to the deprecated `user_profiles.marital_status`/`dependents`) → three Yes/No questions (spouse, children + count, dependent parents), wired to `POST /family/onboarding-seed`.
- Verified live via full browser click-through against the real running backend and Postgres — not just type-checking.

### Added (Milestone 2 — Task 3: Scheme Eligibility Evaluation Service, 2026-07-06)
- Seeded `scheme_eligibility_rules` (previously empty — a Milestone 1 gap found and fixed): SSY (`max_age<10`, `gender=female`), SCSS (`min_age>=60`), all sourced from `GovernmentPolicyReport.md`.
- `app/services/scheme_eligibility_service.py` — household-wide eligibility evaluation (eligible/potentially_eligible/not_eligible) and a single-child SSY helper, sharing one rule-evaluation path.
- Task 2's `eligible_schemes` field (previously always empty) now returns real, live-sourced results on child add/update.
- Fixed an age-calculation precision bug (`days/365.25` approximation → exact calendar-date arithmetic) caught while writing the age-boundary test, before merge.
- 13 new backend tests; full suite now 234 tests passing, 96.89% coverage.

### Added (Milestone 2 — Task 2: Household & Member Service + API, 2026-07-06)
- `/api/v1/family/*` — onboarding household seeding, Family Home (with lazy-provision for pre-Milestone-2 accounts), and full member CRUD (spouse/child/parent/other), with type-specific validation.
- `household_members.name`, `dependents.gender`, `dependents.relationship_detail` — three schema gaps discovered while implementing, resolved in one migration (`008_household_member_name`). See `docs/database.md`.
- The first household-ownership authorization pattern in this codebase (data not keyed directly to `user_id`), with explicit cross-household negative-path tests.
- 26 new backend tests; full suite now 221 tests passing, 96.94% coverage. Backend/API only — frontend is Tasks 4/5, per the approved `ImplementationChecklist.md`.

### Added (Milestone 2 — Task 1: Family Goal Tagging Schema, 2026-07-06)
- `goal_household_members` table — a purely descriptive "who this goal affects" tag, not a joint-ownership model; `goals.user_id` remains the sole owner of record.
- `goals.custom_inflation_rate` (nullable) — per-goal inflation override for education/medical goals.
- `dependents.has_own_insurance` (nullable) — parent-dependent insurance status, feeding the future Family Insurance recommendation.
- 10 new backend tests; full suite now 195 tests passing, 97.07% coverage. Schema-only task — no router/API/frontend yet, per the "one feature at a time" implementation order.

### Added (Foundation Reconciliation, 2026-07-06)
- Nullable `huf_entity_id` ownership column on `income_sources`/`expenses`/`assets`/`liabilities` (`ON DELETE SET NULL`) — HUF entities can now be attributed real financial data, resolving a HIGH-severity gap where HUF's entire tax rationale (a separate taxable entity with its own income) had no data to compute against. See `FoundationReconciliationReport.md`.
- `best_practice_rules` and `company_policies` tables (Policy Engine Layers 2-3) — structural support only, no logic, unblocking the Recommendation Engine milestone's dependency on company-policy rows.
- `user_profiles.dependents`/`marital_status` and `financial_assumptions.tax_rate` marked deprecated in code (not removed) in favor of the household/policy-engine entities, with a documented future migration plan.
- 7 new backend tests; full suite now 185 tests passing, 97.05% coverage.

### Added (Milestone 1 — Foundation, 2026-07-06)
- 20 new database tables (household/family, versioned government policy engine, estate/nominee, insurance, recommendation, audit) — purely additive, zero existing tables changed. See `PROJECT_STATE.md` and `docs/database.md`.
- `backend/scripts/seed_policy_data.py` — idempotent seed of verified government scheme rates and tax data (PPF, EPF, NPS, SSY, SCSS, NSC, KVP, APY, PMVVY, both Income-tax Acts, new-regime tax slabs), sourced exclusively from live-verified research, not invented figures.
- 14 new backend tests covering the new models; full suite now 178 tests passing, 96.98% coverage.

### Fixed
- Missing `password_reset_tokens` Alembic migration — forgot-password was hard-broken against any freshly-migrated database (model existed, migration never did)
- Profile page silently overwrote `dependents`/`marital_status` in the database on any unrelated save (e.g. renaming yourself) — it never loaded real saved profile data
- Goal optimizer's "Switch to {risk profile}" suggestion was a non-functional decorative element with no click handler
- Reports page rendered negative net worth as `$-149500` instead of a properly signed, abbreviated value
- 12 Ruff violations and 18 `mypy --strict` errors in the backend (forward-reference type hints, untyped third-party library boundaries, incorrect middleware parameter types) — zero behavior change, all fixes are annotation/formatting-only
- `docs/architecture.md` documentation drift: stale router list, stale table list, stale JWT-storage description (said localStorage-only; refresh token has been in an httpOnly cookie since a prior session)

### Added
- FastAPI backend with async PostgreSQL via asyncpg
- JWT authentication (access + refresh tokens, bcrypt passwords)
- Monte Carlo simulation engine (10 000 log-normal paths per goal)
- Financial optimizer (contribution, risk-shift, and combined strategies)
- Goal-based planning service with automatic probability refresh
- AI Copilot endpoint (GPT-4o with rule-based fallback)
- Alembic migration scaffold with initial schema (001)
- Full test suite: unit tests for simulation engine and optimizer,
  integration tests for auth and goals APIs
- `docker-compose.yml` orchestrating PostgreSQL + backend + frontend
- Complete documentation: README, architecture, backend, frontend, database,
  CONTRIBUTING, CHANGELOG, CLAUDE.md
- Frontend `api.ts` updated to call real endpoints with mock fallback

---

## [0.1.0] — 2025-01-01

### Added
- TanStack Start frontend scaffolded by Lovable
- Deep Navy Premium design system (oklch colour palette)
- Marketing landing page with hero, features, how-it-works, CTA
- Sign-in page (form UI, no backend yet)
- Onboarding placeholder wizard
- Dashboard route with net-worth chart, allocation pie, goals summary, AI suggestions
- Goals route with Monte Carlo probability badges and new-goal modal
- AI Copilot chat interface (mock responses)
- Reports route with bar chart
- Mock data fixtures and placeholder API service layer
