# Performance Baseline — Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Method:** Real browser instrumentation against the running application — no estimates. Two independent measurement techniques were used, and their results corroborate each other.

---

## Method 1: Real network request capture

A fresh test account (`phase0-perf-2026-07-08@example.com`, cleaned up after) was created, signed in, and the network log was captured filtered to `api/v1` (excluding Vite's dev-server module-loading noise, which is unrelated to this measurement). Starting from the Dashboard (already mounted from login), 6 sidebar-click navigations were performed in sequence: **Goals → Family → Reports → Settings → AI Copilot → Dashboard.**

**Raw, measured request counts across this sequence:**

| Endpoint | Count |
|---|---|
| `GET /api/v1/auth/me` | **14** |
| `GET /api/v1/dashboard` | **12** |
| `GET /api/v1/goals` | 2 (expected — Dashboard's own goals list, fetched twice because Dashboard was visited twice in the sequence) |
| `GET /api/v1/family/dashboard`, `GET /api/v1/family` | 1 each (expected — Family screen's own data, visited once) |
| `GET /api/v1/reports/summary` | 1 (+2 CORS `OPTIONS` preflights, browser-level, not application calls) |

**Interpretation:** `auth/me` and `dashboard` are called far more often than any screen-specific data (`goals`, `family`, `reports/summary`, each called once or twice, exactly matching how many times their own screen was actually visited). This is the direct, measured signature of `AppShell` re-fetching both on every single navigation, regardless of which screen was the destination — 6 navigations produced roughly 12–14 calls to endpoints that have no reason to be called more than once per session.

**Note on the 14-vs-12 discrepancy (reported honestly, not smoothed over):** the two counts are not identical. The most likely explanation, consistent with code already inspected during Dependency Validation: `app.copilot.tsx` contains its own **second, independent** `auth.me()` call site (separate from `AppShell`'s), and this sequence passed through the Copilot screen once — meaning the true count attributable to `AppShell` alone is closer to 12–13, with the remainder coming from that separate, pre-existing, out-of-scope call site (see `ArchitectureReview_Phase0.md` §8 — `app.profile.tsx` has a similar independent call; `app.copilot.tsx` evidently does too and was not previously catalogued as such). This is flagged as an observation, not resolved here, since only `AppShell`'s own fetches are in scope for Phase 0.

## Method 2: Direct DOM node-identity proof (independent corroboration)

A reference to the live `<aside>` (sidebar) and `<header>` DOM nodes was captured via injected JavaScript immediately after reaching the Dashboard. A single sidebar-click navigation to Goals was then performed, and the same DOM query was re-run:

```
Before navigation: captured references to <aside> and <header>
After navigating Dashboard → Goals:
  sidebarSameNode: false
  headerSameNode: false
  sidebarStillInDocument: false   ← the ORIGINAL sidebar node is no longer attached to the page at all
```

**This is direct, undeniable proof that `AppShell` is not merely re-rendering on navigation — it is being fully unmounted and a new instance is being mounted in its place.** A re-render would have produced `sidebarSameNode: true` (same object, updated in place); a remount destroys the old node entirely and creates a new one, which is exactly what was observed. This corroborates, independently of the network evidence, the root cause documented in `ArchitectureReview_Phase0.md` §1–2.

## Summary of the measured baseline

| Metric | Measured value |
|---|---|
| `auth.me()` network requests across 6 navigations | **14** |
| Plan-health (`GET /dashboard`) network requests across 6 navigations | **12** |
| `AppShell` DOM identity across a single navigation | **Confirmed different node — full remount, not a re-render** |
| Screen-specific data calls (goals/family/reports) | Exactly matches visit count (1–2 each) — **not** over-fetching; only the shell's own two data needs are |

**What "unnecessary rerenders" turned out to actually be:** the investigation found something more expensive than excess re-renders — **unnecessary full unmount/remount cycles** of the entire shell subtree (sidebar, header, and all their internal state) on every single navigation. This is the condition Phase 0's implementation must eliminate, and this document is the "before" measurement against which `PerformanceComparison.md` will report the "after" numbers once Step 7 re-measures using the identical method.
