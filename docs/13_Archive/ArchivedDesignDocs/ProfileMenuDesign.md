# Profile Menu — Design

**Date:** 2026-07-08
**Status:** Design only. No code written.
**Depends on:** `GlobalShellArchitecture.md`

---

## 0. A concrete gap this closes, not just a UX nicety

Investigating "mobile behavior" surfaced a real, previously-unflagged functional gap: **on mobile viewports, there is currently no way to sign out at all.** The working "Sign out" button lives inside `<aside className="hidden lg:flex ...">` — the desktop sidebar, entirely hidden below the `lg` breakpoint. The mobile bottom nav's "More" overflow menu (`MOBILE_MORE = ["/app/reports", "/app/profile", "/app/settings"]`) does not include sign-out anywhere. A mobile user who wants to sign out has no UI path to do so. **The Profile Menu is not optional polish — it is the fix for a real, currently-missing capability**, and should be scoped and prioritized accordingly in `GlobalShellImplementationPlan.md`.

## 1. Menu contents

| Item | Destination/action | Justification |
|---|---|---|
| **Identity header** (name, email, avatar) | Display only, no action | Matches the existing pattern on the Profile page itself; confirms "who am I signed in as" before the user picks an action — standard, low-risk, zero new data (already fetched for the header avatar today) |
| **Profile** | Navigate to `/app/profile` (existing, working page) | Direct shortcut to the one place account details live today |
| **Settings** | Navigate to `/app/settings` (existing, working page) | Same rationale |
| **AI Settings** | **Not included in V1 — see §2** | |
| **Theme** | **Not included — see §3** | |
| **Sign out** | Reuse the exact existing `handleSignOut` handler already in `app-shell.tsx` (calls `auth.logout()`, clears the token, navigates to sign-in) | Already correct and tested; this design only asks for a **second entry point** to it, not a new implementation. The existing sidebar button is unaffected/kept as-is for desktop |

**Deliberately excluded, and why:** "Preferences" was named as an investigation area but has no concrete content to populate it with — there is no user-configurable app-wide preference anywhere in the current product (no notification cadence setting, no default risk-profile setting, no language toggle). Adding a "Preferences" menu item with nothing behind it would repeat the exact mistake this whole review exists to catch (a menu that looks functional but leads nowhere). If a real preference is identified later, it should first get a home on the Settings page (following that page's own established "Coming soon" card pattern) before earning a dedicated top-level Profile Menu entry.

## 2. "AI Settings" — investigated, deliberately deferred

There is currently nothing to configure about the AI Copilot: no model choice, no response-length preference, no data-sharing toggle, no memory/reset control — `app.copilot.tsx` has zero settings surface today, and (per this session's separate AI Assistant Research documents) even the *planned* local-model architecture doesn't introduce user-facing settings until a later roadmap version (conversation memory, tool-category toggles). Recommendation: **do not add an "AI Settings" menu item in this phase.** When real AI-related settings exist, they should first appear as a card on the Settings page (matching the honest, established "Coming soon" → real-card pattern already used for Notifications and Linked Accounts there), and only then, if it grows into enough content to warrant a dedicated screen, earn a Profile Menu shortcut. Adding the menu item ahead of the content would recreate exactly the "menu item that goes nowhere" problem the Interactive Product Audit exists to catch.

## 3. Theme — a direct conflict with an explicit project decision

`styles.css` defines `.dark { /* same; app is dark by default */ }` — an intentionally empty override, confirming Northstar is a **single-theme, dark-only product by deliberate design choice**, and `CLAUDE.md` separately instructs: *"Never change the UI design system... frozen palette."* A functional light/dark theme toggle in the Profile Menu would directly contradict both.

**Recommendation: do not build a theme toggle.** If product direction changes in the future and a light theme becomes a real initiative, that is a design-system decision requiring its own dedicated review (new token set, contrast audit across every screen, explicit sign-off to un-freeze the palette) — it should not be introduced as a side effect of building a profile menu. This design treats "Theme" as **investigated and declined**, not silently dropped: the reasoning above should be preserved so a future engineer doesn't reach for it as a quick add-on without realizing the constraint.

## 4. Component approach

**Reuse `@radix-ui/react-dropdown-menu` via the already-built `components/ui/dropdown-menu.tsx`** rather than hand-rolling a new menu. Three concrete reasons, grounded in this session's own audit findings:
1. It's already installed and already fully scaffolded — zero new dependency, zero new primitive to design from scratch.
2. Radix's dropdown menu implements the full WAI-ARIA menu pattern out of the box: `role="menu"`/`role="menuitem"`, roving `tabindex`, arrow-key navigation, `Home`/`End`, type-ahead, and `Escape`-to-close, focus-return-to-trigger on close — all the accessibility behavior the Interactive Product Audit found **missing** from this app's several hand-rolled interactive elements (the Goals page, `app.family.add.tsx`'s stray links). Building this menu by hand would risk repeating that exact pattern a third time.
3. It composes cleanly with the shared `GlobalShellProvider` state proposed in `GlobalShellArchitecture.md` (open/closed state, mutual exclusion with Search/Notifications on mobile) via its own controlled `open`/`onOpenChange` props — no fighting the library's state model.

## 5. Accessibility

- The avatar trigger element must become a real `<button>` (it is currently a plain `<div>` — a Dead Click Report finding on its own) with `aria-haspopup="menu"` and `aria-expanded`, which Radix's `DropdownMenuTrigger` provides when applied to a real focusable element — this alone fixes the "no click target at all" defect the audit found, independent of what's inside the menu.
- Focus-visible styling on the trigger and every item, using the same utility class already established and applied consistently across the Family module (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ...`), for consistency with the rest of the app rather than inventing a new focus treatment.
- Sign out being reachable and operable via keyboard alone (Tab to avatar → Enter/Space to open → Arrow keys to Sign out → Enter) is itself a meaningful accessibility fix, since today it is only reachable by a mouse click on a sidebar element that doesn't even render on mobile.

## 6. Mobile behavior

A small anchored dropdown near the top-right corner (Radix's default popover-style positioning) is a poor fit for a mobile screen — hard to reach with a thumb, and visually cramped against the header's edge. **Recommendation: on narrow viewports, render the same menu content inside a bottom sheet instead of a corner dropdown**, using the already-installed `vaul` drawer library and the already-scaffolded `components/ui/drawer.tsx` (same "already have the primitive, never wired it up" situation as `cmdk`/`command.tsx`). This also gives the Profile Menu the same dismiss affordances (swipe-down, backdrop tap, Escape) the existing mobile "More" nav menu already established for a similar overflow-menu use case — visual and interaction consistency with a pattern users have already learned elsewhere in this same app, rather than a fourth bespoke overlay behavior.

## 7. Interaction with other shell overlays

Per `GlobalShellArchitecture.md` §4, opening the Profile Menu should close the Search palette and Notification panel if either is open (and vice versa) on narrow viewports where screen space is genuinely contested; on desktop, where the header has room for the notification bell and avatar to sit side by side, this mutual exclusion is a courtesy rather than a hard requirement, but should still hold for one clear reason: a user is very unlikely to want two overlapping overlays open simultaneously regardless of screen size, and enforcing one-open-at-a-time everywhere is a simpler, more predictable rule than a viewport-conditional one.
