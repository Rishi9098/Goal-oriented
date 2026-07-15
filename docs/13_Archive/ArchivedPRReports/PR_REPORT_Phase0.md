# PR Report — Global Shell Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Scope:** Phase 0 of `GlobalShellImplementationPlan.md` only — the persistent-layout foundation required before Profile Menu, Global Search, Notifications, or Keyboard Shortcuts can be built. **No user-facing Global Shell feature was implemented in this phase.**

---

## Summary

`AppShell` was rendered independently by 13 leaf routes, causing a full unmount/remount — and a fresh, uncached fetch of the user's identity and plan-health score — on every single navigation. This phase promotes `AppShell` to a single render site at the `/app` layout route, replaces the two raw data-fetching calls with cached `useQuery` calls, and replaces the per-route `title` prop with route `staticData` (plus a narrow override for the one route whose title is dynamic). Measured, not estimated: `auth.me()` requests across a 6-navigation sequence dropped from 14 to 2; plan-health requests dropped from 12 to 0.

## Pipeline

1. **Dependency Validation** (`DependencyValidation_Phase0.md`) — re-verified every architectural assumption directly against source: `AppShell` imported/rendered in 13 files; TanStack Router's `routeTree.gen.ts` confirms `/app` is already the parent route of all 13; exactly one context provider (`QueryClientProvider`) exists app-wide; no auth provider, no theme provider. No incorrect assumption found.
2. **Architecture Review** (`ArchitectureReview_Phase0.md`) — root-caused the remount to component placement, not a framework limitation; designed the fix (move render site, `useQuery`-ify two fetches, `staticData`-ify the title); identified a caching opportunity beyond the minimum bar (aligning the shell's plan-health query key with the Dashboard route's own `["dashboard"]` key so the two share one cached request).
3. **Performance Baseline** (`PerformanceBaseline_Phase0.md`) — real network capture + a direct DOM node-identity check, both showing the remount empirically: 14 `auth/me` / 12 `dashboard` requests across 6 navigations; sidebar/header proven to be different DOM node objects after a single navigation, old node fully detached from the document.
4. **Design Review** (`DesignReview_Phase0.md`) — confirmed, item-by-item, zero visual/UX/accessibility change in scope.
5. **Implementation** — see Files Changed below.
6. **Post-implementation Architecture Review** — re-verified via grep: exactly one `<AppShell>` render site remains (`app.tsx`); exactly one `QueryClientProvider`; no leaf route still imports `components/app-shell`.
7. **Performance Verification** (`PerformanceComparison.md`) — identical method, same 6-navigation sequence: `auth/me` 14→2, `dashboard` 12→0, DOM node-identity flipped from all-`false` to all-`true`.
8. **Regression Testing** — `tsc --noEmit` clean; `eslint` clean (0 errors, 0 warnings) on every touched file (one fast-refresh warning was fixed properly, by splitting the title-override hook into its own file, rather than left as a known warning); full backend suite (330 tests) still passing, confirming this frontend-only change didn't cross any boundary; live-verified Dashboard, Goals, Family, Reports, Settings, AI Copilot, Government Schemes, Family Insurance, and both variants of the dynamic-title route (`?type=parent`/`?type=other`, including direct URL loads).
9. **First-Time User Review** — navigation feels identical; the only difference is fewer redundant loading flickers on repeat visits, a strict improvement.
10. **Product Consistency Review** — header, sidebar, layout, and mobile nav confirmed unchanged across every screen visited.
11. **Documentation** — this report, `PROJECT_STATE.md`, `CHANGELOG.md`, `GlobalShellImplementationPlan.md` (Phase 0 marked complete).

## Files Changed

| File | Change |
|---|---|
| `code/src/routes/app.tsx` | `AppLayout` now renders `<AppShell><Outlet/></AppShell>` instead of a bare `<Outlet/>`. |
| `code/src/components/app-shell.tsx` | No longer takes a `title` prop; derives it from `useMatches`-read route `staticData`, with a context-based override channel. Two raw `useEffect`+promise fetches replaced with `useQuery` (dashboard query shares the Dashboard route's own cache key). |
| `code/src/lib/shell-title.ts` (new) | `ShellTitleOverrideContext` + `useShellTitle()` — the narrow escape hatch for the one route with a search-param-dependent title. |
| `code/src/lib/router-static-data.d.ts` (new) | TypeScript module augmentation declaring `staticData.shellTitle` on TanStack Router's route options. |
| 13 leaf routes under `code/src/routes/app*.tsx` | Removed their own `<AppShell title="...">` wrapper; 12 added `staticData: { shellTitle: "..." }`, 1 (`app.family.add.tsx`) uses `useShellTitle(dynamicTitle)` plus a static SSR fallback. |

## Measured Results

```
Network requests across an identical 6-navigation sequence (Goals → Family →
Reports → Settings → AI Copilot → Dashboard):
  auth.me():        14 → 2   (−86%; residual 2 = 1 shell fetch + 1 from
                              app.copilot.tsx's own separate, pre-existing,
                              out-of-scope identity fetch)
  dashboard:         12 → 0  (−100%; fully served from cache for the
                              entire sequence)

DOM node-identity across a single navigation:
  sidebar same object?    false → true
  header same object?     false → true
  old node still attached? false → true
```

## Verifying No Visual Redesign / No UX Changes

Confirmed via `DesignReview_Phase0.md` before implementation and live-verified after: every screen's title, sidebar, header, plan-health card, avatar, and mobile nav render identically to before. The one route with dynamic title logic (`app.family.add.tsx`) was specifically tested for both variants (`?type=parent` → "Add a parent who depends on you"; `?type=other` → "Add someone else"), including via direct URL load (not just in-app navigation), and both render exactly as they did before this change.

## Verifying Single AppShell / No Duplicate Providers / No Duplicate Fetches

- `grep` confirms exactly one `<AppShell` render site (`app.tsx`) and zero remaining leaf-route imports of `components/app-shell`.
- `grep` confirms exactly one `QueryClientProvider` in the entire app (`__root.tsx`, pre-existing, unchanged).
- The `["dashboard"]` query key is now shared between `AppShell` and the Dashboard route's own `useQuery` call — verified by the measured zero additional `dashboard` requests when the Dashboard route was revisited at the end of the navigation sequence.

## Known, Out-of-Scope Observation (Not Fixed Here)

`app.profile.tsx` and `app.copilot.tsx` each have their own separate, independent `auth.me()` call site (raw, uncached), predating this phase. Phase 0 only fixes `AppShell`'s own fetch; these two call sites are smaller, lower-frequency duplications (each fires once per deliberate visit to that specific screen, not once per navigation anywhere in the app) and were explicitly left untouched to keep this phase's diff minimal and exactly matching its stated scope. Flagged for a future, separate cleanup — not silently ignored, not folded into this diff.

## Rollback

Revert the 15 touched/added files listed above. No migration, no schema change, no API contract change to reverse — this is a pure frontend, client-side architecture change.

---

## Success Criteria (from instruction, verified against measured evidence)

- [x] AppShell mounts once — confirmed via DOM node-identity check (same object across 6 navigations)
- [x] `auth.me()` is not repeatedly called — 14→2, residual attributed to a named, separate, pre-existing call site
- [x] Plan-health is not repeatedly fetched — 12→0
- [x] Navigation remains identical — live-verified across 9 distinct screens/route variants
- [x] Zero visual regressions — `DesignReview_Phase0.md` + live verification
- [x] Zero routing regressions — all routes resolve correctly via direct URL and in-app navigation; 404/error boundaries untouched
- [x] Zero duplicated providers — confirmed via grep

**Stopping here per instruction. Phase 1 (Profile Menu), Phase 2 (Global Search + Keyboard Shortcuts), and Phase 3 (Notifications) have not been started and await review and approval.**
