# Dependency Map — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. What depends on what, across screens, APIs, database tables, and other milestones — so a change in one place can be traced to everything it touches.

---

## Screen → API → Database

```
§1 Onboarding Family Step
  └─▶ POST /family/onboarding-seed
        └─▶ writes: households, household_members

§2 Family Home
  └─▶ GET /family
        └─▶ reads: households, household_members, dependents

§3-6 Add Family Member (Spouse/Child/Parent/Other)
  └─▶ POST /family/members, PUT /family/members/{id}
        └─▶ writes: household_members, dependents
        └─▶ reads (Child only): schemes, scheme_rates, scheme_eligibility_rules (via Task 3's shared service)

§7 Family Member Detail
  └─▶ GET /family/members/{id}, DELETE /family/members/{id}
        └─▶ reads: household_members, dependents, goal_household_members ⋈ goals, health_policy_coverage ⋈ health_policies
        └─▶ writes: household_members.is_active (soft-delete only)

§8 Family Goals
  └─▶ GET /family/goals, PUT /goals/{id}/family-tags
        └─▶ reads: goals (existing, unmodified query pattern)
        └─▶ writes: goal_household_members (NEW table, §0.1)

§9 Education Planning
  └─▶ PATCH /goals/{id} (existing endpoint, additively extended)
        └─▶ writes: goals.custom_inflation_rate (NEW column, §0.2)
        └─▶ reads: goal_household_members ⋈ goals (to find tagged eligible children), scheme data (SSY reuse)

§10 Family Insurance
  └─▶ GET/POST/PUT /family/insurance/*
        └─▶ reads: dependents.has_own_insurance (NEW column, §0.3), household_members
        └─▶ writes: health_policies, health_policy_coverage (existing, certified)

§11 Family Government Schemes
  └─▶ GET /family/schemes
        └─▶ reads: schemes, scheme_rates, scheme_eligibility_rules (all certified), household_members, dependents
        └─▶ (shares evaluation logic with §3-6's inline SSY check — Task 3)

§12 Family Dashboard
  └─▶ GET /family/dashboard
        └─▶ reads: aggregates of §2, §8, §10, §11's own read sets
        └─▶ reads (pass-through, not recomputed): existing planning_service.get_dashboard() output
```

---

## Schema Dependency Direction

```
Foundation (certified, migrations 001-006)
  households, household_members, dependents, huf_entities, nominees,
  health_policies, health_policy_coverage, schemes, scheme_rates,
  scheme_eligibility_rules, tax_*, recommendations, goals (existing)
        │
        │  (Milestone 2 reads/writes these; never alters their existing columns)
        ▼
Milestone 2's own migration (new, this milestone)
  + goal_household_members (references goals, household_members)
  + goals.custom_inflation_rate (nullable column on existing table)
  + dependents.has_own_insurance (nullable column on existing table)
```

No Milestone 2 change alters a Foundation table's existing column meaning, nullability, or constraint — every dependency arrow points from Milestone 2's new schema *into* Foundation's certified schema, never the reverse (a Foundation table never gains a required dependency on a Milestone 2 table).

---

## Cross-Screen Dependencies (within Milestone 2)

| Screen | Depends On (within M2) | Reason |
|---|---|---|
| §2 Family Home | §1 | Needs seeded members to display anything beyond the empty state |
| §3-6 Add Member | §2 | Entry point; also reachable directly for "+ Add a parent" etc. |
| §7 Member Detail | §3-6, §8 | Edit re-enters those forms; tagged-goals list needs §8's data |
| §8 Family Goals | §2 | Tagging requires household members to exist |
| §9 Education Planning | §8 | Needs a tagged goal to know which member's eligibility to check |
| §10 Family Insurance | §5 (parent flow specifically) | Needs `has_own_insurance` captured to compute its recommendation |
| §11 Schemes | §2, Task 3's shared service | Needs members; reuses the same eligibility logic as §4 |
| §12 Dashboard | §2, §8, §10, §11 | Pure aggregator — cannot be built before its sources exist |

---

## External Dependencies (existing codebase, reused not modified)

| Component | Used By | Modification? |
|---|---|---|
| `get_current_user` (auth middleware) | Every new endpoint | None — reused as-is |
| `planning_service.get_dashboard()` | §12 | None — called, not altered |
| Existing `goals` router/service | §8, §9 | Additively extended (new sub-route, new optional field) — existing behavior untouched |
| `FinancialAssumptions.inflation_rate` | §9 (fallback) | Read-only reference, not modified |
| Existing `Stat`/`StatSkeleton` dashboard components | §12 | Reused for the six new cards, not reinvented |
| Existing dialog/confirm pattern (`GoalSimPanel.tsx`) | §7 (Remove confirmation) | Reused pattern, not a new component |
| Existing rate limiter (`middleware/rate_limit.py`) | All new endpoints | Applied unchanged; no new sensitive-path entries |

---

## Dependencies on Other Milestones (forward-looking, not blocking Milestone 2)

| Milestone 2 Element | Future Milestone That Extends It | Nature of the Dependency |
|---|---|---|
| §8's `goal_household_members` (presentational tag) | Milestone 2-later or a dedicated follow-up (Finding E's full resolution) | A future true joint-ownership model would likely supersede or build alongside this table — Milestone 2 does not block that future work, but implementers should not assume this table *is* that future work |
| §11's 3-rule-type evaluator (Task 3) | Milestone 3 (Government Policy Engine, full generality) | Milestone 3 will likely generalize rule-type parsing (`FutureCompatibilityAuditReport_v2.md` Finding I); Milestone 2's implementation is deliberately narrow and should not be mistaken for Milestone 3's full scope |
| §10's fixed-figure insurance recommendation | Milestone 5 (Recommendation Engine) | Milestone 5's `best_practice_rules`/`company_policies` tables (built empty in the Foundation Reconciliation) will eventually generalize this; §10's recommendation is a hand-coded special case, not built on that infrastructure, and should be revisited (not necessarily replaced) when Milestone 5 ships |
| §9's per-goal `custom_inflation_rate` | Milestone 4 (Calculation Engine) | The Monte Carlo re-simulation that would ideally react to a changed inflation assumption is Milestone 4's concern; Milestone 2 only stores the input |

**No Milestone 2 element requires a future milestone to be built first.** Every arrow above points forward (Milestone 2 → future), never backward (nothing in Milestone 2 is blocked waiting on Milestone 3, 4, or 5) — consistent with `FutureCompatibilityAuditReport_v2.md`'s verdict that Milestone 2 is buildable now.
