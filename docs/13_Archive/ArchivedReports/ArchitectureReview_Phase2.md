# Architecture Review — Phase 2 (Global Command Palette & Search)

**Date:** 2026-07-08

---

## 1. One palette, not multiple search systems

A single `GlobalPalette` component, rendered once inside the already-persistent `AppShell` (Phase 0), built entirely from the existing `Command`/`CommandDialog`/`CommandInput`/`CommandList`/`CommandGroup`/`CommandItem`/`CommandEmpty` scaffold (`components/ui/command.tsx`). This replaces the decorative search bar's markup in place — there is no second search box, no second keyboard shortcut, no parallel filtering implementation anywhere else in the app.

## 2. State ownership

- **Open/closed**: `const [paletteOpen, setPaletteOpen] = useState(false)` inside `AppShell` — the same pattern already used for `moreOpen` (mobile nav) and consistent with Phase 1's `DropdownMenu` (each piece of shell UI state stays local to `AppShell`, no new Context, per `GlobalShellArchitecture.md`'s guidance against over-scoping shared state for state that has exactly one consumer).
- **Query text**: local to the palette (`cmdk`'s own `Command` component manages this internally via `CommandInput`, standard usage).
- **Recent searches**: `localStorage`, keyed per-user (per `GlobalSearchDesign.md` §5), read/written from inside the palette component, cleared on sign-out alongside the access token (extending `handleSignOut`).

## 3. Search indexing — client-side, lazy, zero backend

Per `GlobalSearchDesign.md` §3 (already reviewed and unchanged by this implementation): no new backend endpoint. Four entities are fetched via `useQuery`, **gated so they never fetch before the palette has been opened once**:

```
const [everOpened, setEverOpened] = useState(false);
// on first open: setEverOpened(true) — queries below then enable and stay enabled
useQuery({ queryKey: ["goals"], queryFn: api.getGoals, enabled: everOpened })
useQuery({ queryKey: ["family-home"], queryFn: api.getFamilyHome, enabled: everOpened })
useQuery({ queryKey: ["family-schemes"], queryFn: api.getFamilySchemes, enabled: everOpened })
useQuery({ queryKey: ["family-insurance"], queryFn: api.getFamilyInsurance, enabled: everOpened })
```
Query keys intentionally match existing usages (`["goals"]` matches the Dashboard's own goal-preview query; the three `family-*` keys match their respective pages) so opening the palette after already having visited those pages costs zero additional requests — and vice versa. Filtering itself uses `cmdk`'s own built-in fuzzy scorer (`command-score`, already a transitive dependency) — no custom ranking algorithm written.

## 4. Keyboard listener — exactly one, registered once

A single `document.addEventListener("keydown", handleShortcut)` inside `AppShell`'s `useEffect` (empty dependency array beyond the setter), checking `(e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"`, calling `e.preventDefault()` and toggling `paletteOpen`. Because `AppShell` mounts exactly once per session (Phase 0's own measured proof), this listener attaches exactly once — never duplicated by navigation. `Escape`-to-close and outside-click-to-close are **not** hand-built — both come free from `CommandDialog`'s underlying Radix `Dialog`, exactly as Phase 1's `DropdownMenu` got its Escape/outside-click handling for free rather than re-implementing the mobile nav's hand-rolled listener pattern a third time.

## 5. Route metadata — reused, extended by exactly 3 entries

The existing `nav` array (7 top-level sidebar destinations) is reused verbatim for most of the "Pages" group. Three real, working routes are not in `nav` (they're reached via in-page links, not the sidebar): `/app/family/schemes`, `/app/family/insurance`, `/app/family/recommendations`. A small, palette-local `PAGES` array is defined as `nav`'s 7 entries plus these 3 — 10 total, one entry per named entity in this phase's Search Scope Review. No route file changes needed for this — TanStack Router's existing `<Link to>` type-checking already validates these paths at compile time.

## 6. Command categories

| Group | Content | Shown when |
|---|---|---|
| Recent | Last 5 searches (query + selected result), from `localStorage` | Query empty |
| Pages | 10 static navigation entries | Always (filtered by query text against label) |
| Quick Actions | 2 real actions (§7) | Always (filtered) |
| Goals | Live-fetched, filtered by name/category | Query non-empty and matches exist |
| Family Members | Live-fetched, filtered by name/relationship | Query non-empty and matches exist |
| Government Schemes | Live-fetched, filtered by scheme name | Query non-empty and matches exist |
| Family Insurance | Live-fetched, filtered by policy type/insurer | Query non-empty and matches exist |

**Recommendations, Reports, Settings, Dashboard, AI Copilot, Profile are represented only in the Pages group, not as separately-searched entity lists** — each is either a single static page with nothing to search *within* (Reports, Settings, Dashboard, AI Copilot, Profile), or (Recommendations specifically) has no stable per-item name/ID to search by, only full-sentence `why` text with no natural short label — treating full sentences as "named entities" in a results list would look inconsistent with every other group's clean-name display. This is a considered scope boundary, not an oversight — consistent with the instruction's "do not fabricate future features."

## 7. Quick Actions — a real architectural constraint surfaced, one small, flagged exception made

Investigating "Create Goal" and "Add Family Member" as quick actions surfaced a genuine limitation: **neither the Goals page's "New goal" modal nor any goal/scheme/policy's detail view is addressable by URL** — their open/closed state is local `useState` inside `app.goals.tsx`/`app.family.schemes.tsx`/etc., not reflected in the route. A quick action or search result can only `navigate()` to a route; it cannot reach into a different, not-yet-mounted page's local component state to open a modal.

- **"Add Family Member" is a real quick action with zero new code**: `/app/family/add?type=other` is already a complete, dedicated creation page (not a modal) — the quick action simply navigates there.
- **"Create Goal" requires one small, deliberate addition**, flagged explicitly here rather than silently worked around: `app.goals.tsx` gains support for a `?new=true` search param that opens the already-existing "New goal" modal on load (the same modal the page's own "+ New goal" button already opens — no new UI, no new form, no new logic, just one additional way to trigger an existing, working piece of UI). This is the one file this phase touches outside `AppShell`/`command.tsx`-adjacent code, and it is scoped to exactly this one param. Without it, "Create Goal" would either not exist (contradicting this phase's own named example) or would be a misleading action (navigating to a list, not creating anything) — the smaller, safer risk is the one-param addition, reusing 100% existing modal/form code.
- **Goal, scheme, and policy search results have the same limitation**: selecting a specific goal from search results navigates to `/app/goals` (the list), not directly to that goal's detail panel — because no URL-addressable detail view exists for a goal today. This is documented honestly in the UX Review rather than presented as a seamless deep link it isn't. Family Member results are the one exception that **can** deep-link precisely, since `/app/family/members/$id` is already a real, ID-addressable route.

## 8. Performance

- **Bundle impact**: `cmdk` and the Radix `Dialog` it depends on are already-installed dependencies (no new package.json entries) — the only new bundle weight is the palette component's own code, a few KB.
- **No network cost until first open** (§3) — the palette adds zero requests to a normal session that never invokes it.
- **Search latency**: `cmdk`'s scorer runs synchronously in-memory over already-fetched, small arrays (a handful of goals/members/schemes/policies per household) — no debounce needed at this data volume; input latency is bound by React's own render cycle, not by any async work.
- **Re-renders**: `paletteOpen` toggling only re-renders `AppShell` and the palette subtree, not the currently-mounted route's own content (verified conceptually — the palette is a sibling of `{children}`, not a wrapper around it).

## 9. Lazy loading

Covered by §3's `enabled` gating — this is the mechanism by which "lazy loading" is achieved for this phase (data lazy-loads on first palette open); no route-level code-splitting/dynamic `import()` is introduced for the palette component itself, since `cmdk`/`Dialog` are small enough that splitting them into a separate chunk would add complexity (a `React.lazy` boundary, a loading fallback) for negligible bundle savings — consistent with Engineering Constitution Rule 7 (no premature optimization for a size problem that doesn't exist here).

## 10. Conclusion

One palette, one keyboard listener, one query-key strategy reusing existing cache entries, ten navigable pages, two real quick actions (one requiring a small, explicitly-flagged addition to `app.goals.tsx`), four dynamically-searched entity groups, and an honest, documented limitation on deep-linking to specific goals/schemes/policies. **Proceeding to Search Scope Review (already substantially covered above) and UX Review.**
