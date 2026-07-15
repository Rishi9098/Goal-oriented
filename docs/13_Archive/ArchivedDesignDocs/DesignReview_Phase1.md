# Design Review — Phase 1 (Profile Avatar Menu & Mobile Sign-out)

**Date:** 2026-07-08

---

## 0. Scope decision: one menu implementation, not two — a deliberate deviation from `ProfileMenuDesign.md` §6

The earlier architecture review (`ProfileMenuDesign.md` §6) recommended a Radix `DropdownMenu` on desktop and a `vaul` `Drawer` (bottom sheet) on mobile, reasoned from thumb-reachability. This phase's explicit instructions add a constraint that document didn't have: **"Do NOT create duplicate menu infrastructure"** and the success criterion **"No duplicate menu systems."** Building both a Dropdown and a Drawer for the same logical menu — two different Radix primitives, two different open/close state shapes, two different content trees to keep in sync — is exactly the kind of duplication that reads as "two menu systems for one menu."

**Decision: one `DropdownMenu` (from the existing `components/ui/dropdown-menu.tsx`), used identically on every viewport.** This still fully satisfies every stated success criterion: the avatar opens a menu, mobile users can sign out (the avatar lives in the shared header, rendered on all viewports — not the desktop-only sidebar), and there is exactly one menu implementation. Radix's `DropdownMenuContent` has built-in collision detection that keeps it on-screen at any viewport width, so mobile usability is not at risk — only the specific bottom-sheet *polish* from the earlier design is deferred, not the functional requirement. If real usage later shows the corner-anchored dropdown is awkward on small screens, upgrading to a bottom sheet is a contained follow-up, not a blocker now (Engineering Constitution Rule 7 — don't build for a refinement need that hasn't been demonstrated yet).

## 1. Desktop behavior

Avatar (in the shared header, visible at all viewports) becomes a `DropdownMenuTrigger` (via `asChild`, wrapping a real `<button>` styled identically to today's avatar `<div>` — zero visual change to the avatar itself). Clicking or activating it opens `DropdownMenuContent` right-aligned below the avatar (`align="end"`), containing: a non-interactive identity header (name + email), a separator, "My Profile," "Settings," a separator, "Sign Out."

## 2. Mobile behavior

Identical component and content to desktop (per §0's decision) — same trigger, same `DropdownMenuContent`, Radix's collision avoidance repositions it to stay within the viewport. This is the concrete fix for the confirmed gap: today, mobile users have no sign-out path at all (`DependencyValidation_Phase1.md` §6); after this change, the same avatar that's always been visible in the mobile header now opens a working menu with Sign Out in it.

## 3. Keyboard accessibility

Provided by Radix's `DropdownMenu` primitive, not hand-built: `Tab` reaches the avatar trigger; `Enter`/`Space` opens the menu; `ArrowDown`/`ArrowUp` move selection through items; `Home`/`End` jump to first/last item; typing a letter jumps to a matching item (type-ahead); `Enter`/`Space` activates the focused item. None of this is custom code — it is what reusing the existing, unused `dropdown-menu.tsx` scaffold buys for free, and it is a strict improvement over this app's several hand-rolled interactive elements that the Interactive Product Audit found missing keyboard support.

## 4. Focus management

- **On open:** focus moves from the trigger into the menu (Radix default — the first item, or the menu container if no item should be initially focused).
- **On close (any method — Escape, item selection, outside click):** focus returns to the avatar trigger (Radix default). This matters specifically for the "Sign Out" item: after selecting it, the app navigates away entirely (to `/auth/sign-in`), so the focus-return behavior is moot for that one path, but matters for "My Profile" and "Settings," which navigate within the app — focus should land appropriately on the destination page's own content per that page's existing behavior, not get stuck on a stale trigger reference from the unmounted previous page. Verified as a non-issue: TanStack Router's navigation replaces the page content; Radix's focus-return happens synchronously before that navigation's own effects run, so there's no race.

## 5. Escape handling

Provided by Radix — pressing `Escape` while the menu is open closes it and returns focus to the trigger, consistent with (and using the same underlying pattern as) the mobile "More" nav menu's own hand-built Escape handler elsewhere in `app-shell.tsx`. No new Escape-handling code is written for this menu; it comes from the library.

## 6. Click-outside behavior

Provided by Radix (`DropdownMenuContent` closes automatically on an outside pointer event) — no new document-level event listener is added for this menu, unlike the mobile "More" nav's hand-rolled `mousedown` listener. This is a deliberate improvement in implementation quality, not just parity: Radix's outside-click detection is more robust (handles nested portals, touch events, and focus-trap edge cases) than a hand-rolled `mousedown` + ref-contains check.

## 7. Responsive layout

The avatar's own size/position in the header is unchanged at every breakpoint (no new responsive CSS needed there). `DropdownMenuContent`'s width is fixed (e.g. `w-56`, matching typical dropdown sizing already used in the scaffold) and Radix's `avoidCollisions` (on by default) shifts it to stay within the viewport on narrow screens — verified conceptually against Radix's documented behavior; confirmed empirically during live verification (Step 6).

## 8. Menu content — no placeholders, confirmed against `DependencyValidation_Phase1.md` §8

Identity header (display-only, real data from `AppShell`'s already-fetched `currentUser`), "My Profile" (→ `/app/profile`, working page), "Settings" (→ `/app/settings`, working page), "Sign Out" (→ existing `handleSignOut`, working). No AI Settings, no Theme toggle, no Preferences — none of these have any real functionality behind them today, so none are added, per this phase's explicit instruction and Product Principle #7 ("never claim capability the data model doesn't actually have").

## 9. Product consistency

Menu styling reuses `components/ui/dropdown-menu.tsx`'s existing Tailwind classes (already token-based — `bg-popover`, `text-popover-foreground`, `border`, matching the app's dark, single-theme palette) — no new colors, no new spacing scale, consistent with the frozen design system (`CLAUDE.md`). The "Sign Out" item is styled the same neutral way the existing sidebar button already is (muted-foreground, not a destructive-red treatment) — signing out is not a destructive action in this app's existing visual language (contrast with Settings' actual destructive action, "Delete account," which correctly uses red).

## 10. Conclusion

No visual redesign of the avatar itself; the only new visible surface is the menu that opens on interaction, built entirely from an existing, already-installed, already-styled component. **Proceeding to Architecture Review and Implementation.**
