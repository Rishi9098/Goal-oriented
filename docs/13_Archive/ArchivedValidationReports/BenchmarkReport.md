# Benchmark Report

**Date:** 2026-07-05
**Environment:** Local development machine, single process, warm Python interpreter. These are directional/relative numbers for regression-tracking purposes, not production SLA measurements — no load-testing infrastructure exists in this repo (see below), so there is no multi-request-concurrency or production-hardware figure to report honestly.

---

## Methodology

Each benchmark below calls the actual production function directly (not through the HTTP layer, to isolate compute cost from ASGI/network overhead), with one untimed warm-up call followed by 10 timed runs; the median is reported. All benchmarks are reproducible with the inline Python snippets shown — there is no dedicated `benchmarks/` directory or `pytest-benchmark` integration in this repo today (see Recommendations).

## Core Compute Benchmarks

| Function | Scenario | Median (10 runs) |
|---|---|---|
| `monte_carlo.run_simulation()` | 10,000 paths, 240-month horizon — the production default for `/simulate` | **43.2ms** |
| `monte_carlo.run_simulation()` | 2,000 paths — the fast-probe path used by `quick_probability`/`quick_probability_async` for every goal-refresh call | **8.7ms** |
| `optimizer.generate_suggestions()` | 5-suggestion generation, each internally running its own probability estimate (so this cost is a small multiple of the 2,000-path figure above) | **53.2ms** |

## Concurrency Benchmark (existing, not newly written)

`refresh_goal_probabilities`'s `asyncio.gather` dispatch (AUDIT #9, prior session) already has a dedicated concurrency-proof test (`TestRefreshGoalProbabilitiesConcurrency`) that asserts more than one simulation is genuinely in-flight simultaneously, rather than measuring wall-clock speedup directly — this is the right kind of test for proving *the fix works* (no more artificial serialization) without depending on timing-sensitive assertions that would be flaky in CI. No new concurrency benchmark added this session since one already exists and still passes.

## Backend Test Suite Runtime

```
164 tests: 65.6s - 65.9s wall clock (two independent runs this session, consistent)
```

## Frontend Build Time

```
vite build: 388ms (client bundle), full nitro/wrangler output generation: a few seconds total
```

---

## What This Report Does NOT Contain (and why)

- **Load/throughput benchmarks** (requests/sec, p50/p95/p99 latency under concurrent load): no k6, Locust, wrk, or similar tool is installed in this repo. Fabricating numbers for a load-testing setup that doesn't exist would be worse than reporting nothing — flagging the gap instead.
- **Memory/allocation profiling**: no `memray`/`tracemalloc` harness exists. Given the earlier validation pass found no unbounded in-process state beyond the already-fixed/tested rate-limiter buckets, a full memory-profiling pass would be measuring a system with no known leak candidates — lower priority than standing up load testing first.
- **Database query benchmarks**: no `EXPLAIN ANALYZE` baseline captured. The 9 routers reviewed all issue single, indexed, `user_id`-scoped queries with no N+1 patterns (see `PerformanceReport.md`), so there's no specific slow query to benchmark yet.

---

## Remaining Risks

- Without a load-testing harness, the actual behavior of `uvicorn`'s 4 worker processes under concurrent Monte Carlo requests (CPU-bound work competing for the same cores) is unverified. The inline-simulation architectural decision (`docs/architecture.md`) is predicated on p99 latency staying under 200ms — that assumption has only ever been checked via single-request timing, never under realistic concurrent load.

---

## Recommendations

1. If this project scales past its current single-developer/QA-driven testing model, the highest-value addition here is a minimal `k6` script hitting `/simulate` and `/simulate/optimize` at increasing concurrency, specifically to validate the "inline vs. worker queue" threshold in `docs/architecture.md` against real concurrent load rather than single-request timing.
2. Consider `pytest-benchmark` for the three functions measured here, so these numbers become a tracked regression gate in CI rather than a one-time manual measurement.
