# Future Compatibility Audit — v2 (Post-Reconciliation)

**Date:** 2026-07-06
**Supersedes:** `FutureCompatibilityAuditReport.md` (v1, pre-reconciliation). v1 is kept, not deleted — this v2 documents what changed and re-verdicts each milestone against the now-reconciled schema (Milestone 1 + `006_foundation_reconciliation`).

---

## Status of the Four HIGH-Severity Findings

| Finding | v1 Severity | Status | How resolved |
|---|---|---|---|
| A — duplicate "dependents" source of truth | HIGH | **Resolved** (documented authority, not physically merged) | `user_profiles.dependents`/`marital_status` marked deprecated in code; `household_members`/`dependents` declared authoritative; migration plan documented, not executed |
| B — HUF cannot hold its own financial data | HIGH | **Resolved** (schema) | Nullable `huf_entity_id` added to `income_sources`/`expenses`/`assets`/`liabilities`, `ON DELETE SET NULL`, verified live against Postgres |
| C — unreconciled `tax_rate` | HIGH | **Resolved** (documented authority) | Marked deprecated in code; `tax_slabs`/`tax_regimes` declared authoritative; confirmed via grep that nothing currently depends on the legacy field, so removal risk is low whenever it happens |
| D — Policy Engine Layers 2-3 missing | HIGH | **Resolved** (schema) | `best_practice_rules`, `company_policies` added — structural only, no logic |

**No HIGH-severity findings remain from v1.**

## Findings Deliberately Left Open (not part of this reconciliation's authorized scope)

Per this task's explicit instruction to resolve "strictly in this order" and "not invent additional issues," the following v1 findings were **not** touched this session. Listed here for honesty, not because they were forgotten:

| Finding | v1 Severity | Status |
|---|---|---|
| E — no joint-ownership model for goals/income | MEDIUM-HIGH | Open — `goals`/`income_sources` remain strictly single-`user_id`-owned |
| F — no `Recommendation` lifecycle/dismissal state | MEDIUM | Open |
| G — `TaxAct`/`TaxRegime` inconsistent versioning shape | LOW-MEDIUM | Open — and now joined by a structurally identical gap in `best_practice_rules`/`company_policies` (see `FoundationReconciliationReport.md`'s Database Review finding #3) |
| H — `VARCHAR` vs. native `ENUM` inconsistency | LOW-MEDIUM | Open |
| I — untyped `scheme_eligibility_rules.value` | LOW-MEDIUM | Open |
| J — no uniqueness constraint on `household_members(household_id, user_id)` | LOW | Open |
| K — no `Recommendation`→`Simulation` citation link | MEDIUM | Open |
| M — unbounded audit/recommendation table growth | LOW (tracked) | Open, tracked in `RiskRegister.md` |

None of these block any milestone from *starting*; they're quality/completeness gaps within milestones that are otherwise supported, called out per-milestone below.

---

## Per-Milestone Verdict

### Milestone 2 — Family Planning: **Partially Supported**

Household/spouse/children/parents/dependents, education/medical planning, inheritance/estate-prep/nominee status tracking are all schema-ready. **Not supported:** genuinely joint goals/joint income with per-person contribution tracking (Finding E, unresolved) — a "joint goal" today can only be represented as one member's individual goal that the household view surfaces, not a single entity multiple people contribute to and see as jointly theirs. Recommend resolving Finding E before or early within Milestone 2, since it's the one gap in this milestone that a schema-only fix (not a business-logic fix) would need.

### Milestone 3 — Government Policies: **Supported**

Layer 1 storage (schemes, rates, eligibility rules, tax acts/sections/regimes/slabs) is complete and was validated with real seed data in Milestone 1. Finding I (untyped rule value) is a real implementation-quality note for whoever writes the rule-evaluation logic, not a schema blocker — the data can be read and parsed by `rule_type`-keyed logic in application code without any further migration.

### Milestone 4 — Calculation Engine (incl. Tax Planning): **Partially Supported**

The versioned tax-slab computation itself is fully supported, including the HUF case (Decision 2 resolved Finding B specifically so this milestone's HUF tax computation has real data to work against). **Not yet supported:** a place to store which regime a user has *elected* (as opposed to the *computed comparison* of both) — this gap was noted in v1's Tax Planning section but was never one of the four authorized findings, so it remains open. This is a small, additive, low-risk future migration (one nullable column on `financial_assumptions` or `user_profiles`) — flagged so Milestone 4 doesn't discover it mid-build.

### Milestone 5 — Recommendation Engine: **Supported**

The HIGH-severity blocker (Finding D) is resolved — `company_policies` rows can now back the ranking/gating logic `RecommendationEngineReport.md` specified. Two MEDIUM gaps remain (F: no dismissal state, K: no simulation citation) — real, but don't block the milestone from starting; they'd surface as "the dashboard can't hide a stale recommendation" and "a recommendation can cite policy but not the Monte Carlo run behind it," respectively, which are reasonable to fix within Milestone 5 itself rather than requiring a pre-milestone reconciliation.

### Milestone 6 — AI Advisor: **Supported**

Unchanged from v1 — `AI_CONVERSATIONS`/`AI_MESSAGES` were always correctly scoped to this milestone itself, not Foundation. Nothing in this reconciliation blocks or changes that plan. Finding K (citation gap) mildly limits how richly the AI Advisor can cite Monte Carlo grounding versus policy grounding, worth a small schema addition within Milestone 6 or 5, whichever ships first.

### Milestone 7 — Scenario Planning: **Supported**

Unchanged from v1 — needs new, purely additive tables (`scenarios`/`scenario_simulations`-shaped), same as always. Nothing this session helps or hinders this milestone; it was never blocked.

### Milestone 8 — Document Intelligence: **Supported**

Unchanged from v1 — needs a new, purely additive `documents` table. Nothing this session helps or hinders this milestone.

---

## Summary

| Milestone | v1 Verdict (implicit) | v2 Verdict |
|---|---|---|
| 2 — Family Planning | Blocked on Findings A/E | **Partially Supported** (A resolved; E still open) |
| 3 — Government Policies | Supported | **Supported** (unchanged) |
| 4 — Calculation/Tax | Blocked on Findings B/C | **Partially Supported** (B, C resolved; regime-election field still missing) |
| 5 — Recommendation Engine | Blocked on Finding D | **Supported** (D resolved) |
| 6 — AI Advisor | Supported | **Supported** (unchanged) |
| 7 — Scenario Planning | Supported (additive) | **Supported** (unchanged) |
| 8 — Document Intelligence | Supported (additive) | **Supported** (unchanged) |

**Net result:** every milestone that was blocked by a HIGH-severity finding in v1 is now at least Partially Supported, and the one HIGH-severity blocker with no partial-credit possible (Finding D, Recommendation Engine) is now fully Supported. The two remaining Partially Supported milestones (2 and 4) are each gated on a single, small, already-scoped, low-risk additive change — not a redesign — identified precisely so neither milestone discovers it as a surprise mid-build.
