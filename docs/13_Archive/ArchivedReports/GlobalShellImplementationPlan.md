# Global Shell — Implementation Plan

**Date:** 2026-07-08
**Status:** Planning only. No code written. This document sequences the work described in `GlobalShellArchitecture.md`, `GlobalSearchDesign.md`, `NotificationCenterDesign.md`, `ProfileMenuDesign.md`, and `KeyboardShortcutDesign.md` — it does not repeat their reasoning, only their execution order, dependencies, risk, and effort.
**This plan is not an authorization to begin building.** Per instruction, implementation should not start until this plan itself is reviewed and approved.

---

## Guiding principle for sequencing

Order phases by **(lowest risk + highest already-built-asset reuse + closes a real gap)** first, and **(new backend schema + new persisted state)** last. This puts the one item with a concrete, user-facing functional gap — mobile users cannot currently sign out at all — ahead of the two items that are "merely" currently-dead decorative elements, and puts the only phase requiring new database tables last, after the shared foundation it would depend on is proven.

---

## Phase 0 — Shell foundation (prerequisite for everything else)

**Status: ✅ Complete (2026-07-08).** See `PROJECT_STATE.md`'s "Global Shell — Phase 0" entry and `PR_REPORT_Phase0.md` for the full pipeline (Dependency Validation, Architecture Review, Performance Baseline/Comparison, Design Review). Implemented as designed below, with one addition the design didn't originally anticipate: one route (`app.family.add.tsx`) has a title that depends on a search param, not just which route matched — `staticData` alone can't express that, so a narrow `useShellTitle()` context-based override (`code/src/lib/shell-title.ts`) was added for that single case. Measured results: `auth.me()` requests across a 6-navigation sequence dropped from 14 to 2; plan-health (`dashboard`) requests dropped from 12 to 0. Phases 1–3 below are unaffected by this addition and remain not started.

**What:** Promote `AppShell` from a per-route-instantiated component to a persistent layout mounted once at `app.tsx`'s layout-route level (`<Outlet/>` for content, page title supplied via a lightweight mechanism instead of a per-screen prop), and introduce the single `GlobalShellProvider` described in `GlobalShellArchitecture.md` §4, replacing the current raw `useEffect`+promise calls to `auth.me()` and `api.getDashboard()` with `useQuery`-backed equivalents.

**Why first:** every other phase needs shell state that survives navigation (an open palette, an unread count, a mid-transition sign-out) — building any of them on top of today's remount-on-every-navigation shell means solving this problem partially, three more times, inconsistently. This is purely an internal refactor of existing, already-working code; no new user-facing behavior ships in this phase.

**Risk:** Low-to-medium. This touches the one component that wraps every authenticated screen, so a regression here is maximally visible — but the change is mechanical (move a render location, replace two data-fetching calls with equivalent cached versions) rather than a redesign, and the existing 20-route test surface (manual + the app's existing patterns) gives a fast way to confirm nothing broke.

**Dependencies:** None — this can start immediately.

**Exit criteria:** Every existing route still renders identically; sidebar/mobile-nav active-state highlighting, sign-out, and the plan-health card all still work exactly as before; `auth.me()`/`api.getDashboard()` are each called once per session (or once per their natural `staleTime`), not once per navigation — verifiable via a network-tab check during manual click-through of several routes in sequence.

**Estimated effort:** Small-medium (a few hours) — mechanical refactor, no new features.

---

## Phase 1 — Profile Menu

**What:** Wire the existing `components/ui/dropdown-menu.tsx` (desktop) and `components/ui/drawer.tsx`/`vaul` (mobile) to the avatar element per `ProfileMenuDesign.md`: identity header, Profile link, Settings link, Sign out (reusing the existing `handleSignOut` handler verbatim).

**Why second:** closes the confirmed mobile sign-out gap (§0 of `ProfileMenuDesign.md`) — the single highest-value, lowest-effort item in this entire capability, since it needs zero new backend work, zero new dependencies (everything required is already installed), and reuses a handler that is already correct and tested.

**Risk:** Low. No new state model beyond "is this menu open" (a boolean in `GlobalShellProvider`), no new data fetching beyond identity data the header already needs today.

**Dependencies:** Phase 0 (for the shared open/closed state and to avoid the avatar's menu-open state resetting on a stray re-render).

**Exit criteria:** Avatar becomes a real, keyboard-operable button (`Tab` reaches it, `Enter`/`Space` opens the menu, arrow keys move through items, `Escape` closes and returns focus to the avatar); Sign out from the menu produces identical behavior to the existing sidebar Sign out button; on a mobile viewport, Sign out is reachable for the first time without any code existing today to reach it.

**Estimated effort:** Small (roughly a day, mostly wiring + the mobile-drawer breakpoint logic + focus-management verification).

---

## Phase 2 — Keyboard shortcuts + Global Search

**What:** Wire the existing `components/ui/command.tsx` (`cmdk`-based) to the header search bar per `GlobalSearchDesign.md`: client-side aggregation over already-cached React Query data (goals, family members, insurance, schemes) plus a static navigation/quick-actions list; global `⌘K`/`Ctrl+K` listener per `KeyboardShortcutDesign.md`; `localStorage`-backed recent searches scoped per user.

**Why third:** the second-lowest-risk phase — no new backend endpoint (per `GlobalSearchDesign.md` §3's explicit V1 decision), no new persisted schema, but it does introduce the first genuinely new piece of logic (cross-entity fuzzy matching/grouping) rather than pure wiring, and the global keyboard listener needs cross-browser verification (Chrome/Firefox/Safari, per `KeyboardShortcutDesign.md` §2) that Phase 1 didn't require.

**Risk:** Medium. The global `document`-level keydown listener is the riskiest single piece of new code in this entire plan — it must not conflict with existing form inputs, the Goals page's "New goal" modal, or browser-native shortcuts, and must be properly cleaned up to avoid duplicate-listener bugs across the now-persistent (per Phase 0) shell lifecycle.

**Dependencies:** Phase 0 (persistent shell for a listener attached once, not per-route) and benefits from, but does not strictly require, Phase 1 (shared mutual-exclusion-of-overlays logic).

**Exit criteria:** `⌘K` opens the palette from every screen exactly once per press (no double-open from a leftover listener); typing filters across all four entity groups plus navigation items with the loading/empty states specified in `GlobalSearchDesign.md` §7; selecting a result navigates correctly and closes the palette; recent searches persist across a page reload within the same session and clear on sign-out; verified specifically in Chrome, Firefox, and Safari per this project's own minimum browser-testing standard.

**Estimated effort:** Medium (a few days) — the aggregation/ranking logic and the cross-browser keyboard verification are the bulk of the time, not the UI wiring itself.

---

## Phase 3 — Notification Center

**What:** New backend tables (`notification_seen_markers`, `notifications`, per `NotificationCenterDesign.md` §3), a new small backend service/router exposing unread count + panel list + mark-read/dismiss actions, and frontend wiring of the bell to a lazy-loaded panel with React Query polling (`refetchInterval: 120_000`, `refetchOnWindowFocus: true`).

**Why last:** the only phase requiring new database migrations and new backend endpoints — appropriately sequenced after the shared frontend shell foundation (Phase 0) and the established overlay/keyboard patterns (Phases 1–2) are already proven, so this phase can focus entirely on its own genuinely new surface (schema + polling) rather than also debugging shell-foundation issues discovered along the way.

**Risk:** Medium-high, concentrated entirely in the backend: the dedupe-key design in `NotificationCenterDesign.md` §2 is the one piece of genuinely new architectural reasoning in this whole plan (not just wiring existing assets) and should go through this project's standard Dependency Validation → Root Cause Analysis → Implementation → Testing → Live Verification pipeline on its own, the same rigor applied to every Milestone 2.1 finding this session, rather than being folded into a larger "ship the whole shell" change.

**Dependencies:** Phase 0 (shared unread-count state feeding the header badge without a per-route refetch) and Phase 1/2's established overlay-and-focus patterns (the notification panel should look and behave like a sibling of the palette and profile menu, not a fourth bespoke pattern).

**Exit criteria:** New migration applies cleanly (additive-only, per Engineering Constitution Rule 3) with a real upgrade/downgrade cycle tested against a real database (Rule 9); insurance/scheme notifications correctly appear when their underlying live condition is true and correctly disappear when it resolves, without any explicit cleanup job (the property `NotificationCenterDesign.md` §2 designs for); unread badge count matches the panel's actual unread rows; full backend test coverage for the new service (≥80%, per this project's standing testing bar) before this phase is considered done.

**Estimated effort:** Medium-large (most of a sprint) — the majority of this is backend schema/service/test work, not frontend.

---

## Cross-cutting risks that apply across all four phases

1. **Scope creep back toward the unused `components/ui/` library as a whole.** This plan reuses exactly four specific primitives (`command.tsx`, `dropdown-menu.tsx`, `drawer.tsx`, and the Radix packages behind them) because they map precisely onto this capability's needs — it is not a license to start wiring up the other ~46 unused files opportunistically. Each future use of an unused primitive should get its own justification, not ride along on this plan's momentum.
2. **Mobile-viewport testing must be real, not assumed.** Per this project's own web-testing standard (screenshot key breakpoints, verify touch interactions), each phase's exit criteria should include an actual mobile-viewport pass, not just a desktop verification with a mental note that "it should also work on mobile" — Phase 1 specifically exists to fix a mobile-only gap, so mobile verification is not optional there.
3. **Do not let Phase 3 pressure a shortcut through the `Recommendation`/`RecommendationCitation` tables.** `NotificationCenterDesign.md` §2 already explains why those tables are the wrong foundation; the temptation to "just reuse what's already there" should be resisted with that reasoning in hand, not re-litigated under implementation time pressure.

## Explicitly not planned here

Per the review instruction, this plan sequences design work already produced — it does not itself authorize starting Phase 0. The next step, if this plan is approved, is a standard Dependency Validation for Phase 0 specifically (the smallest, first, prerequisite unit of work), following this project's established per-finding pipeline rather than treating "Global Shell" as one undifferentiated implementation effort.
