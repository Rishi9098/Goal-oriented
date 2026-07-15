# Search Performance Report — Phase 2 (Global Command Palette)

**Date:** 2026-07-08
**Method:** Real network capture + direct behavioral observation during live verification. Where a claim could not be measured with the tools available this session, it is marked as such rather than asserted as measured.

---

## Initial bundle impact

**Zero new dependencies.** `cmdk` (`^1.1.1`) and `@radix-ui/react-dialog` (backing `Dialog`/`DialogContent`) were already in `package.json` before this phase — confirmed in `DependencyValidation_Phase2.md` §1. The only new code is `global-palette.tsx` itself (~300 lines) plus a handful of lines in `app-shell.tsx` and `app.goals.tsx` — no new package.json entries, no bundle-size regression from third-party code.

## Lazy loading — verified with real network capture

Per the design (`ArchitectureReview_Phase2.md` §3/§9), the four entity queries (`goals`, `family-home`, `family-schemes`, `family-insurance`) are gated behind `enabled: everOpened`. Verified directly during live testing: on a fresh session, navigating to the Dashboard and letting it load fully triggers only the Dashboard's own requests (`auth/me`, `dashboard`, `goals` — the last one because the Dashboard's own goal-preview widget already fetches it, unrelated to the palette) — none of `family-home`, `family-schemes`, or `family-insurance` fire until `⌘K` is pressed for the first time. This matches the intended "zero cost to a session that never invokes search" property exactly.

## Search latency — observed, not independently benchmarked

At the data volumes this product actually has per household (single digits to low tens of goals/members/schemes/policies), `cmdk`'s in-memory fuzzy scorer operates well under any perceptible threshold — confirmed by direct observation during live testing: typing "Goa", "Priya", "Emergency", and "Create Goal" each produced correctly-filtered results with no visible lag between keystroke and re-render, across several repeated tests. No dedicated latency-measurement harness was built for this, since the data volumes involved (single households, not a shared corpus) make sub-frame latency the expected, uninteresting result — a synthetic benchmark against these volumes would not surface anything a stopwatch couldn't already confirm by eye.

## Re-renders — architectural reasoning, not profiler-measured

**Honest limitation:** no React DevTools Profiler session was run this session to produce an exact re-render count. What is confirmed instead: toggling `paletteOpen` is local `AppShell` state — the same category of state as `moreOpen` (mobile nav, pre-existing) and Phase 1's `DropdownMenu` open state, both of which have operated in this codebase without observed performance complaints. Opening/closing the palette does not trigger any `useQuery` refetch in the currently-mounted route's own content (query state lives in React Query's cache, independent of `AppShell`'s render cycle) — confirmed by network capture showing zero additional requests to route-specific endpoints (e.g., `reports/summary`, `family/insurance`) when the palette is opened and closed while sitting on an unrelated page.

## Keyboard listener count — verified via consistent behavior, not a raw count

No browser API was available this session to enumerate `document`-level listeners directly from page-context JavaScript. Instead, this was verified **behaviorally**: `⌘K` and `Ctrl+K` were each pressed multiple times across multiple different pages (Dashboard, Goals, Family Member detail) during live verification, and every single press produced exactly one open/close toggle — no flicker, no double-toggle, no missed press. A duplicate-listener bug would produce visibly inconsistent behavior (two listeners firing on one keypress nets to no visible change, or an immediate open-then-close flicker) — none was observed across roughly a dozen presses in this session. This is consistent with, and expected from, Phase 0's own proven guarantee that `AppShell` — and therefore any `useEffect` inside it — mounts exactly once per session.

## Summary

| Metric | Result |
|---|---|
| New dependencies | Zero |
| Network requests before first palette open | Zero (verified) |
| Network requests per subsequent open (cached) | Zero, when data is already loaded |
| Search input lag (observed) | None perceptible |
| Duplicate keyboard listeners | None observed across ~12 presses on 3 different pages |
| Route re-fetch triggered by opening/closing palette | None (verified via network capture) |
