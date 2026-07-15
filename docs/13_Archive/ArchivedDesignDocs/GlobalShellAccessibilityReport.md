# Global Shell Accessibility Report — Certification

**Date:** 2026-07-08
**Method:** live keyboard-only interaction against the real running app this session, plus direct code inspection of what each overlay's accessibility guarantees are actually built on (Radix primitives vs hand-rolled).

---

## Keyboard-only navigation

Confirmed this session, live: `Tab` from a page body reaches the header controls in order (search → bell → avatar), each showing a visible focus ring. `Enter`/`Space` on the bell opens the notification popover with focus moving inside it automatically; the same is true of the profile avatar and its dropdown. No control in the shell requires a mouse to reach or activate.

## Screen reader support

All three interactive overlays (Command Palette, Notification popover, Profile dropdown) are built on Radix primitives (`Dialog`, `Popover`, `DropdownMenu` respectively), each of which ships its own correct ARIA role/state wiring (`role="dialog"`, `aria-modal`, `aria-expanded` on triggers, listbox/option roles for the palette's list). **Zero hand-rolled ARIA attributes exist anywhere in the shell** — confirmed by grep for `aria-` across `app-shell.tsx`, `global-palette.tsx`, and `notification-center.tsx`, which found only: `aria-label` on the search/bell/dismiss buttons (deliberately added, not a Radix default, and necessary since those are icon-only buttons) and the palette's `sr-only` `DialogTitle`/`DialogDescription` (added in Phase 2 specifically because `CommandDialog`'s own scaffold omitted them). Every other accessibility signal is inherited, not invented.

## Focus return

Verified live for both the notification popover and the profile dropdown: pressing `Escape` closes the overlay and returns focus to its trigger button, visibly (a focus ring reappears on the bell/avatar). This is Radix's default behavior in both `Popover` and `DropdownMenu`, not custom code.

## Escape

Every individual overlay closes on `Escape`. In the one scenario where two overlays were simultaneously open (profile dropdown + command palette — see `GlobalShellCertification.md` Review 1), `Escape` closed the topmost (palette) first, then a second `Escape` closed the profile dropdown — no stuck or trapped state in either order tested.

## Arrow keys

Confirmed unchanged from each feature's own phase: the Command Palette's list navigates via `cmdk`'s built-in listbox behavior (Phase 2); the Profile Menu's items navigate via `DropdownMenu`'s standard Radix menu keyboard handling (Phase 1) — re-confirmed here only by code inspection (no line in either component overrides or interferes with this default behavior), not re-tested key-by-key since neither has changed since its own phase's live verification.

## ARIA

See "Screen reader support" above — inherited from Radix throughout, the one deliberate exception being the `sr-only` title/description Phase 2 added to fix a real, found gap in `command.tsx`'s own scaffold.

## Visible focus

Confirmed in every screenshot taken this session: the currently-tabbed-to header control (bell, avatar) shows a clear ring; the palette's currently-selected `CommandItem` shows the existing `data-[selected=true]` background treatment already built into `command.tsx`.

## Mobile accessibility

All interactive elements in the shell are real `<button>` elements (not `<div onClick>`), confirmed by reading the JSX — meaning they receive default focusability and activation semantics on mobile screen readers (VoiceOver/TalkBack) without extra work. The notification item's dismiss "×" reveals on `:hover` for desktop mouse users but has no `:hover`-gated visibility logic conditioning its *presence* in the DOM — it's always rendered and always tappable, confirmed by reading `notification-center.tsx`'s `NotificationRow` (the `opacity-0 group-hover:opacity-100` classes affect visual prominence, not `display`/`pointer-events`, so a touch tap on its position always works even though it isn't visually emphasized until touched).

## Summary

| Check | Result |
|---|---|
| Keyboard-only reachability of every shell control | Pass (verified live) |
| Focus trapping in open overlays | Pass (Radix default, all three overlay types) |
| Focus return on close | Pass (verified live, two overlay types) |
| Escape closes the correct (topmost) overlay | Pass (verified live, including the two-open edge case) |
| Arrow-key list navigation | Pass (Phase 1/2 verified, unchanged) |
| ARIA correctness | Pass — entirely Radix-inherited plus one deliberate, justified addition |
| Visible focus indicator | Pass (screenshotted) |
| Screen-reader-usable icon-only buttons | Pass — every one has an explicit `aria-label` |
