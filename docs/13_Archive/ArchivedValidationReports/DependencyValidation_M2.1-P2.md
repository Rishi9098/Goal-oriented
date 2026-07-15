# Dependency Validation — Milestone 2.1-P2 (Insurance Policy Audit Logging)

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §2/§6/§13 — insurance-policy writes are not audit-logged, unlike every other Family write.

## Checklist

| Requirement | Status |
|---|---|
| `AuditLog` model | ✅ `app/models/audit.py` — generic `{user_id, action, before_state, after_state, created_at}` shape, already used for `household_created`, `family_member_added`, `family_member_updated`, `family_member_removed`, `family_goal_tag_changed` (all in `family_service.py`). |
| Existing pattern to reuse | ✅ `db.add(AuditLog(user_id=..., action="<snake_case>", before_state=..., after_state=...))` called in the same session, right after the primary write's `db.flush()`, before the function returns — five call sites in `family_service.py`, confirmed identical shape each time. |
| Insurance write endpoints that need logging | Exactly two exist: `POST /family/insurance/policies` → `create_policy()`, and `PUT /family/insurance/policies/{id}/coverage` → `replace_policy_coverage()`. **Confirmed via full read of `family_insurance_service.py`: no third write function exists.** |
| A "delete" action for policies | ❌ **Does not exist.** `HealthPolicy.is_active` is a real column (used defensively in every read query's WHERE clause), but **no endpoint anywhere sets it to `False`** — confirmed via full read of `family_insurance_service.py` and `routers/family.py`'s insurance routes. There is no delete/deactivate action to audit-log today. |
| Existing audit-log consumers (queries) to stay compatible with | ✅ **None exist.** Grepped the entire backend for any `select(AuditLog)` or read-side usage — zero. The table is currently write-only from every existing call site; there is nothing to break. |
| Transaction boundary | ✅ `app/database.py`'s `get_db()` wraps the entire request in one transaction — commit happens once, after the endpoint returns; any exception anywhere rolls back everything written in that request, audit log included. This is the same boundary every existing `AuditLog` call site already relies on — not something this finding needs to change. |

## Conclusion

**No blocker.** The audit infrastructure, its exact call pattern, and the two real write functions needing it are all already known and unambiguous. One scope boundary to state plainly rather than invent around: **there is no delete action for insurance policies in this product today** — this finding logs create and update (coverage-replace); it does not add a delete endpoint just to have something to audit, which would be new-feature work outside "implement ONLY insurance audit logging."
