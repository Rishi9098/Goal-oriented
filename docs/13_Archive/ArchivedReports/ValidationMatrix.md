# Validation Matrix — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Every field across every Milestone 2 endpoint, consolidated. Cross-reference: `Milestone2ImplementationContract.md`, `APIContract.md`.

| Field | Screen(s) | Required? | Type / Format | Business Rule | Edge Case Handling |
|---|---|---|---|---|---|
| `has_spouse` | §1 | Yes | boolean | — | — |
| `has_children` | §1 | Yes | boolean | — | — |
| `children_count` | §1 | Conditional (required if `has_children=true`) | int | `1 ≤ n ≤ 10` | `>10` rejected with `422`, not silently capped — likely a data-entry error, not a real household size |
| `has_dependent_parents` | §1 | Yes | boolean | — | — |
| `name` (any member) | §3-6 | Yes | string | 1-255 chars, non-empty after trim | Duplicate names across members allowed (twins, common names) — no uniqueness check |
| `date_of_birth` (spouse, child) | §3, §4 | Yes | date | Not in the future; not >130 years in the past | Future date → `422`; exactly today's date is valid (a same-day-born child) |
| `date_of_birth` (parent, other) | §5, §6 | No | date | Same bounds as above when provided | Omitted entirely is valid — some users may not know an elderly parent's exact DOB |
| `gender` (child) | §4 | No | enum: `female`\|`male`\|`other`\|unset | Drives SSY eligibility check only when `female` | Unset never blocks any other field or flow |
| `relationship` (parent) | §5 | Yes | enum: `mother`\|`father` | — | — |
| `has_own_insurance` (parent) | §5 | Yes | enum: `yes`\|`no`\|`not_sure` | Drives §10's recommendation | `not_sure` is a first-class valid answer, not a soft-reject prompting the user to "please find out" |
| `relationship` (other) | §6 | Yes | free text, 1-100 chars | — | — |
| `member_id` (path param, §3-7) | §3-7 | Yes (path) | UUID | Must resolve to a member of the caller's own household | Foreign household's id → `404` |
| `household_member_ids` (goal tags) | §8 | No | array of UUID | Each must be an active member of caller's household | Empty array valid (untag all); any invalid id → `422` for the whole request, not partial application |
| `custom_inflation_rate` | §9 | No | float | `0 ≤ rate ≤ 0.5`, matches existing `FinancialAssumptions.inflation_rate` bound | `null` explicitly means "revert to global rate," distinct from omitting the field (no change) |
| `policy_type` | §10 | Yes | enum: `family_floater`\|`individual`\|`senior_citizen_standalone` | — | — |
| `sum_insured` | §10 | Yes | float | `> 0` | `0` or negative → `422` |
| `annual_premium` | §10 | Yes | float | `≥ 0` | — |
| `insurer` | §10 | No | string, ≤255 chars | — | — |
| `covered_household_member_ids` | §10 | Yes | array of UUID, min length 1 | Each must be an active member of caller's household | Empty array → `422` ("a policy must cover at least one person") |
| `relationship_type` (server-set, `POST /members`) | §3-6 | Yes | enum: `spouse`\|`child`\|`parent`\|`other` | Determines which of the above field sets apply | Mismatched fields for the declared type → `422` (e.g., `has_own_insurance` sent for a `child` type is ignored, not silently stored) |

## Government Eligibility Validation (§11, read-only, no user input — listed for completeness)

| Rule Type (from `scheme_eligibility_rules.rule_type`) | Evaluated Against | Example |
|---|---|---|
| `min_age` | Member's computed age from `date_of_birth` | SSY: member age < 10 |
| `max_age` | Member's computed age | SSY: member age < 10 (upper bound of the eligible window) |
| `residency_status` | `user_profiles.country`/existing tax-residency fields | NRI-specific scheme exclusions |

**Hard filter, not a rule-evaluation output:** `schemes.status = 'closed_to_new'` (e.g., PMVVY) removes a scheme from `eligible`/`potentially_eligible` unconditionally, before rule evaluation even runs — this is not a validation rule a household could ever satisfy, it's a scheme-level gate.

## Duplicate Detection — Explicitly Not Enforced, With Reasoning

| Scenario | Enforced? | Why |
|---|---|---|
| Two children with the same name | No | Twins, common names — false-positive risk outweighs the (low) value of catching an accidental duplicate |
| Same `household_member_id` tagged twice on a goal (§8) | Enforced at the DB level via `UNIQUE(goal_id, household_member_id)` on `goal_household_members` | A genuine data-integrity concern (a tag either exists or doesn't); the API's "full replacement" semantics (§8) make client-side duplicate submission harmless in any case |
| Two health policies covering the exact same member+policy_type | No | A user may legitimately hold two policies of the same type from different insurers during a transition period |

## Cross-Field / Cross-Screen Validation

- A goal's `custom_inflation_rate` (§9) can only be set on goals with `category='education'` or `category='medical'` — attempting to set it on any other category is rejected with `422` (the field exists on the `goals` table generally per §0.2's minimal-diff schema choice, but its *use* is restricted by business rule, not by a database constraint, consistent with `docs/ENGINEERING_CONSTITUTION.md` Rule 7's preference for application-level rules over schema-level rigidity where the schema-level version would need a `CHECK` referencing another column's value — Postgres supports this, but it adds coupling for a rule that may need to expand to more categories later).
- Removing a household member (§7 DELETE) that is the sole tagged member on a goal does not delete the goal or the tag row — the tag row's `household_member_id` FK has `ON DELETE CASCADE` (per §0.1), so the tag itself is removed, and the goal reverts to showing only under "You," consistent with §7's Acceptance Criteria.
