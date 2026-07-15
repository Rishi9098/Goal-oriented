# Future Compatibility Audit — Milestone 1 Foundation

**Date:** 2026-07-06
**Scope:** Audit only. No code was modified to produce this report. Every claim below was verified against the actual model files (`app/models/household.py`, `policy.py`, `estate.py`, `insurance.py`, `recommendation.py`, `audit.py`), the actual migration (`005_family_policy_foundation`), and the actual pre-existing tables they connect to (`users`, `assets`, `goals`, `income_sources`, `user_profiles`, `financial_assumptions`) — re-read in full for this audit, not recalled from memory of designing them.

---

## Verdict, Stated Plainly First

**The Foundation supports most of the eight planned milestones without structural redesign — but not all of them cleanly, and I found real issues, not just theoretical ones.** Three findings below are concrete, already-latent problems, not speculative future risk: a duplicate source of truth for "dependents" that reproduces a bug class this project has already shipped and fixed once; an HUF entity that cannot actually hold the separate income/assets its entire tax rationale depends on; and two policy-engine layers (best-practice rules, company policy) that `PolicyEngineReport.md` and `RecommendationEngineReport.md` both assume exist but were never built in Milestone 1. These are reported, not fixed, per your instruction.

---

## Cross-Cutting Findings (affect multiple milestones — read this section before the per-milestone tables)

### Finding A — Duplicate source of truth: `user_profiles.dependents` vs. the new `dependents` table (HIGH)

`app/models/profile.py` has had `dependents: Mapped[int]` (a plain count, default 0) since before this milestone. Milestone 1 added a full `dependents` table (`household_member_id`, `date_of_birth`, `dependent_type`, `is_tax_dependent`). **Nothing reconciles these two.** A user could have `user_profiles.dependents = 2` while zero, one, or five rows exist in the new `dependents` table for their household — and nothing in the schema prevents or detects that drift.

This is not a hypothetical risk: it is the *exact same bug class* already found and fixed in this codebase (the Profile page's `dependents`/`marital_status` silent-overwrite bug, `ValidationReport.md`/`TechnicalDebt.md`, prior session). That bug happened because two representations of the same fact existed and only one was kept correct. The Foundation has now reintroduced that exact shape of risk at the schema level, one layer up. `user_profiles.marital_status` (a flat string) has the same relationship to the new `household_members.relationship_type = 'spouse'` presence-check — a second, independent way to answer "is this user married" that can silently disagree with the first.

**Affects:** Family Planning (directly), Family Dashboard (any view combining both fields), Tax Planning (dependents count affects certain deductions).

### Finding B — HUF cannot hold its own income, assets, or expenses (HIGH)

`FamilyHUFPlanningReport.md`'s entire tax rationale for HUF is that it is *"a separate legal taxable entity... that can independently own assets, earn income, and file its own tax return, distinct from any individual member's."* `HUFEntity` exists (`karta_user_id`, `funding_source`, `huf_pan`), but `income_sources`, `assets`, `expenses`, and `liabilities` are all still keyed **only** to `user_id` (confirmed by re-reading `app/models/financials.py`) — there is no `huf_entity_id` column, nullable or otherwise, on any of them. **The schema can record that an HUF exists, but not what the HUF owns or earns.** This means the Tax Planning milestone's HUF-tax-computation use case (separate exemption, separate deduction ceiling, computed against the HUF's *own* income) has no data to compute against — only the karta's personal financial data is recorded anywhere.

**Affects:** Tax Planning (cannot compute HUF tax without HUF-scoped income/assets), Family Planning (an "HUF's net worth" has no representable data), Recommendation Engine (an HUF tax-saving recommendation's projected rupee benefit cannot be grounded in real HUF financial data).

### Finding C — `financial_assumptions.tax_rate` is an unreconciled legacy field (HIGH)

Confirmed via grep: `tax_rate` is set only as a default (`0.22`) in the model, schema, and router seed defaults — no service or router *computes against* it today. The new `tax_regimes`/`tax_slabs` engine (built this milestone) is a complete, independent parallel path to the same conceptual fact ("what tax rate applies to this user"). Nothing in the schema states which one wins, whether `tax_rate` is deprecated, or how the two relate. When Tax Planning (Milestone 4/Calculation Engine #14) is built, a decision is needed: deprecate `tax_rate` (a modification to an existing table — removing or repurposing a column users may have already set), or keep it as a fallback and define precedence rules. Left unresolved, this is exactly the kind of two-sources-of-truth risk as Finding A, in the tax domain specifically.

**Affects:** Tax Planning directly; Government Policy Engine (a `financial_assumptions` row and a `tax_slabs` computation could legitimately disagree for the same user today, right now, if anything read `tax_rate` — nothing does yet, which is the only reason this hasn't already surfaced as a live bug).

### Finding D — Two policy-engine layers designed but never built (HIGH)

`PolicyEngineReport.md` specifies five layers: Government Rules, Best-Practice Rules, Company Policy, User Preferences, Market Assumptions. `RecommendationEngineReport.md`'s ranking and conflict-resolution logic explicitly depends on `best_practice_rules` and `company_policies` tables ("this ranking is itself a `company_policies` row... not hardcoded application logic"). **Neither table was built in Milestone 1.** Only Layer 1 (`schemes`, `scheme_rates`, `scheme_eligibility_rules`, `tax_acts`, `tax_sections`, `tax_regimes`, `tax_slabs`, `policy_citations`) exists. This means the Recommendation Engine milestone cannot be built exactly as designed in the research phase without an additional migration first — a real, concrete gap between what was designed and what was implemented, worth surfacing plainly rather than discovering mid-milestone.

**Affects:** Recommendation Engine (cannot implement ranking/gating as designed without a new migration), Government Policy Engine milestone (Layer 1 logic can proceed; Layers 2-3 cannot).

### Finding E — No representable ownership model for joint goals or joint income (MEDIUM-HIGH)

`goals` and `income_sources` remain strictly `user_id`-keyed, exactly as before this milestone (unchanged, as intended — see `DatabaseDesignReport.md`'s explicit design principle: "household-level views are computed by joining... never by adding a `household_id` column to those tables directly"). That principle correctly supports *aggregate* household views (sum of each member's individual goals/income). It does **not** support a genuinely *joint* goal or income source — e.g., a single home-down-payment goal that two spouses both contribute to and both should see as "their" goal, with per-person contribution tracking. Today, a "joint goal" can only be modeled as one spouse's individual goal that the other spouse views via the household aggregate — which is a real product-behavior gap, not just a display nuance, if per-person contribution attribution is ever required (and Milestone 2's brief explicitly lists "Joint goals" and "Joint income" as required features).

**Affects:** Family Planning milestone directly — this is arguably the single largest gap between what Milestone 2 needs and what Milestone 1 provides.

### Finding F — `Recommendation` has no dismissal/lifecycle state (MEDIUM)

Every other user-owned mutable entity in this schema has `is_active` (soft-delete/dismiss). `Recommendation` and `RecommendationCitation` do not (correctly, by the documented "reference/versioned data" exception — but `Recommendation` is neither reference data nor versioned in the `effective_from`/`effective_to` sense; it's a per-user generated artifact, closer in kind to a `Goal` than to a `SchemeRate`). Without a status/dismissed field, there is no way to represent "the user saw this and dismissed it" or "this recommendation is stale because the scheme rate it cited changed" without deleting the row and losing the audit trail `AuditLog`/`RecommendationCitation` were built to preserve.

**Affects:** Recommendation Engine and Family Dashboard (an "Upcoming Tasks"/"AI Insights" dashboard section needs to stop showing a dismissed recommendation).

### Finding G — `TaxAct` and `TaxRegime` have inconsistent versioning shapes (LOW-MEDIUM)

`TaxAct` has both `effective_from` and `effective_to`. `TaxRegime` has only `effective_from`. Both are "dimension"-like tables in the same file, describing conceptually similar things (a governing framework that's in force over a date range), but one supports representing a closed-ended historical era and the other doesn't. Not obviously broken today (only two regimes exist, "old" and "new," both presumably still open-ended), but an inconsistency a future engineer extending this file would reasonably trip on.

### Finding H — New tables use free-text `VARCHAR` where the existing schema uses native `ENUM` (LOW-MEDIUM)

`goals.category` and `goals.risk_profile` are native Postgres `ENUM` types (`goal_category`, `risk_profile`, created in migration 001). Every comparable fixed-vocabulary field introduced this milestone (`schemes.status`, `schemes.category`, `household_members.relationship_type`, `dependents.dependent_type`, `huf_entities.funding_source`, `health_policies.policy_type`, `estate_documents.document_type`, `scheme_eligibility_rules.rule_type`/`operator`) uses plain `VARCHAR` instead. This was a deliberate choice (documented in `policy.py`'s module comment: extensibility without an `ALTER TYPE`), but it is a genuine, real inconsistency against the pre-existing convention — not a defect, but worth a conscious decision (documented as an accepted deviation, or reconciled) rather than an implicit one.

### Finding I — `scheme_eligibility_rules.value` has no type discriminator (LOW-MEDIUM)

`value: String(255)` must hold an age (`"40"`), a boolean-like status (`"non_taxpayer"`), or a count (`"2"`) depending on `rule_type`, with no column indicating how to parse it. Functionally works (proven by the seed script and tests), but the Government Policy Engine milestone's rule-*evaluation* logic (Milestone 3) will need type-casting logic keyed off `rule_type` strings rather than a schema-enforced type — a source of exactly the kind of stringly-typed bugs `mypy --strict` (already enforced elsewhere in this codebase) is meant to catch, and can't, across this boundary.

### Finding J — No uniqueness constraint on `household_members(household_id, user_id)` (LOW)

Nothing prevents the same `user_id` from being added to the same household twice. Likely harmless today (no code creates household members yet), but worth a constraint before Milestone 2 builds the household-member CRUD API, or duplicate-membership bugs become possible from day one of that milestone.

### Finding K — No citation link from a `Recommendation` to the `Simulation` that grounds it (MEDIUM)

`RecommendationCitation` links to `scheme_id`/`tax_section_id` only. `AIArchitectureReport.md`'s explainability requirement includes "supporting calculations" — for a Monte Carlo–grounded recommendation ("your goal is at 4% probability, here's why"), there is no structured FK back to the specific `simulations` row that produced that number, only to policy citations. Today's citation model can explain *policy* grounding but not *calculation* grounding.

### Finding L — `Scenario Planning` and `Document Intelligence` need entirely new tables (INFORMATIONAL, not a problem)

No entities for either exist yet, correctly — neither was in Milestone 1's scope. Both are additive: a `scenarios`/`scenario_simulations` table pair and a `documents` table with extraction-status/extracted-data fields. Flagged here only so the "no structural redesign needed" claim is checked honestly: these two milestones need **new tables**, not modified ones — which counts as compatible-with-Foundation (additive), not a redesign, but is worth being precise about rather than implying zero future migrations will ever be needed.

### Finding M — Unbounded-growth tables still unaddressed (LOW, already tracked)

`audit_logs`, and future `recommendations`/`ai_messages`, are append-only with no partitioning/retention strategy. Already flagged in `RiskRegister.md` from the research phase; repeated here only for completeness since it's a genuine scalability concern that remains open after Milestone 1.

---

## Per-Milestone Assessment

### 1. Family Planning

| Q | Answer |
|---|---|
| 1. Implementable on current schema? | **Partially.** Household/dependent/spouse/parent structure: yes. Joint goals/joint income: **no** (Finding E). Education/medical planning: yes (health_policies exist; category-specific inflation is a calculation-layer gap, not schema). Inheritance/estate prep/nominees: yes, at the "status tracking" level designed (not full inheritance distribution logic, which was always out of scope). |
| 2. Migration required? | Yes — at minimum to resolve Finding E (a `goal_contributors`-style join table, or a nullable `household_id` on `goals`) and ideally Finding A/reconciling `user_profiles.dependents`. |
| 3. Existing table modification? | Likely yes for `goals`/`income_sources` if true joint ownership is required (Finding E); likely yes or a deprecation decision for `user_profiles.dependents`/`marital_status` (Finding A). |
| 4. Problematic relationships? | None structurally broken; the `household_members.user_id` nullable design (tested, working) is the one relationship that had to get this right, and it does. |
| 5. Missing fields? | Joint-ownership/contribution-split fields (Finding E); no unique constraint on membership (Finding J). |
| 6. Over-normalized entities? | `Dependent` as a separate 1:0/1 table from `HouseholdMember` is a defensible normalization choice (avoids NULL columns for non-dependent members), not over-normalization — but it is an extra join on every dependent-aware query, a real (small) cost worth naming. |
| 7. Under-normalized entities? | None new beyond what's already noted (Findings A, C apply here as duplicate-source-of-truth issues, which is the opposite problem — under-*reconciliation*, not under-normalization per se). |
| 8. Scalability concerns? | None beyond the already-tracked bounded household-size fan-out (Finding M's siblings), which remains a non-issue at realistic scale. |
| 9. Naming inconsistencies? | Finding A (`dependents` the column vs. `dependents` the table) is the sharpest one in the whole audit. |
| 10. Violates original architecture? | No routers/services were added, so the "thin router" principle is untouched. The dual-source-of-truth pattern (Finding A) does arguably violate this codebase's own established lesson from `TechnicalDebt.md` about exactly this failure mode, even though no code violates it yet — the *schema* now permits the same class of bug to recur. |

### 2. Government Policy Engine (lookup/logic layer)

| Q | Answer |
|---|---|
| 1. Implementable? | **Layer 1 (government rules) yes. Layers 2-3 (best practices, company policy) no — not built (Finding D).** |
| 2. Migration required? | Yes, for Layers 2-3. |
| 3. Existing table modification? | No — Layers 2-3 are purely additive new tables. |
| 4. Problematic relationships? | `TaxRegime`↔`TaxAct` have no FK linking them despite being conceptually related (Finding G's underlying cause) — not broken, but a relationship that *should* arguably exist and doesn't. |
| 5. Missing fields? | `scheme_eligibility_rules.value`'s type discriminator (Finding I); the entire Layer 2/3 tables (Finding D). |
| 6. Over-normalized? | No — the Layer 1 tables are appropriately granular given the proven need for per-field, per-date versioning. |
| 7. Under-normalized? | `scheme_eligibility_rules.value` as untyped string (Finding I). |
| 8. Scalability? | None — this data is small and slow-changing (quarterly at most). |
| 9. Naming inconsistencies? | Finding G, Finding H. |
| 10. Violates architecture? | No — this is squarely what "policy engine, never hardcode" was designed to be; it's incomplete, not architecturally wrong. |

### 3. Tax Planning

| Q | Answer |
|---|---|
| 1. Implementable? | **Partially, with a real conflict.** The versioned slab/section engine is ready to compute against. Computing correctly for a user requires resolving Finding C first (which "tax rate" wins), and HUF tax computation is blocked entirely by Finding B. |
| 2. Migration required? | Likely yes — a place to store the user's *elected* regime (a preference, distinct from the computed comparison) doesn't exist on `user_profiles` or `financial_assumptions` today. |
| 3. Existing table modification? | Yes, probably — `financial_assumptions` (add a regime-election field; decide `tax_rate`'s fate) and possibly `income_sources`/`assets`/etc. if Finding B is resolved by adding an alternate-owner column rather than parallel HUF-scoped tables. |
| 4. Problematic relationships? | `HUFEntity` currently has no relationship to any financial data at all (Finding B) — the most "broken" relationship in this audit, in the sense of an entity that structurally cannot do the one thing it exists for. |
| 5. Missing fields? | User's elected regime; HUF-scoped income/asset ownership (Finding B); resolution of `tax_rate` vs. `tax_slabs` (Finding C). |
| 6-7. Normalization? | Not a normalization problem — a completeness problem (data that needs to exist doesn't yet). |
| 8. Scalability? | None. |
| 9. Naming inconsistencies? | None beyond Finding C's conceptual overlap. |
| 10. Violates architecture? | The existence of an un-reconciled `tax_rate` alongside the new engine is the closest thing to an architectural violation found — two independent, un-cross-referenced sources of the same fact, which is precisely what the policy engine was designed to prevent, now recreated one layer up. |

### 4. AI Advisor

| Q | Answer |
|---|---|
| 1. Implementable? | Mostly yes for the narration/citation architecture. `AI_CONVERSATIONS`/`AI_MESSAGES` need building (expected, per `PROJECT_STATE.md`'s own decision log — correctly deferred, not an oversight). |
| 2. Migration required? | Yes, for conversation/message tables (already planned, additive). |
| 3. Existing table modification? | Possibly minor — linking a `Recommendation` to the specific conversation turn that produced it would need a nullable FK addition to `recommendations`. Not required for a basic implementation. |
| 4. Problematic relationships? | None new. |
| 5. Missing fields? | Conversation/message tables themselves; the `Recommendation`↔`Simulation` citation gap (Finding K) directly limits how well the AI Advisor can cite Monte Carlo grounding, not just policy grounding. |
| 6-7. Normalization? | N/A — nothing built yet to assess. |
| 8. Scalability? | `ai_messages` will be another unbounded-growth, append-only table (Finding M's pattern) — worth designing its retention story from day one rather than retrofitting. |
| 9. Naming inconsistencies? | None yet. |
| 10. Violates architecture? | No. |

### 5. Recommendation Engine

| Q | Answer |
|---|---|
| 1. Implementable? | **No, not as designed** — `RecommendationEngineReport.md`'s ranking/conflict-resolution logic explicitly requires `company_policies` rows that don't exist (Finding D). The storage for the *output* of a recommendation (`recommendations`, `recommendation_citations`) is ready; the storage for the *rules that decide* a recommendation's priority is not. |
| 2. Migration required? | Yes (Finding D). |
| 3. Existing table modification? | Possibly `recommendations` needs a dismissal/status field (Finding F). |
| 4. Problematic relationships? | Citation model can't reach `Simulation` (Finding K). |
| 5. Missing fields? | Finding D (whole tables), Finding F (status), Finding K (simulation citation). |
| 6-7. Normalization? | `alternatives_considered`/`assumptions_used` as JSON blobs is deliberately under-normalized per `DatabaseDesignReport.md`'s own stated justification (write-once, whole-object read pattern) — flagged here for completeness of the audit, not as a new discovery. |
| 8. Scalability? | Same append-only growth pattern as Finding M. |
| 9. Naming inconsistencies? | None new beyond D. |
| 10. Violates architecture? | The gap between what `PolicyEngineReport.md`/`RecommendationEngineReport.md` designed and what Milestone 1 built (Finding D) is the most direct instance of "the plan and the implementation disagree" found in this audit. Worth resolving deliberately (via a documented decision, same as `PROJECT_STATE.md`'s existing decision log) rather than silently. |

### 6. Scenario Planning

| Q | Answer |
|---|---|
| 1. Implementable? | No entity exists yet (correctly — out of Milestone 1's scope). |
| 2. Migration required? | Yes — new `scenarios`/`scenario_simulations`-style tables. |
| 3. Existing table modification? | Possibly `simulations` needs a nullable `scenario_id` if scenario runs should share the same result-storage shape as real simulations, rather than a fully parallel table — an open design decision, not yet forced either way. |
| 4. Problematic relationships? | None yet — nothing built to conflict with. |
| 5. Missing fields? | The entire scenario storage layer. |
| 6-7. Normalization? | N/A. |
| 8. Scalability? | Multiple scenario runs per user, each a full Monte Carlo pass, could multiply `simulations`-scale storage significantly if not designed with its own retention policy from the start. |
| 9. Naming inconsistencies? | None yet. |
| 10. Violates architecture? | No — this is a clean additive milestone from the Foundation's perspective. |

### 7. Document Intelligence

| Q | Answer |
|---|---|
| 1. Implementable? | No entity exists yet (correctly out of scope). |
| 2. Migration required? | Yes — a `documents` table (file storage reference, extraction status, extracted data, confirmation state). |
| 3. Existing table modification? | No — purely additive. Auto-populating the profile from extracted data would *write into* existing tables (`income_sources`, `assets`, etc.) through the normal application layer, not require schema changes to them. |
| 4. Problematic relationships? | None. |
| 5. Missing fields? | The whole `documents` entity. |
| 6-7. Normalization? | N/A yet. |
| 8. Scalability? | File storage itself (not modeled in Postgres — presumably object storage referenced by key) needs its own retention/size consideration, outside this audit's database scope. |
| 9. Naming inconsistencies? | `estate_documents.document_type` and a future `documents.document_type` will use the same column name for different vocabularies (Finding L's naming note) — not a conflict (different tables), but a name worth being deliberate about when this milestone is built, so the two aren't confused in code or documentation. |
| 10. Violates architecture? | No. |

### 8. Family Dashboard

| Q | Answer |
|---|---|
| 1. Implementable? | Yes, as a read/aggregation layer over existing tables — no new entities needed, assuming Findings A/E are either accepted as known limitations or resolved first. |
| 2. Migration required? | No, for the dashboard itself. Indirectly yes if Findings A or E are resolved before this milestone (recommended, since a dashboard is exactly where showing two disagreeing "dependents" numbers, or a "joint goal" that's really just one spouse's goal, would become directly user-visible). |
| 3. Existing table modification? | Not for the dashboard itself. |
| 4. Problematic relationships? | The per-member fan-out query pattern is fine at realistic household scale (already reviewed, `DatabaseDesignReport.md`'s Scalability Review, unchanged conclusion). |
| 5. Missing fields? | None dashboard-specific; inherits every gap above that the dashboard would surface to a user. |
| 6-7. Normalization? | N/A. |
| 8. Scalability? | None new. |
| 9. Naming inconsistencies? | Inherits Finding A directly — this is the milestone where that inconsistency stops being a latent schema risk and becomes a visible, confusing product bug if not resolved first. |
| 10. Violates architecture? | No. |

---

## Summary Table

| Finding | Severity | Blocks which milestone(s) outright | Needs new migration | Needs existing-table modification |
|---|---|---|---|---|
| A — dual "dependents" sources | HIGH | Family Dashboard (visibly) | No | Yes (or a deliberate deprecation) |
| B — HUF can't hold its own data | HIGH | Tax Planning (HUF case) | Yes | Yes (or parallel HUF tables) |
| C — unreconciled `tax_rate` | HIGH | Tax Planning | No | Yes (or deprecation) |
| D — Layers 2-3 policy tables missing | HIGH | Recommendation Engine | Yes | No |
| E — no joint-ownership model | MEDIUM-HIGH | Family Planning | Yes | Possibly (`goals`/`income_sources`) |
| F — no Recommendation lifecycle state | MEDIUM | Recommendation Engine, Family Dashboard | No | Yes (`recommendations`) |
| K — no Recommendation→Simulation citation | MEDIUM | AI Advisor, Recommendation Engine | No | Yes (`recommendation_citations`) |
| G — TaxAct/TaxRegime shape mismatch | LOW-MEDIUM | Government Policy Engine | No | Possibly (`tax_regimes`) |
| H — VARCHAR vs ENUM inconsistency | LOW-MEDIUM | None outright | No | N/A (style, not function) |
| I — untyped eligibility rule value | LOW-MEDIUM | Government Policy Engine (logic quality) | No | Possibly (`scheme_eligibility_rules`) |
| J — no household membership uniqueness | LOW | Family Planning (data integrity) | No | Yes (`household_members`) |
| L — new tables needed for Scenario/Document milestones | INFORMATIONAL | None (expected) | Yes (both) | No |
| M — unbounded audit/recommendation growth | LOW (tracked) | None outright, long-term risk | No (design decision) | N/A |

**Net assessment against your stated objective:** the Foundation does **not** require a structural redesign to support the eight planned milestones — every finding above is additive (a new table or column) or a reconciliation decision, never a "the existing design is wrong and must be torn up" finding. But three of those findings (A, B, D) are not minor, and two of them (A, B) are the kind of gap that gets more expensive to fix the longer real user data accumulates against the current shape. Resolving A and B before Milestone 2 begins in earnest would be materially cheaper than resolving them after Family Planning has shipped and users have started relying on the current (incomplete) behavior.
