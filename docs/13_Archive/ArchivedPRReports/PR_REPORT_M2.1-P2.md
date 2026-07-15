# PR Report — Milestone 2.1-P2: Insurance Policy Audit Logging

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §2/§6/§13 — insurance-policy writes were not audit-logged, unlike every other Family write.

## Summary

Added audit logging to the two real insurance-policy write actions (create, coverage-update), reusing the existing `AuditLog` infrastructure and exact call pattern `family_service.py` already established for every other Family write. No new audit mechanism, no schema change, no new endpoint.

## Review Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.1-P2.md`) — confirmed exactly two write functions exist (`create_policy`, `replace_policy_coverage`); confirmed no delete/deactivate action exists anywhere for policies today (`HealthPolicy.is_active` is a real column, but nothing ever sets it `False`); confirmed no existing code queries `audit_logs`, so adding two new action strings cannot break anything.
2. **Root Cause Analysis** (`RootCauseAnalysis_M2.1-P2.md`) — traced the gap to a straightforward omission during Task 10's implementation (not a deliberate scoping decision — Task 10's own review docs never discuss audit logging). Confirmed this is a completeness/auditability gap, not a security defect — the Certification's Security Review already found no IDOR or ownership issue on any insurance endpoint.
3. **Data Integrity Review** (`DataIntegrityReview_M2.1-P2.md`) — one audit call per write function, matching the single-call-per-write shape every existing site uses (no duplicate-entry path). Verified "audit logging failures cannot corrupt the primary transaction" against the actual transaction boundary: `get_db()` commits the whole request atomically (the same guarantee every existing `AuditLog` call site already relies on), and the audit payload is built exclusively from already-validated primitives copied from the object that just succeeded — no independent failure mode exists.
4. **Security Review** (`SecurityReview_M2.1-P2.md`) — confirmed no PII (member names, DOB, insurance status) is written to audit records, only policy figures and member UUIDs, matching the existing pattern exactly. No new read surface added.
5. **User Trust Review** (`UserTrustReview_M2.1-P2.md`) — confirmed this is an invisible, backend-only change with no new user-facing claim to keep honest; closes the one exception to an otherwise-consistent audit posture.
6. **Implementation** — `backend/app/services/family_insurance_service.py`: `insurance_policy_created` in `create_policy()`; `insurance_policy_coverage_updated` (with before/after covered-member-id sets, mirroring `family_goal_tag_changed`'s exact "replace a set" shape) in `replace_policy_coverage()`.
7. **Testing** — 4 new tests in `test_family_insurance.py`: create is logged exactly once with no PII; coverage-update is logged with correct before/after ids; no duplicate entries per action; reads never produce an audit entry. Full suite: 329 passed (was 325), 97.52% coverage. `ruff`/`mypy --strict` clean.
8. **Live Verification** — created a policy and edited its coverage for a fresh test account against the real running backend and Postgres; queried `audit_logs` directly and confirmed both new action rows exist exactly once each, with correct before/after state, format byte-for-byte consistent with the pre-existing `household_created`/`family_member_added` rows. Test account fully cleaned up.
9. **Documentation** — `PROJECT_STATE.md`, `CHANGELOG.md`, this report.

## Files Changed

| File | Change |
|---|---|
| `backend/app/services/family_insurance_service.py` | Added two `AuditLog` writes, matching the existing pattern. |
| `backend/tests/test_family_insurance.py` | 4 new tests. |

## Verifying Every Insurance Create/Update Action Is Audit Logged

Both real write functions now log. Confirmed live against the actual database, not just the test suite.

## Verifying Format Matches the Existing Family Audit Pattern

`insurance_policy_created`'s `after_state` shape (id, type, figures, member ids) matches `family_member_added`'s shape (id, type). `insurance_policy_coverage_updated`'s before/after covered-member-id-set shape directly mirrors `family_goal_tag_changed`'s before/after tagged-member-id-set shape — the closest existing precedent for a "replace a set" action, chosen deliberately.

## Verifying No Duplicate Audit Entries

One `db.add(AuditLog(...))` call per function, placed once. Permanent test asserts exactly one row per action after a single request.

## Verifying Audit Logging Failures Cannot Corrupt the Primary Transaction

Traced the actual transaction boundary (`app/database.py`'s `get_db()`) — the whole request commits atomically, exactly as every pre-existing `AuditLog` call site already relies on. The audit payload's only inputs are already-validated primitives from the object that just succeeded — there is no scenario where constructing the audit dict fails independently of the primary write.

## Verifying Existing Audit Queries Remain Compatible

No code anywhere queries `audit_logs` today (confirmed via full-codebase grep) — nothing to break.

## Documentation

`PROJECT_STATE.md` (P2 entry), `DependencyValidation_M2.1-P2.md`, `RootCauseAnalysis_M2.1-P2.md`, `DataIntegrityReview_M2.1-P2.md`, `SecurityReview_M2.1-P2.md`, `UserTrustReview_M2.1-P2.md`, `CHANGELOG.md`.

## Known, Not Fixed Here (Scope Discipline)

No delete/deactivate endpoint exists for insurance policies today — this finding does not add one just to have something to audit-log. If a delete action is added in the future, it should carry its own audit-log call following this same pattern.

## Rollback

Revert the two `AuditLog` calls in `family_insurance_service.py`. No migration, no schema change to reverse.

---

## Definition-of-Production-Ready Checklist (this finding's contribution)

- [x] No silent data loss (nothing removed; purely additive logging)
- [x] No misleading UI (backend-only change, no user-facing claim)
- [x] No read operation mutates state (verified live + permanent test — unrelated to this finding, unchanged)
- [x] Audit logging complete (for insurance — create and coverage-update now logged, matching every other Family write)
- [ ] Accessibility passes — unrelated to this finding, tracked separately
- [x] Product Consistency passes (for this finding) — audit format matches the existing pattern exactly
- [ ] First-Time User Review passes — not applicable; this is an invisible backend change with no user-facing surface to review
- [x] Architecture Health passes (for this change) — no new mechanism, one reused pattern applied to two call sites
- [x] Financial Correctness passes (for this change) — no financial calculation touched
- [ ] Milestone Certification = CERTIFIED FOR PRODUCTION — not yet; more findings remain per `Milestone2CertificationReport.md`

**Stopping here per instruction. Awaiting approval before beginning the next Milestone 2.1 finding.**
