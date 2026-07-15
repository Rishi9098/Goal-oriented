# Architecture Review — Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Builds on:** `DependencyValidation_Phase0.md` (all assumptions confirmed correct — no stop condition triggered)

---

## 1. Why AppShell remounts (root cause, precisely stated)

`AppShell` remounts on every navigation between any two `/app/*` screens because it is rendered **inside** each of 13 leaf route components, not **above** them. TanStack Router's `/app` layout route (`app.tsx`) already sits between the auth guard and every one of those 13 leaves — but its `AppLayout` component renders only `<Outlet />`, so the router faithfully unmounts and remounts whatever each leaf renders (including its own fresh `<AppShell>` instance) on every route transition, exactly as React Router-family libraries are supposed to behave when a component isn't hoisted to a persistent ancestor. **This is not a bug in TanStack Router or in `AppShell` itself — it is a component-placement decision that was never revisited once the app grew from a handful of screens to thirteen.**

## 2. Current lifecycle

```
Navigate to any /app/* route
  → app.tsx's beforeLoad guard runs (unaffected either way)
  → app.tsx's AppLayout renders <Outlet/>
  → the destination leaf route's component renders, which itself renders <AppShell title="...">
  → AppShell mounts fresh:
      - useState(initials), useState(planHealth) reset to their initial values
      - useEffect fires: auth.me() and api.getDashboard() called again, uncached
      - sidebar, header, mobile nav all re-render from scratch
  → leaf's own content renders inside AppShell's {children}
Navigate again to a different /app/* route
  → previous leaf (and its AppShell instance) unmounts completely
  → the cycle above repeats from zero
```

Net effect: every single click on a sidebar or nav link re-fetches the user's identity and plan-health score from the network, even though neither has any reason to have changed.

## 3. Desired lifecycle

```
Navigate to any /app/* route (first time this session)
  → app.tsx's beforeLoad guard runs (unchanged)
  → app.tsx's AppLayout renders <AppShell><Outlet/></AppShell>
  → AppShell mounts ONCE:
      - useQuery(["currentUser"], auth.me) and useQuery(["dashboard"], api.getDashboard)
        fire once, results cached by the app's single QueryClient
  → the destination leaf renders inside AppShell's <Outlet/>, supplying only its title
Navigate again to a different /app/* route
  → AppLayout does NOT unmount (it is the persistent parent); only <Outlet/>'s
    content swaps to the new leaf
  → AppShell itself never unmounts — sidebar, header, and their state (moreOpen,
    the cached identity/plan-health data) all persist untouched
  → the new leaf's title is read from the route's own static data by the
    still-mounted AppShell, header text updates, nothing else does
```

## 4. Required routing change: how the header gets its title without a per-render prop

Today, each of the 13 leaf routes passes `title` as a JSX prop to its own `<AppShell>` instance. Once `AppShell` is rendered once by the layout instead of by each leaf, there is no longer a leaf-to-shell prop channel for this — some other mechanism must supply the same title text on the same routes, preserving identical visible behavior.

**Recommended mechanism: TanStack Router route `staticData`.** Each route file already declares route-level configuration via `createFileRoute(path)({ head: () => (...), component: ... })`; `staticData` is the router's own built-in field for exactly this "a route wants to tell an ancestor something about itself, without prop-drilling" need — e.g. `createFileRoute("/app/goals")({ staticData: { shellTitle: "Goals" }, ... })`. The now-persistent `AppShell` reads the current deepest match's `staticData.shellTitle` via `useRouterState({ select: (s) => ... })` — the same hook `AppShell` already imports and uses today for `pathname`, so this introduces no new dependency, just a second selector on an already-used hook.

**Rejected alternative: a central pathname → title lookup table inside `app-shell.tsx`.** This was considered and rejected because it creates a second, separate source of truth for "what title does this route have," physically distant from the route file it describes — exactly the kind of documentation/data drift this project's own prior certification work (the stale ADR-001 status line, found and flagged in the Milestone 2 re-certification) has already shown is a real, recurring risk in this codebase. Keeping the title declaration inside each route file (just via `staticData` instead of a prop) preserves today's "the route owns its own title" property instead of trading it away.

**This is plumbing, not a feature.** The visible title text on every one of the 13 routes must remain byte-for-byte identical to today — this change only relocates *how* that string reaches the header, not what it says.

## 5. State ownership (after this change)

| State | Owner | Mechanism |
|---|---|---|
| `pathname`, active-nav-item highlighting | `AppShell`, via `useRouterState` | Unchanged |
| Page title | `AppShell`, via `useRouterState` reading route `staticData` | Changed mechanism, identical output |
| Current user identity (name/email/initials) | New shared source, `useQuery(["currentUser"], auth.me)` | Consumed by `AppShell`; fetched once, cached |
| Plan health score | New shared source, `useQuery(["dashboard"], api.getDashboard)` | Consumed by `AppShell` |
| `moreOpen` (mobile "More" menu) + its click-outside/Escape listeners | `AppShell`, local `useState`/`useRef` | **Unchanged** — this is transient UI state with no reason to survive beyond the menu's own open/closed lifecycle; it was never the source of the remounting problem and Phase 0 does not touch it |

## 6. Provider hierarchy

**One new, narrowly-scoped provider** is introduced at the `app.tsx` layout level, wrapping `AppShell` (or, equivalently, implemented as a small custom hook backed directly by `useQuery` calls inside `AppShell` itself, with no separate Context object at all if a Context turns out to add no value beyond what `useQuery`'s own cache already provides — this decision is deferred to the Design Review, since it's an implementation-shape detail, not an architectural one). Either way, the resulting hierarchy is:

```
__root.tsx: QueryClientProvider  (unchanged, already existed)
  app.tsx: AppLayout
    AppShell  ← now mounted here, once, instead of inside every leaf
      <Outlet/>  ← leaf route content swaps here on navigation
```

No provider is added for `moreOpen` or any other transient UI state — per §5, that remains local to `AppShell` exactly as it is today. This keeps the provider surface as small as the problem requires, consistent with `GlobalShellArchitecture.md`'s own reasoning against over-scoping shared state.

## 7. Caching opportunity found during this review (not previously documented)

**`app.index.tsx`'s Dashboard route already calls `useQuery({ queryKey: ["dashboard"], queryFn: () => api.getDashboard() })` for its own net-worth/cash-flow stats — the exact same endpoint AppShell's plan-health figure comes from.** If AppShell's new plan-health fetch uses the **identical query key** (`["dashboard"]`), React Query will deduplicate the two consumers automatically: whichever mounts first fires the network request, the other reads the same cached result, and revisiting the Dashboard page after the shell has already loaded costs zero additional requests within the cache's `staleTime` window. This is a direct, "for free" improvement beyond the phase's minimum bar (stop refetching per navigation) — the shell and the Dashboard page's own data need stop being two independent fetches of the same information for the first time. This should be implemented as designed, not treated as a nice-to-have to skip.

## 8. Explicitly not changed in this phase

- `app.profile.tsx` has its own, separate, pre-existing `auth.me()` call (independent of `AppShell`'s). This is a smaller, lower-frequency duplication (it fires once per deliberate visit to the Profile page, not once per navigation anywhere in the app) and is **not** the problem this phase exists to fix. Left untouched, flagged here as a known, minor, separate item for a future cleanup pass — not folded into Phase 0's diff, per the instruction's explicit scope list and this project's minimal-diff discipline.
- `app.family.tsx`'s own thin `<Outlet/>`-only layout is untouched — Family sub-routes already inherit the promoted shell transitively through `/app` → `/app/family` → leaf, with no change needed at the `/app/family` level itself.
- No visual, styling, or UX change of any kind — covered in full in `DesignReview_Phase0.md`.

## 9. Conclusion

The required change is small and precisely bounded: move one component's render location from 13 call sites to 1, replace two raw-promise data fetches with two `useQuery` calls (one of which can share an existing cache key), and replace a prop-based title with a `staticData`-based one. No new routing concepts beyond a router feature (`staticData`) already designed for this exact situation; no new provider beyond the minimum the state actually requires. **Proceeding to Step 3 (Performance Baseline).**
