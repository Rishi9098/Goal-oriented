# Dependency Validation Report — Milestone 2, Task 3 (Scheme Eligibility Evaluation Service)

**Date:** 2026-07-06
**Status:** ⛔ BLOCKED — one dependency is not ready. No code written. Per the workflow's Step 3, generating this report instead of proceeding or guessing.

---

## What Was Checked

| Dependency | Required for Task 3 | Status |
|---|---|---|
| `schemes` table (Foundation) | Read-only source of scheme identity/status | ✅ Ready — 9 rows seeded (confirmed via live query), correct `status` values including `PMVVY: closed_to_new` |
| `scheme_rates` table (Foundation) | Not directly used by eligibility logic, but confirms the seed script ran | ✅ Ready — 13 rows seeded |
| `scheme_eligibility_rules` table (Foundation, schema) | **The entire data source Task 3's evaluation logic reads** | ✅ Table exists, correctly designed (Milestone 1) |
| `scheme_eligibility_rules` **rows** (seed data) | Task 3 cannot evaluate eligibility against rules that don't exist | ⛔ **BLOCKED — zero rows.** Confirmed via live query against the real dev database. |
| `household_members`/`dependents` (Task 1/2) | Source of the age/gender/relationship facts rules are evaluated against | ✅ Ready |
| UX approval | `FamilyPlanningDesign.md` §7, approved | ✅ Ready |
| No unresolved audit findings blocking this specifically | Finding I (`scheme_eligibility_rules.value` has no type discriminator) is open but doesn't block *building* the service — it's a code-quality note for the parsing logic, not a missing precondition | ✅ Not blocking (tracked, not a blocker) |

## The Blocker, In Detail

`backend/scripts/seed_policy_data.py` — the script that populated `schemes`, `scheme_rates`, `tax_acts`, `tax_sections`, `tax_regimes`, `tax_slabs` during Milestone 1 — **never references `SchemeEligibilityRule` at all** (confirmed via `grep`, zero matches). The table was built (correctly) in Milestone 1's migration, but no seed data was ever written for it. This was not caught during Milestone 1's or the Foundation Reconciliation's validation because neither milestone needed to *read* eligibility rules — only Task 3 does.

Task 3's entire scope, per `ImplementationChecklist.md`, is: "The rule-evaluation logic itself... as a standalone, directly-testable service function." A rule-evaluation service with nothing to evaluate against isn't a service — it's dead code that would need to be revisited the moment real data was added anyway. Writing and unit-testing the evaluator now, against an empty table, would produce tests that pass by returning empty results for everything — a false signal of completeness, not real coverage of "does SSY correctly say eligible for a 7-year-old daughter."

## Why This Wasn't Caught Earlier

`Milestone2ImplementationContract.md` §11 and `TestPlan.md` §1 both describe eligibility-rule testing in detail, and both implicitly assumed rule rows would already exist by the time Task 3 started (reasonably, since `scheme_rates` — the sibling reference-data table — was fully seeded). No one actually queried `scheme_eligibility_rules` to confirm this until this dependency-validation step. This is exactly what Step 3 of this workflow is for.

## Proposed Resolution (not yet implemented — awaiting approval)

Seed `scheme_eligibility_rules` with only what `GovernmentPolicyReport.md` already verified, nothing invented:

| Scheme | Verified fact (GovernmentPolicyReport.md, quoted) | Proposed rule row |
|---|---|---|
| SSY | "Girl child must be under 10 at account opening" | `rule_type='max_age', operator='<', value='10'` |
| SCSS | "Individuals 60+..." (base case only) | `rule_type='min_age', operator='>=', value='60'` |

**What will NOT be seeded, and why:** SCSS's report also verifies two special-case eligibility routes — "55+ if retired under superannuation/VRS" and "retired defense personnel 50+." These are real, verified facts, but this app captures no field anywhere (not in `household_members`, `dependents`, or `user_profiles`) recording retirement status, VRS status, or defense-service history. Seeding a rule for a fact the app has no way to evaluate would be worse than not seeding it — it would silently never match, which is indistinguishable from a bug. Per `docs/ENGINEERING_CONSTITUTION.md` Rule 4 ("never invent... state the gap explicitly instead"), this gap will be documented in the seed script's own docstring and in `docs/database.md`, exactly as Milestone 1's seed script already documents its own deliberate gaps (old tax regime slabs, Section 80CCD(1B)).

No other scheme in the seeded set (`EPF`, `PPF`, `NPS`, `NSC`, `KVP`, `APY`, `PMVVY`) has a verified age/residency eligibility rule distinct from "any Indian resident" in `GovernmentPolicyReport.md` — so only these two rows would be added. `PMVVY` needs no eligibility rule at all, since its `closed_to_new` status is a harder, unconditional filter that Task 3's logic applies before any rule evaluation runs (per the Contract's own Business Rules).

## Requested Decision

