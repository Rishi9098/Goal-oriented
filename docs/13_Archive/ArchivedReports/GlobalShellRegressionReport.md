# Global Shell Regression Report — Certification

**Date:** 2026-07-08
**Method:** live testing against the real running app and backend this session — a fresh account through the full lifecycle (register → onboarding → use → logout), plus direct verification of the auth boundary and cache behavior.

---

## Routing

No regressions found. TanStack Router's route tree structure is unchanged by any Global Shell phase — Phase 0 promoted `AppShell` to the `/app` layout route (an intentional, reviewed change, not an accidental one), Phase 2 added a `?new=true` search param to `app.goals.tsx`, and no phase altered any route's path, nesting, or guard logic. Verified this session: direct navigation to `/app` while unauthenticated correctly redirects to `/auth/sign-in`; navigation between Dashboard/Goals/Family/Profile all landed on the correct routes with correct content.

## Authentication

- **Logout is complete, not cosmetic:** verified `localStorage.getItem("ns_access_token")` is `null` immediately after clicking "Sign Out" — the session token is actually cleared, not just the UI navigated away from.
- **Route guard holds post-logout:** a direct navigation to `/app` after logout redirected to sign-in with no protected content visible first.
- **Token validity is enforced by the backend, not just the frontend:** every protected endpoint tested without a token returned 403 (not a silent empty response).

## Stale cache / stale user state

None found within the shell's own components. `["currentUser"]`, `["dashboard"]`, and the various `["family-*"]`/`["goals"]` keys used by `AppShell`/`GlobalPalette`/`NotificationCenter` are shared and consistent. The one caveat (already covered in the Performance and Technical Debt reports): `app.goals.tsx` and `app.profile.tsx` don't participate in this cache at all, so they always show fresh data on their own terms — this means they can never show *stale* data (they never cache), only *redundant* fetches. Not a correctness regression.

## No duplicate API requests (within the shell)

Verified via network capture during a 4-page navigation sequence: the shell's own queries (`["dashboard"]`) fired exactly once, reused correctly on return to Dashboard. The repeats observed (`/goals` x3, `/family`/`/auth/me` x2 each) trace entirely to the two non-`useQuery` pages, not to `AppShell`, `GlobalPalette`, or `NotificationCenter`.

## No memory leaks

Every `document`-level listener registered by the shell has a corresponding cleanup function in its `useEffect` return, confirmed by reading `app-shell.tsx` directly. A single session that opened and closed all four overlay types repeatedly (palette, notification popover, profile dropdown, mobile "More" sheet) showed no degradation and zero console warnings when checked fresh with console tracking active.

## Cross-phase interaction regressions (specific to this certification, not covered by any single phase's own report)

- **Phase 2 (palette) × Phase 3 (notifications):** notification popover correctly auto-closes when the palette opens — no regression, no conflict.
- **Phase 1 (profile menu) × Phase 2 (palette):** **real finding** — the profile dropdown does not auto-close when the palette opens, so both can be simultaneously visible. This is a genuine cross-phase interaction gap neither Phase 1's nor Phase 2's own isolated testing could have caught, since each was verified independently before the other existed. Documented as the one certification condition in `GlobalShellCertification.md`.
- **Phase 0 (persistent shell) × Phases 1-3:** all three later phases correctly built their state as local state *inside* the already-persistent `AppShell`/`NotificationCenter`, none re-introduced a remount-on-navigation regression — confirmed by the `["dashboard"]` single-fetch evidence above, which would not hold if the shell were remounting.

## Summary

| Area | Result |
|---|---|
| Routing | No regressions |
| Auth (logout, route guard, token validation) | No regressions — verified live |
| Stale cache | None found (shell components); non-shell pages never cache at all, not stale |
| Duplicate requests | None within shell; pre-existing outside it |
| Memory leaks | None found |
| Cross-phase overlay interaction | One real, verified gap (profile menu vs. palette) — see certification condition |
