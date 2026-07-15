# Root Cause Analysis — Milestone 2.1-P2 (Insurance Policy Audit Logging)

**Date:** 2026-07-07

## Why the gap exists

`family_service.py` established the audit-log pattern early (household creation, member add/update/remove, goal tagging) and applied it consistently to every write it introduced. `family_insurance_service.py` (Task 10) was built later, reusing `family_service`'s household/member/ownership patterns extensively (`is_complete`, `resolve_member_name`, the delete-then-reinsert coverage-replace pattern) — but the audit-logging call was not among the patterns carried over. This is a straightforward omission during Task 10's implementation, not a deliberate scoping decision (no design review from that task discusses or defers audit logging) — confirmed by re-reading Task 10's own review documents, which focus entirely on the insurance recommendation's integrity and never mention audit logging at all.

## Is this a security defect?

**No.** The Milestone 2 Certification's Security Review found no IDOR, no ownership-bypass, no authorization gap on any insurance endpoint — `get_policy()` correctly scopes by `primary_holder_user_id == user.id`. This finding closes a **completeness/auditability gap**, not an access-control vulnerability: today, a policy can be created or have its coverage changed with no permanent record of who did it or when, which matters if this data is ever the subject of a compliance or dispute review, but does not let one user affect another's data.

## Scope of the fix

Two call sites, matching the two real write functions:

1. `create_policy()` — log `insurance_policy_created`, `after_state` describing the new policy (id, type, sum insured, premium, covered member ids).
2. `replace_policy_coverage()` — log `insurance_policy_coverage_updated`, `before_state`/`after_state` as the covered-member-id sets before and after the replace (mirroring `family_goal_tag_changed`'s exact before/after-ids shape, the closest existing precedent for a "replace a set" audit entry).

## What this finding does not do

- Does not add a delete/deactivate endpoint (none exists today — see `DependencyValidation_M2.1-P2.md`).
- Does not add audit logging to any read endpoint (`GET /family/insurance` and the recommendation/dashboard/schemes endpoints remain correctly unaudited — they perform no writes).
- Does not change `HealthPolicy`'s or `HealthPolicyCoverage`'s schema, and does not add a new audit table or mechanism — reuses `AuditLog` exactly as it exists.
