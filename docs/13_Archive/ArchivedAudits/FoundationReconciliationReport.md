# Foundation Reconciliation Report

**Date:** 2026-07-06
**Scope:** Resolution of the four verified HIGH-severity findings from `FutureCompatibilityAuditReport.md`. Architecture reconciliation only — no Milestone 2 (Family Planning) feature work, no recommendation logic, no routers, no UI. Migration `006_foundation_reconciliation` is the only schema change; two legacy fields were documented/deprecated in place with no schema change.

---

## Decision Log

### Decision 1 — Duplicate "dependents"/"marital_status" source of truth (Finding A)

**Problem:** `user_profiles.dependents` (int count) and `user_profiles.marital_status` (string) coexist with the new, richer `household_members`/`dependents` entities with nothing reconciling them — the same bug shape already fixed once in this codebase (the Profile-page silent-overwrite bug, prior session).

**Options considered:**
1. Remove the legacy fields now and force all reads through the new entities.
2. Add a background sync job keeping both in agreement.
3. Keep the legacy fields, mark them deprecated in code, and route all *new* logic exclusively to the new entities.

**Chosen solution:** Option 3.

**Reasoning:** Option 1 would change the existing Profile page's API contract and onboarding flow behavior — both explicitly out of bounds for this task ("Do not change APIs," "Preserve the existing implementation wherever possible"). Option 2 (silent synchronization) is explicitly the outcome this task's own instructions forbid ("Never silently synchronize two independent sources forever") — a sync job doesn't resolve ambiguity, it hides it, and would itself need to handle every edge case (what if they disagree at sync time? which wins?) that Option 3 avoids by declaring an authority up front.

**Trade-off:** The legacy fields remain fully functional and unchanged for existing users — no migration risk, no behavior change — but the codebase now carries two representations of the same fact indefinitely until Milestone 2 deliberately migrates off the legacy fields. This is an accepted, bounded, documented debt, not a silent one.

**Future implication / migration plan (documented, not executed):** When Milestone 2 builds real household/dependent CRUD, it should (a) backfill every existing `user_profiles` row into a `household` + `household_member` + `dependents` structure using the legacy fields as the initial seed data, (b) switch the Profile page and onboarding flow to read/write the new entities, and (c) only then — once nothing reads the legacy fields — schedule their removal in a dedicated migration. This report and the code comments added this session (see `app/models/profile.py`) are the record that this decision was made deliberately, so a future engineer doesn't need to re-derive it.

### Decision 2 — HUF financial ownership (Finding B)

**Problem:** `HUFEntity` existed with no way to record what it owns or earns, undermining the entire tax rationale for modeling it as a separate entity.

**Options considered:**
1. Parallel HUF-specific tables (`huf_income_sources`, `huf_assets`, `huf_expenses`, `huf_liabilities`) mirroring the existing four tables.
2. A fully generalized polymorphic "owner" abstraction — a common `Owner` supertype that both `User` and `HUFEntity` implement, with `income_sources.owner_id` (etc.) pointing at it instead of directly at `users.id`.
3. A nullable `huf_entity_id` sibling column added to the existing four tables, alongside the unchanged, still-required `user_id`.

**Chosen solution:** Option 3.

**Reasoning:** Option 1 was explicitly the outcome the audit finding itself warned against ("avoid creating HUF-specific copies of every financial table unless absolutely necessary") — it would quadruple the number of tables needing the same CRUD logic, the same tests, and the same future schema changes in lockstep, for no benefit over a single shared table with an ownership flag. Option 2 is the most "architecturally elegant" answer in the abstract, and was seriously considered (it directly matches the audit's own instruction to "evaluate whether a generalized ownership abstraction provides a cleaner architecture") — but it requires changing `user_id`'s FK target on four existing, stable, actively-used tables from `users.id` to a new generic `owners.id`, which is a breaking structural change to working code, not an additive one, and there are exactly two owner types in this domain today (User, HUF) with no third type concretely planned (Phase 3's research explicitly deferred Trust structures as needing dedicated research, not as a near-term entity). Building a polymorphic supertype for a hypothetical third owner type that isn't yet designed is the premature generalization this project's own engineering principles (`CLAUDE.md`, `TechnicalDebt.md`) consistently warn against. Option 3 is purely additive, changes no existing column's meaning, and is exactly sufficient for the two owner types that actually exist.

**Trade-off:** If a third owner type (e.g., a Trust) is added later, this pattern would need to repeat (a third nullable `trust_id` column) rather than slotting into an existing polymorphic column — a real but bounded cost, and one that can be reassessed with real requirements at that time rather than guessed at now.

**Why `user_id` stays required even for HUF-owned rows:** the HUF has no login of its own — only a `karta_user_id`. `user_id` continues to answer "which login can see/manage this row" (access control); `huf_entity_id`, when set, answers "who is this row's true beneficial owner for tax/net-worth purposes." These are different questions and both need an answer, which is why this is a sibling column, not a replacement.

**`ON DELETE SET NULL`, not `CASCADE`:** deleting (deactivating) an HUF must never delete the underlying financial data — that data still belongs to the karta personally once the HUF wrapper is gone. Verified directly against the real Postgres dev database (see Database Review, below).

**Future implication:** Tax Planning (Milestone 4) can now compute an HUF's own tax position by querying `WHERE huf_entity_id = ?` across the four tables — no further schema change needed for the basic case. Application-level enforcement is still needed (not built this session, correctly out of scope) to ensure a `huf_entity_id` set on a row is only ever set by that HUF's actual karta — this is a business-rule validation, not a schema-level concern, and belongs in Milestone 2/4's service layer.

### Decision 3 — Incomplete Policy Engine (Finding D)

**Problem:** `PolicyEngineReport.md` specified five layers; only Layer 1 (government rules) was built in Milestone 1. `RecommendationEngineReport.md`'s ranking logic explicitly depends on Layer 3 (`company_policies`) rows.

**Determination:** Layers 2 (`best_practice_rules`) and 3 (`company_policies`) belong inside Foundation as structural support, **not** deferred — per this task's own instruction, "if Recommendation Engine architecture depends on them, implement only the minimum infrastructure necessary." Layer 4 (User Preferences) and Layer 5 (Market Assumptions) are **not** added this session: Layer 4 substantially already exists (`goals.risk_profile`, `goals.priority`) and Layer 5 already exists (`financial_assumptions`) — both pre-date this reconciliation and needed no new table, only the Tax Planning milestone's own future work to actually use `goals.priority` (already unused, a pre-existing gap, not a Foundation gap).

**What was built:** `best_practice_rules` and `company_policies` — schema only, no seeded rows, no ranking/gating logic, no routers. This matches Milestone 1's own established pattern (pure structural addition) exactly.

**Reasoning:** Building the minimum two tables now means the Recommendation Engine milestone can start immediately against a stable schema instead of needing its own reconciliation pass first — directly serving this task's objective that "the architecture should support all remaining milestones without requiring structural redesign."

**Trade-off:** These two tables will sit empty and unused until the Recommendation Engine milestone populates and reads them — dead schema in the interim, but a small, well-documented, zero-behavior-risk cost (an empty table changes nothing for any existing code path).

### Decision 4 — Legacy `tax_rate` field (Finding C)

**Problem:** `financial_assumptions.tax_rate` (flat, single rate) coexists with the new `tax_regimes`/`tax_slabs` engine with no stated authority.

**Verification before deciding:** Re-confirmed via `grep -rn "tax_rate" app/` that this field is set only to its default (`0.22`) in the model, schema, and router — no service or calculation reads it. This is a live, present-tense fact about the current codebase, not a historical note.

**Chosen solution:** Same pattern as Decision 1 — mark the field deprecated in code (see `app/models/assumptions.py`), state `tax_slabs`/`tax_regimes` as the sole authoritative source for any new tax computation, document the migration strategy, make no schema change now.

**Migration plan (documented, not executed):** Once Tax Planning (Milestone 4) ships a working `tax_slabs`-based computation, `tax_rate` should be removed in a dedicated migration — there is no backfill concern here (unlike Decision 1) since nothing currently reads or depends on this field's value, so removal carries materially lower risk than the `dependents`/`marital_status` case.

---

## Architectural Review

Every claim below is backed by a specific, re-checked piece of evidence — nothing here is asserted from memory of the original design.

| Property | Finding | Evidence |
|---|---|---|
| **Single source of truth** | Two known violations remain, both now documented/deprecated rather than silent (Decisions 1 & 4). No new violations introduced this session. | `grep` confirms `tax_rate` is write-only-to-default; `user_profiles.dependents`/`marital_status` now carry explicit deprecation comments pointing to the authoritative alternative. |
| **Ownership consistency** | Resolved for HUF (Decision 2) — `user_id` = access control, `huf_entity_id` = beneficial owner, consistently applied across all four financial tables with identical column shape and `ON DELETE SET NULL` semantics. | All four `ALTER TABLE` statements in migration 006 are textually identical modulo table name; verified via `\d income_sources` / `\d assets` output showing matching FK definitions. |
| **Policy layer separation** | Layer 1 (government) and Layers 2-3 (best practice, company policy) are now three structurally distinct tables with no FK coupling forcing a company policy to reference a specific scheme row — `company_policies.rule_definition` is JSON precisely so Layer 3 can reference Layer 1/2 facts loosely rather than being schema-coupled to them. | `app/models/company_policy.py`; no FK from `company_policies`/`best_practice_rules` to `schemes`/`tax_sections`. |
| **Referential integrity** | Zero orphaned `huf_entity_id` references across all four financial tables (checked directly against live Postgres data, not just schema inspection). | `SELECT count(*) ... LEFT JOIN huf_entities ... WHERE huf_entity_id IS NOT NULL AND h.id IS NULL` → 0 for `income_sources`, `expenses`, `assets`, `liabilities`. |
| **Normalization** | `best_practice_rules`/`company_policies` are appropriately granular (one row per rule/policy, no repeating groups). `company_policies.rule_definition` as JSON is a deliberate, documented under-normalization for the same reason as `recommendations.assumptions_used` in Milestone 1 (write-once, whole-object read pattern) — consistent with existing precedent, not a new inconsistency. | Direct comparison to `app/models/recommendation.py`'s existing JSON-field justification. |
| **Naming consistency** | The `VARCHAR`-vs-`ENUM` inconsistency flagged in the original audit (Finding H) was **not** resolved this session — it wasn't one of the four findings this task authorized fixing, and "do not invent additional issues" / "resolve findings strictly in this order" means it correctly stays out of scope here. Flagged again in the re-run audit below so it isn't lost. | `FutureCompatibilityAuditReport.md` Finding H, unchanged. |
| **Entity responsibilities** | `BestPracticeRule` and `CompanyPolicy` each have one clear responsibility (convention vs. company decision) with no overlapping fields between them. | Direct model comparison — no shared columns beyond the universal id/timestamps. |
| **Future extensibility** | The `huf_entity_id` pattern (Decision 2) generalizes to a third owner type by adding one more nullable column, without touching the first two — confirmed by construction, not merely asserted, since the pattern was already applied identically four times this session. | Migration 006's four near-identical `ALTER TABLE` blocks. |
| **Dependency direction** | Unchanged and still correct: `models` has no new dependency on `routers`/`services`; the new `huf_entity_id` columns depend on `huf_entities` (Milestone 1), consistent with the existing `routers → services → models` direction — no new file in this session imports "upward." | Import statements in `financials.py`, `company_policy.py` — no router/service imports present. |
| **Bounded contexts** | The Government Policy context (Layer 1) and the Company/Convention context (Layers 2-3) remain separately migratable and separately ownable (e.g., Layer 1 data could plausibly be updated by an automated scraper/data pipeline in the future; Layers 2-3 require human/product judgment) — kept as distinct tables specifically so those two very different update workflows never need to touch the same table. | Structural — no shared table between `schemes`/`tax_*` and `best_practice_rules`/`company_policies`. |

---

## Database Review — Every Table Touched or Added This Session

| Table | FKs | Indexes | Constraints | Cascade rule | Soft delete | Versioning | Auditability | Ownership |
|---|---|---|---|---|---|---|---|---|
| `income_sources` (modified) | +`huf_entity_id → huf_entities.id` | +`ix_income_sources_huf_entity_id` | none new | `SET NULL` (verified live against Postgres, see below) | unchanged (`is_active`, pre-existing) | N/A | N/A | Dual: `user_id` (access) + `huf_entity_id` (beneficial, nullable) |
| `expenses` (modified) | +`huf_entity_id → huf_entities.id` | +`ix_expenses_huf_entity_id` | none new | `SET NULL` | unchanged | N/A | N/A | Same dual model |
| `assets` (modified) | +`huf_entity_id → huf_entities.id` | +`ix_assets_huf_entity_id` | none new | `SET NULL` | unchanged | N/A | N/A | Same dual model |
| `liabilities` (modified) | +`huf_entity_id → huf_entities.id` | +`ix_liabilities_huf_entity_id` | none new | `SET NULL` | unchanged | N/A | N/A | Same dual model |
| `best_practice_rules` (new) | none | unique index on `rule_code` | `UNIQUE(rule_code)` at the column level | N/A (no FK) | none — reference data, same exception as Layer 1 tables | via `last_reviewed_date` (single date, not a full effective_from/to range — see finding below) | N/A (not user data) | N/A (not user-owned) |
| `company_policies` (new) | none | unique index on `policy_code` | `UNIQUE(policy_code)`, tested and confirmed rejecting duplicates | N/A | none, same exception | via `effective_from` only (no `effective_to`) | `changelog_notes`/`approved_by` fields exist for a manual audit trail | N/A |

**Findings with evidence (database-level, this session only):**

1. **`ON DELETE SET NULL` verified correct against live Postgres**, not just asserted from the migration file: a real INSERT → DELETE → SELECT cycle (wrapped in a transaction and rolled back, no data left behind) confirmed the asset row survives its HUF's deletion with `huf_entity_id` reset to `NULL`.
2. **`company_policies.policy_code` uniqueness verified by test**, not just by the `UNIQUE` DDL clause: `test_policy_code_must_be_unique` inserts a duplicate code and confirms `IntegrityError` is actually raised at the SQLAlchemy layer, not merely assumed from the DDL.
3. **`best_practice_rules` and `company_policies` versioning is weaker than the Layer 1 tables**: `scheme_rates`/`tax_slabs`/`tax_sections` all carry paired `effective_from`/`effective_to` columns (true interval versioning). `best_practice_rules.last_reviewed_date` and `company_policies.effective_from` are single dates with no corresponding "to" column — meaning neither table can represent "this rule/policy was in effect from X to Y and has since been superseded," only "this is the current row, dated." This is a real, evidence-based inconsistency with the Layer 1 pattern this session established elsewhere, surfaced honestly here rather than glossed over — not fixed in this pass, since it wasn't one of the four authorized findings, but flagged for whoever builds Recommendation Engine logic against these tables.
4. **Zero orphaned records** confirmed for every new/modified FK relationship touched this session (see Referential Integrity row above).
5. **No existing table's pre-existing columns, indexes, or constraints were altered** — confirmed by re-inspecting `\d` output for all four modified tables: every column present before migration 006 is still present, unchanged, in the same order.
