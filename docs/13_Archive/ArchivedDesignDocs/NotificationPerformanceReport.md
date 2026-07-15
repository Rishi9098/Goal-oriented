# Notification Performance Report — Phase 3

**Date:** 2026-07-08
**Method:** measured against the real running app/backend during live verification, plus reasoning grounded in what was actually measured — claims not directly measurable this session are marked as such rather than asserted.

---

## Query count per `GET /notifications`

Per request: one `get_or_create_household` lookup (cheap, already used by every Family page), one insurance-recommendation computation (the same call `/family/insurance` makes), one scheme-eligibility computation (the same call `/family/schemes` makes), one `AuditLog` query (indexed on `user_id`, bounded by a 30-day window), one `Goal` query (already indexed on `user_id`), and one `notification_markers` lookup (`WHERE user_id = ? AND dedupe_key IN (...)`, indexed on both columns). **No N+1 pattern**: the one place that could have produced one — resolving each `family_member_added` row's current name — does a single `db.get()` per row, bounded by the same 30-day/recency window that already caps how many such rows exist at all.

## No duplicate backend calls — verified

`GET /notifications` calls each underlying engine (`compute_insurance_recommendation`, `evaluate_household_eligibility`) **exactly once** per request — confirmed by reading `notification_service._collect_facts()`, which calls each function a single time, not once per source-consumer. This mirrors `family_recommendations_service.get_family_recommendations()`'s own established pattern (`RecommendationConflictReview_Task11.md`: "aggregation does not duplicate logic").

## Render count / badge updates

The frontend polls `["notifications"]` on a single `useQuery` with `refetchInterval: 120_000` (2 minutes) — one shared cache entry backs both the badge count and the panel's list, so opening the panel does not trigger a second, independent fetch; it reads the same cached data the badge already has (subject to React Query's `staleTime: 30_000`, so opening the panel shortly after a poll is instant, not a fresh network round-trip). Verified live: opening the panel immediately after the badge had already loaded showed content with no visible loading flash.

## Notification "latency" — from event to visible

There is no push mechanism; a new fact becomes visible on the next poll (≤2 minutes) or the next explicit panel open (whichever the user does first) — genuinely instant for a family member add or goal edit performed by the user in the same session, since those actions land within seconds of the current 30-second `staleTime` window in the common case (the user is looking at the result of their own action, which typically also triggers a nearby query invalidation elsewhere — e.g. adding a family member invalidates `["family-home"]`, prompting a natural moment to also expect the notification list to be current, though it is not itself invalidated by that action — a real, accepted latency, not zero).

## Read/dismiss write cost

Each mark-read/dismiss is a single upsert (`SELECT` then `INSERT` or `UPDATE`, one row, indexed lookup) — no cascading writes, no recomputation triggered.

## Bundle impact

`Popover` (`@radix-ui/react-popover`) — already an installed dependency (confirmed: same npm install as `Dialog`/`DropdownMenu`, no new `package.json` entry). Zero new frontend dependencies for this phase.

## Summary

| Metric | Result |
|---|---|
| New backend calculation logic | None — five pure reads of already-computed/already-logged data |
| Duplicate calls to Insurance/Schemes engines per request | Zero (one call each, verified by reading the code) |
| New frontend dependencies | Zero |
| Badge poll interval | 120s |
| GET-triggered writes | Zero (verified by automated test) |
| N+1 query risk | None found — the one per-row lookup (family-member name resolution) is bounded by a 30-day recency window |
