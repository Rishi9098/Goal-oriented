# Dependency Validation — Phase 2 (Global Command Palette & Search)

**Date:** 2026-07-08
**Scope:** Verify every assumption this phase depends on, against current source, before implementation.

---

## 1. `cmdk` package — confirmed installed, unused

`"cmdk": "^1.1.1"` in `code/package.json`. Zero import sites anywhere in the app today (confirmed by the original Interactive Product Audit and re-confirmed now).

## 2. Existing `command.tsx` — confirmed fully built, one real gap found

`code/src/components/ui/command.tsx` exports `Command`, `CommandDialog`, `CommandInput`, `CommandList`, `CommandEmpty`, `CommandGroup`, `CommandSeparator`, `CommandItem`, `CommandShortcut` — a complete, styled wrapper around `cmdk`'s primitives plus the existing `Dialog`/`DialogContent` (`code/src/components/ui/dialog.tsx`).

**Gap found, not previously documented:** `CommandDialog`'s implementation wraps `<Dialog><DialogContent>{children}</DialogContent></Dialog>` but never renders a `DialogTitle`. Radix's `Dialog` requires a `DialogTitle` for screen-reader accessibility — using `CommandDialog` as-is will trigger a console accessibility warning and leave the dialog's accessible name empty. **This phase's implementation must add a visually-hidden `DialogTitle`** (using the `sr-only` Tailwind utility already established elsewhere in this codebase, e.g. `app.family.index.tsx`'s member-card `<span className="sr-only">` — not a new, undeclared dependency like `@radix-ui/react-visually-hidden`, which exists only transitively in `node_modules` and is not a direct project dependency).

## 3. AppShell integration point — confirmed

The decorative search bar lives in `app-shell.tsx`'s header, alongside the notification bell and the (now-functional, Phase 1) avatar menu:
```tsx
<div className="hidden md:flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted-foreground w-72">
  <Search className="h-4 w-4" />
  <span>Search goals, holdings, reports…</span>
  <kbd className="ml-auto font-mono text-[10px] text-muted-foreground/70">⌘K</kbd>
</div>
```
Note it is `hidden md:flex` — invisible below the `md` breakpoint today. This phase's palette must be reachable on all viewports (the `⌘K`/`Ctrl+K` shortcut has no viewport restriction, and mobile users need a way to trigger it too, e.g. tapping this same element) — addressed in Architecture Review.

Because `AppShell` is now a persistent, single-mount component (Phase 0), any `document`-level keydown listener registered inside it via `useEffect` attaches **exactly once per session**, not once per navigation — confirmed by Phase 0's own measured proof (DOM node-identity check). This is the correct, safe place to register the global `⌘K` listener; no risk of duplicate listeners from remounting.

## 4. Current routing / route metadata — confirmed

`staticData.shellTitle` (Phase 0, `router-static-data.d.ts`) exists per route for the header title. This phase does not need to extend that mechanism — the palette's "Pages" group can be built from the existing `nav` array already defined in `app-shell.tsx` (7 entries: Dashboard, Goals, Family, AI Copilot, Reports, Profile, Settings), plus two additional real, navigable routes not in that top-level array: `/app/family/schemes` (Government Schemes) and `/app/family/insurance` (Family Insurance) and `/app/family/recommendations` (Recommendations) — all three confirmed live, working routes (Interactive Product Audit, Milestone 2.1).

## 5. Existing navigation — confirmed, reused verbatim

The `nav` array's `{ to, label, icon }` shape is exactly the data a "Pages" command group needs — reused directly, not duplicated into a second navigation list.

## 6. Searchable entities — confirmed against real data, one pre-existing inconsistency noted

| Entity (per this phase's required scope) | Data source | Query key already in use elsewhere | Verified fields |
|---|---|---|---|
| Goals | `api.getGoals()` | `["goals"]` (used by `app.index.tsx`'s Dashboard preview) | `id, name, category, targetAmount, currentAmount, probability, onTrack` |
| Family Members | `api.getFamilyHome()` | `["family-home"]` | `id, name, relationship_type, is_complete` |
| Government Schemes | `api.getFamilySchemes()` | `["family-schemes"]` | `scheme_code, scheme_name, member_name, reason`, grouped `eligible/potentially_eligible/not_eligible` |
| Family Insurance | `api.getFamilyInsurance()` | `["family-insurance"]` | policy `policy_type`, `insurer`, covered members |
| Recommendations | `api.getFamilyRecommendations()` | `["family-recommendations"]` | `source, recommendation_type, why`, no stable per-item name field (see Search Scope Review) |
| Reports, Settings, Dashboard, AI Copilot, Profile | No list — each is a single static page | N/A | Represented as **navigation** items only, not searchable entity lists (there is nothing to search *within* a single page with no sub-items) |

**Pre-existing inconsistency found, not caused by and not fixed in this phase:** the Goals *page itself* (`app.goals.tsx`) does not use `useQuery` at all — it fetches goals via a raw `useEffect`/`useState` with no cache key. Only the Dashboard's own goal-preview list uses `useQuery(["goals"], ...)`. This means the palette's own `useQuery(["goals"], api.getGoals)` call will share cache with the Dashboard but **not** with the Goals page — functionally harmless (the palette still gets correct, live data), but flagged here honestly rather than silently assumed to be a clean shared cache across the whole app. Out of scope to fix (that would be touching the Goals page's own internals, not this phase's job).

## 7. Backend — confirmed zero changes needed

Every entity above is already fetched by an existing, working endpoint. No new backend route, no new database query, no new schema — consistent with this phase's explicit "zero backend changes" success criterion.

## Conclusion

One real implementation detail surfaced (missing `DialogTitle` in `CommandDialog` — must be added for accessibility), one pre-existing, out-of-scope cache inconsistency noted (Goals page vs. Dashboard's goal cache), no assumption found that blocks proceeding. **No stop condition triggered — proceeding to Architecture Review.**
