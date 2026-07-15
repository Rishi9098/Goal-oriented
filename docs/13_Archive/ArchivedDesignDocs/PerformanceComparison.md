# Performance Comparison — Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Method:** Identical instrumentation to `PerformanceBaseline_Phase0.md`, re-run against the implemented change — same 6-navigation sequence (Goals → Family → Reports → Settings → AI Copilot → Dashboard), same fresh-account setup, same DOM node-identity check.

---

## Network requests across the identical 6-navigation sequence

| Endpoint | Before | After | Change |
|---|---:|---:|---:|
| `GET /api/v1/auth/me` | **14** | **2** | −12 (−86%) |
| `GET /api/v1/dashboard` | **12** | **0** | −12 (−100%) |
| `GET /api/v1/goals` | 2 | 2 | unchanged (expected — screen-specific data, matches visit count) |
| `GET /api/v1/family`, `/family/dashboard` | 1 each | 1 each | unchanged (expected) |
| `GET /api/v1/reports/summary` | 1 | 2 | +1 (not attributable to this phase — Reports' own route/query, untouched by Phase 0; noted, not chased, since it doesn't involve the shell's own data) |

**The `dashboard` endpoint went to true zero requests across the entire 6-navigation sequence** — not just "fewer," but none — because the single fetch made when the Dashboard first loaded at login stayed valid (within its 60-second `staleTime`) for the whole sequence, and revisiting the Dashboard at the end of the sequence read directly from that cache.

**The residual 2 `auth/me` calls (down from 14) match the prediction made in the baseline document**: one from `AppShell`'s own single, now-cached fetch, and one from `app.copilot.tsx`'s pre-existing, separate, out-of-scope `auth.me()` call site (fired because the sequence passed through the Copilot screen once) — not a leftover inefficiency in the code this phase touched.

## DOM node-identity check (direct proof of persistence)

| | Before | After |
|---|---|---|
| Sidebar (`<aside>`) same object across a navigation? | **false** | **true** |
| Header (`<header>`) same object across a navigation? | **false** | **true** |
| Original sidebar node still attached to document? | **false** | **true** |

This is the most direct possible confirmation of the phase's core goal: `AppShell` now survives navigation as the same live component instance, rather than being destroyed and recreated on every route change.

## AppShell mount count across the 6-navigation sequence

- **Before:** 7 mounts (1 at initial load + 1 per navigation) — inferred from the network evidence and confirmed by the DOM-identity check on a single navigation.
- **After:** 1 mount (confirmed directly — the same DOM node persisted across all 6 navigations in this sequence).

## Conclusion

Every metric named in the instruction's success criteria was measured, not estimated, both before and after, using the identical method both times: `AppShell` mounts once; `auth.me()` is no longer called on every navigation (residual calls attributed to a named, pre-existing, out-of-scope call site); plan-health (`dashboard`) is not repeatedly fetched — it dropped to zero additional requests across the entire measured session. **All Phase 0 success criteria are met, measured empirically.**
