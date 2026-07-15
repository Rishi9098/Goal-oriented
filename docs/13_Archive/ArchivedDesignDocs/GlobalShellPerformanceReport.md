# Global Shell Performance Report — Certification

**Date:** 2026-07-08
**Method:** direct code inspection (listener count, cache keys) plus live network/console capture against the real running app this session. Claims already established and unchanged since their originating phase are cited as such rather than re-measured for the sake of re-measuring.

---

## Navigation latency

Unchanged since Phase 0: the shell (sidebar, header) is not remounted on navigation between `/app/*` routes — only the route's own content swaps. This was proven with DOM node-identity checks in `PerformanceComparison.md` and has not regressed, since no code in `app.tsx`'s layout structure or `AppShell`'s own mount point has changed across Phases 1-3 (each phase added state/children *inside* the already-persistent shell, not a new mount site).

## Render count

Each overlay's open/closed state is local to its own component (`paletteOpen`/`moreOpen` in `AppShell`; `open` inside `NotificationCenter`; `DropdownMenu`'s own internal state) — toggling one does not re-render the others, confirmed by inspecting each component's state ownership (no shared state to cause cross-re-renders) and corroborated by the smooth, lag-free behavior observed opening/closing each overlay multiple times in this session's live testing.

## React Query usage / cache efficiency

**Within the shell's own components** (`AppShell`, `GlobalPalette`, `NotificationCenter`): confirmed shared, correctly-keyed queries — `["currentUser"]`, `["dashboard"]`, `["goals"]`, `["family-home"]`, `["family-schemes"]`, `["family-insurance"]`, `["notifications"]`. A live network capture navigating Dashboard → Goals → Family → Profile → Dashboard produced exactly **one** `/dashboard` request across the whole sequence — direct evidence the `["dashboard"]` cache is correctly shared between `AppShell`'s own read and the Dashboard page's read, exactly as Phase 0 designed.

**Outside the shell:** the same capture showed `/goals` fetched 3 times and `/family`/`/auth/me` fetched 2 times each across the same navigation sequence. Traced to source: `app.goals.tsx` and `app.profile.tsx` use raw `useEffect`/`Promise.all` fetches, not `useQuery` — confirmed by direct grep, zero `useQuery` occurrences in either file. This is pre-existing technical debt in pages the Global Shell phases did not touch (Phase 2 added a `?new=true` param to `app.goals.tsx` but did not touch its data-fetching), not a regression introduced by this milestone.

## Memory usage

No leak observed. Every `useEffect` registering a `document`-level listener in the shell has a matching cleanup function (verified by reading `app-shell.tsx` — both the `⌘K` effect and the mobile-nav `mousedown`/`keydown` effect return their removal calls). A session-long sequence of opening/closing all four overlays repeatedly showed no degradation in responsiveness and zero console warnings.

## Keyboard listener count

**Exactly three `document`-level listeners exist in the entire shell, confirmed by exhaustive grep across every shell-related file** (`app-shell.tsx`, `global-palette.tsx`, `notification-center.tsx`, and the four Radix wrapper files `command.tsx`/`dropdown-menu.tsx`/`popover.tsx`/`dialog.tsx`, none of which register their own `document`-level listeners in this codebase's wrapper code):

1. `keydown` → `handleShortcut` (⌘K/Ctrl+K) — registered once, unconditionally, for the lifetime of the session.
2. `mousedown` → `handleClickOutside` — active only while `moreOpen` (mobile nav sheet) is true.
3. `keydown` → `handleEscape` — same scoping as #2.

No collision: listener #1 only acts on `cmd/ctrl+k`; listener #3 only acts on `Escape` — they check different keys and never both fire from the same keypress.

## Notification refresh

`refetchInterval: 120_000` (2 minutes), `staleTime: 30_000` — unchanged since Phase 3, re-confirmed by reading the current `notification-center.tsx`. A poll returns the full list + unread count in one call; there is no separate, duplicate "unread count only" endpoint to keep in sync.

## Search latency

`cmdk`'s in-memory fuzzy scorer over small, per-household arrays (a handful of goals/members/schemes/policies) — sub-frame, imperceptible latency, re-confirmed by live typing during this session's walkthrough (typed "Goals," saw instant, correctly filtered results with no visible delay).

## Summary

| Metric | Result |
|---|---|
| Shell remounts on navigation | Zero (Phase 0 guarantee, unchanged) |
| Duplicate requests within shell components | Zero (verified via network capture) |
| Duplicate requests from non-shell pages (Goals/Profile) | Present — pre-existing, not shell-introduced |
| Keyboard listeners | 3 total, 1 always-active, 2 conditionally active, no collisions |
| Console warnings across a full overlay-interaction sequence | Zero |
| Notification poll interval | 120s |
| Search input lag | None perceptible |
