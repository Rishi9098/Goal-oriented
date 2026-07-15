# Dead Click Report — Northstar

**Date:** 2026-07-08
**Definition used:** an element that visually presents as interactive (button styling, hover state, cursor change, or a label implying an action) but has no attached handler, no wired navigation, or no reachable destination. This report lists **only** confirmed dead clicks — each verified by direct code trace (absence of `onClick`/`href`/`<Link>` target, or a target that resolves to nothing).

---

## Confirmed dead clicks

### 1. Global Search bar
- **Screen:** Every authenticated screen (`components/app-shell.tsx`, header)
- **Presents as:** A bordered, padded box with a search icon, placeholder text ("Search goals, holdings, reports…"), and a "⌘K" keyboard-shortcut hint — every visual signal of a functioning search trigger.
- **Actual element:** A plain `<div>`. No `<input>`. No `onClick`. No keyboard event listener for `⌘K`/`Ctrl+K` exists anywhere in the entire frontend codebase (confirmed via exhaustive grep for `metaKey`, `ctrlKey`, and the literal key `"k"`).
- **Frontend handler exists:** No · **API exists:** No · **Backend exists:** No · **Classification:** Never implemented — pure visual mock left in from an early design pass.

### 2. Notification bell
- **Screen:** Every authenticated screen (header)
- **Presents as:** A bordered icon button with an unread-indicator dot.
- **Actual element:** `<button>` with **no `onClick` attribute at all**. The unread dot renders unconditionally (not tied to any real notification count) and can never be opened, read, or dismissed.
- **Frontend handler exists:** No · **API exists:** No · **Backend exists:** No (no notification model, table, or endpoint exists anywhere in the backend) · **Classification:** Never implemented.

### 3. Avatar (top-right)
- **Screen:** Every authenticated screen (header)
- **Presents as:** A circular avatar bubble with the user's initials, in the position a profile/account menu trigger conventionally occupies.
- **Actual element:** A plain `<div>` — not a `<button>`, no `onClick`, no `aria-haspopup`, no dropdown of any kind. There is no menu to open; clicking does precisely nothing.
- **Classification:** Never implemented. The "Profile Avatar Menu" named in this audit's special-attention list does not exist in any form.

### 4. Dashboard goal preview cards
- **Screen:** Dashboard (`app.index.tsx`)
- **Presents as:** Cards with a hover-triggered border-color change (`hover:border-border-strong`), the same visual affordance the Goals page uses on its own, fully-clickable goal cards.
- **Actual element:** A plain `<div>` with no `onClick` and no `<Link>` wrapper.
- **Classification:** Partially implemented — the display half of the pattern was built, the interaction half was not.

### 5. Landing page — "Security" nav anchor
- **Screen:** Landing page, top navigation
- **Presents as:** A nav link styled identically to the other three (working) nav links.
- **Actual element:** `href="#trust"` — no element with `id="trust"` exists anywhere in the page's DOM. Clicking scrolls nowhere and changes the URL hash to a target that resolves to nothing.
- **Classification:** Orphaned — the section this once pointed to was either removed or never built.

### 6. Landing page — footer legal links
- **Screen:** Landing page, footer
- **Presents as:** Three standard-looking footer links: Privacy, Terms, Disclosures.
- **Actual element:** All three are `href="#"`.
- **Classification:** Never implemented — no legal-page content or routes exist for any of the three.

---

## Borderline cases (reviewed, not classified as dead clicks)

- **"View live demo" (landing page):** technically navigates (to `/app`) and the navigation "succeeds" in the sense that a redirect fires — this is a **misleading-affordance** issue, not a dead click, and is covered in `BrokenInteractionReport.md` instead.
- **Reports "Export PDF":** triggers a real, working browser action (`window.print()`) — not dead, just mislabeled. Covered in `BrokenInteractionReport.md`.
- **AI Copilot suggestion buttons, goal-card "Simulate" icon, all Family-module links:** all confirmed to have real, working handlers — not included here.

## Root-cause pattern across all six dead clicks

Every dead click in this report belongs to one of two categories:
1. **Global-shell decoration that was designed but never wired** (Search, Notifications, Avatar) — these three sit in the app's most-viewed real estate (every single screen) and were evidently built for visual completeness during initial scaffolding, with the intention of wiring them up later.
2. **Marketing-site orphans** (Security anchor, footer links) — content/pages that were planned in the nav/footer structure but never actually built.

No dead click was found inside any of the actual product's certified, tested feature areas (Goals, Family, Insurance, Recommendations, Schemes, Reports, Settings, onboarding) — every dead click is either global chrome or unauthenticated marketing surface.
