# Acceptance Criteria — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Consolidated from `Milestone2ImplementationContract.md`'s per-screen criteria, plus cross-cutting criteria that span multiple screens. Every item here is written to be objectively checkable (by a test, not a judgment call).

---

## Onboarding & Household Creation (§1, §2)

- [ ] A user answering "children: yes, count: 3" has exactly 3 `household_members` rows with `relationship_type='child'` immediately after onboarding completes.
- [ ] Re-submitting the onboarding family step for a user who already has a household does not create a second household or duplicate member rows.
- [ ] A user answering "No" to all three onboarding questions has exactly one household member (`relationship_type='self'`) and sees the Family Home empty state, not an error, on first visit.
- [ ] A pre-Milestone-2 user (no household row) visiting `/app/family` for the first time is lazily provisioned a household + self member, not shown a 404.

## Adding & Editing Family Members (§3-7)

- [ ] Adding a daughter with `date_of_birth` implying age < 10 immediately returns `eligible_schemes` containing SSY, sourced from live `scheme_rates` data (verifiable: changing the seeded SSY rate changes the displayed rate without a code change).
- [ ] Adding a daughter age ≥ 10 does not return an SSY entry.
- [ ] Marking a parent `has_own_insurance='no'` causes that parent to appear in Family Insurance's (§10) recommendation on the very next `GET /api/v1/family/insurance` call — no caching staleness, no manual refresh workaround required.
- [ ] Attempting to `PUT`/`GET`/`DELETE` a `member_id` belonging to a different user's household returns `404`.
- [ ] Removing a household member sets `is_active=false` — the row is still present in the database afterward (verifiable via direct query), never hard-deleted.
- [ ] Removing the `relationship_type='self'` member is rejected with `400`.
- [ ] A removed member's previously-tagged goals no longer display that member in "who this affects," while the goal itself and its other tags remain unaffected.

## Family Goals (§8) — Joint-Tag Disclosure (UX_REVIEW.md Revision #2)

- [ ] Tagging a goal with at least one household member causes the mandatory disclosure text to render on that goal's detail view, every time, not as a dismissible one-time tooltip.
- [ ] Untagging all members removes the goal from every "grouped by member" view but does not delete or alter the goal itself.
- [ ] Attempting to tag a goal with a `household_member_id` from a different household returns `422`.
- [ ] The goal's `user_id` (owner) is provably unchanged by any tagging operation (verifiable: the owner field before and after any §8 API call is identical).

## Education Planning (§9)

- [ ] An education-category goal with `custom_inflation_rate=null` displays a projection using the global `financial_assumptions.inflation_rate`.
- [ ] Setting a `custom_inflation_rate` persists across a page reload and is reflected in the projection.
- [ ] Attempting to set `custom_inflation_rate` on a non-education, non-medical goal is rejected.
- [ ] The SSY callout on this screen only renders when the goal is tagged with a currently-eligible member — never unconditionally on every education goal.

## Family Insurance (§10)

- [ ] A household with a parent marked `has_own_insurance` in (`no`, `not_sure`) sees the separate-policy recommendation; a household with no such parent does not.
- [ ] The recommendation's cited figures (₹25,000 base 80C/123 limit, doubled for a separate parent policy, ₹50,000 senior-citizen tier) match `GovernmentPolicyReport.md` exactly — verified by direct comparison, not visual approximation.
- [ ] Creating a policy with an empty `covered_household_member_ids` array is rejected with `422`.
- [ ] Every covered member on a policy resolves to an active member of the caller's own household — verified by attempting a cross-household id and confirming rejection.

## Family Government Schemes (§11)

- [ ] A scheme with `status='closed_to_new'` (e.g., PMVVY) never appears in `eligible` or `potentially_eligible`, for any household composition tested, including one that would otherwise match every rule.
- [ ] A household with a daughter under 10 sees SSY in `eligible` with a reason string naming that specific child.
- [ ] A household with no member over 55 sees SCSS in `not_eligible`, not `potentially_eligible`.
- [ ] The "Not Eligible" section renders collapsed by default on first load.

## Family Dashboard (§12)

- [ ] Each of the six cards updates correctly on the next load after a relevant underlying change (e.g., adding an uninsured dependent parent flips the "Parents" card to a warning state) — no manual cache-bust required.
- [ ] The `retirement_readiness` and `emergency_readiness` card values are byte-identical to the existing `/api/v1/dashboard` endpoint's equivalent figures for the same user at the same point in time (proving reuse, not reimplementation/drift).
- [ ] Every item in the `recommendations` feed traces to either the Insurance (§10) or Schemes (§11) computation — no orphaned or independently-generated recommendation text.

## Cross-Cutting

- [ ] Zero existing tests regress (full backend suite + frontend `tsc` clean) after Milestone 2 implementation.
- [ ] Every new mutation endpoint writes a corresponding `audit_logs` row.
- [ ] No endpoint returns another user's or another household's data under any tested input, including guessed/enumerated UUIDs.
- [ ] `ruff check app/` and `mypy --strict app/` remain clean.
