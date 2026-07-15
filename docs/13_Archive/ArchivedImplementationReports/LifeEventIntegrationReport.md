# Life Event Integration Report — Phase 2

**Scope:** Exactly what `LifeEventIntegrationReview.md` decided — surface Life Events on Dashboard, Reports, Financials, and Family; add an honest, always-true recommendations note on Dashboard and Family Recommendations; a dynamic, context-aware suggested prompt on AI Copilot; and a real type-safety fix plus copy update on Notifications. Zero backend changes.

---

## Files Changed

| File | Change |
|---|---|
| `code/src/lib/api.ts` | `NotificationSource` widened to include `"life_event"` and `"divorce_review"` — both are real values the backend (`app/schemas/notification.py`) has sent all along; the frontend type was simply never updated to match. |
| `code/src/components/notification-center.tsx` | Empty-state copy now mentions life events. |
| `code/src/components/life-events/RecentLifeEventsCard.tsx` | **New.** Shared card, reused on Dashboard and Family — fetches `GET /life-events`, optionally filtered client-side to a set of event types, renders a compact link-card matching the app's existing `surface-card`/`FamilyCard` visual language. Two empty-state modes: `"prompt"` (Dashboard — invites recording a first event) and `"hidden"` (Family — mirrors `FamilyCard`'s own existing "say nothing if there's nothing to say" rule). |
| `code/src/routes/app.index.tsx` | Renders `RecentLifeEventsCard` (prompt mode) below the existing Family card. Adds one always-true sentence to the AI Copilot suggestions card: recommendations already reflect anything recorded as a life event. |
| `code/src/routes/app.reports.tsx` | New "Life Events This Year" section, independently fetched (matching this file's existing per-section fetch pattern) via `GET /life-events` scoped to the current calendar year using its existing `start_date`/`end_date` params. |
| `code/src/routes/app.financials.tsx` | New info banner at the top of the page pointing to Life Events for real-world changes ("a raise, a new loan, a move"). |
| `code/src/routes/app.family.index.tsx` | Renders `RecentLifeEventsCard`, scoped to the Life Event catalog's own "Family" category (`marriage`, `birth_of_child`, `adoption`, `divorce`, `dependent_parent` — derived from `LIFE_EVENT_TYPES`, not a second hand-maintained list), hidden entirely when none exist. |
| `code/src/routes/app.family.recommendations.tsx` | Same always-true recommendations note as Dashboard. |
| `code/src/routes/app.copilot.tsx` | Fetches the single most recent life event; when one exists, prepends a dynamically-worded suggested prompt ("How did recording my Salary Raise affect my plan?") above the static suggestions, under a "Based on your recent activity" label. |

## Files Not Changed (and why)

| File / area | Reason |
|---|---|
| `backend/**` (all) | Confirmed via `git status` — zero backend files touched. Every integration reuses `GET /life-events`, which already supports every filter needed (`event_type`, `start_date`, `end_date`, `limit`). |
| `notification_service.py` | Already correct — `_collect_life_event_facts`/`_collect_divorce_review_facts` were found, read, and verified working; nothing needed fixing there. Only the frontend's stale type needed correcting. |
| Any recommendation service (`family_recommendations_service`, `planning_service`, etc.) | ADR-005 compliance — recommendations remain computed live and are never persisted or recalculated by this phase. The two new notes added to the UI state an already-true fact about the existing system; they compute nothing new. |
| Per-notification-source icons | Every existing source already renders with no icon at all today; adding one only for life events would introduce a new inconsistency rather than fix one — deferred to Phase 6 (Cross-module Consistency), where it belongs. |
| Life Events page's own type-filter / URL query params | Not needed for this phase's scope — Family's card links to the unfiltered `/app/life-events` history, which is sufficient to answer "what happened." Pre-filtered deep-linking is a reasonable future enhancement, not required here. |

## Implementation Summary

1. Read `notification_service.py` and `app/schemas/notification.py` directly rather than trusting `ProductDesignAuthorityReview.md`'s assumption that Life Events had no Notification integration — found it was already built, and found the real gap (a frontend type omission) instead.
2. Built one shared, reusable component (`RecentLifeEventsCard`) instead of three copy-pasted ones, parameterized for the two real differences needed (event-type filter, empty-state behavior).
3. Every new data fetch reuses the exact same `GET /life-events` endpoint the Life Events page itself already calls — no new endpoint, no new backend schema, no new calculation.
4. Every new claim of the form "recommendations reflect X" is literally true today (ADR-005), stated as a fact, never as a fabricated causal attribution the system can't verify (explicitly called out as a line this phase would not cross, in `LifeEventIntegrationReview.md` §5).
5. Each new fetch matches its host file's existing convention rather than introducing a third fetching pattern into a codebase that already has two (`useQuery` on Dashboard/Family, raw `useEffect` on Reports/Copilot) — a deliberate, minimal-footprint choice, not an oversight.

## Manual Validation

Performed live in Chrome against the running dev build (`localhost:8080`, backend `localhost:8010`), using a real, previously-onboarded test account:

- **Dashboard:** "Recent life events" card renders with real data ("Salary Raise · 12 Jul · Salary Raise · 12 Jul"), links to `/app/life-events`. AI Copilot card shows the new one-line note beneath its recommendations, confirmed by screenshot.
- **Family:** Card correctly renders **nothing** (verified — no layout gap, no error) because no Family-category life event has been recorded yet for this account, exercising the `emptyState="hidden"` path exactly as designed.
- **Reports:** "Life Events This Year" section renders with both recorded Salary Raise events and dates, "View full history" link present and correctly pointing to `/app/life-events`.
- **Financials:** New banner renders above the Income section exactly as designed, with a working link to Life Events.
- **AI Copilot:** "Based on your recent activity" section renders the dynamic prompt "How did recording my Salary Raise affect my plan?" — clicked it live, confirmed it sends through the existing, unmodified `api.chat` call and receives a real, contextually relevant response from the live backend.
- **Notifications:** Popover opens correctly, shows a real notification (`goal_at_risk` source), no runtime errors from the widened `NotificationSource` type (a compile-time-only change, so this was a smoke test, not a behavior change).
- Console checked (`read_console_messages`, filtered `error|Error`): only the same pre-existing, unrelated Grammarly-extension hydration warning seen in Phase 1 — no new errors introduced by this phase's changes.

## Automated Validation

- `npx tsc --noEmit` — clean, zero errors.
- `npx eslint` on all nine changed/new files — clean after one auto-fix pass (three Prettier-only formatting nits, no logic changes).
- `npm run build` (full Vite + Nitro production build) — succeeded.
- Backend: `ruff check app/` and `mypy --strict app/` — both clean (87 source files, no issues), run for completeness; confirmed via `git status` that zero backend files are part of this phase's diff.
- Backend test suite: not re-run — identical reasoning to Phase 1 (zero backend code changed; the existing 673-pass result from earlier in this session remains the valid, current baseline).

## Regression Risk

**Low.** Every change is additive:
- The `NotificationSource` type change is a pure type-level widening (adding two literal members to a union) — cannot break any existing code that switches/compares against the previous five values, since TypeScript unions are structurally open to this kind of extension.
- Every new UI element (`RecentLifeEventsCard`, the Reports section, the Financials banner, the Copilot suggestion, the two recommendations notes) is additive to its host screen — no existing element was removed, restyled, or had its behavior changed.
- The one genuine new failure mode introduced is a network call that can fail: `RecentLifeEventsCard`'s and Reports'/Copilot's new fetches. Each is wrapped in its own error handling (`RecentLifeEventsCard` returns `null` while loading and treats a failed/empty result the same as "nothing to show"; Reports' and Copilot's new effects `.catch()` to an empty/absent state rather than surfacing an error) — a failure here degrades gracefully to "the new element doesn't appear," never to a broken page, mirroring the exact philosophy the pre-existing `FamilyCard` already established ("the money dashboard must never break... because [an unrelated aggregate] is unavailable").

## Performance Impact

Each of Dashboard, Family, Reports, and AI Copilot now issues one additional network request on load (a `GET /life-events` call). All four are small, already-indexed, already-paginated (`limit`-bounded) reads against an endpoint that already exists and is already exercised by the Life Events page itself — no new query pattern, no N+1, no unbounded fetch. Dashboard and Family's calls go through React Query with a 30-second `staleTime`, so rapid back-and-forth navigation within that window reuses the cached result rather than re-fetching.

## Backward Compatibility

Fully preserved. No route, prop, or exported type signature was removed or had a required shape changed — the only type change (`NotificationSource`) is purely additive. No existing component's props changed shape.

## Outstanding Risks

1. Family's card and Reports'/Copilot's new fetches are independent of each other and of Dashboard's — if a user records a life event and immediately checks Family (whose query key differs by its `eventTypes` filter), the two caches don't share data. This is correct behavior (different filters, different results) but worth noting: there is no single "life events" cache shared app-wide, only per-usage-shape caches, consistent with how `useQuery` already works everywhere else in this codebase.
2. Reports' new fetch inherits that file's own pre-existing, already-documented technical debt (FE-005 — bypasses React Query entirely). Not fixed here, as doing so would mean converting the whole file's fetch pattern, which is out of this phase's scope; flagged for whichever future phase addresses fetch-pattern consistency directly.
3. The AI Copilot's dynamic suggestion only considers the single most recent life event — if a user has recorded several in quick succession, only the latest is offered as a suggested prompt. This is a deliberate, minimal choice (one honest suggestion, not a fabricated summary of several), not an oversight.

## Ready for Next Phase

**Yes.** Phase 2's scope is closed and validated. Continuing automatically to Phase 3 (Plan Health Experience) per the mission's instruction not to pause between phases.
