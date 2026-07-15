# Design Review — Phase 0 (Persistent AppShell Foundation)

**Date:** 2026-07-08
**Purpose:** Confirm, before any code is written, that this phase is a pure architectural/internal change with zero visual or UX surface change — consistent with `GlobalShellImplementationPlan.md`'s Phase 0 scope ("no user-facing behavior ships in this phase") and this project's frozen design system (`CLAUDE.md`: "Never change the UI design system").

---

## 1. What must look and feel identical

| Element | Verification |
|---|---|
| Sidebar contents, order, active-item highlighting | Same `nav` array, same `active` computation via `useRouterState`/`pathname` — unchanged logic, only its render location moves |
| Header title text per screen | Must render the exact same string on the exact same route as today — the mechanism changes (`staticData` instead of a prop, per `ArchitectureReview_Phase0.md` §4) but the displayed output does not |
| Plan health card (value, progress bar, styling) | Same data (`plan_health_score`), same visual treatment — only the fetch mechanism changes |
| Avatar initials | Same computation, same data source, same appearance |
| Mobile bottom nav + "More" overflow menu | Entirely untouched — `moreOpen` state and its listeners remain exactly where they are today, per `ArchitectureReview_Phase0.md` §5 |
| Search bar, notification bell placeholders | Untouched — still the same non-functional decorative elements they are today; Phase 0 explicitly does not wire them up (that's Phases 1–3) |
| All 13 screens' own content | Zero change — Phase 0 does not touch any screen's own JSX, only how each one reaches `AppShell` |

## 2. What changes, and confirmation that none of it is visible

- **Where `AppShell` is instantiated** (moved from 13 leaf components to 1 layout component) — a render-tree location change, invisible in the rendered output, since the JSX `AppShell` produces is unchanged.
- **How identity/plan-health data is fetched** (raw `useEffect`+promise → `useQuery`) — a data-fetching mechanism change. The *values* displayed are identical; the *timing* of when they first appear may very slightly improve (React Query can serve a cached value instantly on subsequent navigations instead of showing the brief `"··"`/`null` loading state every single time) — this is a **strict improvement in perceived polish, not a redesign**: the loading state itself (its markup, styling) is unchanged, it will simply be skipped more often because the data is already there.
- **How the header title is supplied** (prop → route `staticData`) — an internal plumbing change with no visible effect, per §1.

## 3. Explicit non-goals for this phase (confirmed against the instruction's DO-NOT list)

Verified this design introduces **none** of the following, all correctly deferred to later phases per `GlobalShellImplementationPlan.md`:
- No Profile Menu (avatar remains a non-interactive display element, exactly as today)
- No Global Search (search bar remains the same static, non-functional placeholder)
- No Notifications (bell remains the same non-functional placeholder)
- No Keyboard Shortcuts (no new listeners beyond what already exists for the mobile "More" menu)
- No theme toggle of any kind
- No AI Copilot behavior change

## 4. Accessibility — must not regress

- Every existing `focus-visible` treatment, `aria-*` attribute, and keyboard-operable element inside `AppShell` (the mobile "More" button's `aria-haspopup`/`aria-expanded`, its `role="menu"`/`role="menuitem"` structure) must survive the move to a new render location unchanged — this is a copy/relocate of existing JSX, not a rewrite, so no attribute should be dropped incidentally.
- Tab order must remain identical: sidebar links, then main content, then (on mobile) bottom nav — promoting `AppShell` to wrap `<Outlet/>` preserves this DOM ordering naturally, since the outlet's content still renders in the same `<main>` position relative to the sidebar/header it did before.

## 5. Styling — must not regress

No CSS, Tailwind class, or design token changes are in scope. `styles.css` is not touched. The single-theme dark palette (`CLAUDE.md`'s frozen design system) is unaffected — this phase does not go anywhere near theming.

## 6. Conclusion

This phase is verified to be **purely internal**: a component's mount location, two data-fetching call sites, and one prop-to-staticData plumbing change — with an explicit, item-by-item confirmation that no pixel, no interaction, and no accessibility attribute is expected to differ for an end user. **Proceeding to Step 5 (Implementation).**
