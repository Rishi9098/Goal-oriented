# Architecture Drift Review — Continuous Architecture Health Checkpoint

**Date:** 2026-07-07
**Trigger:** Run ahead of its originally-noted schedule (`PROJECT_STATE.md` had it slated for "after Task 5") per explicit instruction, as part of the Milestone 2 resumption gate — a reasonable point to run it, since a full Stabilization Sprint just landed non-trivial backend changes. Investigation only; no code changed.
**Scope:** Verify no architecture drift, no duplicate services/APIs/calculations, no deprecated consumers, no broken ownership model, no policy inconsistencies — across the whole backend, not just the files the Stabilization Sprint touched.

---

## No Architecture Drift

**Router thinness (Rule 1):** Re-verified `routers/goals.py`, `routers/dashboard.py`, `routers/reports.py` post-sprint — all three remain thin. `goals.py`'s `create_goal`/`update_goal` each call exactly one service function (`calculate_goal_probability`) and one ORM operation; no branching business logic was introduced in the router during this sprint. **Pass.**

**Additive-only migrations (Rule 3):** No migration was touched or needed by any of the three PCA fixes — confirmed no new Alembic revision exists for this work. **Pass, trivially — not applicable to this sprint.**

**No premature abstraction (Rule 7):** The centralization performed during PCA-3 (`calculate_goal_probability`) reduced abstraction count (two implementations → one), consistent with this rule rather than in tension with it. **Pass.**

## No Duplicate Services

Grepped the entire backend for every remaining caller of the Monte Carlo engine:

| Caller | File | Persists a result? | Purpose |
|---|---|---|---|
| `calculate_goal_probability` | `services/planning_service.py` | Yes — the sole persister | Centralized trigger (goal create/update) |
| `generate_suggestions` → `_prob` | `services/optimizer.py` | No | Read-only exploration for `/simulate/optimize` |
| `simulate()` router | `routers/simulate.py` | Yes, but to a different, append-only table (`simulations`) | Explicit, user-triggered full-engine run — a deliberately separate feature, not a duplicate of goal-probability calculation |

No second implementation of "compute a goal's probability" exists anywhere in the codebase — confirmed via `grep` for `refresh_goal_probabilities`/`_refresh_probability` (both removed during PCA-3): zero remaining references anywhere in `app/` or `tests/`. **Pass.**

## No Duplicate APIs

- `GET /api/v1/family` has exactly one backend implementation (`routers/family.py`, Task 2) and, as of PCA-2, exactly one frontend client function (`api.getFamilyHome()`). `FutureCompatibilityAudit_Light.md` confirms Task 5 will reuse this same client function rather than writing a second one. **Pass.**
- `GET /dashboard` and `GET /reports/summary` remain two distinct, legitimately different endpoints (different response shapes, different consumers) that both correctly call the same single `get_dashboard()` service function — this is normal, sanctioned reuse, not duplication. **Pass.**

## No Duplicate Calculations

This is the exact category PCA-3 fixed. Re-verified post-fix: `plan_health_score` is computed in exactly one place (`compute_plan_health`, `planning_service.py`), called from exactly one place (`get_dashboard`). A goal's `probability`/`on_track` is computed in exactly one place (`calculate_goal_probability`), called from exactly two, both legitimate (create, update). **Pass.**

## No Deprecated Consumers

Re-ran the same check that originally surfaced PCA-2, now covering the whole codebase rather than just Profile:

```
grep -rn "marital_status|\.dependents\b" code/src/ --include="*.tsx" --include="*.ts"
```

Zero matches remain in any `.tsx`/`.ts` file (the one prior match, `app.profile.tsx`, was resolved by PCA-2). `financial_assumptions.tax_rate` (the second field Rule 11 exists to track) — confirmed no remaining frontend reader; it remains marked deprecated per the Foundation Reconciliation, with no removal date yet, which is the documented, acceptable state per Rule 11's own text ("a removal plan exists" — the plan is documented in `FoundationReconciliationReport.md`, not yet executed). **Pass — no undocumented deprecated-field consumer exists anywhere in the codebase today.**

## No Broken Ownership Model

The household-ownership check pattern (Task 2, `family_service.py`) is untouched by all three Stabilization Sprint fixes — none of PCA-1/2/3 read or write `households`/`household_members`/`dependents` in a way that bypasses or duplicates this check. Goal ownership (`goals.user_id`) is likewise untouched — `calculate_goal_probability` operates on an already-authorized `Goal` object passed in by the router, after the router's own existing ownership-scoped query; it does not introduce a second ownership path. **Pass.**

## No Policy Inconsistencies

Checked `docs/ENGINEERING_CONSTITUTION.md`'s 11 rules against every Stabilization Sprint change for internal consistency:

- Rule 4 (never invent a financial fact) — untouched; no new financial constant was introduced by any of the three fixes.
- Rule 9 (verify against real infrastructure) — satisfied by all three fixes' live verification steps (documented in each `PR_REPORT.md`).
- Rule 11 (Deprecation Completion, added during PCA-2) — the rule itself is new but consistent with, not contradicting, Rules 1-10; it formalizes a discipline (grep the whole codebase before considering a deprecation "done") that Rules 6 and 9 already implied for testing and verification generally.

No rule added or invoked during this sprint conflicts with any pre-existing rule. **Pass.**

---

## Summary

| Check | Result |
|---|---|
| Architecture drift | None found |
| Duplicate services | None found |
| Duplicate APIs | None found |
| Duplicate calculations | None found (the one that existed — PCA-3 — is now fixed) |
| Deprecated consumers | None found (the one that existed — PCA-2 — is now fixed) |
| Broken ownership model | Not found; untouched and intact |
| Policy inconsistencies | None found |

**Architecture Health Checkpoint: PASS.** No new drift introduced by the Stabilization Sprint; the sprint's own fixes measurably improved this checkpoint's baseline (one fewer duplicate calculation path, one fewer deprecated-field consumer, one new formal rule closing the exact gap PCA-2 exposed).
