# Architecture Review — Phase 2 (Final, Post-Implementation)

**Date:** 2026-07-08
**Supersedes:** nothing in `ArchitectureReview_Phase2.md` (the pre-implementation design) — this document records what was actually built, including two real bugs found and fixed during live verification that the design phase did not anticipate.

---

## What was built, exactly as designed

- One `GlobalPalette` component (`code/src/components/global-palette.tsx`), rendered once inside the persistent `AppShell`, built entirely from the existing `command.tsx`/`dialog.tsx` scaffold and `cmdk`.
- One global `⌘K`/`Ctrl+K` keydown listener in `AppShell`, registered once (Phase 0's persistent-mount guarantee), toggling `paletteOpen`.
- Four lazily-loaded entity queries (`goals`, `family-home`, `family-schemes`, `family-insurance`), gated on `everOpened`, sharing cache keys with existing pages.
- Ten "Pages" entries, two "Quick Actions," a "Recent" group backed by per-user `localStorage`.
- A visually-hidden `DialogTitle`/`DialogDescription` added (the accessibility gap found in Dependency Validation §2), satisfying Radix's requirement that `command.tsx`'s own `CommandDialog` doesn't provide out of the box.

## Two real bugs found during live verification, both fixed

**1. "Create Goal" didn't open the modal when already on the Goals page.** `app.goals.tsx`'s `useState(openNewGoal)` only reads its initial value once, on first mount — but TanStack Router doesn't remount a route component for a search-param-only navigation (e.g., `/app/goals?new=false` → `/app/goals?new=true` while already there). Selecting "Create Goal" from the palette while already on the Goals page silently did nothing. **Fixed** with a `useEffect(() => { if (openNewGoal) setOpen(true); }, [openNewGoal])` — re-checks on every navigation to the route, not just the first. Verified live, twice: once from a different page (fresh mount, worked even before the fix) and once from the Goals page itself (only worked after the fix).

**2. Entity groups appeared on an empty query, contradicting the UX Review's own stated design.** The initial implementation's render conditions (`goalsLoading || (goals && goals.length > 0)`) didn't check `inputValue`, so once the lazy queries resolved, every goal/family member/scheme/policy would list unfiltered the moment the palette opened — before the user typed anything. **Fixed** by adding `!!inputValue &&` to all four entity-group conditions. Verified live: opening the palette on an account with a real, existing goal showed only Pages + Quick Actions (no Goals group) until a query was typed, at which point the exact matching goal appeared and nothing else.

**Both bugs were caught by live verification, not by static review** — a direct demonstration of why Step 8 (Live Verification) is mandatory and not a formality: `tsc`/`eslint` were clean the entire time these bugs existed, because both were logic errors, not type or lint errors.

## Confirmed unchanged from the pre-implementation design

Single palette (no second search system), zero backend changes, zero new dependencies, reused `dropdown-menu`/`command`/`dialog` scaffolding, the honest goal/scheme/policy deep-link limitation (navigates to the list, not a specific item — Family Members are the one exception, confirmed live with a real member ID).
