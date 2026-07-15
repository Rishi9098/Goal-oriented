# API Contract — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06
**Convention:** All routes prefixed `/api/v1`, matching every existing router (`docs/architecture.md`). Every route requires a bearer access token (`get_current_user`, unchanged). Every 4xx follows the existing FastAPI/Pydantic error-body shape already used throughout this codebase. New routers: `app/routers/family.py` (screens 1-2, 4-7, 10-12), extending `app/routers/goals.py` (screen 8-9's `family-tags`/`custom_inflation_rate`). No existing endpoint's request/response shape changes except the one explicit, additive extension noted below.

---

## Household & Members

### `POST /api/v1/family/onboarding-seed`
**Screen:** §1. **Auth:** bearer.
Request:
```json
{ "has_spouse": bool, "has_children": bool, "children_count": int|null, "has_dependent_parents": bool }
```
`201` (new household) or `200` (existing household, idempotent no-op) → `{ household: {...}, members: [{...}] }`
Errors: `422` if `has_children=true` and `children_count` missing/out of `[1,10]`.

### `GET /api/v1/family`
**Screen:** §2. **Auth:** bearer + ownership.
`200` → `{ household: {...}, members: [{ id, relationship_type, name, is_complete }] }`
If no household exists for an authenticated user (pre-Milestone-2 account), lazily provisions one rather than erroring — see §2 Acceptance Criteria.

### `POST /api/v1/family/members`
**Screens:** §3-6 (add-new path). **Auth:** bearer + household ownership.
Request: `{ relationship_type: "spouse"|"child"|"parent"|"other", name, ...type-specific fields (see below) }`
`201` → created member (+ dependent row where applicable).

### `PUT /api/v1/family/members/{member_id}`
**Screens:** §3-6 (edit/complete-placeholder path), §7 (Edit action). **Auth:** bearer + household ownership.
Request (type-specific; `member_id`'s existing `relationship_type` determines which fields apply):

| relationship_type | Required fields | Optional fields |
|---|---|---|
| spouse | `name`, `date_of_birth` | — |
| child | `name`, `date_of_birth` | `gender`, `is_tax_dependent` |
| parent | `name`, `relationship` (`mother`\|`father`), `has_own_insurance` (`yes`\|`no`\|`not_sure`) | `date_of_birth` |
| other | `name`, `relationship` (free text) | `date_of_birth` |

`200` → updated member + dependent; for `child` with `gender=female` and computed age `<10`, also includes `eligible_schemes: [{code, reason}]`.
Errors: `404` (member not in caller's household), `422` (validation — see `ValidationMatrix.md`).

### `GET /api/v1/family/members/{member_id}`
**Screen:** §7. **Auth:** bearer + household ownership.
`200` → `{ member, dependent, tagged_goals: [...], coverage: [...] }`

### `DELETE /api/v1/family/members/{member_id}`
**Screen:** §7 (Remove). **Auth:** bearer + household ownership.
`204`, soft-delete (`is_active=false`) only. Errors: `400` if `relationship_type='self'`.

---

## Goals — Family Tagging & Education Extension

### `GET /api/v1/family/goals`
**Screen:** §8. **Auth:** bearer.
`200` → existing goals, each `+ tagged_members: [{id, name, relationship_type}]`.

### `PUT /api/v1/goals/{goal_id}/family-tags`
**Screen:** §8. **Auth:** bearer + goal ownership + household-membership check per tag.
Request: `{ household_member_ids: [uuid, ...] }` (full replacement, not incremental).
`200` → updated tag list. Errors: `404` (goal not owned by caller), `422` (any id not an active member of caller's household).

### `PATCH /api/v1/goals/{goal_id}` — **existing endpoint, additively extended**
**Screen:** §9. **Auth:** unchanged (bearer + goal ownership).
**New optional field added to the existing request schema:** `custom_inflation_rate: float | null`, bound `[0, 0.5]`. All other fields and behavior unchanged — this is the one place in Milestone 2 that touches an existing endpoint rather than adding a new one, and it does so additively (a new optional field, old clients unaffected).

---

## Insurance

### `GET /api/v1/family/insurance`
**Screen:** §10. **Auth:** bearer.
`200` → `{ policies: [{...}, coverage: [...]}], recommendation: {...} | null }`

### `POST /api/v1/family/insurance/policies`
**Screen:** §10. **Auth:** bearer + household-membership check on covered ids.
Request: `{ policy_type, sum_insured, annual_premium, insurer?, covered_household_member_ids: [uuid, ...] }` (min length 1).
`201` → created policy + coverage.

### `PUT /api/v1/family/insurance/policies/{policy_id}/coverage`
**Screen:** §10. **Auth:** bearer + policy ownership + household-membership check.
Request: `{ covered_household_member_ids: [uuid, ...] }` (full replacement, min length 1).
`200` → updated coverage. Errors: `422` if the array would be empty.

---

## Government Schemes

### `GET /api/v1/family/schemes`
**Screen:** §11. **Auth:** bearer.
`200` → `{ eligible: [...], potentially_eligible: [...], not_eligible: [...] }`, each item `{ scheme_code, member_name?, reason }`. `closed_to_new` schemes are filtered server-side before this response is constructed — never present in `eligible`/`potentially_eligible` regardless of rule match.

---

## Dashboard

### `GET /api/v1/family/dashboard`
**Screen:** §12. **Auth:** bearer.
`200` → six card payloads (`who_depends_on_me`, `education_costs`, `insurance_coverage`, `parents`, `retirement_readiness`, `emergency_readiness`) + `recommendations: [{source: "insurance"|"schemes", ...}]`. `retirement_readiness`/`emergency_readiness` are pass-through values from the existing `planning_service.get_dashboard()` — not recomputed.

---

## Cross-Cutting Rules (apply to every endpoint above)

- **Ownership check pattern:** every `member_id`/`policy_id`/`goal_id` path or body parameter is resolved through a query scoped to the caller's own household/goals — never trusted as globally addressable. A mismatch returns `404` (not found), never `403` (forbidden) — consistent with this codebase's existing convention of not confirming another resource's existence to an unauthorized caller.
- **No endpoint in this milestone performs a financial calculation beyond what already exists** (`planning_service`, `monte_carlo`, `optimizer` are read, never modified) — Milestone 2 is data capture, aggregation, and rule-based (not simulation-based) recommendation only, per `docs/ENGINEERING_CONSTITUTION.md` Rule 7's minimal-scope discipline.
- **Rate limiting:** existing global + sensitive-path rate limiter (`middleware/rate_limit.py`) applies unchanged; none of these endpoints are added to the `_SENSITIVE_PREFIXES` list (they're not auth/registration/simulation endpoints), consistent with that list's existing scope.
