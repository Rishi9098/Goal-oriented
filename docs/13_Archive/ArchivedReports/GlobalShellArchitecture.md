# Global Shell Architecture Review

**Date:** 2026-07-08
**Status:** Architecture review / design only. No code written, no implementation started.
**Framing:** Global Search, the Notification Bell, the Profile Avatar Menu, and the ⌘K keyboard shortcut are treated here as **one capability** — "the Global Shell" — because they share one host component (`components/app-shell.tsx`), one header, one set of overlay/positioning concerns, and (per this review's central finding) should share one piece of new shared state rather than four independent, uncoordinated pieces of local state.

---

## 1. What already exists (verified by direct code inspection)

This is the single most important input to this design: **the building blocks are already in the dependency tree and already scaffolded in the component library** — they were never wired up, not never started.

| Asset | Location | State |
|---|---|---|
| `cmdk` (Command palette engine — the library behind Linear/Vercel/GitHub-style ⌘K menus) | `code/package.json` dependency | Installed, unused |
| `@radix-ui/react-dropdown-menu` | `code/package.json` dependency | Installed, unused |
| `@radix-ui/react-popover`, `@radix-ui/react-avatar` | `code/package.json` dependencies | Installed, unused |
| `components/ui/command.tsx` — a **fully built** `CommandDialog`/`CommandInput`/`CommandList`/`CommandItem`/`CommandEmpty`/`CommandShortcut` set, styled and ready | `code/src/components/ui/command.tsx` | Complete, zero import sites in the app |
| `components/ui/dropdown-menu.tsx` — full Radix dropdown scaffold (Trigger, Content, Item, CheckboxItem, RadioGroup, Separator, Shortcut) | `code/src/components/ui/dropdown-menu.tsx` | Complete, zero import sites in the app |
| `components/ui/popover.tsx`, `components/ui/avatar.tsx` | same directory | Complete, zero import sites |

This directly explains the Interactive Product Audit's finding: the Global Shell wasn't abandoned mid-build — it was scaffolded generically (as most of `components/ui/` was) and never connected to real data, a real keyboard listener, or the header. **The default assumption for this design should be "reuse and wire up," not "build new component primitives."**

## 2. What does not exist (verified)

- **No search backend of any kind.** No search endpoint, no full-text index, no `tsvector`/`pg_trgm`/GIN index anywhere in any of the 9 Alembic migrations.
- **No notification backend of any kind.** No `Notification` model, no notification router, no read/unread column anywhere.
- **No user preferences storage.** The `User` model (`backend/app/models/user.py`) has exactly: `email`, `hashed_password`, `full_name`, `is_active`, `is_verified`, timestamps. No JSON preferences column, no theme field, no notification-settings field.
- **No theme system.** `styles.css` defines a `.dark { /* same; app is dark by default */ }` — an intentionally empty override. Northstar is a **single-theme, dark-only product by explicit design decision**, consistent with `CLAUDE.md`'s "Never change the UI design system... frozen palette" instruction. This directly constrains the Profile Menu design (see `ProfileMenuDesign.md`).
- **No real-time transport.** No WebSocket or SSE library in `package.json`. Any "real-time" notification design must in practice mean polling via the React Query the app already uses everywhere else.
- **One partially-relevant, currently-dead backend table:** `Recommendation` / `RecommendationCitation` (`backend/app/models/recommendation.py`) — a full schema for persisted, citable recommendations exists in the codebase but is **never read or written by any router or service**. This is architecturally significant for Notification Center design (see `NotificationCenterDesign.md` §2) — it's either the right foundation to build notifications on, or a second, competing persistence model that needs a deliberate decision, not silent duplication.

## 3. The real architectural problem: there is no shared shell state today

Investigating "shared state / Context providers" turned up a concrete, fixable problem that predates and directly blocks good Search/Notification/Profile design:

**`AppShell` is not a persistent layout — it is re-instantiated by every route.** `app.tsx`'s `AppLayout` (the `/app` layout route) renders only `<Outlet />`; it does **not** render `AppShell`. Instead, every leaf route (`app.index.tsx`, `app.goals.tsx`, `app.family.index.tsx`, etc.) independently imports `AppShell` and wraps its own content: `<AppShell title="X">{content}</AppShell>`. The consequence: **navigating between any two `/app/*` screens fully unmounts and remounts the entire shell**, including its sidebar, header, and the `useEffect` that fetches the user's initials (`auth.me()`) and plan-health score (`api.getDashboard()`) — both fetched with a raw `useEffect`+promise, **not** `useQuery`, so neither gets the React Query cache's deduping or staleTime benefits the rest of the app relies on.

**Why this matters for this specific capability:** every one of the four features under review needs state that should *survive navigation* — an open command palette shouldn't be dismissed by the act of navigating to its own search result; an unread notification count shouldn't flicker to a loading state on every click; a profile menu's "logging out…" transition shouldn't race a shell remount. Building any of the four on top of the current per-route AppShell instantiation means re-solving this problem four times, inconsistently. **Recommendation: promote `AppShell` to `app.tsx`'s layout (rendered once, `<Outlet/>` for content, title passed via a lightweight route-context or a small `useRouterState`-derived lookup instead of a prop) as a Phase 0 prerequisite**, detailed in `GlobalShellImplementationPlan.md`. This is a refactor of existing, working code — the audit found no bug caused by it today, only a foundation problem for what's being asked now.

## 4. Proposed shared-state shape (Context, not four contexts)

One `GlobalShellProvider` (mounted once, at the promoted `AppShell` layout level) exposing:

```
currentUser: { id, fullName, email, initials } | null    — replaces the ad-hoc auth.me() call
planHealth: number | null                                  — replaces the ad-hoc getDashboard() call
commandPaletteOpen: boolean, openCommandPalette(), closeCommandPalette()
notificationsOpen: boolean, unreadCount: number
profileMenuOpen: boolean
```

Rationale for **one** provider rather than one per feature: all four pieces of state are read and toggled from the same header, need to be mutually exclusive on mobile (only one overlay open at a time on a narrow viewport — opening Search should close Notifications, etc.), and share the same "current user identity" dependency (Notifications and Profile Menu both need to know who's logged in; Search's "recent searches" needs a stable user-scoped cache key). A single provider avoids prop-drilling four independent pieces of state through the same header component and gives a single place to enforce the mutual-exclusion rule. This does **not** mean one monolithic reducer for unrelated concerns — `currentUser`/`planHealth` (data) and the three `*Open` booleans (UI state) are logically separate and should be separate pieces of context value, just delivered by one provider component for the reasons above.

React Query remains the source of truth for all *server* data (search results, notification list, user profile) — the Context only tracks *which overlay is open* and a lightweight cached copy of identity/plan-health for the header's own immediate rendering needs. This matches the project's existing pattern (React Query for all server state) rather than introducing a second state-management paradigm.

## 5. Performance and responsiveness

- **Command palette:** must not fetch anything until first opened (lazy — no cost on every page load). Once open, debounce input (≈150–200ms) before querying, per `GlobalSearchDesign.md`.
- **Notifications:** unread count is the only thing needed on every page; the full list is fetched lazily on open. Polling interval must be conservative (see `NotificationCenterDesign.md` §5) to avoid turning every idle screen into a recurring network request storm — React Query's `refetchInterval` plus `refetchOnWindowFocus` covers this without new infrastructure.
- **Profile menu:** pure client-side state, zero network cost beyond identity (already needed for the header's avatar initials today).
- **Responsiveness:** all three overlays (palette, notification panel, profile menu) need distinct mobile treatments — a centered modal/sheet is appropriate for the command palette on mobile (no room for a small popover), the notification panel and profile menu can use the same bottom-sheet pattern the existing mobile "More" nav menu already establishes (click-outside + Escape to close — already implemented once in `app-shell.tsx` and should be extracted into one shared `useDismissableOverlay` hook rather than copy-pasted a fourth time).

## 6. Summary of what this review is asking each companion document to resolve

- `GlobalSearchDesign.md` — global-vs-page-specific decision, searchable entities, backend design, ranking, recent searches, keyboard shortcut, states.
- `NotificationCenterDesign.md` — schema, read/unread, categories, real-time-vs-polling, and the `Recommendation`-table decision.
- `ProfileMenuDesign.md` — menu contents, and the theme-toggle conflict with the frozen design system.
- `KeyboardShortcutDesign.md` — ⌘K, Esc, arrow navigation, and their interaction with the existing mobile-nav Escape handler.
- `GlobalShellImplementationPlan.md` — sequencing, starting with the Phase 0 shell-promotion prerequisite above.

No code changes have been made. This document and its companions are inputs to a future planning/implementation decision, not a commitment to build.
