# Interactive Product Audit — Northstar

**Date:** 2026-07-08
**Method:** Direct source-code trace of every route, layout, and shared component in `code/src/routes/` and `code/src/components/` — every `onClick`, `<Link>`, `<a href>`, `<form onSubmit>`, `<button>`, `<select>`, `<input>` was located and traced to its handler, then to its `api.ts` client function, then to its backend router/service (or confirmed mock-only). Ambiguous or user-facing-critical items were additionally verified live against the running application. No fixes were made — audit only.
**Legend:** ✓ Works correctly · ⚠ Partially works / misleading · ❌ Doesn't work (dead click / broken)

---

## 1. Global Shell (`components/app-shell.tsx`) — renders on every authenticated screen

| Component | Expected behavior | Actual behavior | Status |
|---|---|---|---|
| Sidebar nav links (Dashboard, Goals, Family, AI Copilot, Reports, Profile, Settings) | Navigate to each section, highlight active | `<Link>` via TanStack Router, active-state class applied correctly | ✓ |
| Logo (top-left) | Navigate home | `<Link to="/">` | ✓ |
| Plan health card | Display-only | Shows `plan_health_score` from real `api.getDashboard()` call | ✓ |
| **Sign out** | End session, return to sign-in | Calls `auth.logout()` (best-effort) + `clearAccessToken()` + navigate — verified live this session | ✓ |
| Mobile bottom nav (4 primary icons) | Navigate to primary sections | Same `<Link>` pattern as sidebar | ✓ |
| Mobile "More" button | Open overflow menu (Reports/Profile/Settings) | Opens/closes correctly; closes on outside-click and Escape; closes after selecting an item | ✓ |
| **Global Search bar** (header, "⌘K") | Open a search interface, or at minimum focus a real input | **Pure static `<div>`** — no `<input>`, no `onClick`, no keyboard listener anywhere in the codebase for `⌘K` | ❌ |
| **Notification bell** | Open a notification center/dropdown | **Plain `<button>` with no `onClick`** — the red unread-dot renders unconditionally and can never be dismissed or inspected | ❌ |
| **Avatar** (top-right, user initials) | Open a profile menu (settings, sign out, etc.) | **Plain `<div>`**, not even a `<button>` — no click target, no menu, no `aria-haspopup` | ❌ |

## 2. Dashboard (`app.index.tsx`)

| Component | Expected | Actual | Status |
|---|---|---|---|
| Stat cards (Net worth, Invested, Liquid, Monthly savings) | Display-only | Real data from `api.getDashboard()` | ✓ |
| Family summary card | Navigate to `/app/family` | `<Link>`, real data from `api.getFamilyDashboard()`, correctly renders nothing on load/error (deliberate) | ✓ |
| Net worth projection chart | Hover shows tooltip per scenario | Recharts `<Tooltip>` — native, works | ✓ |
| Net worth breakdown (donut) | Display-only | Pure computed display | ✓ |
| "Manage goals" / "Add your first goal" links | Navigate to `/app/goals` | `<Link>` | ✓ |
| **Goal preview cards** (mini list, up to 4) | Hover style implies clickability (`hover:border-border-strong`) | **No `onClick`, no `<Link>` wrapper — clicking does nothing**, despite the Goals page's own near-identical cards being fully clickable | ❌ |
| "Open copilot" link | Navigate to `/app/copilot` | `<Link>` | ✓ |
| AI Copilot suggestion mini-cards | Display-only | Real `dashData.suggestions` | ✓ |

## 3. Goals (`app.goals.tsx` + `GoalSimPanel.tsx` + `EducationPlanningSection.tsx`)

| Component | Expected | Actual | Status |
|---|---|---|---|
| Search input | Filter goal list by name | Real client-side filter | ✓ |
| Filter buttons (All / On track / At risk) | Filter goal list | Real client-side filter, active state styled | ✓ |
| "New goal" button + modal | Open create form | Modal opens, backdrop-click and Cancel both close it | ✓ |
| New-goal form (name, category, amounts, years, risk profile) | Create a goal | Real `api.createGoal()`, error surfaced inline | ✓ |
| Goal card (click anywhere) | Open detail/simulation panel | Opens `GoalSimPanel` | ✓ |
| "Simulate" icon button on card | Same as above, without triggering card's own click twice | `stopPropagation()` + opens panel — works, but redundant with the card click itself | ✓ (minor redundancy) |
| GoalSimPanel — Edit (pencil) toggle | Show/hide edit form | Toggles, pre-fills current values | ✓ |
| GoalSimPanel — Save changes | Persist edits | Real `api.updateGoal()` | ✓ |
| GoalSimPanel — Run 10,000 paths | Run Monte Carlo | Real `api.simulate()`, shows percentiles | ✓ |
| GoalSimPanel — Optimize toward 80% | Run optimizer | Real `api.optimize()`, shows suggestions | ✓ |
| GoalSimPanel — "Switch to [risk]" suggestion button | Apply optimizer's suggested risk change | Real `api.updateGoal({riskProfile})` | ✓ |
| GoalSimPanel — Delete (two-step confirm) | Delete goal | Real `api.deleteGoal()`, confirm/cancel both work | ✓ |
| Education cost projection — "Set/Change custom rate" | Save a custom inflation rate for this goal | Real `api.updateGoal({customInflationRate})` | ✓ |
| **Accessibility note:** none of the above elements (search, filters, New goal, goal cards, modal Cancel/Create, risk-profile selector, Edit/Save/Run/Optimize/Delete buttons) carry `focus-visible` styling — this entire screen was outside the Milestone 2.1 Accessibility Polish fix's scope (Family module only). | | | ⚠ (keyboard-focus gap) |

## 4. Family module

### 4a. Family Home (`app.family.index.tsx`)
All links (member cards, Quick Actions, Goals/Insurance/Schemes/Recommendations link-cards, dashboard mini-cards, retry buttons on error states) are real `<Link>`/`onClick` elements wired to live data via `api.getFamilyHome()` and `api.getFamilyDashboard()`. Loading/error/empty states all handled. **All ✓.** Focus-visible present throughout (fixed in Milestone 2.1 Accessibility Polish).

### 4b. Add Family Member (`app.family.add.tsx` + `FamilyMemberForm.tsx`)
Form fields, client-side validation, and submit (`api.createFamilyMember()`) all real and functional. Scheme-eligibility confirmation state shown correctly when applicable. **✓.**
**Gap found:** the "Back to Family" link (top of page) and the "Back to Family →" link (inside the post-submit scheme-callout state) have **no `focus-visible` styling** — this file was missed by the Milestone 2.1 Accessibility Polish fix, which covered 6 files but not this 7th one.

### 4c. Family Member Detail, Goals, Insurance, Recommendations, Schemes
All screens' interactive elements (edit/save/cancel, coverage editing, remove-member confirm flow, policy add/edit forms, scheme bucket disclosures, retry buttons) verified functional and backed by real endpoints, per the extensive live testing performed during their respective Milestone 2/2.1 implementations this session. **✓** across the board; no dead handlers found on a fresh code re-scan.

## 5. Reports (`app.reports.tsx`)
Stat cards, goal breakdown table, cash-flow strip: all real data via `api.getReportSummary()`. **"Export PDF" button calls `window.print()`** — it does not generate or download a PDF file; it opens the browser's native print dialog, requiring the user to manually choose "Save as PDF." **⚠ Partially works / mislabeled.**

## 6. Profile (`app.profile.tsx`)
Avatar, name/email display: real data. Household list: real, correctly labeled read-only.
**Full name field:** editable, saves correctly via `auth.updateMe({full_name})`. **✓**
**Email field:** editable, contributes to the dirty/Save-button state, but **the save handler never sends it** (`auth.updateMe()` only accepts `full_name`/`password`, and the backend's `UserUpdate` schema and `update_me()` handler have no `email` field at all). The UI shows "✓ Saved" after submit, but the email change is silently discarded. **❌ Misleading UI / silent data loss.**

## 7. Settings (`app.settings.tsx`)
Change password (show/hide toggles, real `auth.changePassword()`), Delete account (type-DELETE confirm, real `auth.deleteAccount()`) — both fully functional and backend-verified. "Notifications" and "Linked accounts" cards are honestly labeled "Coming soon," visually de-emphasized, non-interactive. **✓** across the board — this is a model example of correctly-implemented placeholder UI (contrast with the landing page's claims below).

## 8. AI Copilot (`app.copilot.tsx`)
Chat input + send, suggested-prompt buttons: both call real `api.chat()` → `POST /copilot` (or mock fallback in mock mode). **✓ functional.**
**Header label "GPT-Planner · 4o" is hardcoded** and displayed regardless of whether `OPENAI_API_KEY` is actually configured server-side — the backend silently falls back to a rule-based responder with no signal surfaced to the UI. **⚠ Misleading when running in fallback/mock mode.**

## 9. Authentication (Sign in, Forgot password, Reset password)
All forms, show/hide password toggles, and submit handlers verified functional against real backend endpoints (`/auth/login`, `/auth/forgot-password`, `/auth/reset-password`). **✓** across the board. Forgot-password page conditionally renders a "Dev mode — reset token" block when the backend returns one (non-production behavior) — correctly gated, flagged for a production-config double-check, not a code defect.

## 10. Onboarding (`onboarding.tsx` + `wizard-steps.tsx` + `list-steps.tsx`)
All 12 steps (account creation through Done), every Back/Skip/Next button, and every list-add/remove row (income, expenses, assets, investments, liabilities) trace to real, working API calls. **✓** across the board.
**Minor inconsistency:** the "Sign in" link on the account-creation step uses a plain `<a href>` instead of the app's `<Link>` router component, causing a full page reload instead of client-side navigation — works, but inconsistent with the rest of the app.

## 11. Landing Page (`index.tsx`, unauthenticated)
| Component | Expected | Actual | Status |
|---|---|---|---|
| "Get started" / "Build your plan" (multiple) | Navigate to onboarding | `<Link to="/onboarding">` | ✓ |
| "Sign in" | Navigate to sign-in | `<Link>` | ✓ |
| Nav — Product, How it works | Scroll to section | Real `id="product"`/`id="how"` anchors exist | ✓ |
| **Nav — Security** | Scroll to a security/trust section | **Points to `#trust` — no element with that id exists anywhere on the page** | ❌ |
| Nav — Pricing | Scroll to CTA section | Real `id="pricing"` anchor exists | ✓ |
| **"View live demo"** | Show a demo of the product | Links to `/app`, which is auth-guarded — an unauthenticated visitor is silently redirected to `/auth/sign-in`, identical to clicking "Sign in" | ⚠ Misleading — no demo is ever shown |
| **Footer — Privacy / Terms / Disclosures** | Open legal pages | **All `href="#"` — dead placeholder links, no pages exist** | ❌ |

## 12. Root-level (`__root.tsx`)
404 page ("Go home" link) and error boundary ("Try again" / "Go home") both functional. **✓.**

## 13. Structural observation: unused component library
None of the ~50 shadcn/ui primitives in `components/ui/` (dialog, dropdown-menu, tabs, select, table, pagination, context-menu, accordion, alert-dialog, command, etc.) are imported anywhere in the app's actual routes or components — confirmed via exhaustive grep. Every interactive surface in the product (modals, dropdowns, confirmations) is hand-rolled with plain Tailwind + `motion/react`. This is not itself "broken," but it means the audit's requested categories of **Dropdowns, Tabs, real Select components, Pagination, and Context menus do not exist anywhere in the shipped product** — there is nothing to find broken because nothing was built with them.

See `BrokenInteractionReport.md`, `DeadClickReport.md`, `NavigationAudit.md`, and `FeatureCompletenessMatrix.md` for prioritized detail on the above.
