# Accessibility Audit — Phase 8

**Date:** 2026-07-13
**Method:** direct code inspection (grep across every route/component for hand-rolled overlay patterns, icon-only buttons, images, and div-as-button anti-patterns) plus live keyboard-only interaction against the running app, cross-checked against the accessibility work already certified in `GlobalShellAccessibilityReport.md` and `AccessibilityReview_M2.1-P3.md` so this phase doesn't re-audit ground already covered.

**Ground rule, per the mission:** verify against the actual codebase, not documentation. The two existing accessibility reports certify the global shell (Command Palette, Notification popover, Profile dropdown — all Radix-based) and the Family module. This phase's job is to check what those two didn't: everything else, especially anything *not* built on Radix.

---

## 1. What's already covered (confirmed, not re-tested key-by-key)

- **Global shell overlays** (Command Palette, Notification popover, Profile dropdown): all Radix primitives, all certified in `GlobalShellAccessibilityReport.md` — focus trap, Escape, focus return, and ARIA are Radix defaults, re-confirmed present by reading the same files again (unchanged since that report).
- **Family module**: all interactive elements confirmed native `<button>`/`<Link>`/`<input>`/`<select>` with focus-visible rings, per `AccessibilityReview_M2.1-P3.md` — re-confirmed no `<div onClick>` exists anywhere in the module (grep, this session).
- **Images**: grep for `<img` across every route and component found zero instances missing an `alt` attribute.
- **Div-as-button anti-pattern**: grep for `div` elements carrying `onClick` across the entire `routes/` and `components/` tree returned zero matches — every clickable surface in the app is a real `<button>`, `<a>`/`<Link>`, `<input>`, or `<select>`.
- **Touch targets**: grep for undersized icon-button dimensions (`h-6 w-6`, `h-7 w-7`, `h-8 w-8` on `<button>`) found no matches — no interactive control smaller than the shell's existing 36px+ icon buttons.

## 2. Finding: three hand-rolled modals lack the ARIA/keyboard/focus behavior the rest of the app gets for free

**What's actually there (verified in code):** `RecordLifeEventDialog.tsx`, `GoalSimPanel.tsx`, and the inline "New goal" modal in `app.goals.tsx` are the only three overlay surfaces in the entire app *not* built on a Radix primitive — all three are hand-rolled with `framer-motion`'s `motion.div` for the backdrop and panel. Grepping all three for `role="dialog"`, `aria-modal`, and any `Escape`-key handling returned nothing in any of them.

Concretely, before this phase:
- None of the three had `role="dialog"` or `aria-modal="true"` — a screen reader has no way to know these are modal dialogs rather than ordinary page content.
- None of the three closed on `Escape` — the only way to dismiss any of them was a mouse click on the backdrop or an explicit Cancel/X button, which fails a keyboard-only user (the exact case `GlobalShellAccessibilityReport.md` verified *does* work for every Radix overlay in the shell).
- None of the three moved focus into the dialog on open or trapped `Tab` inside it — a sighted mouse user wouldn't notice, but a keyboard user tabbing from the trigger button would tab straight through into the page content behind the (visually) modal overlay.
- None of the three returned focus to the trigger element on close.
- `GoalSimPanel`'s close ("×") button had no accessible name at all — no `aria-label`, no text content, no `title` — a screen reader would announce it only as "button."

This is a real, user-facing gap, not a theoretical one: every other overlay in the product (Command Palette, notifications, profile menu) already behaves correctly here, so a keyboard or screen-reader user hitting Life Events' "Record life event" dialog or the Goals page's "New goal"/goal-detail panel would hit a materially worse experience than the rest of the app, with no way to tell why.

## 3. Decision

Extract the missing behavior into one small, reusable hook (`useDialogA11y`) rather than fixing each of the three call sites with duplicated logic — the repetition here is real (three near-identical `motion.div` overlay shells), not speculative, so a shared hook is the DRY choice, not a premature abstraction. The hook:

- Captures `document.activeElement` on open and restores it on close (focus return).
- Moves focus to the first focusable element inside the dialog on open (or the dialog container itself if it has none).
- Closes the dialog on `Escape`.
- Traps `Tab`/`Shift+Tab` cycling within the dialog's own focusable elements while open (a minimal, hand-rolled equivalent of what Radix's `Dialog` already does internally for the shell's overlays).

Applied to all three call sites, plus:
- `role="dialog"` / `aria-modal="true"` / `aria-labelledby` (pointing at each dialog's own visible heading) added to each dialog's outer panel element.
- `aria-label="Close"` added to `GoalSimPanel`'s icon-only close button.

**Not changed:** the visual design, the framer-motion animation, the click-outside-to-close behavior (kept as-is, it's additive to Escape, not a replacement), and every other already-certified overlay (Radix ones untouched — they don't need this hook, they already have equivalent behavior built in).

## 4. Implementation shape

1. New hook: `code/src/hooks/use-dialog-a11y.ts` — `useDialogA11y(onClose, isOpen = true)`, returning a `ref` to attach to the dialog's outer panel element. Defaults `isOpen` to `true` for dialogs that are their own component and only ever mounted while open; an inline dialog behind `{open && (...)}` in an always-mounted parent (the Goals page's "New goal" modal) passes its own `open` boolean through explicitly instead.
2. Wire the hook + `role`/`aria-modal`/`aria-labelledby` into `RecordLifeEventDialog.tsx` (all three of its internal views — picker, form, celebration — share one `aria-labelledby` id, since only one is ever rendered at a time), `GoalSimPanel.tsx`, and the "New goal" modal in `app.goals.tsx`.
3. Add the missing `aria-label="Close"` to `GoalSimPanel`'s "×" button.
