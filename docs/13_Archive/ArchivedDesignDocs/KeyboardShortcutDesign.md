# Keyboard Shortcuts — Design

**Date:** 2026-07-08
**Status:** Design only. No code written.
**Depends on:** `GlobalShellArchitecture.md`

---

## 1. What exists today (verified)

Exactly **one** keyboard listener exists anywhere in the frontend relevant to this capability: `app-shell.tsx`'s mobile "More" nav menu attaches a `document.addEventListener("keydown", handleEscape)` while open, closing the menu on `Escape`, and removes the listener on close/unmount. This is the **only** working precedent for keyboard-driven overlay dismissal in the app today, and this design deliberately follows its shape rather than inventing a new one.

No `⌘K`/`Ctrl+K` listener exists anywhere (confirmed by exhaustive grep across the frontend for `metaKey`, `ctrlKey`, and the literal key `"k"`) — the header's "⌘K" hint is currently just static text next to a non-functional search box.

## 2. ⌘K / Ctrl+K — open the command palette

- **Binding:** `metaKey` (Mac) or `ctrlKey` (Windows/Linux) + key `"k"`, attached at `document` level (not scoped to the header element), active on every authenticated screen — matching the promoted, persistent `AppShell` layout proposed in `GlobalShellArchitecture.md` §3, so the listener is attached once, not re-attached on every route navigation as would happen under the current per-route `AppShell` instantiation.
- **Must call `preventDefault()`:** some browsers bind `Ctrl+K` to their own address-bar/search behavior; without intercepting it, the palette and the browser's own UI could both react, or the browser could win and the palette never opens. This must be verified across Chrome, Firefox, and Safari specifically (per the project's own web-testing standard's minimum browser matrix) before this is considered done, not assumed correct from the code alone.
- **Toggle, not just open:** pressing `⌘K` again while the palette is already open should close it (matches the established pattern in comparable products and avoids a confusing "nothing happens" feel if a user double-presses out of habit).
- **Disabled while a text input already has focus in a way that would conflict:** not applicable here since `⌘K`/`Ctrl+K` is not a common in-field editing shortcut, but the implementation should still confirm it doesn't fire while the user is inside another modal that should take input precedence (e.g., the Goals page's "New goal" form) — see §5 on overlay precedence.

## 3. Escape — universal dismissal

**Rule: `Escape` closes whatever shell overlay is currently open** — Search palette, Notification panel, or Profile Menu — using the same `document`-level listener pattern the mobile "More" menu already establishes, generalized to check "is any shell overlay open" rather than one hardcoded piece of state. This is exactly why `GlobalShellArchitecture.md` proposes a single shared provider rather than four independent state pieces: a single `Escape` handler can check one shared "what's open" value instead of duplicating the same listener three more times with slightly different logic each time (which is how the current codebase ended up with focus-visible gaps and inconsistent patterns across screens, per the Interactive Product Audit).

**Precedence when multiple things could claim Escape:** if a shell overlay is open *and* something else on the page also listens for Escape (e.g., a future modal), the shell overlay should be treated as "on top" and consume the event first (`stopPropagation()` after handling), since it is, by construction, the most recently opened thing in the mutual-exclusion model from `GlobalShellArchitecture.md` §4. This needs explicit verification once the Goals page's "New goal" modal (which currently does **not** listen for Escape at all, per the Interactive Product Audit's navigation findings) is eventually brought up to the same standard — flagged here as a related, pre-existing gap this work should not silently paper over or accidentally worsen.

## 4. Arrow-key navigation

Handled differently per surface, deliberately reusing each surface's own natural pattern rather than one custom implementation:

- **Command palette:** `cmdk`'s own built-in keyboard handling (up/down to move selection, `Enter` to activate, already implemented inside the library this app already depends on) — no custom arrow-key code needed at all.
- **Profile Menu:** Radix `DropdownMenu`'s own built-in roving-`tabindex` arrow-key navigation (up/down moves selection, `Home`/`End` jump to first/last, type-ahead jumps to a matching label) — same reasoning, zero custom code.
- **Notification panel:** a plain scrollable list of cards, not a `<select>`-like construct — arrow-key *item-to-item* navigation is not proposed here (there's no established precedent for it in this app, and forcing an ARIA-listbox pattern onto what is fundamentally a feed of dismissible cards would be over-engineering relative to the actual interaction: open panel, read, optionally dismiss). Standard `Tab` order through each card's action buttons (mark-read, dismiss) is the appropriate, simpler mechanism here, consistent with how the rest of the app (e.g., the Goals list, the Family recommendations feed) already handles scrollable card collections — none of which use arrow-key list navigation today.

## 5. Overlay precedence and focus management

- Opening any shell overlay must move focus **into** it (the palette's input, the first menu item, the panel's first focusable element) — this is standard, expected modal/menu behavior and is provided for free by both Radix and `cmdk` when using their documented patterns; it must not be bypassed by a custom wrapper that forgets to forward this behavior.
- Closing any shell overlay (via Escape, selection, or outside click) must return focus to the element that opened it (the search box, bell, or avatar) — again, provided by Radix's primitives out of the box; `cmdk`'s `CommandDialog` (built on the same `Dialog` primitive already in `components/ui/dialog.tsx`) provides the same guarantee.
- **Do not build a custom focus-trap.** The existing mobile "More" menu's hand-rolled click-outside/Escape logic works, but it is not a full focus trap (it doesn't prevent Tab from leaving the menu into content behind it) — this is acceptable for a small overflow nav menu, but would be a real accessibility regression for a command palette or a menu with form-like content. The Radix- and `cmdk`-based components should be used specifically *because* they solve this correctly already, rather than extending the simpler hand-rolled pattern to a use case it wasn't built for.

## 6. Accessibility summary

Every interaction described above is a direct consequence of reusing Radix and `cmdk`'s built-in ARIA patterns rather than hand-rolling new keyboard logic — which is also the single biggest accessibility win available here, given the Interactive Product Audit's repeated finding that this app's hand-rolled interactive elements have inconsistent (or missing) keyboard-focus support. The one piece of genuinely new code this capability needs (the global `⌘K`/`Escape` document-level listeners) is small, isolated, and testable independent of any single screen — unlike the per-screen `focus-visible` gaps the audit found, which arose specifically *because* the same pattern had to be manually repeated across many files.

## 7. Explicitly out of scope for V1

- A user-facing "keyboard shortcuts" help screen (e.g., pressing `?` to see a cheat sheet) — a reasonable future addition once there are enough shortcuts to warrant documenting, but three shortcuts (`⌘K`, `Escape`, arrow keys inherited from library primitives) don't yet justify a dedicated help surface.
- Customizable/rebindable shortcuts — no product requirement identified for this; would add real complexity (a preferences store, per `ProfileMenuDesign.md` §1's finding that no preferences system exists yet) for no stated user need.
