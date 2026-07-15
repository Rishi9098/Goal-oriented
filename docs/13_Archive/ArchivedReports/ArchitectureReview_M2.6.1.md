# Architecture Review — M2.6.1 (Overlay Mutual Exclusion Fix)

**Date:** 2026-07-08

---

## The mechanism: one discriminated-union state, owned where the shortcut handler already lives

Replace the two independent booleans `AppShell` already owns (`paletteOpen`, `moreOpen`) and the two it doesn't (`NotificationCenter`'s local `open`, `DropdownMenu`'s fully-uncontrolled internal state) with **one** state variable in `AppShell`:

```ts
type ActiveOverlay = "palette" | "notifications" | "profile" | "more" | null;
const [activeOverlay, setActiveOverlay] = useState<ActiveOverlay>(null);
```

Every overlay becomes a **controlled** read of this one variable (`isOpen = activeOverlay === "x"`) and every open/close action becomes a **write** to it (`setActiveOverlay("x")` to open, `setActiveOverlay(null)` to close). Because it is a single variable that can only hold one value, **it is structurally impossible for two overlays to both read `true` at once** — this is a type-level guarantee, not a runtime check that could be forgotten or raced.

## Why this satisfies every stated requirement

- **Only one global overlay may be open at a time:** guaranteed by construction (one variable, one value) — not by a convention every future call site has to remember to honor.
- **Opening one overlay closes any other:** `setActiveOverlay("palette")` doesn't need to separately know to close the other three — whichever one currently reads `activeOverlay === "profile"` (for example) will simply now read `false`, on the very next render, automatically.
- **Escape behavior remains correct:** unchanged. Each of `Dialog` (palette), `Popover` (notifications), and `DropdownMenu` (profile) still detects `Escape` itself, exactly as before — the only change is *where the resulting `onOpenChange(false)` call writes to*. Radix's own Escape handling is not touched, wrapped, or duplicated.
- **Focus return remains correct:** same reasoning — each primitive's own focus-trap/return logic is untouched. The one behavior this *actively fixes* (not just preserves) is the dependency validation's finding #6: with only one overlay ever open, there is only ever one focus trap active, eliminating the "two silent, competing traps" scenario the current bug produces.
- **No duplicate state:** the opposite of the current situation — four independent booleans (two visible to `AppShell`, one hidden inside `NotificationCenter`, one hidden inside Radix's own `DropdownMenu` internals) become one.
- **No global event bus:** not needed. `AppShell` is already the common ancestor of all four overlays (it renders the palette, the notification center, the profile dropdown, and the mobile sheet directly or as immediate children) — lifting state to a common ancestor already-in-the-tree is the plain "lift state up" pattern this codebase uses everywhere else (`GlobalPalette` already receives `open`/`onOpenChange` this exact way), not a new architectural concept.
- **Reuses existing architecture:** `GlobalPalette`'s controlled-component contract (`{ open: boolean; onOpenChange: (open: boolean) => void }`) is extended to `NotificationCenter` (which needs to accept these as props instead of managing them internally) and to the profile `DropdownMenu` (which needs `open`/`onOpenChange` added — Radix's own standard controlled-mode props, already used for `GlobalPalette`'s underlying `Dialog` and about to be used for `Popover` too).

## What changes, file by file

- **`app-shell.tsx`:** `paletteOpen`/`moreOpen` booleans replaced by `activeOverlay`. The `⌘K` handler toggles `"palette"` instead of a boolean. The mobile "More" button and its click-outside/Escape effect key off `activeOverlay === "more"` instead of `moreOpen`. The `DropdownMenu` gains `open={activeOverlay === "profile"} onOpenChange={(v) => setActiveOverlay(v ? "profile" : null)}`. `NotificationCenter` gains two new props (`open`, `onOpenChange`) wired the same way.
- **`notification-center.tsx`:** drops its internal `useState(false)`; accepts `open`/`onOpenChange` as props instead, passed straight through to its own `<Popover>` exactly as before — the component's internal behavior (queries, mutations, rendering) is completely unchanged, only the *source* of its open boolean moves.
- **`global-palette.tsx`:** no change — it already receives `open`/`onOpenChange` as props; only the value `AppShell` passes in changes shape (derived from `activeOverlay` instead of being its own boolean).

## What does not change (explicitly, per this task's scope)

Search behavior, notification content/read/dismiss logic, profile menu contents, routing, navigation, theme, and AI are untouched — every line of the diff is either a rename (`paletteOpen`/`moreOpen` → `activeOverlay` comparisons) or a prop being threaded through where a `useState` used to live locally. No new dependency, no new file beyond this review's own documentation, no schema/backend change (this is a pure frontend fix).

## Conclusion

One `activeOverlay` state, owned by `AppShell` (already the natural common ancestor and already the owner of two of the four overlay booleans), with `NotificationCenter` and the profile `DropdownMenu` becoming controlled components using the exact pattern `GlobalPalette` already established. **Proceeding to Accessibility Review.**
