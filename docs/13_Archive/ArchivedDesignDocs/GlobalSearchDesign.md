# Global Search — Design

**Date:** 2026-07-08
**Status:** Design only. No code written.
**Depends on:** `GlobalShellArchitecture.md` (shared shell state, existing `cmdk`/`command.tsx` asset)

---

## 1. Global or page-specific?

**Global.** The existing (currently non-functional) header search bar already spans every authenticated screen, and its placeholder text — "Search goals, holdings, reports…" — states a cross-entity intent that a single page could never satisfy. A page-specific search (e.g., the Goals page's own working name-filter, which already exists and works today) is the *wrong* model to extend to the header: the header's promise is "search anything, from anywhere," which is precisely what a **command palette** (search + navigation actions in one place) is for, and is exactly the pattern the already-installed `cmdk` library and the already-built `components/ui/command.tsx` were clearly scaffolded to support.

**Recommendation: the ⌘K palette should do two related things, not one** — this is the standard, user-tested shape of every product that ships this pattern (Linear, Vercel, GitHub, Notion):
1. **Entity search** — find a specific goal, family member, policy, or scheme.
2. **Navigation / quick actions** — jump to a screen ("Go to Family", "Go to Settings") or trigger a common action ("New goal", "Sign out") without leaving the keyboard.

This does not replace the Goals page's own inline search box (which remains useful for filtering a long, already-open list) — it complements it for the "I don't know or don't want to navigate to find this" use case.

## 2. What should be searchable

Ranked by how directly the existing placeholder text and the app's actual data model support them:

| Entity | Source (already exists) | Match fields | Notes |
|---|---|---|---|
| **Goals** | `api.getGoals()` (already fetched/cached by the Dashboard and Goals page) | `name`, `category` | Named explicitly in the current placeholder ("Search goals…") |
| **Family members** | `api.getFamilyHome()` | `name`, `relationship_type` | High-value: users forget exact spelling of e.g. a child's name in a long member list |
| **Insurance policies** | `api.getFamilyInsurance()` | `policy_type`, `insurer` | Matches "holdings" in the placeholder loosely (financial records) |
| **Government schemes** | `api.getFamilySchemes()` | `scheme_name`, `scheme_code` | Useful once a household has several eligible/potential schemes |
| **Reports** | N/A — one static page | — | Not an entity list; represent as a single **navigation** item ("Go to Reports"), not a search-result type |
| **Settings sections** | N/A — one static page with sub-sections (Password, Delete account) | — | Represent as navigation/quick-action items ("Change password", "Delete account") — a well-established "settings search" pattern (Notion, Linear, Slack all do this) that costs nothing beyond a static list, since Settings has no dynamic content to index |
| **Static navigation** | The existing sidebar `nav` array in `app-shell.tsx` | Screen labels | "Dashboard", "Goals", "Family", "AI Copilot", "Reports", "Profile", "Settings" as always-available quick-jump items |

**Explicitly not in scope for V1:** free-text search inside recommendation reasoning, scheme eligibility-rule text, or any RAG/knowledge-base content referenced in this session's separate AI Assistant research — that content doesn't exist as a queryable corpus yet, and conflating "global product search" with "AI assistant retrieval" would be a scope-creep mistake this design should explicitly avoid.

## 3. Backend API — does it exist?

**No.** Confirmed by direct inspection: no search router, no full-text index (`tsvector`/`pg_trgm`/GIN) in any of the 9 Alembic migrations, nothing in `requirements.txt` resembling a search library.

**V1 recommendation: no new backend endpoint at all.** Every entity above is already fetched by an existing endpoint and already cached client-side via React Query (`["goals"]`, `["family-home"]`, etc. — the same query keys the Dashboard and Family screens already populate). At the data volumes this product actually has per user (a handful of goals, a handful of family members, 0–3 policies, up to ~9 schemes), **client-side aggregation and fuzzy-filtering across already-cached React Query data is sufficient, has zero new backend surface, and is consistent with `cmdk`'s own built-in fuzzy scorer** (the `command-score` algorithm cmdk ships with, already a transitive dependency).

**When a real backend endpoint becomes justified (V2 trigger, not a V1 requirement):** if search scope grows to include free-text content that isn't already fetched wholesale by an existing screen (e.g., searching *inside* long-form report text, or a future transaction/holdings list with hundreds of rows per user), a dedicated `GET /search?q=` aggregating endpoint — querying multiple tables with simple `ILIKE` predicates, or a proper `tsvector` + GIN index if match quality demands it — would be the natural next step. This is explicitly deferred, not designed in detail here, because building it now would be solving a scale problem the product doesn't have yet (Engineering Constitution Rule 7: no premature abstraction).

## 4. Ranking strategy

**V1:** rely on `cmdk`'s built-in fuzzy-match scoring (subsequence matching + proximity/prefix weighting), applied per-entity-group, with three deterministic tie-breakers layered on top:
1. **Exact prefix match** ranks above fuzzy subsequence match within the same group.
2. **Entity-group order** is fixed, not scored: Goals → Family members → Insurance → Schemes → Navigation/Settings actions — reflecting the frequency with which users look for each, most-used first (goals and family are the app's primary daily surfaces; navigation/settings actions are a fallback affordance, always available but always ranked last so they don't crowd out real data results).
3. **Recency** (see §5) nudges recently-viewed items above equally-scored peers within the same group, but never above a strictly better text match.

**Not recommended for V1:** a cross-entity relevance model (e.g., machine-learned ranking, click-through weighting) — there's no query-log data to train it on yet, and the entity counts are small enough that simple grouped fuzzy-match is already a good experience. Revisit only if user feedback specifically identifies ranking as a problem.

## 5. Recent searches

**Recommendation:** store the last 5 executed searches (the query string *and* which result the user selected, not just the raw text) client-side, scoped per signed-in user, shown as a "Recent" group when the palette opens with an empty query.

- **Storage:** `localStorage`, keyed by user ID (`ns_recent_searches_<userId>`), so switching accounts on a shared machine doesn't leak the previous user's search history into the new session. Cleared on sign-out alongside the access token, for the same reason.
- **Not server-side for V1** — this is low-stakes UX convenience state with no cross-device requirement stated or implied by any existing product principle, and server-side storage would require the backend work explicitly deferred in §3. If cross-device recent-searches becomes a real user request later, promote it to a small backend table at that point.
- **Content sensitivity note:** a recent search for e.g. "mother" or a specific family member's name is not especially sensitive on its own, but the clear-on-sign-out behavior above is the appropriate, low-cost safeguard consistent with the project's existing privacy-conscious defaults (per this session's separate AI Assistant Research work on data handling).

## 6. Keyboard shortcut

Covered in full in `KeyboardShortcutDesign.md`; the search-specific requirements are: **⌘K (Mac) / Ctrl+K (Windows/Linux)** opens the palette from anywhere in the authenticated app (global `keydown` listener, not scoped to the header element, since the whole point is "don't make me click first"); the existing header search bar's visual "⌘K" hint becomes truthful for the first time once this is wired up. The palette **must** intercept the browser's own default behavior for this combination where one exists (some browsers bind Ctrl+K to their own address-bar search) via `preventDefault()`.

## 7. Loading and empty states

| State | Behavior |
|---|---|
| **Palette just opened, no query typed** | Show "Recent" group (§5) if any exist, then the static Navigation/Quick-actions group. No network activity yet — nothing to load, since all entity data is already cached from normal app usage by the time a user is likely to search (if a query is typed before, e.g., Goals have ever loaded this session, fall through to the next row) |
| **Underlying entity data not yet cached** (e.g., user opens the palette before ever visiting Family) | Trigger the same `useQuery` fetches those screens use (shared query keys mean this "just works" via React Query — no bespoke loading logic needed), show a lightweight per-group skeleton row only for the group(s) still loading, other groups render as soon as their own cache is ready |
| **Query typed, matches found** | Grouped results as designed in §2/§4, each row showing entity type icon + name + one line of context (e.g., a goal's category and progress, a family member's relationship) |
| **Query typed, zero matches across all entities** | A single, honest empty state — "No results for '{query}'" — never a blank palette (matches UX Principle #11: empty states are normal states, not apologies) |
| **A given entity's own data fetch failed** (e.g., Family API errored) | That group is silently omitted from results rather than showing an error inside the palette — the palette is a fast, low-stakes tool; surfacing a full error UI inside it would be disproportionate. The underlying screen's own error state (already implemented, e.g. Family Home's "We couldn't load your family information") remains the place a user learns about and retries a real data problem |

## 8. Explicitly out of scope for V1

- Searching across other users' data (not applicable — every entity above is already household/user-scoped by its existing endpoint's own auth).
- Any AI-assisted/semantic search — this is exact/fuzzy text matching only; conflating this with the AI Copilot's retrieval capability (a separate research track) would blur two very different reliability and latency profiles.
- Command execution beyond navigation (e.g., "create a goal named X" typed directly into the palette) — a real feature, but a distinct one from search; revisit once basic navigation + entity search is shipped and evaluated.
