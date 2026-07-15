# Notification Identity Review — Phase 3

**Date:** 2026-07-08
**Purpose:** define, per source, the stable identity a notification is deduplicated by — precise enough to implement without further design decisions.

---

## General rule

Every notification's identity is `uuid.uuid5(NOTIFICATION_NAMESPACE, f"{source}:{natural_key}")` — a deterministic UUID computed from a fixed namespace plus a source-specific natural key string. Same natural key → same UUID, every time, on every machine, with no database round-trip needed to compute it. This UUID is what `notification_markers.dedupe_key` stores, and what the two `POST` endpoints (read/dismiss) take as their path parameter — opaque, URL-safe, and reveals nothing about the underlying fact to a client inspecting the URL.

## Per-source natural key

| Source | Natural key | Why this, not something narrower/broader |
|---|---|---|
| **Insurance** | `f"{user_id}:{sorted(subjects)}"` (`subjects` is `list[str]` of member *names* — `InsuranceRecommendation` does not carry member IDs, confirmed in `app/schemas/insurance.py`) | Matches exactly the set of people the current recommendation names. If the subject set changes (e.g., a policy is added covering one of two previously-uninsured parents), the natural key changes — correctly treated as a *new* fact, not an update to the old one. Same acknowledged name-vs-ID limitation as the Schemes source below — not fixed here, as it would mean changing `InsuranceRecommendation`'s shape. |
| **Schemes** | `f"{user_id}:{scheme_code}:{member_name}"` | `SchemeEligibilityItem` (the existing, unmodified type `evaluate_household_eligibility()` returns) carries `member_name`, not a member ID. This is an honest, acknowledged limitation, not a new gap introduced by this phase: renaming a family member would produce a "new" scheme notification for the same underlying eligibility fact. Not fixed here — fixing it would mean changing `SchemeEligibilityItem`'s shape, which is exactly the kind of recommendation-engine change this phase is not authorized to make. Flagged for whoever next touches that type. |
| **Family member added** | `f"{audit_log_row.id}"` | The cleanest of all five — `AuditLog` rows already have a stable, unique primary key. No hashing of business fields needed at all. |
| **Goal at risk** | `f"{goal_id}:at_risk"` | One notification per goal, for as long as it stays not-on-track. If dismissed, it does not reappear unless the goal's `on_track` flips back to `true` and later back to `false` again is impossible to distinguish from "still the same at-risk episode" with a snapshot-only design — accepted, documented trade-off, identical in kind to how the Insurance/Schemes sources already behave (dedup by current-fact identity, not by discrete state-transition events; see §"Accepted trade-off" below). |
| **Goal completed** | `f"{goal_id}:completed"` | A goal, once its `current_amount` reaches `target_amount`, is expected to stay completed — a natural one-time congratulatory notification, not a recurring one. |

## Accepted trade-off, stated plainly (applies to Insurance, Schemes, Goal-at-risk, Goal-completed)

All four "standing fact" sources dedupe by **the fact's current identity**, not by **the event of it becoming true**. Practically: if a user dismisses "Priya is at risk of missing her goal," and later edits the goal so it briefly becomes on-track and then not-on-track again for an unrelated reason, the dismissed notification **does not reappear** — the natural key (`goal_id:at_risk`) hasn't changed. This is a deliberate, consistent property across every fact-based source in this phase, not a defect unique to one of them — building true event-transition tracking (distinguishing "newly became at-risk" from "still at-risk") would require persisting a *history* of on_track values per goal, which is new calculation-adjacent state this phase's scope does not include. If this trade-off proves wrong in practice, it's a scoped, well-understood follow-up, not a silent gap.

**"Family member added" does not have this trade-off** — because its identity is the `AuditLog` row's own ID (a genuine, one-time event), not a re-derived snapshot condition, dismissing it is truly final and correct with no edge case.

## Read / dismissed state model

| State | Condition |
|---|---|
| Unseen (new) | No `notification_markers` row exists for this `(user_id, dedupe_key)` |
| Unread, seen | Row exists, `read_at IS NULL`, `dismissed_at IS NULL` |
| Read | Row exists, `read_at IS NOT NULL`, `dismissed_at IS NULL` |
| Dismissed | Row exists, `dismissed_at IS NOT NULL` (regardless of `read_at`) |

`GET /notifications` returns unseen + unread-seen + read facts (i.e., everything not dismissed) by default, each annotated with its current state; dismissed facts are excluded from the default list entirely (matching the everyday meaning of "dismiss" — it's gone, not just marked read). Marking read and dismissing are two independent `POST` actions — a fact can be read without being dismissed (the common case: you saw it, you'll deal with it later) or dismissed directly without ever being marked read first (you recognized what it is from the summary alone and don't need to expand it).

## Unread count

`count(facts where state ∈ {unseen, unread-seen})` — computed from the same live fact-fetch + marker-reconciliation `GET /notifications` already does; the header bell's badge count is a lightweight variant of the same query (count only, no need to build the full list), not a separate calculation.
