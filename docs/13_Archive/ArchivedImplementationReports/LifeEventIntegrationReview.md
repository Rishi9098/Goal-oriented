# Life Event Integration Review — Phase 2

**Date:** 2026-07-12
**Scope:** How Life Events shows up (or doesn't) in Dashboard, Reports, Recommendations, Financials, Family, AI Copilot, and Notifications. The test for every change: does the user come away knowing *what changed*, *what happened*, and *what to do next*?

---

## 1. Documents and code read before deciding anything

- `LifeEventEngineArchitecture.md`, `LifeEventAPI_ImplementationReport.md`, `LifeEventEngine_BackendHardeningReport.md` — confirmed the read surface available: `GET /life-events` already supports `event_type`, `start_date`, `end_date`, `limit`, `offset` — everything needed for every integration below already exists; nothing new needs to be added to the API.
- `ArchitectureDecisionRecordBible.md` — ADR-001 (goal probability never recalculated on read) and ADR-005 (recommendations computed live, never persisted) were the two constraints most likely to be at risk in this phase. Every change below is read-only against already-existing endpoints; nothing recalculates or persists anything new.
- `NotificationArchitecture.md`, `backend/app/services/notification_service.py`, `backend/app/schemas/notification.py` — read directly, not assumed. This surfaced the single most important finding of this review (§2).
- `ProductDesignAuthorityReview.md` §8/§9 — the prior review's complaint that "Recommendations appear to materialize from nowhere" and "no screen ever says 'because of your recent event'" is the design mandate this phase answers, with one correction (§2): the complaint was accurate for Insurance/Schemes recommendations, but **already partially wrong** for Divorce, whose backend has real, working, life-event-aware notification logic the prior review didn't know about because it only inspected the Divorce *form*, not the notification engine.
- `FrontendArchitectureUserExperienceBible.md` — confirmed current fetch-pattern conventions per file (Dashboard/Family use `useQuery`, Reports and AI Copilot use raw `useEffect`), so each new fetch added below matches its own host file's existing convention rather than introducing a third pattern.

## 2. The most important finding: the backend already does more than the frontend shows

Direct inspection of `notification_service.py` found that **Life Event integration into Notifications is already built and working on the backend** — better than `ProductDesignAuthorityReview.md` assumed:

- `_collect_life_event_facts()` already turns every recorded life event (minus four types that already get an equivalent notification through a different collector, to avoid a double notification for one real action) into a notification, titled per event type, linking to `/app/life-events`.
- `_collect_divorce_review_facts()` already generates exactly the two follow-up prompts a CFP would want after a divorce — "review insurance coverage" and "review beneficiary/nominee designations" — computed live from real coverage/nominee rows, not fabricated.
- Both use `source` values (`"life_event"`, `"divorce_review"`) that are correctly declared in the backend's `NotificationSource` Pydantic `Literal`.

**The actual defect:** the frontend's own `NotificationSource` type (`code/src/lib/api.ts`) only lists five of the seven real values — `"life_event"` and `"divorce_review"` are missing. This is exactly the "documentation/implementation disagree" scenario this mission's own instructions anticipated, except here it's a frontend type lagging a backend schema, not a doc lagging code. Per those instructions: the backend schema (`app/schemas/notification.py`) is verified as the real, current source of truth, and the frontend type was simply never updated when these two sources were added. This is a real type-safety gap, not a design choice — fixed in §4 with zero backend change.

The empty-state copy in `notification-center.tsx` ("New goal, insurance, and scheme updates will show up here") also never mentions life events, understating what the feature already does.

## 3. What's genuinely missing (verified, not assumed)

| Surface | Current state (verified in code) | Gap |
|---|---|---|
| Dashboard | Stats, a Family summary card, Goals card, AI Copilot suggestions card. Zero mention of Life Events anywhere. | No visibility into "what did I record recently" on the first screen a user sees. |
| Reports | Net worth/goal/cash-flow snapshot only. | No "this year in your financial life" section, despite the exact data (`GET /life-events` with a date range) already existing. |
| Recommendations (Dashboard's Copilot card + `/app/family/recommendations`) | Computed live from current state (ADR-005) — genuinely already reflect any life event's effects automatically, on the very next read. | Nothing on either screen *tells* the user this is true, so a user has no reason to trust that recording an event actually did anything to their recommendations. |
| Financials | A pure CRUD ledger view; no reference to Life Events anywhere, despite several Life Events writing directly into the same rows this page displays. | No signal that a "real life change" should usually go through Life Events instead of a raw edit here. |
| Family | Rich module (household summary, dashboard, goals/insurance/schemes/recommendations links). Zero mention of Life Events, despite five of the eighteen event types (Marriage, Birth of Child, Adoption, Divorce, Dependent Parent) being pure Family-module changes. | A user managing their family has no idea that "Life Events" is where Marriage/Divorce/etc. actually get recorded. |
| AI Copilot | Generic greeting + four static suggested prompts, zero awareness of anything the user has done. | The single easiest, lowest-risk win in this phase — a smarter suggested prompt costs nothing and requires no backend change. |
| Notifications | Backend already correct (§2); frontend type incomplete, empty-state copy doesn't mention the feature. | Type-safety fix + copy fix. |

## 4. Decisions (all additive, all read-only, zero backend changes)

1. **New shared component, `RecentLifeEventsCard`** (`components/life-events/`) — fetches `GET /life-events` (already supports everything needed), renders a compact card matching the app's existing `surface-card`/`FamilyCard` visual language. Reused on Dashboard (all recent events) and Family (Family-category events only, via the *existing* `LIFE_EVENT_TYPES` config's `categoryLabel`, not a new hardcoded list — one source of truth for "which events are Family events").
2. **Dashboard** gets the card (with a "record your first one" empty state, since this is the first screen a new user sees) plus a one-line, always-true note on the existing AI Copilot suggestions card: recommendations already reflect anything recorded. No new fetch for this note — it's a static, always-accurate sentence, not a conditional claim requiring its own data.
3. **Reports** gets a new "Life Events This Year" section, filtered by the report's own year via the existing `start_date`/`end_date` params — reusing the exact `GET /life-events` endpoint, zero new backend surface.
4. **Financials** gets a single, dismissable-by-nature (not sticky/modal) info banner pointing to Life Events for real-world changes — not hidden, not a redesign of the page.
5. **Family** gets the same `RecentLifeEventsCard`, scoped to Family-category events, rendered only when at least one exists (mirrors the existing `FamilyCard`'s own "render nothing if there's nothing to say" rule on Dashboard — consistency with an existing, deliberate pattern, not a new one).
6. **`/app/family/recommendations`** gets the same one-line, always-true note as Dashboard's Copilot card.
7. **AI Copilot** dynamically prepends one suggested prompt referencing the user's single most recent life event (e.g. "How did recording my Salary Raise affect my plan?") when one exists in the last 30 days, ahead of the four static suggestions. This is an honest smarter *suggestion*, not a claim that the model has been given special context it wasn't — clicking it just sends that literal question through the existing, unmodified `api.chat` call.
8. **Notifications**: widen the frontend `NotificationSource` type to match the backend's real seven values; update the empty-state copy to mention life events.

## 5. What this phase explicitly does not do

- Does not add per-notification-source icons — every existing source (insurance, schemes, goal_at_risk, etc.) already renders identically today with no icon at all; adding one only for life events would create a *new* inconsistency in a phase that isn't about consistency. Tracked as an input to Phase 6.
- Does not fabricate causal attribution ("this recommendation appeared *because of* your Home Sale") — the backend does not compute or store that provenance, and inventing it in the frontend would be presenting a claim the system cannot actually verify. The honest, available claim — "recommendations already reflect everything you've recorded" — is used instead everywhere this matters.
- Does not add URL-based filtering/deep-linking from Family's card into a pre-filtered Life Events view — the Life Events page's type filter is local component state today, not URL-driven; adding query-param support is a reasonable future enhancement but is its own small feature, not required to satisfy "the user should understand what happened."
- Does not touch `get_dashboard()`, any recommendation service, or any calculation function — confirmed no backend file is part of this phase's changes.
