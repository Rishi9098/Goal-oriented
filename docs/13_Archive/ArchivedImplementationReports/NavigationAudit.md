# Navigation Audit — Northstar

**Date:** 2026-07-08
**Scope:** Every route, guard, redirect, and navigational element in the application.

---

## 1. Route inventory

All 20 route files under `code/src/routes/` were located and traced:

| Route | Guarded? | Renders |
|---|---|---|
| `/` | No | Landing page |
| `/auth/sign-in`, `/auth/forgot-password`, `/auth/reset-password` | No | Auth flows |
| `/onboarding` | No | 12-step wizard |
| `/app` (layout) | **Yes** — `beforeLoad` + client `useEffect` re-check | Redirects to `/auth/sign-in` if no token |
| `/app/` (Dashboard), `/app/goals`, `/app/copilot`, `/app/reports`, `/app/profile`, `/app/settings` | Inherits `/app` guard | ✓ all render correctly |
| `/app/family` (layout) | Inherits guard | Thin `<Outlet/>` wrapper — correct, minimal |
| `/app/family/`, `/app/family/add`, `/app/family/goals`, `/app/family/insurance`, `/app/family/recommendations`, `/app/family/schemes`, `/app/family/members/$id` | Inherits guard | ✓ all render correctly, verified via direct navigation this session |

**No orphaned or unreachable routes found** — every route file has at least one navigational path leading to it from within the app.

## 2. Auth guard mechanics

`/app`'s `beforeLoad` checks `localStorage.getItem("ns_access_token")` and throws a redirect to `/auth/sign-in` if absent; the component also re-checks in a `useEffect` on mount (covers SSR-hydration edge cases). This correctly protects every `/app/*` screen with a single guard at the layout level rather than per-route — clean, DRY, and verified working (unauthenticated visits to any `/app/*` URL redirect correctly).

**Note (not a navigation defect, but adjacent):** the access token is read from `localStorage`, which is readable by any script running on the page (XSS-accessible) rather than an httpOnly cookie. This doesn't break any navigation behavior today, but is worth flagging to a security review since the guard's integrity depends on this token's confidentiality.

## 3. Global navigation elements

| Element | Status | Notes |
|---|---|---|
| Sidebar (desktop, `lg:` breakpoint+) | ✓ | 7 items, active-state highlighting correct, order matches design doc's diagram |
| Mobile bottom nav (< `lg:`) | ✓ | 4 primary + "More" overflow; overflow menu opens/closes correctly (click-outside, Escape, item-select all close it) |
| Breadcrumbs | **Not implemented anywhere in the app** | Not a defect — the app never adopted a breadcrumb pattern; all "back" navigation is via explicit "Back to X" links instead, which are present and functional on every sub-screen |
| "Back to Family" links (Insurance, Recommendations, Goals, Member Detail, Add Member) | ✓ (except 2 instances) | See Broken Interaction Report #9 — `app.family.add.tsx`'s two instances lack focus-visible styling; functionally they navigate correctly |
| **Global search (⌘K)** | ❌ Dead | See Dead Click Report — not a real search, no keyboard shortcut registered anywhere in the codebase |
| **"View live demo"** (landing page) | ⚠ Misleading | Not a broken *link* — it correctly navigates to `/app`, but the guard immediately redirects unauthenticated users to sign-in, so the navigation doesn't do what its label promises |
| **Nav "Security" anchor** (landing page) | ❌ Broken | Points to `#trust`, which does not exist on the page |
| Footer legal links (landing page) | ❌ Dead | All `href="#"` |

## 4. Deep-linking / direct URL access

Verified live this session (multiple times, across the Milestone 2.1 and re-certification work): direct navigation to `/app/family/insurance`, `/app/family/recommendations`, `/app/family/schemes`, `/app/profile`, `/app/family/members/$id` with a real ID all resolve correctly when authenticated. Query-param-based routes (`/app/family/add?type=parent`, `/auth/reset-password?token=...`) both correctly hydrate their initial state from the URL via `zod`-validated `validateSearch` schemas.

## 5. Error / not-found handling

- **404 (unmatched route):** `__root.tsx`'s `notFoundComponent` renders a clean 404 page with a working "Go home" link. ✓
- **Render error (component throws):** `__root.tsx`'s `errorComponent` renders a recovery screen with "Try again" (calls `router.invalidate()` + local `reset()`) and "Go home" — both functional. Uses a plain `<a href="/">` rather than `<Link>` for "Go home" here, which causes a full reload; acceptable in an error-recovery context where a fresh page load is arguably desirable anyway. ✓ (no fix needed)

## 6. Keyboard navigation (route-level)

- Tab order through the sidebar and mobile nav is correct (native DOM order, no `tabIndex` overrides that would break it).
- Focus-visible styling is present on all Family-module navigation links (Milestone 2.1 fix) and Family Home's dashboard/recommendation link-cards, but **absent on the Goals screen and on `app.family.add.tsx`'s two "Back to Family" links** — see Broken Interaction Report #9, #10.
- No keyboard trap was found on any screen (modals — the Goals "New goal" modal and `GoalSimPanel` — both close via a backdrop click or an explicit Cancel/X button reachable by keyboard; neither traps focus in a way that prevents `Escape`-adjacent recovery via those buttons, though neither modal listens for the `Escape` key itself — a minor, non-blocking gap worth a future look, since the mobile "More" menu *does* correctly implement Escape-to-close and could serve as the reference pattern).

## 7. Summary

Northstar's core navigation (sidebar, mobile nav, deep links, 404/error handling, Family module cross-links) is solid and well-tested. The defects are concentrated in two places: (1) the unauthenticated marketing site (dead anchor, dead footer links, misleading demo button), and (2) two small, scoped keyboard-accessibility gaps left over from an otherwise-thorough prior accessibility pass. No broken navigation was found anywhere inside the authenticated application's core flows.
