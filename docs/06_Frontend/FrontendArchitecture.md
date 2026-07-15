# Frontend Architecture & User Experience

**Status:** Canonical · **Last verified against code:** 2026-07-13 (updated past the source Bible's 07-10 compile date with the most recent completion mission's Phases 1–9, which touched Navigation, Life Events UI, Plan Health, Microcopy, Automation, Cross-Module Consistency, Behavioral Design, Accessibility, and Performance UX — each update called out explicitly below rather than silently merged in)
**Supersedes:** `FrontendArchitectureUserExperienceBible.md` (archived), plus the Global Shell rebuild's own Phase 0–3 design/validation cluster (`GlobalShellArchitecture.md`, `GlobalShellImplementationPlan.md`, `GlobalShellCertification.md`, `NotificationCenterDesign.md`, `GlobalSearchDesign.md`, `KeyboardShortcutDesign.md`, `ProfileMenuDesign.md`, and 18 further Phase-0–3 design/validation/PR docs — see `docs/14_KnowledgeBase/DocumentationInventory.md` §2.2 SHELL_PHASES cluster), and the Navigation mission (`NavigationAudit.md`/`NavigationReview.md`/`NavigationImplementationReport.md`).
**Method:** every route file, hand-written component, and `lib/` file was read in full for the source Bible; this document re-verifies anything that could have changed since and folds in nine phases of subsequent, verified frontend work.

---

## 1. Overview

Northstar's frontend is a **TanStack Start** (React 19) application — file-based routing via `@tanstack/react-router`, SSR-capable, built with Vite 8. It originated as a **Lovable-generated project** (confirmed by `__root.tsx`'s default meta tags and `lovable-error-reporting.ts`), later customized into the Northstar product.

**Two operating modes, one codebase:** every function in `lib/api.ts` branches on `VITE_API_BASE_URL`. When set, every call hits the real FastAPI backend; when unset, every call resolves a mock fixture after an artificial 350ms delay — the entire UI is fully interactive and visually complete with zero backend running. Mock functions deliberately mirror the *exact* business rules of their real counterparts (onboarding-seed shape, `is_complete` logic, SSY eligibility), so the mock path exercises the same UI branches production does.

**No frontend automated test suite exists** — no `*.test.tsx` file anywhere under `code/src/`, confirmed at Bible-compile time and unchanged since. Frontend correctness is verified by `tsc --noEmit`, `eslint`, `npm run build`, and manual/live browser verification only — a deliberate, consistently-applied compensation, not an oversight, confirmed by every one of the most recent mission's nine phase reports following this identical validation pattern.

**Screen count:** 21+ routed screens (2 public + 4 auth + 1 onboarding wizard + 14+ authenticated `/app/*` screens, now including `/app/life-events`, added since the Bible).

---

## 2. Folder Structure

```
code/src/
├── routes/                    File-based routes — one file = one URL
│   ├── __root.tsx              Root: HTML shell, QueryClientProvider, 404/error boundaries
│   ├── index.tsx, auth.*.tsx, onboarding.tsx
│   ├── app.tsx                  "/app" layout — auth guard + mounts <AppShell> once
│   ├── app.index.tsx, app.goals.tsx, app.life-events.tsx   (life-events added since the Bible)
│   ├── app.family.*.tsx (7 files), app.copilot.tsx, app.profile.tsx, app.settings.tsx, app.reports.tsx
├── components/
│   ├── app-shell.tsx, global-palette.tsx, notification-center.tsx   (shell-level)
│   ├── dashboard/    PlanHealthInfo.tsx added since the Bible (Phase 3)
│   ├── life-events/   RecordLifeEventDialog.tsx, life-event-field-inputs.tsx — added since the Bible
│   ├── family/, onboarding/, ui/ (57-file shadcn scaffold)
├── hooks/
│   ├── use-mobile.tsx
│   └── use-dialog-a11y.ts   NEW since the Bible (Phase 8) — see §12
├── lib/
│   ├── api.ts (the entire backend contract), mock-data.ts, utils.ts
│   ├── life-events.ts, life-events-form.ts   NEW since the Bible
│   ├── financial-labels.ts   NEW since the Bible (Phase 4)
│   └── family.ts, shell-title.ts, error-page.ts, error-capture.ts, lovable-error-reporting.ts
├── router.tsx, start.ts, server.ts, routeTree.gen.ts (auto-generated, never hand-edited)
└── styles.css   "Deep Navy Premium" design tokens — frozen per CLAUDE.md
```

**Organizing principle:** file-based routing means the `routes/` tree *is* the sitemap. Components split by scope: shell-level, domain-scoped (`dashboard/`, `family/`, `life-events/`, `onboarding/`), and the generic `ui/` scaffold.

---

## 3. Routing & Route Guarding

Engine: TanStack Router, file-based, `routeTree.gen.ts` auto-generated and never hand-edited. `/app`'s `beforeLoad` checks `localStorage["ns_access_token"]`, SSR-safe; the layout component re-checks on every mount via `useEffect` before rendering `<AppShell>` — the single gate for every authenticated screen; no leaf route below `/app` has its own auth check.

`staticData.shellTitle` (module-augmented via `router-static-data.d.ts`) declares each `/app/*` leaf's persistent-header title; `app.family.add.tsx` is the one route needing a render-time-dynamic title, handled via the narrow `useShellTitle()` escape hatch.

**Search-param validation (Zod):** `/app/goals` (`{new: boolean}`, lets the Command Palette's quick action open the New Goal modal), `/auth/reset-password` (`{token}`), `/app/family/add` (`{type}`).

404/error handling is declared once at root — every route inherits the same UI.

---

## 4. App Shell

`components/app-shell.tsx` is mounted exactly once by `/app`'s layout route and persists across every navigation — only `<Outlet/>`-rendered leaf content swaps. Owns the desktop sidebar (7-item nav, live Plan Health mini-card — **now a `PlanHealthInfo` trigger button rather than a static number, since Phase 3**), the header (page title, Search trigger, Notification bell, Profile dropdown), the mobile bottom nav (4 primary + "More" overflow), and the `activeOverlay` single discriminated-union state (Milestone 2.6.1) structurally guaranteeing only one header overlay is ever open.

---

## 5. Authentication UX

Four hand-rolled screens (Sign in, Forgot/Reset Password, Onboarding's account step), no shared `<AuthLayout>`. Session mechanics: `setAccessToken`/`clearAccessToken` write/clear `localStorage`; the refresh token and CSRF pair are never touched by React code directly — only `apiFetch`'s automatic-refresh-on-401 logic references them.

---

## 6. Navigation System

Three concurrent surfaces sharing intent but not one literal array: the desktop sidebar (7 items), the mobile bottom nav + "More" sheet (4 primary + 3 overflow), and the Command Palette (10 page entries + 2 quick actions). Family Home's Quick Actions are the *only* way to reach Schemes/Insurance/Recommendations outside the Palette — no sidebar/bottom-nav entry links to any of the three directly.

**Updated since the Bible (Navigation mission, Phase 1):** `NavigationAudit.md`/`NavigationReview.md`/`NavigationImplementationReport.md` reviewed this exact system and made targeted information-architecture improvements — full detail preserved in the archived Navigation mission documents (§ this document's own footer).

---

## 7. Dashboard

`app.index.tsx`. 4 stat cards (skeleton while loading), `FamilyCard` (deliberately renders `null` on loading/error — "the money dashboard must never break or grow a second spinner because the family aggregate is unavailable"), a cash-flow strip (implicit empty state — no strip at all for a brand-new account, not a strip full of zeroes), Net Worth Projection + Wealth Breakdown charts, and a goals list.

**Updated since the Bible:** a `RecentLifeEventsCard` was added (Phase 2), and the Dashboard's AI Copilot preview card gained a dynamic "Based on your recent activity" note (Phase 2).

---

## 8. Life Events (new surface, not in the source Bible)

`app.life-events.tsx` + `RecordLifeEventDialog.tsx` + `life-event-field-inputs.tsx`. A picker of 18 events grouped into 5 categories, a guided per-event form with `<datalist>` suggestions and auto-select-single-option for entity fields (Phase 5), a "Preview effects" step, a history list with plain-language effect summaries (Phase 4) and a guarded Undo, and — for 6 unambiguous milestones — an honest, manual-dismiss celebration screen, plus a calm supportive-note banner for 2 hard events (Phase 7). Full architecture: `docs/02_Architecture/LifeEventEngine.md`.

---

## 9. Goal Management, Family Workspace, Schemes, Insurance, Recommendations, Reports, AI Copilot, Search, Notifications, Profile, Settings

Each of these screens' detailed composition, data sources, and interaction patterns are preserved in full from the source Bible (§8–§18 there) — none of their underlying structure changed in the most recent mission, which touched only copy, loading-state presentation, and accessibility wiring on top of the existing composition. See the archived Bible for full per-screen detail; the deltas that *did* land are called out in §11–§13 below.

---

## 10. Forms, Validation, State Management, React Query, API Layer, Component Architecture

**State management is unchanged in shape:** exclusively TanStack React Query for server state (one `QueryClient`, deliberately shared cache keys — `["currentUser"]`, `["dashboard"]`, `["goals"]`, `["family-home"]`, `["family-dashboard"]`, `["notifications"]`), TanStack Router for client routing state, `react-hook-form`+Zod for forms, ordinary `useState` everywhere else. No mutation anywhere uses optimistic updates — every write waits for the server response.

**API layer:** `lib/api.ts` (1,293+ lines) is the entire backend contract in one file. Only Goals has a dedicated snake_case↔camelCase mapping layer; every domain added afterward (Family, Insurance, Schemes, and now Life Events) declares its frontend types directly in snake_case, matching the backend's Pydantic schemas verbatim — a real, deliberate-if-unstated convention shift, consistent enough (zero mixed-case leakage) to read as considered.

**Component architecture:** no formal container/presentational split is enforced; most components both fetch their own data and render their own markup. No `React.memo`, no `useMemo`/`useCallback` beyond incidental `useId()` — consistent with this codebase's stated preference for simplicity over premature optimization.

---

## 11. Known Gap, Reconciled — FE-005 (React Query bypass)

**The source Bible named 4 screens** bypassing React Query via raw `useEffect`+`.then()`: `app.goals.tsx`, `app.profile.tsx`, `app.reports.tsx`, `EducationPlanningSection.tsx`. **The most recent completion mission's own Phase 9 report separately named a 5th: `app.copilot.tsx`.** This document reconciles both claims by re-verifying directly against the live codebase this pass:

```
$ grep -c useQuery routes/app.goals.tsx routes/app.profile.tsx routes/app.reports.tsx routes/app.copilot.tsx components/dashboard/EducationPlanningSection.tsx
0  0  0  0  0
```

**Confirmed: all 5 files bypass React Query entirely, still true today.** None of the nine most recent mission phases fixed this (Phase 2's own review explicitly flagged it as known and out of scope; Phase 9's own audit did the same) — it remains open, tracked consistently across both this Bible and the newer mission's reports as the same underlying gap, not two different findings.

---

## 12. Accessibility — Updated Since the Bible

The source Bible's §27 findings on focus-visible rings, `aria-label`/`aria-hidden`/`role="alert"`/`role="status"` usage, and the absence of a skip-link/live-region/reduced-motion handling **all remain accurate and unchanged**. **One material addition since:** the most recent mission's Phase 8 found and fixed a real gap the Bible didn't cover — three hand-rolled (non-Radix) modals (`RecordLifeEventDialog`, `GoalSimPanel`, the inline "New goal" modal) had no `role="dialog"`, no `aria-modal`, no Escape-to-close, no focus trap, and no focus return, unlike the shell's Radix-based overlays. A new shared hook, `hooks/use-dialog-a11y.ts`, now gives all three the same keyboard/focus behavior — live-verified via keyboard-only testing. `GoalSimPanel`'s previously-unlabeled icon-only close button also gained `aria-label="Close"` in the same pass.

**Still open, unchanged from the Bible:** no skip-to-content link, no `aria-live` on the notification badge or Copilot's "thinking" indicator, no documented color-contrast verification, no reduced-motion handling on any `motion.div` animation.

---

## 13. Loading States — Updated Since the Bible

The Bible's §31 table (skeleton blocks as the dominant pattern; spinner icons for button/action-level "in progress"; silent-render for `FamilyCard`/`EducationPlanningSection`) remains accurate, **with one correction:** the Bible listed "Reports' full-page load" as a spinner-based exception to the skeleton convention. **This was fixed in the most recent mission's Phase 9** — Reports now uses a content-shaped skeleton (4 stat-card placeholders, a table skeleton, a cash-flow-strip skeleton) matching every sibling screen, removing the one screen that previously spoke a different loading-state dialect.

---

## 14. Findings Register (frontend-specific, FE-001 through FE-011)

*(Preserved from the source Bible in full — none of these were in scope for, or touched by, the most recent completion mission, which is explicitly noted per finding where relevant.)*

| ID | Severity | Finding | Status |
|---|---|---|---|
| **FE-001** | **High** | The Landing/Sign-in pages market "SOC 2 Type II," "AES-256 at rest," and "OAuth read-only account linking" — **none of which exist anywhere in the verified backend** (hand-rolled JWT, no OAuth linking, no documented encryption-at-rest, no SOC 2 evidence). `app.settings.tsx`'s own "Linked accounts... coming in a future release" directly contradicts the Landing page's framing of the same capability as already real. The clearest violation of "never claim capability the data model doesn't actually have" found anywhere in this frontend — more severe than any backend-side instance, since it's user-facing marketing copy. | **Still open** — not touched by any of the nine most recent mission phases, none of which scoped the public marketing pages. |
| FE-002 | High | Onboarding's Assumptions step claims "These defaults power every projection" — false for 3 of 4 fields on that exact screen; only `inflation_rate` has any real effect, on one frontend-only projection. | Still open. |
| FE-003 | Medium | Onboarding's Personal step claims profile fields "help tailor projections to your tax region and life stage" — these fields have zero calculation consumers. | Still open. |
| FE-004 | Medium | `FamilyMemberForm`'s spouse DOB hint claims it "affects joint retirement timing and health-insurance premium calculations" — neither exists; spouses are never evaluated by the Insurance Engine. | Still open. |
| FE-005 | Medium | React Query bypass — see §11 above, now confirmed at 5 files, not 4. | Still open; explicitly out of scope for Phases 2 and 9 of the most recent mission (both noted it, neither fixed it). |
| FE-006 | Low | `react-hook-form`/Zod-for-forms/`ui/form.tsx`/`ui/sidebar.tsx`/`use-mobile.tsx` are declared dependencies with zero real application consumer. | Still open — not addressed. |
| FE-007 | Info | Single dark theme only — deliberate, per CLAUDE.md's frozen design system. | Unchanged, deliberate. |
| FE-008 | Info | `NetWorthProjection`'s hardcoded deterministic rates render with no visual distinction from genuinely-probabilistic Monte Carlo results elsewhere on the same Dashboard. | Still open. |
| FE-009 | Info | Command Palette cannot deep-link Goal/Scheme/Insurance results to a specific record — only Family Member results do. | Still open, documented scoped limitation. |
| FE-010 | Low | Settings' Delete Account copy overstates a soft-delete as "not... recoverable." | Still open. |
| FE-011 | Low | `EducationPlanningSection`'s per-tagged-member `getFamilyMember` calls run sequentially in a `for` loop, not `Promise.all` — an N+1-shaped, currently-low-volume inefficiency. | Still open. |

**New findings from the most recent mission**, in the same register style: none rose to a FE-0xx-numbered finding in that mission's own reports — every issue it found (Phase 6's color-token investigation, Phase 8's dialog accessibility gap, Phase 9's Reports loading-state gap) was found *and fixed* within the same phase, rather than logged open. The one exception carried forward as genuinely open is FE-005 (§11).

---

## Related Documents
`docs/02_Architecture/SystemArchitecture.md` §9 · `docs/02_Architecture/LifeEventEngine.md` §8's frontend detail · `docs/07_AI/AIArchitecture.md` (the Copilot UI referenced in §9) · `docs/03_Engineering/ArchitectureDecisionRecords.md` · `docs/08_Testing/ValidationStrategy.md` (Global Shell Certification detail)

## Related ADRs
The Global Shell overlay-consolidation decision (Milestone 2.6.1, `activeOverlay`).

## Related APIs
Every endpoint in `docs/04_API/RESTAPI.md` — `lib/api.ts` is this frontend's complete client for all of them.

## Related Database Tables
None directly — this document's domain is presentation only; see `docs/05_Database/DatabaseSchema.md` for what each screen ultimately reads/writes through its API calls.

## Related Services
None directly — routed through `backend/app/routers/*` via `lib/api.ts`.

## Related Frontend Components
`app-shell.tsx`, `global-palette.tsx`, `notification-center.tsx`, `RecordLifeEventDialog.tsx`, `GoalSimPanel.tsx`, `PlanHealthInfo.tsx`, `use-dialog-a11y.ts`, `financial-labels.ts`, `life-events.ts`.


## Related Tests
**None** — the single most consequential fact this document repeats: no frontend automated test suite exists anywhere in this codebase. Frontend correctness is verified by `tsc`/`eslint`/`npm run build`/manual browser verification only (see `TestingStrategy.md` §3).

## Related Validation Reports
The Global Shell Certification (Phases 0–3), the Navigation mission's `NavigationAudit.md`/`NavigationReview.md`, and the most recent completion mission's Phase 8 (Accessibility) audit — all archived, all summarized in this document's own §12.

## Related Implementation Reports
The Shell Phase 0–3 implementation history (23 files) and the most recent completion mission's 9 phase reports — archived under `13_Archive/ArchivedDesignDocs/` and `ArchivedAudits/` respectively.

## Related Future Work
FE-005's resolution (migrating the 5 React-Query-bypassing screens) · FE-001's resolution (correcting the Landing page's security marketing copy) · a real frontend test suite (Vitest + React Testing Library, per `TestingStrategy.md` §3).
---

*Archived originals: `docs/13_Archive/ArchivedReports/FrontendArchitectureUserExperienceBible.md`, `GlobalShellArchitecture.md`, `GlobalShellImplementationPlan.md`, `GlobalShellCertification.md`, `NotificationCenterDesign.md`, `GlobalSearchDesign.md`, `KeyboardShortcutDesign.md`, `ProfileMenuDesign.md`, `NavigationAudit.md`, `NavigationReview.md`, `NavigationImplementationReport.md`, plus the full Shell-Phase 0–3 design/validation/PR cluster (23 files — see `docs/14_KnowledgeBase/DocumentationInventory.md` §2.2 SHELL_PHASES).*
