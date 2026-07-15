# Architecture Review — Phase 3 (Notification Center)

**Date:** 2026-07-08

---

## The three options, evaluated against this phase's two hard constraints

Two constraints, both non-negotiable per this phase's instructions, must both hold simultaneously: (1) **read/unread and dismiss must genuinely work** (success criteria), and (2) **notifications must never become a second recommendation engine** (objective). Each option is evaluated against both, not just one.

### Option A — Fully generated (no persistence of any kind)

Every request re-evaluates all five sources fresh and returns them; nothing is ever written.

**Disqualified, not just disfavored.** Read/unread and dismiss are inherently stateful concepts — there is no way to know "has this user seen this fact before" or "did this user dismiss it" without remembering *something* across requests. Option A cannot satisfy this phase's own success criteria by construction, not by preference. This isn't a trade-off to weigh; it's a hard requirement Option A cannot meet at all.

### Option B — Fully persisted (a `Notification` table storing generated content)

A background or on-demand process computes notifications and stores their title/body/reasoning, the way the dead `Recommendation`/`RecommendationCitation` tables were originally shaped for.

**Rejected — this is precisely the second recommendation engine the objective forbids.** If a notification's *content* (not just its seen/dismissed state) is persisted, it becomes a second, independent copy of whatever `compute_insurance_recommendation()` or `evaluate_household_eligibility()` said at write time — and it goes stale the moment the underlying household data changes, exactly the failure mode `RecommendationConsistencyReview_Task10.md` proved the live engines *don't* have ("repeated reads never change the recommendation... because it's a pure function of current data, never persisted"). Storing notification content would mean Northstar has to either (a) build a background job to keep the copy in sync — new infrastructure this phase's own instructions don't authorize and this codebase doesn't have (confirmed: no scheduler/queue anywhere, same finding `ArchitectureDecisionRecord.md` made for a different reason), or (b) accept that notifications silently drift from the truth the moment something changes. Both outcomes are worse than the problem being solved.

### Option C — Hybrid: never persist content, persist only a seen/read/dismissed marker keyed by a stable, content-derived identity

Every notification's displayed text is **always** read live from the existing engine at request time — exactly the same call the Insurance/Schemes/Goals pages themselves already make. The **only** new persisted state is a small ledger: *has this specific fact, identified by a stable key, been seen/read/dismissed by this user* — never *what the fact says*.

**Chosen.** This is the only option that satisfies both constraints simultaneously: read/unread/dismiss work (state is persisted), and there is no second recommendation engine (content is never persisted, never drifts, and disappearing conditions naturally stop appearing with no cleanup job required — verified as a real property, not a hoped-for one, in `NotificationCenterDesign.md` §2, written during the earlier Global Shell Architecture Review and re-confirmed unchanged here).

## What gets built — five sources, zero new calculation, one deliberately deferred

Per `DependencyValidation_Phase3.md` §7, five sources are reachable as pure reads of already-computed/already-logged data: **Insurance recommendation, Government scheme eligibility, Family member added (from existing `AuditLog` rows), Goal at risk (`!goal.on_track`), Goal completed (`current_amount >= target_amount`)**. **"Goal probability changed" is explicitly not built in this phase** — it is the one source that would require new state (a "last-notified probability" per goal) beyond a simple seen-marker, and adding that state to the `Goal` model or a new tracking mechanism edges toward "redesigning" a model this phase's instructions explicitly protect ("do not redesign the dashboard," and by clear extension, the goal data it's built from). Flagged here as a real, considered scope boundary, not a silently dropped requirement.

## Read-vs-write discipline — the one subtlety this design must get right

**No `GET` endpoint in this feature ever writes anything.** `GET /notifications` computes all five sources fresh and left-joins against *existing* seen-marker rows (never creating one) — a fact with no marker row is simply reported as unread. Marker rows are created or updated **only** by two explicit, user-initiated `POST` endpoints: mark-as-read and dismiss. This is deliberate, and directly informed by this project's own hard-won lesson: `ArchitectureDecisionRecord.md` (ADR-001) exists because a `GET` endpoint (`get_dashboard()`) was silently mutating stored data on every read. This feature must not repeat that mistake in a new form — even a small, low-stakes "first seen" timestamp write from a passive `GET` would be the same *category* of bug, just with lower financial stakes. Every write in this feature traces to an explicit, nameable user action (open the item / dismiss it), never to the act of merely fetching a list.

## Schema (one new table, additive-only migration)

```
notification_markers
  id            UUID PK
  user_id       UUID FK -> users, indexed
  source        string   ("insurance" | "schemes" | "family_member_added" | "goal_at_risk" | "goal_completed")
  dedupe_key    UUID     (uuid5, deterministic from source + stable natural key — see NotificationIdentityReview.md)
  read_at       timestamp, nullable
  dismissed_at  timestamp, nullable
  created_at    timestamp
  unique(user_id, dedupe_key)
```

One table, not the two-table split `NotificationCenterDesign.md` originally sketched (a second table for hypothetical "true system events" with a persisted body) — that second table is not needed because every source this phase actually implements is a live-re-derivable fact, not a one-off event with no live source to re-check. If a genuine one-off system event ever needs notifying in the future, it is a new, separate design decision, not something to speculatively build now.

## Conclusion

Hybrid (C), one new table, zero new backend calculation logic, zero recommendation-engine or dashboard changes, and a `GET`/`POST` split that keeps every read pure — consistent with this project's own hardest-learned lesson about read-path mutation. **Proceeding to Notification Source Review (folded above) and Deduplication Review.**
