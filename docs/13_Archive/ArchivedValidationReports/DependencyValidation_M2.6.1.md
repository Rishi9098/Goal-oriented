# Dependency Validation — M2.6.1 (Overlay Mutual Exclusion Fix)

**Date:** 2026-07-08
**Scope:** trace exactly why the Profile Menu and Command Palette can be simultaneously open, as the single certification condition requires, before designing a fix.

---

## 1. Profile Menu open state — traced

`app-shell.tsx:223`: `<DropdownMenu>` is rendered with **zero props** — no `open`, no `onOpenChange`, no `defaultOpen`. This is Radix's fully **uncontrolled** mode: `DropdownMenu` owns its own open/closed boolean internally, inside the `@radix-ui/react-dropdown-menu` package, invisible to `AppShell` or any sibling component. `AppShell` has no variable anywhere that reflects whether the profile menu is currently open.

## 2. Command Palette open state — traced

`app-shell.tsx:76`: `const [paletteOpen, setPaletteOpen] = useState(false)`, passed at line 337 as `<GlobalPalette open={paletteOpen} onOpenChange={setPaletteOpen} />`. This is a **controlled** component — `AppShell` fully owns this boolean.

## 3. Notification popover open state — traced

`notification-center.tsx:63`: `const [open, setOpen] = useState(false)`, passed to `<Popover open={open} onOpenChange={setOpen}>` at line 98. This state is controlled, but controlled **locally inside `NotificationCenter` itself** — `AppShell` has no reference to it, the same structural gap as the Profile Menu, just one level further down the tree.

## 4. Keyboard shortcut handling — traced

`app-shell.tsx:84-93`: one `document`-level `keydown` listener, registered once (empty dependency array), checks `(e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"`, and on match calls `setPaletteOpen((v) => !v)` — **only `paletteOpen`**. It has no way to reach into `DropdownMenu`'s internal Radix state (uncontrolled, not exposed) or `NotificationCenter`'s internal `open` state (controlled, but not exposed upward) to close either one. This is the direct, root cause of the certification's finding: the shortcut handler can only affect the one piece of state it was ever given a reference to.

## 5. Overlay lifecycle — traced, and this explains the *inconsistent* behavior the certification observed

The certification found that the notification popover *did* auto-close when the palette opened, but the profile dropdown did *not*. Both are structurally identical from `AppShell`'s point of view (neither is wired to `paletteOpen` in any way) — the difference is entirely inside Radix's own per-primitive default behavior: `Popover`'s default dismiss-on-outside-interaction happened to trigger when `Dialog`'s overlay mounted; `DropdownMenu`'s did not. **This is not a reliable mechanism to depend on** — it is coincidental agreement between two independent libraries' internal heuristics, not a designed guarantee. Relying on it further (e.g., hoping a future third-party component will also cooperate) would be building on an implementation detail, not an architecture.

## 6. Focus management — traced

Each of the three overlays (`Dialog` for the palette, `Popover` for notifications, `DropdownMenu` for the profile menu) independently implements Radix's standard focus-trap-while-open / focus-return-to-trigger-on-close behavior. None of the three currently know about each other's existence. This means: when two are open simultaneously (the certification's reproduced case), there are **two independent focus traps active at once** — whichever mounted more recently wins the DOM's actual focus, while the older one's trap is now silently inert (its trigger is no longer where focus will return to, since the newer overlay is what's actually holding focus). This is a real, if subtle, second consequence of the same root cause, worth fixing for the same reason as the visual overlap.

## 7. Conclusion — exactly why both can coexist, confirmed

**There is no shared state anywhere that all four overlays (palette, notifications, profile menu, mobile "More" sheet) participate in.** Two of the four (`paletteOpen`, `moreOpen`) are controlled by `AppShell`; one (`NotificationCenter`'s `open`) is controlled one level below `AppShell` and never lifted; one (`DropdownMenu`) is fully uncontrolled and invisible to the entire React tree above it. The keyboard shortcut handler can only toggle the one state variable it was written against (`paletteOpen`). No amount of tweaking the shortcut handler alone can fix this — the profile menu's open state must first become *visible* to something that can close it, exactly as `paletteOpen` and `moreOpen` already are, and the notification popover's state must be *lifted* to the same place.

**No incorrect assumption found. No stop condition triggered.** The fix requires: (a) lifting `NotificationCenter`'s `open` state up into `AppShell` (mirroring the pattern `GlobalPalette` already uses — controlled via props, not a new pattern), and (b) making the profile `DropdownMenu` controlled for the first time (also via `open`/`onOpenChange`, the same Radix-standard mechanism, not a new one). **Proceeding to Architecture Review.**
