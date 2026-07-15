# Data Integrity Review — Task 12 (Family Dashboard Integration)

**Date:** 2026-07-07
**Performed before implementation**, per instruction.

## Household ownership

`GET /family/dashboard` resolves the caller's household via `family_service.get_or_create_household()` — the same authority every Family endpoint uses — and every downstream call is scoped to that household or to `user.id`. No new authorization pattern.

## Counting integrity — the denominators must agree

"Insurance coverage: N of M" uses the same member list (`list_members_with_completeness`, active members including 'self') for M as the "Who depends on me?" card uses for its counts — one query, one snapshot, so the two cards can never disagree about household size within a single response. N derives from the union of covered-member IDs across active policies via `list_policies_with_coverage()` — the same data the Insurance screen renders, so tapping the card never reveals a different number than the card showed.

## Persisted values only, read out verbatim

Education/Retirement/Emergency-goal figures are the goals' persisted `probability`/`on_track`/`target_date`/`target_amount` — set only by the Calculation Lifecycle's write paths (ADR-001), never touched here. `plan_health_score`, `liquid_assets`, `monthly_expenses` come from `planning_service.get_dashboard()`, itself documented and verified read-only.

## No dashboard state is persisted

Nothing is written on read: no snapshot rows, no cache tables, no "last viewed" bookkeeping. Consecutive calls against unchanged data return identical payloads (pure function of current state); calls after a data change reflect it immediately on next load — which is exactly the Contract's freshness Acceptance Criterion, and it falls out of statelessness rather than requiring invalidation machinery.

## Partial-failure handling never corrupts or fabricates data

A failed section returns `null` (or `recommendations_unavailable: true`), never a default/zero that could be mistaken for a real figure — a card that couldn't be computed is visibly unavailable, not silently "0 of 0 covered." Errors are logged server-side with full context, never swallowed.

## Known limitation carried forward

The education card names tagged members by the same `resolve_member_name` convention every other Family screen uses; goals with no tagged member show the goal alone (an honest state — Task 8 made tagging optional). No new name-collision surface beyond what `DataIntegrityReview_Task11.md` already documented.
