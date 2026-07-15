# Accessibility Implementation Report — Phase 8

**Scope:** Exactly what `AccessibilityAudit.md` decided — bring the three hand-rolled (non-Radix) modals up to the same keyboard/focus/ARIA baseline every other overlay in the product already has. All changes confined to a new shared hook plus the three affected components; no backend touched.

---

## Files Changed

| File | Change |
|---|---|
| `code/src/hooks/use-dialog-a11y.ts` (new) | `useDialogA11y(onClose, isOpen = true)` — captures and restores focus (focus return), moves focus into the dialog on open, closes on `Escape`, and traps `Tab`/`Shift+Tab` cycling within the dialog's own focusable elements while open. Returns a `ref` for the dialog's outer panel element. |
| `code/src/components/life-events/RecordLifeEventDialog.tsx` | Wired `useDialogA11y` (closing action is `finishCelebration` while the celebration view is showing, `onClose` otherwise). Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="life-event-dialog-heading"`, `tabIndex={-1}` to the dialog panel. Added the matching `id` to whichever of the three internal headings (picker/form/celebration) is currently rendered. |
| `code/src/components/dashboard/GoalSimPanel.tsx` | Wired `useDialogA11y(onClose)`. Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="goal-sim-panel-heading"`, `tabIndex={-1}` to the panel; added the matching `id` to the goal-name heading. Added the missing `aria-label="Close"` to the icon-only "×" button, which previously had no accessible name at all. |
| `code/src/routes/app.goals.tsx` | Wired `useDialogA11y(() => setOpen(false), open)` — this modal is inline JSX behind `{open && (...)}` in an always-mounted route component rather than its own component, so `isOpen` is passed explicitly rather than relying on mount/unmount. Added `role="dialog"`, `aria-modal="true"`, `aria-labelledby="new-goal-dialog-heading"`, `tabIndex={-1}` to the "New goal" panel and the matching `id` to its heading. |

## Files Not Changed (and why)

| File / area | Reason |
|---|---|
| `app-shell.tsx`, `global-palette.tsx`, `notification-center.tsx` (Command Palette, Notifications, Profile dropdown) | Already Radix-based and already certified in `GlobalShellAccessibilityReport.md` — re-confirmed unchanged and still correct by reading them again this phase; they don't need `useDialogA11y`, since Radix's `Dialog`/`Popover`/`DropdownMenu` already provide equivalent behavior internally. |
| Family module (`app.family.*.tsx`, `FamilyMemberForm.tsx`) | Already certified in `AccessibilityReview_M2.1-P3.md`; re-confirmed via grep that no `<div onClick>` pattern exists there and focus-visible rings are still present. Out of this phase's scope since nothing new was found. |
| Every `<img>` in the app | Grep confirmed all already carry `alt`; no gap found. |
| `backend/**` (all) | Every fix is a frontend hook + JSX attribute change; no new endpoint, no new computed value from the server. Confirmed via `ruff`/`mypy` and `git status`. |

## Implementation Summary

1. Grepped every route and component for the same anti-patterns that would normally cause the biggest real-world accessibility failures (`<div onClick>`, images without `alt`, undersized touch targets) before assuming any of them existed — all three came back clean, so this phase's actual, verified gap turned out to be narrower and more specific than a generic "accessibility pass": exactly the three overlays not built on Radix.
2. Built one shared hook instead of three separate fixes, since the three call sites needed the identical behavior (focus-in, Escape, Tab-trap, focus-return) — this matches the DRY principle without inventing an abstraction the codebase didn't actually need (the repetition was real and about to be tripled, not speculative).
3. The hook's `isOpen` parameter defaults to `true` (works unmodified for the two dialogs that are their own component and only mount while open) but accepts an explicit boolean for the one dialog that's inline JSX in an always-mounted parent — this let one hook serve both shapes of call site already present in the codebase, rather than requiring `app.goals.tsx`'s modal to be refactored into its own component just to fit the hook.
4. `GoalSimPanel`'s close button's missing accessible name was a real, separate gap found while wiring the hook in — fixed with a one-line `aria-label="Close"` addition, matching the "Close" label pattern already used for icon-only dismiss controls elsewhere (e.g., the shell's notification dismiss button).

## Manual Validation

Performed live in Chrome against the running dev build (`localhost:8080`, backend `localhost:8010`):

- **Life Events dialog**: opened via "Record life event," confirmed `Escape` closes it and focus visibly returns to the "Record life event" trigger button (screenshotted, focus ring visible).
- **Goals "New goal" modal**: opened via "New goal," confirmed focus moves into the dialog automatically (the "Goal name" input shows a focus ring on open, with no manual Tab needed), confirmed `Escape` closes it and focus visibly returns to the "New goal" trigger button (screenshotted).
- **Goal detail panel (`GoalSimPanel`)**: opened by clicking a goal card, confirmed `Escape` closes it cleanly with no console errors.
- Console checked (`read_console_messages`, filtered `error|Error`) after each of the above: only the same pre-existing, unrelated Grammarly-extension hydration warning seen in every prior phase.

## Automated Validation

- `npx tsc --noEmit --pretty false` (whole project) — clean, zero errors.
- `npx eslint src/hooks/use-dialog-a11y.ts src/components/life-events/RecordLifeEventDialog.tsx src/components/dashboard/GoalSimPanel.tsx src/routes/app.goals.tsx` — one Prettier formatting nit in the new hook, fixed via `--fix` (whitespace-only, re-verified clean afterward), zero errors remaining.
- `npm run build` (full Vite + Nitro production build) — succeeded, twice (before and after this phase's changes).
- Backend: `ruff check app/` — all checks passed; `mypy --strict app/` — success, no issues found in 87 source files. Zero backend files in this phase's diff (confirmed via `git status backend/`).
- Backend test suite: not re-run — zero backend code changed; the existing 673-pass baseline remains valid.

## Regression Risk

**Low.** The hook is new, additive code with no existing caller to break. Its integration into the three components adds attributes (`role`, `aria-*`, `tabIndex`, `id`, `ref`) and a keydown listener scoped to each dialog's own lifetime — it does not alter any existing click handler, form submission logic, or visual styling (the one `className` addition, `outline-none`, exists only to suppress the default browser focus ring on the programmatically-focused container itself, since visible focus is already shown on whichever real control inside it receives focus first).

## Performance Impact

None. Each dialog now adds one `document`-level `keydown` listener only while open, removed on close/unmount — negligible cost, no new network calls, no new renders.

## Backward Compatibility

Fully preserved. `onClose`/`onRecorded` prop contracts on all three components are unchanged; the hook only reacts to the same close callbacks that already existed. No exported type or public component signature changed shape.

## Outstanding Risks

1. The Tab-trap implementation is a minimal hand-rolled equivalent of what Radix provides internally (recompute focusable elements on every `Tab` keypress rather than a more sophisticated `FocusScope`) — sufficient for these three dialogs' actual content (forms and simple button rows, no complex nested focus scopes), but not a general-purpose replacement for Radix's `Dialog` if a future dialog needs more advanced focus semantics (e.g., nested dialogs). If that need arises, adopting Radix's own `Dialog` primitive for that case would be the better long-term fix rather than extending this hook further.
2. This phase's grep-based sweep (div-onClick, missing alt, undersized touch targets) covers the highest-yield anti-patterns but is not a full WCAG 2.2 conformance audit (e.g., color contrast ratios were not measured pixel-by-pixel here, though Phase 6's color-token work already reduced ad-hoc color usage). A dedicated contrast-ratio pass would be the natural next increment if the mission scope is ever extended beyond Phase 10.

## Ready for Next Phase

**Yes.** Phase 8's scope is closed and validated. Continuing automatically to Phase 9 (Performance UX) per the mission's instruction not to pause between phases.
