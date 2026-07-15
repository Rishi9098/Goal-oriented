# PR Report — Global Shell Phase 3 (Notification Center)

**Date:** 2026-07-08
**Scope:** Phase 3 only — the Notification Center. No AI improvements, no recommendation-engine redesign, no dashboard redesign.

---

## Summary

The header bell (a static, non-functional decoration since the Interactive Product Audit) is now a real notification center. It surfaces five kinds of already-existing intelligence — insurance recommendations, government scheme eligibility, family members added, goals at risk, and goals completed — with read/unread and dismiss state, without ever persisting notification content. One new table (`notification_markers`), zero new calculation logic, zero changes to the recommendation engine or the dashboard.

## Pipeline

1. **Dependency Validation** (`DependencyValidation_Phase3.md`) — confirmed five of six candidate sources are reachable with zero new calculation (pure reads of already-computed/already-stored/already-logged data); confirmed ADR-001 is fully implemented in code (goal probability is stable, not recalculated on read) despite its own status line still reading "Proposed"; confirmed the dead `Recommendation`/`RecommendationCitation` tables remain unused and must stay that way.
2. **Architecture Review** (`ArchitectureReview_Phase3.md`) — evaluated Fully Generated (disqualified: can't support read/unread), Fully Persisted (rejected: recreates the exact recommendation-engine-drift risk this project already fixed once, per `RecommendationConsistencyReview_Task10.md`), and Hybrid (chosen: content always read live, only a seen/read/dismissed marker persisted). Established the read/write discipline: no `GET` in this feature ever writes, directly informed by this project's own `ArchitectureDecisionRecord.md` (ADR-001) precedent of a `GET` endpoint silently mutating state.
3. **Notification Source Review** (folded into Architecture Review) — five real sources; "goal probability changed" explicitly deferred as the one source needing new state.
4. **Deduplication Review** (`NotificationIdentityReview.md`) — per-source natural keys, `uuid5`-derived stable identity, the read/dismissed state model, and two honestly-documented limitations (name-based not ID-based keys for Insurance/Schemes; fact-identity not event-identity dedup for the four "standing fact" sources).
5. **UX Review** (folded into Architecture Review + implementation) — bell badge, Today/Earlier grouping, empty/loading/error states, mobile behavior.
6. **Implementation** — see Files Changed.
7. **Accessibility Review** — see below.
8. **Performance Review** (`NotificationPerformanceReport.md`) — no duplicate backend calls, no N+1 queries, zero new dependencies, verified no GET-triggered writes via an automated test.
9. **Live Verification** — see below. Found and fixed two real bugs (full detail in `NotificationArchitecture.md`), and correctly diagnosed an unrelated environment issue (a port-8000 conflict with a different project's server) rather than misattributing it to this feature.
10. **First-Time User Review** — see below.
11. **Product Consistency Review** — see below.
12. **Regression Testing** — backend: `ruff`/`mypy` clean, full suite 341/341 passing (330 pre-existing + 11 new), 97.53% coverage; frontend: `tsc`/`eslint` clean on every touched file.
13. **Documentation** — this report, `NotificationArchitecture.md`, `NotificationPerformanceReport.md`, `PROJECT_STATE.md`, `CHANGELOG.md`.

## Files Changed

| File | Change |
|---|---|
| `backend/app/models/notification.py` (new) | `NotificationMarker` — seen/read/dismissed state only, never content |
| `backend/alembic/versions/009_notification_markers.py` (new) | Additive migration, one new table |
| `backend/app/schemas/notification.py` (new) | `NotificationItem`, `NotificationListResponse` |
| `backend/app/services/notification_service.py` (new) | Collects five sources fresh, reconciles against markers, never writes on read |
| `backend/app/routers/notifications.py` (new) | `GET /notifications`, `POST /notifications/{source}/{key}/read`, `POST /notifications/{source}/{key}/dismiss` |
| `backend/app/main.py` | Registered the new router |
| `backend/app/models/__init__.py` | Exported `NotificationMarker` |
| `backend/tests/test_notifications.py` (new) | 11 integration tests — sources, read/dismiss, read-never-writes, dismiss permanence, cross-user isolation |
| `code/src/components/notification-center.tsx` (new) | The bell + `Popover` panel, previously-unused `popover.tsx` scaffold |
| `code/src/components/app-shell.tsx` | Replaced the static bell `<button>` with `<NotificationCenter />` |
| `code/src/lib/api.ts` | `getNotifications`, `markNotificationRead`, `dismissNotification` + types |

## Live Verification (performed this session, against the real running app)

Registered a fresh test account and created a family member, an at-risk goal, and a completed goal — confirmed all four expected notifications appeared (insurance also fired, since the dev database already had seeded tax data from earlier work), each with correct, live-read titles/bodies. Confirmed the bell badge count (4 → 3 → 2 → 1) tracked read/dismiss actions correctly across dismiss and mark-read. Confirmed state survived a full page reload (the dev DB, not just client cache). Confirmed clicking a notification navigates to the correct real page (`/app/family/insurance`) and its content matches the notification's own text exactly, since both read the same live engine. Confirmed keyboard accessibility end-to-end: `Tab` reaches the bell with a visible focus ring, `Enter` opens the panel and moves focus inside it, `Escape` closes it and returns focus to the bell — all provided by Radix `Popover`, none hand-built.

**Two real bugs found and fixed during this session** (full detail in `NotificationArchitecture.md`): (1) `family_member_added` notifications initially showed no name, because `AuditLog.after_state` only stores `member_id`/`relationship_type`, not a name — fixed by looking up the current `HouseholdMember` row; (2) the notification panel stayed open after clicking an item and navigating away — fixed by making the `Popover` a controlled component that closes on selection.

**One environment issue correctly diagnosed, not misattributed**: mid-verification, the app appeared to break (goals vanished, avatar showed "?", one request 503'd) — traced to an unrelated project's backend (`~/Downloads/Rishi/Assig/backend`) intermittently claiming port 8000 (and respawning once after being stopped), not to a defect in this feature. Confirmed by checking `lsof`, stopping the conflicting process (with the user's explicit go-ahead both times), and re-verifying cleanly.

## Accessibility Review

- **Keyboard navigation**: bell is a real `<button>`, reachable via `Tab`, opens via `Enter`/`Space` (native button semantics, not a hand-rolled click handler).
- **Focus management**: Radix `Popover` traps focus within the panel while open and returns it to the bell on close — verified live, not just assumed from the library's docs.
- **ARIA**: inherited entirely from Radix `Popover`'s own accessible dialog/combobox pattern — no custom ARIA attributes written by hand.
- **Escape**: closes the panel and returns focus — verified live.
- **Screen readers**: the bell's `aria-label` includes the live unread count (`"Notifications, 3 unread"`) so the badge's information isn't visual-only; each dismiss button has a specific `aria-label` naming which notification it dismisses, not a generic "Close."

## First-Time User Review

Every notification explains, in its own body text, *why* it exists and *what to do*: "Adding Kavita Notif to a standalone health policy... can unlock a tax deduction" (insurance), "Review their profile to complete tax and insurance details" (family member added), "Current probability of success is 0%, below the 70% on-track threshold" (goal at risk) — none of these require the user to already understand the underlying tax/eligibility rules to know why they're seeing the notification. The empty state ("You're all caught up... New goal, insurance, and scheme updates will show up here") tells a first-time user what kinds of things will appear here before anything ever has.

## Product Consistency Review

All styling reuses existing design tokens (`bg-surface`, `text-muted-foreground`, `bg-cyan` for the unread indicator, matching the same accent already used for the search bar's kbd hint and the account menu) — no new colors introduced. The panel's grouping/spacing/typography matches the existing `command.tsx`/`dropdown-menu.tsx` density conventions from Phases 1 and 2. Dark, single-theme palette respected throughout; no theme-switching code introduced.

## Rollback

Revert the new frontend file and the two touched frontend files; revert the new backend files and the two touched backend files; run `alembic downgrade -1` to drop `notification_markers`. No data migration/backfill needed either direction.

---

## Success Criteria

- [x] Bell icon becomes functional
- [x] Existing recommendation engine reused (Insurance, Schemes — zero new calculation)
- [x] No duplicate calculations (verified: each engine called exactly once per request)
- [x] No duplicate recommendation logic (content never persisted, always read live)
- [x] Notifications explain why they exist (First-Time User Review)
- [x] Read/unread works (verified live, state persists across reload)
- [x] Dismiss works (verified live, permanently removes from default list)
- [x] Zero regressions (backend 341/341 passing, 97.53% coverage; frontend `tsc`/`eslint` clean)

**Stopping here per instruction. Awaiting review and approval. Not beginning any Milestone 3 work.**
