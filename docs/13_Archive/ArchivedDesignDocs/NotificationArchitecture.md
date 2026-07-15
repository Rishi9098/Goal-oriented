# Notification Architecture — Phase 3 (as built)

**Date:** 2026-07-08
**Supersedes:** nothing in `ArchitectureReview_Phase3.md` (the pre-implementation design) — this records what was actually built, including what live verification surfaced.

---

## The one property that matters most

**Notification content is never persisted.** `notification_markers` stores exactly five columns: `user_id`, `source`, `dedupe_key`, `read_at`, `dismissed_at`. No `title`, no `body`, no copy of anything a recommendation engine said. Every time a notification is displayed — in the list, in the badge count — its title and body are read live from the same functions the Insurance, Schemes, and Goals pages themselves call. This is the mechanism by which "notifications are a presentation layer, not a second recommendation engine" is actually true, not just asserted.

## Five sources, all zero-new-calculation, one deliberately deferred

| Source | Data read | New computation |
|---|---|---|
| `insurance` | `family_insurance_service.compute_insurance_recommendation()` | None |
| `schemes` | `scheme_eligibility_service.evaluate_household_eligibility()` | None |
| `family_member_added` | Existing `AuditLog` rows (`action="family_member_added"`), joined to the current `HouseholdMember` row for its name | None |
| `goal_at_risk` | `goal.on_track` (stored, ADR-001-compliant) | None |
| `goal_completed` | `goal.current_amount >= goal.target_amount` | None |

**"Goal probability changed" was not built** — the one candidate source that would require new state (remembering a goal's last-notified probability), which this phase's scope explicitly excludes from touching the Goal model or dashboard.

## Read/write discipline — verified, not just designed

`GET /api/v1/notifications` computes every source fresh and left-joins against *existing* marker rows — it creates nothing. Verified by an automated test (`test_get_notifications_never_creates_a_marker_row`) that calls the endpoint three times and asserts the `notification_markers` table stays empty throughout. The only writes in this feature are the two explicit `POST` endpoints (`.../read`, `.../dismiss`), each an upsert scoped to exactly the `(user_id, dedupe_key)` the caller names.

## Identity — `uuid5(namespace, "source:natural_key")`

Deterministic, no database round-trip needed to compute, collision-proof within a namespace. Per-source natural keys are documented exhaustively in `NotificationIdentityReview.md`, including two honestly-acknowledged limitations: Insurance and Schemes key off subject *names* (not IDs, since neither `InsuranceRecommendation` nor `SchemeEligibilityItem` carries one), and all four "standing fact" sources (everything except `family_member_added`) dedupe by current-fact identity, not by discrete state-transition events — dismissing "goal at risk" suppresses it permanently for that goal, not just for the current at-risk episode.

## A real bug the implementation surfaced: `after_state` doesn't carry a name

`family_service.py`'s `family_member_added` audit rows store only `member_id` and `relationship_type` — never the member's name (confirmed by reading the actual write site, not assumed). The initial implementation read `after_state.get("name")`, which is always `None`. **Fixed** by looking up the `HouseholdMember` row by the ID stored in `after_state`, using the same `resolve_member_name()` helper the rest of the codebase already uses (correctly special-casing `relationship_type == "self"`) — still a plain read of already-existing data, not a new computation, and covered by a passing integration test.

## A real environment issue found during live verification, unrelated to this feature's code

Port 8000 was intermittently claimed by an entirely unrelated project's backend (`~/Downloads/Rishi/Assig/backend`), which respawned once after being stopped. This produced a run of 404s/503s and one moment where the app correctly (and safely) redirected to sign-in after an auth check failed against the wrong server — a correct reaction to bad data, not a bug in the notification code. Documented here because it looked, briefly, exactly like a real regression before being traced to its actual cause.

## Frontend

`code/src/components/notification-center.tsx` — a `Popover` (previously unused shadcn scaffold, same discovery pattern as Phase 2's `command.tsx`) anchored to the header bell. `useQuery(["notifications"], ..., { refetchInterval: 120_000 })` polls for badge/list updates; `useMutation` for read/dismiss, each invalidating the same query key on success. The popover is a **controlled** component (`open`/`onOpenChange`) specifically so that selecting a notification both marks it read *and* closes the panel before navigating — an early implementation gap (the panel stayed open across the navigation) caught and fixed during live verification, not left in place.

## Conclusion

One new table, zero new calculation logic, two real bugs found and fixed during implementation/verification (the missing-name lookup, the panel-not-closing), one environment issue correctly diagnosed and resolved rather than misattributed to the feature, and a read/write split that holds up under an actual automated test, not just a design intention.
