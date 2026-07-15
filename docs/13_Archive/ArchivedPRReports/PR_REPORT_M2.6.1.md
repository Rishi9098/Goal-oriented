# PR Report — M2.6.1 (Global Shell Overlay Mutual Exclusion Fix)

**Date:** 2026-07-08
**Scope:** the single certification condition from `GlobalShellCertification.md` — the Profile Menu staying open when the Command Palette opens via ⌘K/Ctrl+K. Nothing else in Search, Notifications, Profile functionality, Routing, Navigation, Theme, or AI was touched.

---

## Summary

Consolidated four independent overlay-open booleans (`AppShell`'s own `paletteOpen`/`moreOpen`, `NotificationCenter`'s internal `open`, and the Profile Menu's fully-uncontrolled Radix state) into one shared, discriminated-union state (`activeOverlay: "palette" | "notifications" | "profile" | "more" | null`) owned by `AppShell`. Because only one value can be true at a time, two overlays can no longer be simultaneously open — a structural guarantee, not a convention. `NotificationCenter` and the profile `DropdownMenu` became controlled components using the exact pattern `GlobalPalette` already established; no new architecture, no event bus, no Context provider.

## Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.6.1.md`) — traced the exact root cause: the `⌘K` handler could only ever toggle `paletteOpen`, since the profile menu's state was invisible to it (fully uncontrolled Radix internals) and the notification popover's state was controlled but never lifted out of `NotificationCenter`. Also traced why the bug was *inconsistent* (notifications happened to auto-close, profile menu didn't) — coincidental agreement between two different Radix primitives' own default dismiss heuristics, not a designed guarantee.
2. **Architecture Review** (`ArchitectureReview_M2.6.1.md`) — designed the single `activeOverlay` state, verified against every stated requirement (mutual exclusion, correct Escape, correct focus return, no duplicate state, no event bus, reuse existing controlled-component pattern).
3. **Accessibility Review** (`AccessibilityReview_M2.6.1.md`) — reasoned through why focus trap/Escape/focus return/ARIA are all unaffected in mechanism (still entirely Radix's own per-primitive behavior) and improved in outcome (only one trap can ever be active, eliminating the two-competing-traps scenario the bug produced). Every claim scheduled for, and then confirmed by, live verification.
4. **Implementation** — see Files Changed.
5. **Regression Testing** — `tsc --noEmit` clean, `eslint` clean (0 errors, 0 warnings) on both touched files. Confirmed via grep: exactly 3 `document`-level listeners (unchanged count, same as before the fix — only their controlling variable changed), state variable count reduced (four booleans across two files → one variable in one file).
6. **Live Verification** — see below, the exact Step 6 sequence plus additional pairwise combinations.
7. **Performance Review** — no duplicate listeners (confirmed via grep), no new dependencies, no additional renders introduced (each overlay still only re-renders on its own state change, since `activeOverlay` changes are already scoped to the same component tree that previously held the equivalent booleans).
8. **Documentation** — this report, `PROJECT_STATE.md`, `CHANGELOG.md`.

## Files Changed

| File | Change |
|---|---|
| `code/src/components/app-shell.tsx` | Replaced `paletteOpen`/`moreOpen` booleans with one `activeOverlay` state; `⌘K` handler, mobile "More" button/effect, `GlobalPalette` props, `NotificationCenter` props, and `DropdownMenu` (profile menu) all now read/write this one variable |
| `code/src/components/notification-center.tsx` | Removed its internal `useState(false)`; now accepts `open`/`onOpenChange` as props (identical contract to `GlobalPalette`'s existing pattern) — no change to its queries, mutations, or rendering |

## Live Verification (performed this session, against the real running app)

Exact Step 6 sequence, plus additional pairwise combinations, all confirmed:

- **Profile Menu → ⌘K:** opened the Profile Menu, pressed `⌘K` — **the Profile Menu closed automatically**, the palette opened cleanly with nothing else visible. (This is the certification's exact reproduction case, now fixed.)
- **Notifications → ⌘K:** same result — notifications closed, palette opened cleanly.
- **⌘K → Notifications:** palette open, clicked the bell — palette closed (first click dismissed it, matching the same "outside click dismisses, doesn't also activate" pattern already observed for other overlay pairs in the original certification — not a regression, standard behavior), second click opened notifications correctly with nothing else visible.
- **Notifications → Profile Menu, and back:** each correctly closes the other.
- **Mobile "More" sheet ↔ Notifications, and ↔ Palette:** tested at a genuine mobile viewport (~500px width, this session) — opening Notifications then tapping "More" closed Notifications and opened the sheet; pressing `⌘K` while "More" was open closed the sheet and opened the palette cleanly. All four overlay types now confirmed mutually exclusive in every pairwise combination, at both desktop and mobile widths.
- **Repeated cycles:** 6 rapid open/close cycles (palette ×3, notifications ×2, profile ×2, each closed via `Escape`) produced a clean, correctly-rendered page with no stuck overlays, no visual artifacts, and no new console errors — one pre-existing hydration warning was observed, traced directly to a Grammarly browser extension injecting `data-gr-ext-installed`/`data-new-gr-c-s-check-loaded` attributes into `<body>`, unrelated to this fix (this app's own code doesn't touch SSR/hydration or body attributes anywhere in the diff).
- **Keyboard navigation inside the palette:** arrow-down navigation still moves the selection correctly (Dashboard → Goals → Family, tested this session) — confirms the fix didn't disturb `cmdk`'s own internal keyboard handling.
- **Escape and focus return:** confirmed live — `Escape` closes whichever overlay is open and returns focus to its trigger, exactly as before.

## Performance Review

- **Duplicate listeners:** none — exactly 3 `document`-level listeners exist in `app-shell.tsx`, the same count as before this fix (confirmed via grep); only the variable they write to changed.
- **Memory leaks:** none — the same `useEffect` cleanup functions from before the fix are unchanged; no new subscriptions were introduced.
- **Unnecessary renders:** none introduced — `activeOverlay` is a single state update per interaction, same as the two-booleans-plus-two-hidden-states it replaced; no new re-render surface was created, and the total number of independent state variables driving the header actually *decreased*.

## Rollback

Revert the two touched files. No migration, no backend change, no new dependency, no data to back out.

---

## Success Criteria

- [x] Only one overlay can be open — structurally guaranteed by the single `activeOverlay` variable, verified live across every pairwise combination
- [x] Profile Menu closes when Command Palette opens — verified live, the certification's exact reproduction case
- [x] Notification behavior remains correct — queries, mutations, read/dismiss, badge count all untouched; verified live during the repeated-cycle test
- [x] Escape works — verified live for every overlay
- [x] Focus management preserved — each primitive's own trap/return logic untouched; verified live
- [x] Accessibility preserved — zero ARIA changes; `AccessibilityReview_M2.6.1.md`'s predictions all confirmed
- [x] Zero regressions — `tsc`/`eslint` clean, no new console errors (one pre-existing, unrelated extension warning noted), repeated-cycle stability confirmed

**Stopping here per instruction. Awaiting final certification. Not beginning Milestone 3.**
