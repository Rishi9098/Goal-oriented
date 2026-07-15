# Security Review — Milestone 2.1-P2 (Insurance Policy Audit Logging)

**Date:** 2026-07-07

## What this finding is, and isn't

This is a completeness fix, not a vulnerability fix — the Milestone 2 Certification's Security Review already found no IDOR/ownership-bypass on any insurance endpoint. This review verifies the audit-logging addition itself introduces no new security surface.

## PII in audit records

`after_state`/`before_state` for `insurance_policy_created` will include the policy's `sum_insured`, `annual_premium`, `policy_type`, and covered `household_member_ids` (UUIDs, not names) — no household member's name, date of birth, or insurance-status text is written to the audit log, matching the existing pattern (`family_member_added`'s `after_state` similarly stores only `member_id`/`relationship_type`, never a name). `audit_logs.user_id` already has a foreign key to `users`, scoping every row to one account — no cross-user data ever appears in a row.

## Access control on the audit data itself

No new endpoint is added to read `audit_logs` — this finding is write-only, matching the existing pattern where no read endpoint for this table exists anywhere in the product. No new exposure surface.

## Does adding audit logging change any existing authorization check?

No. `create_policy()` and `replace_policy_coverage()` keep their exact existing ownership/validation logic (`_validate_member_ids()`, the household-scoped queries already in place) — the audit-log call is additive, placed after the existing checks have already run, never replacing or weakening them.

## Conclusion

No new vulnerability surface. This finding closes a real, if narrow, auditability gap without introducing one.
