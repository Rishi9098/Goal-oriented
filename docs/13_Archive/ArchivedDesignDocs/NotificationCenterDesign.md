# Notification Center — Design

**Date:** 2026-07-08
**Status:** Design only. No code written.
**Depends on:** `GlobalShellArchitecture.md`

---

## 1. Current backend support

**None.** No `Notification` model, no notification router, no read/unread column anywhere in the backend. The header's notification bell (`components/app-shell.tsx`) is a `<button>` with no `onClick` and a permanently-rendered unread dot tied to nothing — confirmed dead in the Interactive Product Audit.

**One adjacent, currently-unused table exists and must be explicitly addressed, not silently ignored:** `Recommendation` / `RecommendationCitation` (`backend/app/models/recommendation.py`) is a fully-designed schema for *persisted, citable* recommendations (reasoning, confidence score, citations back to specific `scheme_rates`/`tax_sections` rows) — but it is never read or written by any current router or service. **This design deliberately does not build the Notification Center on top of it**, for a reason grounded in this codebase's own established doctrine (§2).

## 2. Why persisted recommendations are the wrong foundation — and what to use instead

Milestone 2's Family Recommendations feed (`family_recommendations_service.py`) was explicitly designed so recommendations are **"never persisted, computed fresh on every read"** (`RecommendationIntegrityReview_Task10.md` #4) — this was a deliberate choice to guarantee a recommendation can never go stale relative to the household data it's based on. Building notifications by persisting recommendation *content* (via the dead `Recommendation` table or a new equivalent) would silently reintroduce exactly the staleness risk that design decision was made to prevent — e.g., a persisted notification could keep telling a user "add insurance for your mother" for days after they actually added it, if the persisted copy isn't perfectly kept in sync with the live engine.

**The correct architecture separates two different things that "notification" conflates by default:**

1. **Derived notifications** (insurance gaps, scheme matches) — the *content* is never persisted; only a lightweight **"seen" marker** is. At render time, the system re-fetches the live, authoritative feed (`family_recommendations_service.get_family_recommendations()` — already built, already tested) and cross-references it against the seen-marker table by a **stable dedupe key**, not by row ID (since there is no row). A natural dedupe key: `hash(user_id + source + recommendation_type + sorted(subject_member_ids))` — stable as long as the same fact keeps being true, and naturally different once the underlying fact changes (e.g., the subject list changes because a policy was added).
   - **This design has a genuinely elegant property**: if a recommendation's underlying condition resolves before the user ever opens the notification panel (e.g., they add the missing policy first), the live feed simply stops returning it — there is nothing stale to show, and no cleanup job is ever needed to retract a notification. This could not work if the *content* were persisted.
2. **True event notifications** (one-off things that happened, not standing facts that can be re-derived) — e.g., a security-relevant account event. These genuinely need a persisted body, because there's no live "current state" to re-derive them from. This is a small, separate table (§3).

## 3. Proposed schema (design only — not a migration)

**Table A — `notification_seen_markers`** (backs category 1, derived notifications)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `dedupe_key` | string, indexed | as defined above |
| `source` | string | `"insurance"` \| `"schemes"` — mirrors `FamilyRecommendation.source`, already an established enum in `family_recommendations_service.py` |
| `first_seen_at` | timestamp | when the notification panel first showed this fact to this user |
| `read_at` | timestamp, nullable | set when the user opens/expands it |
| `dismissed_at` | timestamp, nullable | explicit dismiss, separate from read — a user may mark something read without wanting it gone, or dismiss without expanding it |

**Table B — `notifications`** (backs category 2, true events)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `category` | string | `"system"` (initial, only category populated at launch — see §4) |
| `title`, `body` | string, text | |
| `action_url` | string, nullable | deep link (e.g., to Settings) |
| `read_at`, `dismissed_at` | timestamp, nullable | same semantics as Table A |
| `created_at` | timestamp | |

This mirrors the existing `AuditLog` model's shape closely enough (`user_id`, action-like field, timestamps, before/after-equivalent) that it should follow the same file/service conventions rather than inventing a new pattern.

## 4. Categories

**V1, deliberately narrow:**
- **Insurance** — sourced live from `family_insurance_service.compute_insurance_recommendation()`, zero new business logic.
- **Schemes** — sourced live from `scheme_eligibility_service.evaluate_household_eligibility()`, zero new business logic.
- **System** — reserved for Table B events. **No events populate this category at V1 launch** — it exists so the schema doesn't need a migration the first time a real one is needed (e.g., a future "your export is ready" or security-notice use case), but nothing should be invented to fill it just to have content.

**Explicitly deferred, and why:** a "Goal milestone" category (e.g., "your retirement goal crossed 80% probability") is a natural, appealing fourth category — but it requires **new** derived logic that doesn't exist today (comparing today's Monte Carlo probability against the last-seen value, which means the system needs to remember the last-seen value somewhere, most naturally as a small addition to Table A's pattern once it's proven in production). Deferred to V2 rather than designed in full here, to keep V1's scope to "wire up what's already computable" (Constitution Rule 7 — no speculative generality).

## 5. Read/unread

Read/unread is `read_at IS NULL` (unread) vs. populated (read) in both tables — a single, consistent convention across both notification types, so the frontend's rendering logic doesn't need to branch on which table a notification came from. Unread **count** (the header bell's badge) is a single lightweight aggregate query: `count(Table A rows not dismissed and unread) + count(Table B rows not dismissed and unread)` — cheap at this data volume (single-digit rows per user in practice) and cacheable via the same React Query pattern as everything else.

**Dismiss vs. read, precisely defined:** dismissing removes an item from the default panel view (like archiving); it does not require the item to have been read first (a user can dismiss something they recognize without opening it) and does not delete the row (kept for the dedupe-key mechanism in Table A, so a dismissed insurance gap doesn't immediately reappear the next time the panel loads — it only reappears if the underlying live fact meaningfully changes, at which point it's arguably a *new* fact worth re-surfacing, which the dedupe key already handles correctly since a changed subject list produces a new key).

## 6. Real-time vs. polling

**No WebSocket or SSE library exists in the frontend dependency tree; none is proposed here.** Recommendation: **polling via React Query**, consistent with every other data-fetching pattern already in this app.

- **Unread count:** `useQuery` with `refetchInterval: 120_000` (2 minutes) and `refetchOnWindowFocus: true`. The underlying facts (insurance gaps, scheme eligibility) only change when the user themselves edits family/goal data in the same session, or extremely rarely from a scheduled rate/policy update — there is no scenario in this product where sub-minute freshness matters, unlike a chat or trading application. Two minutes is conservative enough to avoid meaningful battery/network cost on an idle tab, responsive enough that a notification appears "soon" after its triggering condition (e.g., adding a parent with no insurance) without the user needing to manually refresh.
- **Full panel list:** fetched only when the panel is opened (lazy, matching the Search palette's own lazy-fetch design in `GlobalSearchDesign.md`), not polled continuously.
- **Why not real-time:** building WebocketSSE infrastructure for a notification volume of "a handful of standing facts per household, refreshed every couple of minutes" would be substantial new operational surface (a persistent connection layer, reconnection handling, a pub/sub backend) for no measurable user benefit at this product's actual usage pattern. This is the same judgment this session's separate AI Assistant research applied to inference infrastructure: don't build for a scale or immediacy requirement the product doesn't have.

## 7. Future compatibility

- The dedupe-key mechanism in Table A generalizes cleanly to future derived-notification sources (goal milestones, future recommendation types) without a schema change — only a new `source` value and a new dedupe-key formula per source.
- Table B's `category`/`action_url` shape is intentionally generic enough to carry future system events (billing, security, product announcements) without redesign.
- If the product ever does need real-time (e.g., a future collaborative/shared-household feature where one member's edit should instantly notify another logged-in member), the polling design degrades gracefully into that — the same `useQuery` call simply gets a shorter interval or is supplemented by a push invalidation signal later; nothing in this design needs to be torn out to add that.
- This design does not touch, migrate, or repurpose the existing dead `Recommendation`/`RecommendationCitation` tables. They remain as-is; a separate, future decision (outside this design's scope) should determine whether to formally remove them or find them a real use — leaving them untouched avoids conflating two unrelated cleanup/build decisions.
