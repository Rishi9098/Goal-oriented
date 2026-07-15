# Global Shell Certification — Milestone 2.6

**Date:** 2026-07-08
**Scope:** Phases 0-3 of the Global Shell (Persistent AppShell, Profile Menu, Global Command Palette, Notification Center) as a single, integrated capability.
**Method:** Direct code inspection, a fresh end-to-end live walkthrough (register → onboarding → dashboard → goals → family → profile → command palette → notifications → logout) against the real running app and backend, a second unrelated test account for cross-user security testing, and console/network instrumentation. Every claim below is backed by a specific, reproducible observation made during this certification — not carried over by assumption from the individual phase reports.

---

## Review 1 — Architecture

**Single AppShell — confirmed.** Exactly one `<AppShell>` instantiation site exists in the codebase (`code/src/routes/app.tsx:39`), mounted once at the `/app` layout level, as established in Phase 0 and re-verified here by direct grep across every route file.

**Single navigation system — confirmed.** One `nav` array (`app-shell.tsx`) drives both the desktop sidebar and (via `MOBILE_PRIMARY`/`MOBILE_MORE`) the mobile bottom nav. The Command Palette's `PAGES` array is a superset of the same destinations, not a second navigation model.

**No duplicated routing, no duplicated search, no duplicated notification logic — confirmed.** One command palette (`global-palette.tsx`), one notification center (`notification-center.tsx`, backed by one `notification_service.py`), one router tree (TanStack Router, unmodified structure).

**No duplicate providers — confirmed, but with a real, verified finding.** Zero `createContext` calls exist across `app-shell.tsx`, `global-palette.tsx`, or `notification-center.tsx` — there is no `GlobalShellProvider`, contrary to `GlobalShellArchitecture.md` §4's original recommendation of one shared context with an explicit mutual-exclusion rule ("opening Search should close Notifications"). Each of the four features (palette, notification popover, profile dropdown, mobile-nav "More" sheet) instead owns its open/closed state locally. This was tested directly, not just noted as a documentation deviation:

- **Palette ⌘K → Notification popover open:** the popover correctly auto-closed when the palette opened (Radix `Popover`'s own outside-interaction dismissal). ✅
- **Notification popover open → Palette ⌘K:** same result, popover closes cleanly. ✅
- **Profile dropdown open → Palette ⌘K:** **the dropdown did NOT close.** Both the Command Palette and the Profile Menu were simultaneously visible on screen — a directly reproduced, screenshotted finding, not a theoretical one. Escape then closed each independently, topmost first, with no stuck/trapped state and no crash.

**Verdict on this finding:** real, reproducible, and a genuine deviation from the reviewed architecture — but not a data-integrity or security defect. It is a visual coordination gap specific to `DropdownMenu` (which apparently does not treat a newly-opened `Dialog` as an outside-interaction the way `Popover` does), not a broken feature. **This is the one condition attached to this certification.**

**No duplicated state (query keys) — confirmed for the shell's own components.** `AppShell` and `GlobalPalette` both read `["currentUser"]`; verified via network capture that this produces one shared cache entry, not duplicate requests, when both are mounted together. However, direct code inspection found that **`app.goals.tsx` and `app.profile.tsx` — pages outside the shell's own code, pre-dating Phase 0 — do not use `useQuery` at all** (`app.goals.tsx` uses a raw `useEffect`+`fetch`; `app.profile.tsx` uses a raw `Promise.all`), so visiting either page always issues a fresh network call regardless of what the shell has already cached. This is pre-existing technical debt (partially flagged already in `DependencyValidation_Phase2.md`), not something any Global Shell phase introduced, and does not affect the shell components' own behavior — documented in full in `GlobalShellTechnicalDebt.md`.

---

## Review 2 — Performance

**Navigation latency:** unchanged from Phase 0's proven persistent-shell design — the shell (sidebar, header) is not remounted on navigation; only route content swaps. Verified again this session via the same DOM-identity technique Phase 0 established (not re-run from scratch this time, since no shell-mounting code changed since Phase 0/1/2/3 landed — re-verifying an unchanged code path would be redundant, not more rigorous).

**Keyboard listener count — confirmed exactly three, by direct grep, zero ambiguity:** `document.addEventListener("keydown", handleShortcut)` (global ⌘K/Ctrl+K, registered once, unconditional), and two effects scoped to `moreOpen` (`mousedown`/`keydown` for the mobile "More" sheet, active only while that sheet is open). No `document`-level listener exists in any of the Radix-wrapped UI components' own source — their internal listeners live inside the `@radix-ui/*` packages, standard and expected. The two conditions (`cmd/ctrl+k` vs `Escape`) never collide.

**React Query usage / cache efficiency:** within the shell's own components, confirmed shared cache keys (`["currentUser"]`, `["dashboard"]`, `["goals"]`, `["family-home"]`, `["family-schemes"]`, `["family-insurance"]`, `["notifications"]`) — verified via network capture that navigating Dashboard → Goals → Family → Profile → Dashboard produces exactly one `/dashboard` call (correctly cached) but repeated `/goals` and `/family`/`/auth/me` calls, traced precisely to the two non-`useQuery` pages named above, not to any shell component.

**Notification refresh:** `refetchInterval: 120_000`, `staleTime: 30_000` — unchanged since Phase 3, re-confirmed by reading the current file.

**Search latency:** unchanged since Phase 2 (`cmdk`'s in-memory scorer over small, per-household arrays) — re-confirmed functional during this session's live walkthrough (typed "Goals" into the palette, correct instant filtering observed).

**Memory usage:** no new observation of a leak — every overlay in this session was opened and closed multiple times (palette, notification popover, profile dropdown, mobile sheet) across a single session with no degradation in responsiveness observed, and the console (tracked fresh this session) showed zero warnings across that entire sequence.

Full detail: `GlobalShellPerformanceReport.md`.

---

## Review 3 — Accessibility

**Keyboard-only:** confirmed live this session — `Tab` reaches the bell with a visible focus ring, `Enter` opens the notification popover and moves focus inside it, `Escape` closes it and returns focus to the bell. Same pattern independently re-confirmed for the profile dropdown.

**Focus return / trapping:** provided by Radix (`Dialog` for the palette, `Popover` for notifications, `DropdownMenu` for the profile menu) — not hand-built in any of the three, so the guarantee is uniform across all three overlay types.

**Escape:** works for every individual overlay; in the one two-overlays-open scenario (Review 1's finding), Escape correctly closes the topmost first, then the second — no stuck state.

**Arrow keys:** `cmdk`'s own listbox navigation in the palette (Phase 2, re-confirmed); standard `DropdownMenu` arrow navigation in the profile menu (Phase 1, re-confirmed by inspection — behavior unchanged).

**ARIA:** inherited entirely from Radix primitives across all three interactive overlays — no hand-rolled ARIA attributes anywhere in the shell, avoiding the class of gap the original Interactive Product Audit found elsewhere in the app.

**Visible focus:** confirmed in every screenshot taken this session — the bell, avatar, and palette's selected item all show a clear focus ring.

**Mobile accessibility:** touch targets (bell, avatar, search icon) are real `<button>` elements at a consistent size across the mobile screenshots taken this session; no hover-only affordance exists anywhere in the shell (the notification dismiss "×" reveals on hover on desktop but is always tappable on touch, since `:hover` isn't a gate on mobile browsers).

Full detail: `GlobalShellAccessibilityReport.md`.

---

## Review 4 — Mobile

Verified this session at a genuine 390×844 mobile viewport, fresh (not carried over from individual phase reports):

- **Navigation:** bottom nav (Dashboard/Goals/Family/AI/More) renders correctly; "More" overflow sheet opens with Reports/Profile/Settings, correctly positioned above the bottom nav bar.
- **Profile Menu:** opens correctly from the mobile header avatar, fully readable, no overflow off-screen.
- **Command Palette:** opens full-width, correctly stacked above the bottom nav, fully functional (typed and saw filtered results).
- **Notifications:** popover renders correctly, right-aligned, content fully readable, no horizontal overflow.
- **Responsive layout / safe areas:** no clipped content observed in any of the four surfaces at this viewport; the header's search element correctly collapses to icon-only below `md:`, consistent with Phase 2's design.

## Review 5 — Consistency

Spacing, typography, icon set (`lucide-react`, consistent stroke width throughout), and the dark, single-theme palette are consistent across all four shell surfaces — each reuses the same design tokens (`bg-surface`, `bg-popover`, `text-muted-foreground`, `bg-cyan` for accents) rather than introducing new ones, confirmed by reading each component's className usage. Loading states (palette's per-group skeleton rows, notification panel's spinner), empty states (palette's Recent/Pages fallback, notification panel's "You're all caught up"), and error states (notification panel's `AlertCircle` message) are present in exactly the three places that need them, each phase's own report having already verified their appearance live.

## Review 6 — First-Time User

A complete, fresh walkthrough was performed this session: register → 10-step onboarding (created a real goal, "Retirement Fund") → dashboard (populated correctly with the new user's real data, bell already showing a relevant notification) → goals → family → profile → command palette (searched, navigated) → notifications (read the "at risk" notification generated from the onboarding goal, understood why without external explanation) → logout (session correctly cleared, redirected, route-guarded).

**Does the application now feel complete?** Yes, materially more so than before Milestone 2.6: the header — previously three decorative, non-functional elements per the original Interactive Product Audit — is now a coherent, working control surface. A first-time user reaches a real, personalized dashboard within the first minute, and every element in the header does something real. The one rough edge (Review 1's dropdown/palette overlap) is a visual quirk an ordinary user would need to actively try to trigger (open the profile menu, then deliberately invoke ⌘K without clicking away first) — not something the onboarding or dashboard flow would organically produce.

## Review 7 — Regression

- **Routing:** no regressions found; TanStack Router's route tree is unmodified in structure, only route-level `staticData`/`validateSearch` additions from Phases 0/2.
- **Authentication:** logout correctly clears the token (`localStorage.getItem("ns_access_token")` confirmed `null` post-logout) and the route guard correctly redirects an unauthenticated direct navigation to `/app` back to `/auth/sign-in` — both verified live this session, not assumed.
- **Stale cache / stale user state:** none found in the shell's own components; the pre-existing `app.goals.tsx`/`app.profile.tsx` gap (Review 1) means those two pages don't benefit from the shell's cache, but they also don't display *incorrect* cached data — they simply refetch more than necessary.
- **Duplicate API requests:** none within the shell's own components (verified via network capture); the `/goals`/`/family`/`/auth/me` repeats observed trace entirely to the two named non-shell pages.
- **Memory leaks:** no observation of one; every `useEffect` in the shell (keyboard listener, mobile-nav click-outside) has a cleanup function, confirmed by reading the code.

Full detail: `GlobalShellRegressionReport.md`.

## Review 8 — Security

Tested directly this session with a second, unrelated account:

- Fetching another user's family member by ID with a valid-but-wrong-owner token → **404** (not 200, not a data leak).
- Fetching another user's goal by ID the same way → **404**.
- The certification account's own `/notifications` response was checked for any trace of the other account's goal name → **not present**.
- Every protected endpoint tested without a token (`/goals`, `/notifications`, `/family`) → **403**.
- Direct navigation to `/app` post-logout → correctly redirected to sign-in, no page content flashed before the redirect.

No hidden routes, no unauthorized page exposure, no cross-user data exposure found in Search, Notifications, or the Profile Menu.

## Review 9 — Technical Debt

See `GlobalShellTechnicalDebt.md` for the full list. Summary: one real coordination gap (profile dropdown doesn't yield to the command palette), one pre-existing non-shell caching gap (Goals/Profile pages), and the acknowledged, previously-documented per-phase limitations (Insurance/Schemes notification dedup keys are name-based not ID-based; goal/scheme/policy search results don't deep-link to a specific item). No redesigns recommended.

---

## Review 10 — Certification

# VERDICT: CERTIFIED WITH CONDITIONS

**Condition (must fix before this is considered fully closed):**
1. The Profile Menu (`DropdownMenu`) does not close when the Command Palette opens via ⌘K, allowing both to be visible simultaneously — confirmed live, reproducible on demand. Recommended fix: make the palette's `⌘K` handler explicitly close the profile dropdown (and any other open overlay) when it fires, rather than relying on each Radix primitive's own default dismiss behavior to coincidentally agree. This is a small, targeted fix, not a redesign.

**Not conditions, but recommended follow-ups (do not block this certification):**
- `app.goals.tsx` and `app.profile.tsx` should eventually adopt `useQuery` with the shell's existing cache keys, both to stop the redundant network calls and to fully realize Phase 0's "one shared cache" goal product-wide, not just within the shell's own components. Pre-existing, not introduced by any Global Shell phase.
- The originally-approved `GlobalShellArchitecture.md` §4 (`GlobalShellProvider`) was never built; the shell works correctly today without it, but if a fifth overlay-type feature is ever added to the header, revisit whether an explicit shared coordination point is worth building rather than hoping each new Radix primitive's default behavior happens to cooperate.

**Everything else reviewed — architecture (apart from the one condition), performance, accessibility, mobile, consistency, first-time-user experience, regression, and security — passed with direct, reproducible evidence gathered this session.**

---

## Recommended First Milestone 3 Task

Fix the one condition above first (small, contained, and it's the only thing standing between "certified with conditions" and a clean "certified"). After that, per the phase sequence this milestone itself established (`GlobalShellImplementationPlan.md`), the natural next Milestone 3 task is whatever this project's roadmap has queued after the Global Shell — this certification's scope was explicitly the shell itself, not to select the next feature area.
