# Performance Report

**Date:** 2026-07-05
**Method:** Direct measurement on this machine — no figures in this report are copied from documentation without independent verification. Where a documented figure was checked against a live measurement, both are shown.

---

## Summary

The Monte Carlo engine — the one genuinely CPU-bound hot path in this application — measures faster in practice than `docs/architecture.md` claims (43ms actual vs. ~80ms documented, for the full 10,000-path run). Frontend bundle sizes are within this project's own documented budget (`rules/ecc/web/performance.md`: App page ≤ 300kb JS gzipped) but not by a wide margin, and are worth monitoring as more chart/animation libraries get pulled in. No performance regressions were introduced by this session's type/lint fixes (they are annotation-only changes with zero runtime behavior difference, confirmed by the unchanged 164/164 test pass and unchanged Monte Carlo timing).

---

## Backend — Monte Carlo Engine

Measured directly via `run_simulation()`, 10 runs each, median reported (warm interpreter, single process, this machine — not a production server, treat as relative/directional, not an SLA number):

| Scenario | Measured (median) | Documented claim (`docs/architecture.md`) |
|---|---|---|
| Full run — 10,000 paths, 240-month horizon | **43.2ms** | ~80ms |
| Fast probe — 2,000 paths (`quick_probability`, used by the goal-refresh path) | **8.7ms** | not documented separately |

The full-run figure is well under the 200ms p99 threshold `docs/architecture.md` sets as the trigger for moving simulation to a Celery/Redis worker queue — no action needed there today. This session did not change `docs/architecture.md`'s ~80ms figure since it's described as an estimate ("runs in ~80ms on a modern CPU") rather than a measured claim, and the actual number is comfortably inside the range that estimate implies for decision-making purposes (still far under 200ms).

## Backend — Test Suite

```
164 tests, 65.6s wall clock, 96.43% coverage
```
No single slow test identified as an outlier during this run; the wall-clock time is dominated by real async DB round-trips (SQLite via the test fixture), not simulation compute.

## Frontend — Bundle Size

Measured from a real `bun run build` output in `code/.output/public/assets/` (gzip computed directly with `gzip -c | wc -c`, not estimated):

| Chunk | Raw | Gzipped |
|---|---|---|
| `app.index-*.js` (dashboard route) | 393KB | 104KB |
| `index-*.js` (shared vendor: TanStack Router, Recharts, Framer Motion, etc.) | 387KB | 115KB |
| `react-*.js` (React runtime) | 118KB | 37KB |

Combined initial JS for the dashboard route ≈ **256KB gzipped** (vendor + React + route chunk). Against this repo's own documented budget (`~/.claude/rules/ecc/web/performance.md`: App page ≤ 300KB gzipped JS), this is within budget but using ~85% of it. The largest single contributor to the shared vendor chunk is Recharts + Framer Motion + `@tanstack/react-router` (visible in the server-bundle breakdown during build: Recharts alone is ~515KB unminified/~97KB gzip server-side, similar order client-side). Route-level code splitting is already working correctly (each `app.*` route ships its own small chunk, 8-36KB, rather than one monolithic bundle) — this is the main lever already pulled correctly; the remaining lever would be lazy-loading Recharts specifically on pages that don't render charts on first paint, if the budget becomes a real constraint.

## Database

No N+1 query patterns found across the 9 routers read in Phase 2 of the QA pass (each list/detail endpoint issues exactly one `SELECT`, scoped by `user_id` and `is_active`). `get_dashboard()` is deliberately reused by both the dashboard and reports routers to avoid double-computing goal probabilities on the same request cycle (documented in a code comment in `reports.py`) — a real, intentional optimization already in place, not a new finding.

---

## Categories Not Applicable / No Infrastructure Exists

- **Load/stress testing**: no k6, Locust, or similar harness exists in this repo. Not fabricated here — see `BenchmarkReport.md` for what a minimal setup would look like if this becomes a priority.
- **Cache hit rates**: no caching layer exists (no Redis, no in-process cache beyond the rate-limiter's token buckets, which aren't a data cache). Not applicable.
- **Network usage / CDN**: out of scope for a local dev-environment measurement pass; would need a real deployment target to measure meaningfully.

---

## Remaining Risks

- Frontend bundle is at ~85% of its own documented budget for the busiest route. Not a current problem, but the next chart-heavy feature addition could push it over.
- Monte Carlo timing was measured on this development machine, not the production target — the 200ms trigger threshold in `docs/architecture.md` should be re-validated against real deployment hardware before being treated as a hard guarantee.

---

## Recommendations

1. If another visualization library gets added, audit whether Recharts can be dynamically imported (`await import("recharts")`) only on routes that render charts, per this repo's own performance rules on dynamic imports for heavy libraries.
2. No backend changes recommended — the engine has real headroom against its own stated threshold.
