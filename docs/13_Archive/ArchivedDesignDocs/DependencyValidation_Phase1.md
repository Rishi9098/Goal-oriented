# Dependency Validation — Phase 1 (Profile Avatar Menu & Mobile Sign-out)

**Date:** 2026-07-08
**Scope:** Verify every assumption this phase depends on, against current source, before implementation.

---

## 1. Current auth state — one correction to the brief's framing

**There is no `AuthContext`/`AuthProvider` anywhere in this codebase** (confirmed by exhaustive search for `createContext`/`AuthProvider`/`AuthContext` across every route, component, and lib file — the only `createContext` call in the app is `shell-title.ts`'s unrelated title-override channel, introduced in Phase 0). "Auth state" today is two independent things:

1. **Session presence**: `localStorage.getItem("ns_access_token")`, checked by `app.tsx`'s route guard.
2. **Current user identity**: `useQuery(["currentUser"], () => auth.me())`, introduced inside `AppShell` in Phase 0 — this already computes `currentUser` and `initials` as local variables in the exact component the new menu will live in.

**Correction for this phase:** "reuse existing auth context" (per this task's Architecture Review instruction) should be read as *reuse `AppShell`'s already-computed `currentUser`/`initials`* — no separate context object exists to reuse, and none needs to be created; the menu is a sibling of the avatar inside the same component, so it can read these same local variables directly. This is not a blocking issue — it's a more direct integration than a context would even provide — but it is flagged here since the instruction's phrasing assumed something that doesn't exist.

## 2. Logout flow — confirmed working, to be reused verbatim

`AppShell.handleSignOut()` (current code):
```ts
function handleSignOut() {
  void auth.logout();       // POST /auth/logout, best-effort, errors swallowed
  clearAccessToken();       // removes ns_access_token from localStorage
  navigate({ to: "/auth/sign-in", replace: true });
}
```
Confirmed in `src/lib/api.ts`: `auth.logout()` and `clearAccessToken()` both exist and are exactly what the desktop sidebar's existing, working "Sign out" button already calls. **This phase reuses this exact function for both the desktop menu and the new mobile menu — no new logout logic.**

## 3. Avatar component — confirmed as the Dead Click Report described

Current header avatar (`app-shell.tsx`, header section): a plain `<div className="h-9 w-9 rounded-full ...">{initials}</div>` — not a `<button>`, no `onClick`, no `aria-haspopup`. Exactly matches `DeadClickReport.md` item #3. This phase's job is to turn this into a real, keyboard-operable trigger.

## 4. Existing dropdown-menu component — confirmed present, unused, fully built

`code/src/components/ui/dropdown-menu.tsx` wraps `@radix-ui/react-dropdown-menu` (confirmed installed: `"@radix-ui/react-dropdown-menu": "^2.1.16"` in `package.json`) with `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator`, `DropdownMenuLabel` all exported and already styled to match the app's design tokens. Zero import sites anywhere in the app today (confirmed in the original Interactive Product Audit and re-confirmed now) — this phase is its first real use, not a new component.

## 5. Existing drawer component — confirmed present, unused, fully built

`code/src/components/ui/drawer.tsx` wraps `vaul` (confirmed installed: `"vaul": "^1.1.2"`) with `Drawer`, `DrawerTrigger`, `DrawerContent`, `DrawerHeader`, `DrawerClose`, etc. — the mobile bottom-sheet primitive `ProfileMenuDesign.md` §6 specified for mobile. Also zero import sites today.

## 6. Mobile navigation — confirmed the gap is real and exactly as scoped

`MOBILE_PRIMARY = ["/app", "/app/goals", "/app/family", "/app/copilot"]` and `MOBILE_MORE = ["/app/reports", "/app/profile", "/app/settings"]` — the mobile bottom nav's "More" overflow menu lists exactly these three routes and **nothing else**; there is no sign-out control anywhere in the mobile-viewport DOM (the desktop sign-out button lives inside `<aside className="hidden lg:flex ...">`, `display: none` below the `lg` breakpoint). Re-confirmed: `app.settings.tsx` has no sign-out control either (Change Password / two Coming Soon cards / Delete Account only). **Mobile users genuinely cannot sign out today, exactly as `ProfileMenuDesign.md` §0 documented.**

## 7. Desktop navigation — confirmed, will be extended, not replaced

The desktop sidebar's own "Sign out" button (`<aside>`, line ~170) is real, working, and **out of scope to remove** — the new Profile Menu adds a second, equally-valid path to sign out (useful once the header's avatar becomes a real menu everywhere), it does not need to replace the sidebar's existing button. Confirmed no conflict: having two working sign-out affordances (sidebar button + avatar menu) is not a duplicate-menu-system problem, since the sidebar button is a permanent nav element, not a menu.

## 8. Menu content — verified against what actually exists (no placeholders)

Per the instruction's explicit "menu items should only expose functionality that actually exists today":

| Candidate item | Exists today? | Include? |
|---|---|---|
| My Profile → `/app/profile` | Yes, fully working (Interactive Product Audit: ✓) | ✅ |
| Settings → `/app/settings` | Yes, fully working | ✅ |
| Sign Out | Yes, working (`handleSignOut`) | ✅ |
| AI Settings | No settings surface exists for the Copilot anywhere | ❌ Correctly omitted, per `ProfileMenuDesign.md` §2 |
| Theme toggle | No theme system exists; `.dark {}` is intentionally empty (single dark theme by design) | ❌ Correctly omitted, per `ProfileMenuDesign.md` §3 |
| Preferences | No app-wide preference of any kind exists | ❌ Correctly omitted |

This matches the instruction's own suggested menu (My Profile / Settings / Sign Out) exactly — confirmed independently against the codebase rather than assumed from the instruction.

## Conclusion

One correction made (auth "context" → `AppShell`'s existing `useQuery`-backed local state, not a separate object), no assumption found that blocks proceeding. **No stop condition triggered — proceeding to Design Review.**
