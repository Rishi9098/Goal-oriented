# Performance UX Audit — Phase 9

**Date:** 2026-07-13
**Scope, per the mission:** perceived performance only — loading states, transitions, skeletons, optimistic updates, prefetching, rendering. Backend calculations are explicitly out of scope (existing backend performance work is already covered separately by `PerformanceBaseline_Phase0.md`, `PerformanceReview_M2.1-P4.md`, and related reports — those are query-count/architecture concerns, not perceived-performance ones, and are not re-litigated here).
**Method:** grepped every route and component for its own loading-state implementation, compared them against each other for consistency, and live-tested the result.

---

## 1. What's already good (confirmed, not changed)

Every primary list/data screen already uses a **content-shaped skeleton** (`animate-pulse` blocks sized and laid out like the real content that will replace them) rather than a generic spinner:

- Dashboard (`app.index.tsx`) — skeleton stat cards, skeleton chart blocks, skeleton goal rows.
- Goals (`app.goals.tsx`) — skeleton goal cards matching the real card grid.
- Family (`app.family.index.tsx`) — skeleton summary card, skeleton member rows.
- Financials (`app.financials.tsx`) — skeleton table rows.
- Life Events (`app.life-events.tsx`) — skeleton history rows.

Every in-flight async action that isn't a full-page load (form saves, undo, delete, sign-in, sending a message) already shows an inline spinner *on the specific control being acted on* — e.g. Life Events' Undo button swaps its icon for a spinner and disables itself while the request is in flight (verified in `app.life-events.tsx`), Financials' save buttons do the same. This is exactly the right pattern for a discrete action (as opposed to a full-page load) and needed no change.

## 2. Finding: Reports is the one screen still using a generic spinner instead of a content-shaped skeleton

**What's actually there (verified in code, before this phase):** `app.reports.tsx`'s loading state was a single centered `Loader2` spin inside one generic `surface-card`, replacing the entire page body:

```tsx
{loading && (
  <div className="surface-card p-12 text-center">
    <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
  </div>
)}
```

This is the only primary data screen in the app still doing this — every sibling screen (Dashboard, Goals, Family, Financials, Life Events) replaced this exact pattern with a shaped skeleton in earlier work. Two concrete effects of the gap:

1. **Worse perceived performance:** a shaped skeleton lets the user see the page's structure (four stat cards, a table, a cash-flow strip) immediately, so the eventual data "fills in" rather than the whole page "popping in" all at once after a blank/spinner interval — the same reasoning that already motivated every other screen's skeleton.
2. **Inconsistency:** a user who has already seen Dashboard's or Goals' skeleton-shaped loading state, then lands on Reports and sees a completely different, unrelated loading treatment — a small but real "this doesn't feel like the same product" moment, in the same spirit as the visual-consistency work already done in Phase 6.

## 3. Decision

Replace Reports' single generic spinner with a content-shaped skeleton matching its own three sections (the 4-card stat grid, the Goal Breakdown table, the cash-flow strip) — using the exact same `surface-card` / `animate-pulse` / `bg-muted/40` conventions already established by the other five screens, not a new pattern.

**Not changed:** the "Life Events This Year" section has no skeleton because it already has no loading gate at all — it renders only once `yearEvents` arrives and is empty-safe otherwise (`yearEvents && yearEvents.length > 0`), which is the existing, correct, and already-consistent pattern for optional/secondary sections elsewhere (e.g. Dashboard's own optional cards). No backend endpoint or query was touched — this is a pure loading-state UI change over data the page already fetches.

## 4. Other perceived-performance areas checked, no gap found

- **Optimistic updates:** goal creation, life-event recording, and undo all wait for the server response before updating the UI, rather than updating the UI first and rolling back on failure. This is a legitimate, more-conservative alternative to optimistic UI (correct data over a slightly faster-feeling but potentially-wrong one for financial data), consistent with how a financial planning product should treat every write as important enough to confirm — not treated as a gap to fix in this phase.
- **Prefetching:** no route currently prefetches another route's data on hover/intent. Given the app's page count and typical navigation pattern (sidebar-driven, not deep link chains), this wasn't found to produce a noticeable perceived-performance problem in live testing — flagged as a possible future increment, not a finding that rose to the level of a fix this phase.
- **Rendering:** no unnecessary full-list re-renders or obvious layout-shift sources were found on any screen touched this session.
