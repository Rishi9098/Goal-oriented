# PR Report — Global Shell Phase 1 (Profile Avatar Menu & Mobile Sign-out)

**Date:** 2026-07-08
**Scope:** Phase 1 of `GlobalShellImplementationPlan.md` — the Profile Avatar Menu, and the mobile sign-out gap it closes. No Search, Notifications, Keyboard Shortcuts, Theme, or AI work included.

---

## Summary

The header avatar was a plain, non-interactive `<div>` (confirmed dead in the Interactive Product Audit) — and because the only working "Sign out" control lived inside the desktop-only sidebar, mobile users had no way to sign out at all. This phase turns the avatar into a real, keyboard-operable `DropdownMenu` trigger (reusing the existing, previously-unused `components/ui/dropdown-menu.tsx` scaffold) exposing exactly three real, working actions: My Profile, Settings, Sign Out — nothing invented, nothing placeholder.

## Pipeline

1. **Dependency Validation** (`DependencyValidation_Phase1.md`) — verified current auth state, logout flow, avatar markup, the unused dropdown-menu/drawer scaffolds, and both nav surfaces directly against source. One correction made to the brief's framing: no `AuthContext`/`AuthProvider` exists anywhere in the app — "auth state" is `localStorage` plus the `["currentUser"]` React Query cache Phase 0 introduced inside `AppShell` itself, which this phase reads directly rather than via a separate context object.
2. **Design Review** (`DesignReview_Phase1.md`) — one deliberate, documented deviation from the earlier `ProfileMenuDesign.md`: a single `DropdownMenu` is used at every viewport (not a Dropdown-on-desktop/Drawer-on-mobile split), specifically because this phase's own instructions require "no duplicate menu infrastructure." The avatar lives in the shared header (rendered at all viewports, not just desktop), so one implementation closes the mobile gap without a second component tree. Radix's built-in collision avoidance keeps the menu on-screen at any width.
3. **Architecture** — confirmed reuse of the existing `dropdown-menu.tsx` (zero new dependencies), the existing `handleSignOut()` (zero new logout logic), and `AppShell`'s already-fetched `currentUser`/`initials` (zero new data fetch).
4. **Implementation** — see Files Changed below.
5. **Accessibility** — provided entirely by Radix's `DropdownMenu` primitive: full keyboard operation (Tab to trigger, Enter/Space to open, arrow keys to navigate, Enter/Space to activate, Escape to close), automatic focus management (focus enters the menu on open, returns to the trigger on close), and outside-click dismissal — none of it hand-built.
6. **Live verification** — see below.

## Files Changed

| File | Change |
|---|---|
| `code/src/components/app-shell.tsx` | Header avatar `<div>` replaced with a `DropdownMenu`/`DropdownMenuTrigger` (`asChild`, wrapping a real `<button>` with identical visual styling) and `DropdownMenuContent` containing an identity header (name + email, from the already-fetched `currentUser`), "My Profile" and "Settings" (`DropdownMenuItem asChild` wrapping `<Link>`), a separator, and "Sign Out" (`onSelect={handleSignOut}`, the exact existing handler the sidebar button already used). |

## Live Verification (performed this session, against the real running app)

- Registered and signed in with a fresh test account.
- **At an 809px viewport (below the `lg` sidebar breakpoint — i.e., the mobile layout)**: clicked the avatar → menu opened showing the identity header, My Profile, Settings, Sign Out, positioned correctly on-screen (right-aligned, no overflow).
- **Keyboard-only path**: `Escape` closed the menu and returned visible focus to the avatar trigger (confirmed via screenshot — a focus ring rendered on the avatar button). `Enter` reopened the menu with the first item auto-focused; `ArrowDown` twice moved focus to "Sign Out"; `Enter` activated it.
- **Sign-out correctness**: activating "Sign Out" via keyboard navigated to `/auth/sign-in`; confirmed via `localStorage.getItem("ns_access_token")` returning `null` — the session was genuinely cleared, not just visually redirected.
- **Login again / session reset**: signed back in with the same account; dashboard loaded correctly with the same identity (avatar initials matched), confirming no lingering bad state from the sign-out.
- **Not yet screenshotted in this pass:** a genuine ≥1024px desktop-width view of the open menu (a window-resize step was interrupted mid-session). This is a low-risk gap, not a skipped requirement: per the Design Review's own reasoning, this phase deliberately uses **one** code path with no viewport-conditional branching, so the desktop-width render is not a logically distinct implementation to verify — it is the same component tree already confirmed working at 809px, with Radix's viewport-agnostic collision avoidance. Flagged here explicitly rather than silently assumed; recommend a quick confirmatory screenshot at the start of Phase 2's live verification pass, since that work will already have the browser open.

## Regression Testing

`tsc --noEmit`: clean. `eslint` (scoped to the touched file): 0 errors, 0 warnings. No backend files touched — full backend suite unaffected (last run: 330/330 passing, from Phase 0's verification, no backend changes since).

## First-Time User Review

The avatar is in its conventional, expected top-right position; clicking it reveals a standard, immediately-legible identity-menu pattern (name, email, then actions) that any user familiar with modern web apps will recognize without instruction. My Profile and Settings labels match the sidebar's own nav labels exactly (no naming inconsistency to relearn). Sign Out is the last, clearly-separated item, matching the universal convention of "sign out is always at the bottom."

## Product Consistency Review

Menu styling uses only existing design tokens (`bg-popover`, `text-popover-foreground`, `border`, the app's established focus-visible ring utility) — no new colors or spacing introduced, consistent with the frozen design system. "Sign Out" is styled neutrally (matching the existing sidebar button), not as a destructive/red action — consistent with this app's existing visual language, where red is reserved for genuinely destructive actions (e.g., Settings' "Delete account").

## Known, Out-of-Scope (Not Fixed Here)

The desktop sidebar's own standalone "Sign out" button remains, unchanged — a second, equally valid path to the same action, not a duplicate menu system (it's a permanent nav element, not a menu). Not removed, since doing so wasn't asked for and isn't necessary now that the avatar menu exists everywhere.

## Rollback

Revert the one changed section of `app-shell.tsx`. No new dependencies, no migration, no API change.

---

## Success Criteria

- [x] Avatar opens a menu
- [x] Mobile users can sign out (verified at an 809px viewport — below the sidebar breakpoint)
- [x] No duplicate menu systems (one `DropdownMenu`, one code path, all viewports)
- [x] No placeholder functionality (My Profile / Settings / Sign Out only — all three real and working)
- [x] Zero regressions (tsc/eslint clean; sign-out/re-login flow verified end-to-end)

**Stopping here per instruction. Phase 2 (Global Command Palette & Search) begins next, per direction.**
