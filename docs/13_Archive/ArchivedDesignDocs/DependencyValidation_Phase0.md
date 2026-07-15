# Dependency Validation — Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Scope:** Verify every architectural assumption `GlobalShellArchitecture.md` and `GlobalShellImplementationPlan.md` rely on, against the current source code, before any implementation begins.
**Method:** Direct re-inspection of `app.tsx`, `app-shell.tsx`, `__root.tsx`, `router.tsx`, every `/app/*` leaf route, and the auto-generated `routeTree.gen.ts` — not assumed from prior session memory.

---

## 1. Current AppShell lifecycle

**Confirmed by exhaustive grep:** `AppShell` is imported and rendered independently inside **13 separate route component files** — `app.index.tsx`, `app.goals.tsx`, `app.copilot.tsx`, `app.reports.tsx`, `app.profile.tsx`, `app.settings.tsx`, `app.family.index.tsx`, `app.family.add.tsx`, `app.family.goals.tsx`, `app.family.insurance.tsx`, `app.family.recommendations.tsx`, `app.family.schemes.tsx`, `app.family.members.$id.tsx`. Each one wraps its own JSX in `<AppShell title="...">{content}</AppShell>` inside its own component function. `app.profile.tsx` renders `AppShell` twice (loading-state early return and the loaded state) — both are the same component, not a duplication defect, just two conditional render paths within one route.

**No route currently renders `AppShell` as inherited layout chrome.** Every one of the 13 files is a leaf; none of them delegate to a shared parent for this rendering.

## 2. TanStack Router layout hierarchy (mechanically verified via `routeTree.gen.ts`)

The auto-generated route tree confirms: `/app` (`AppRoute`, backed by `app.tsx`) is the **parent route** of every one of the 13 leaves above (`parentRoute: typeof AppRoute` appears on `/app/`, `/app/settings`, `/app/reports`, `/app/profile`, `/app/goals`, `/app/family`, `/app/copilot`, and the family sub-routes). `app.tsx`'s `AppLayout` component renders **only** `<Outlet />` (after an auth-guard check) — it does not render `AppShell`.

**This confirms the architectural assumption stated in `GlobalShellArchitecture.md` §3 exactly, with no correction needed:** TanStack Router's own nesting already puts exactly one parent route between the auth guard and every screen that needs the shell — `app.tsx` — which is precisely where a persistent layout render should live. This is not a workaround or a fight against the router's conventions; it is the standard, intended nested-layout-route pattern TanStack Router is built for, simply not yet used for this purpose.

## 3. Route nesting — no surprises found

- `/app/family` is itself a second-level layout route (`app.family.tsx`, a thin `<Outlet/>`-only wrapper) nested under `/app`, hosting `/app/family/`, `/app/family/add`, `/app/family/goals`, `/app/family/insurance`, `/app/family/recommendations`, `/app/family/schemes`, `/app/family/members/$id`. This nesting is irrelevant to Phase 0 — promoting `AppShell` to `/app`'s layout covers all Family sub-routes automatically, since they already inherit from `/app` transitively through `/app/family`. No change to `app.family.tsx` is implied or needed.
- `/auth/*` and `/onboarding` and `/` (landing) are **siblings** of `/app`, not descendants — confirmed they do not render `AppShell` today and must not gain it in Phase 0 (the shell is authenticated-app-only chrome).

## 4. Context providers — confirmed, only one exists

Exhaustive search for `Provider`/`createContext` across every route and component file (excluding the unused `components/ui/*` scaffold, whose internal contexts back components with zero import sites anywhere in the app) found exactly **one**: `QueryClientProvider`, instantiated in `__root.tsx`'s `RootComponent`, wrapping the entire `<Outlet/>` tree at the true root of the application (TanStack Start has no separate `main.tsx`/client entry — `__root.tsx` is the top). **No `AuthProvider`, no theme provider, no shell-state provider of any kind exists today.**

## 5. Auth provider

**There is no auth context/provider.** Authentication state is read directly from `localStorage.getItem("ns_access_token")` in exactly two places: `app.tsx`'s `beforeLoad` (route guard, runs before render) and its `AppLayout`'s own `useEffect` (a redundant client-side re-check, explicitly commented as covering SSR-hydration edge cases). Current user *identity* (name/email, for the header avatar) is fetched separately and redundantly via `auth.me()` inside `app-shell.tsx`'s own `useEffect` — confirmed as a raw promise call, not a `useQuery`, and confirmed as one of only two `auth.me()` call sites in the whole frontend (the other being `app.profile.tsx`'s own independent call). These two calls do not share a cache today.

## 6. Query client

One `QueryClient` instance is created per router (`router.tsx`'s `getRouter()`), passed through router `context`, and consumed via `QueryClientProvider` in `__root.tsx`. This is correctly a single, app-wide instance — **not** re-created per navigation — so any `useQuery` call anywhere in the app already benefits from a shared cache. The problem Phase 0 fixes is narrower than "no shared cache exists": it's that `app-shell.tsx`'s two data needs (identity, plan-health) were never plumbed through `useQuery` in the first place, so they get none of this already-available caching, and are re-fetched from scratch on every remount because the component holding them remounts on every navigation.

## 7. Sidebar / Header — confirmed as internal to `AppShell`, not separable today

Both the desktop `<aside>` sidebar and the `<header>` (title, search-bar placeholder, notification bell, avatar) are rendered inline inside `AppShell`'s single JSX return — there is no separate `<Sidebar>` or `<Header>` component to independently promote. Phase 0's "promote AppShell" is therefore a single, atomic move (one component, one new mount point), not a multi-component migration.

## 8. Existing state ownership (what Phase 0 must preserve exactly)

| State | Currently owned by | Must remain owned by (post-Phase 0) |
|---|---|---|
| `pathname` (for active-nav-item highlighting) | `useRouterState` inside `AppShell` | Same — this is router-derived, not remount-sensitive, no change needed |
| `initials` | Local `useState` in `AppShell`, populated by raw `auth.me()` call | Derived from a shared, cached identity source (see `ArchitectureReview_Phase0.md`) |
| `planHealth` | Local `useState` in `AppShell`, populated by raw `api.getDashboard()` call | Derived from a shared, cached source |
| `moreOpen` (mobile "More" nav menu) | Local `useState` + `useRef` in `AppShell`, with its own document-level click-outside/Escape listeners | **Must remain purely local to `AppShell`** — this is UI-only, per-render state with no reason to survive a `AppShell` unmount in the first place (it isn't navigation-triggered churn causing a problem here; explicitly out of scope for this phase's fix) |
| `title` (header `<h1>`) | A plain prop passed by each of the 13 leaf routes | Needs a new mechanism once `AppShell` is no longer re-instantiated per route with a fresh prop value each time — addressed in `ArchitectureReview_Phase0.md` |

## 9. Conclusion

**No architectural assumption in `GlobalShellArchitecture.md` or `GlobalShellImplementationPlan.md` was found to be incorrect.** TanStack Router's existing `/app` layout route is exactly the right, already-present seam for this change; there is exactly one component (`AppShell`) to move, one new provider to introduce (scoped narrowly to identity + plan-health + open/closed UI flags, not a general-purpose global store), and no competing or conflicting provider, auth system, or state owner to reconcile. **Proceeding to Step 2 (Architecture Review) — no stop condition triggered.**
