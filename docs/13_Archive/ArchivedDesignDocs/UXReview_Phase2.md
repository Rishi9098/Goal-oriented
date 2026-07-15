# UX Review — Phase 2 (Global Command Palette & Search)

**Date:** 2026-07-08

| Requirement | Behavior |
|---|---|
| ⌘K (Mac) | Global listener (`AppShell`), opens/toggles the palette from any screen |
| Ctrl+K (Windows/Linux) | Same listener, `e.ctrlKey` branch |
| Esc | Provided by `CommandDialog`'s underlying Radix `Dialog` — closes and returns focus to whatever triggered it (the header search bar element, or nothing if opened via keyboard shortcut from elsewhere, in which case focus returns to `document.body`'s prior focus target per Radix default) |
| Arrow navigation | Provided by `cmdk`'s `Command`/`CommandList` — Up/Down moves selection across all visible groups as one continuous list |
| Enter | Activates the selected item — navigates (Pages, entity results) or runs the action (Quick Actions) |
| Mouse | Every `CommandItem` is clickable; hover highlights via the existing `data-[selected=true]` styling already in `command.tsx` |
| Touch | Same `CommandItem` elements; no mouse-only affordances used (no hover-only reveal) |
| Recent searches | Shown as a "Recent" group when the input is empty and history exists; each entry re-runs that query when clicked |
| Empty state (no query yet) | "Recent" (if any) + "Pages" + "Quick Actions" groups — never a blank palette |
| Loading state | Per-group: if a still-`enabled`-but-pending query hasn't resolved yet, that one group shows a lightweight skeleton row; other groups (already cached, or static) render immediately — matches `GlobalSearchDesign.md` §7's original design exactly |
| No-results state | A single, honest "No results for '{query}'" row (`CommandEmpty`) — never an unexplained blank list |
| Reachability on mobile | The header search element (visible at all viewports once un-hidden from today's `hidden md:flex`) is tappable to open the same palette — `⌘K`/`Ctrl+K` isn't usable on a touch keyboard, so a visible tap target is required, not just the shortcut |

**Honesty note carried from the Architecture Review:** selecting a specific Goal/Scheme/Policy result navigates to that entity's *list page*, not a deep-linked detail view (no such URL-addressable view exists yet for those three). This is stated plainly in each result's subtext (e.g., "Goal · view in Goals") rather than implied as a precise jump — consistent with UX Principle #7 ("honesty over polish when the two conflict"). Family Member results are the exception and do jump to the exact member.

**Proceeding to Implementation.**
