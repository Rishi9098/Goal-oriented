# Data Integrity Review — Milestone 2.1-P2 (Insurance Policy Audit Logging)

**Date:** 2026-07-07

## No duplicate audit entries

Each of the two write functions gets exactly one `db.add(AuditLog(...))` call, placed once, immediately after that function's own primary write is flushed — mirroring the exact single-call-per-write shape every existing `family_service.py` site uses. Neither function calls the other, and neither is called twice within a single request, so no code path can produce two audit rows for one user action. `create_policy()` and `replace_policy_coverage()` remain otherwise unmodified — no new branching that could cause a double-log.

## Audit logging failures cannot corrupt the primary transaction, verified against the actual transaction boundary

`app/database.py`'s `get_db()` wraps the entire request in one transaction: `yield session` → `session.commit()` on success, `session.rollback()` on any exception. This means the primary write (the `HealthPolicy`/`HealthPolicyCoverage` row) and its audit-log row share one atomic commit — either both persist, or (on any exception anywhere in the request) neither does. This is **the existing, already-relied-upon behavior of every current `AuditLog` call site**, not something this finding introduces or changes.

Given this, "audit logging failures do not corrupt the primary transaction" is satisfied in the only way that is actually possible without inventing a second, inconsistent mechanism: the audit log's inputs are exclusively primitive values already validated by the time the primary write succeeded (`policy.id`, `policy.policy_type`, `policy.sum_insured`, member UUIDs already validated by `_validate_member_ids()`) — there is no independent failure mode where constructing the audit dict could fail while the primary write itself succeeds. Serializing an already-valid UUID/float/string cannot raise. This mirrors the same reasoning that already makes every existing `family_service.py` audit call safe.

## Existing audit queries remain compatible

No existing code queries `audit_logs` (confirmed via `DependencyValidation_M2.1-P2.md` — zero `select(AuditLog)` anywhere). Adding two new `action` string values (`insurance_policy_created`, `insurance_policy_coverage_updated`) cannot break a query that doesn't exist. The `action` column has no enum/CHECK constraint restricting its values (confirmed by reading the model) — a new action string requires no migration.

## Consistency of the before/after shape with the established convention

`insurance_policy_coverage_updated` mirrors `family_goal_tag_changed`'s exact "before ids / after ids" shape — the closest existing precedent for a "replace a set" action, chosen deliberately rather than inventing a new shape for a structurally identical operation.
