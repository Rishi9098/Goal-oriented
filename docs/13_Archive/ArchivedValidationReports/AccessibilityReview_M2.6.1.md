# Accessibility Review — M2.6.1 (Overlay Mutual Exclusion Fix)

**Date:** 2026-07-08
**Note:** written before implementation, reasoning from the design in `ArchitectureReview_M2.6.1.md`; every claim here is re-checked empirically in Step 6 (Live Verification) against the real running app, not left as a paper guarantee.

---

## Focus trap

Unaffected. Each overlay's focus trap is still implemented entirely by its own Radix primitive (`Dialog`, `Popover`, `DropdownMenu`) — the fix changes only which variable feeds each primitive's `open` prop, never touches the primitives' internal trap logic. The one *improvement*: today, two traps can be active simultaneously (the certification's reproduced bug) with the second, silently-superseded trap left in an inconsistent state. After this fix, at most one trap is ever active, by construction — a strictly safer condition than today, never a worse one.

## Escape

Unaffected in mechanism, improved in outcome. Each primitive still detects `Escape` itself and calls its own `onOpenChange(false)` — this fix only changes where that call writes to (`setActiveOverlay(null)` instead of a local `setOpen(false)`/`setMoreOpen(false)`). The previously-reproduced case (two overlays open, Escape closes them one at a time, topmost first) cannot recur post-fix, since two overlays can no longer both be open to begin with — there is only ever one `Escape` to press.

## Focus return

Unaffected in mechanism (each primitive still returns focus to its own trigger on close, exactly as before), and, per the focus-trap note above, more *reliable* in outcome — with only one overlay ever open, there is no scenario where a second overlay's mount steals focus out from under a first overlay's still-active trap, which is exactly the ambiguous state today's bug can produce.

## Screen readers

No ARIA attribute, role, or label changes anywhere in this fix — `aria-label`, `aria-haspopup`, `aria-expanded` on the mobile "More" button and every other existing accessibility attribute are preserved verbatim; only their driving boolean's source changes (`moreOpen` → `activeOverlay === "more"`), not their presence or values at any given render.

## Keyboard-only flow

Unaffected for reaching and operating any single overlay (`Tab` to trigger, `Enter`/`Space` to open, arrow keys to navigate, `Escape` to close) — all of that is Radix's own behavior, untouched. The flow that *changes* is the specific cross-overlay sequence the certification found broken: opening the profile menu via keyboard, then pressing `⌘K`, will now correctly close the profile menu (its `onOpenChange(false)` fires as `activeOverlay` changes to `"palette"`) before or as the palette opens — verified live in Step 6, not assumed here.

## No regressions anticipated, and why

The fix is a pure "where does this boolean live" change — no primitive's props beyond `open`/`onOpenChange` are touched, no new DOM elements are introduced, no existing `aria-*` attribute is removed or renamed, and no click handler's *content* (only its target variable) changes. The single behavior being deliberately changed — two overlays no longer being able to coexist — is precisely the certification's own success criterion, not a side effect to guard against.

**Proceeding to Implementation**, with this review's every claim scheduled for direct re-verification in Step 6.
