# User Trust Review — Milestone 2.1-P3 (Accessibility Polish)

**Date:** 2026-07-07

## Who this finding is for

Keyboard-only users and screen-reader users navigating the Insurance, Recommendations, Goals, and Member Detail screens — previously, tabbing through these screens gave no visible indication of which control had focus, making it genuinely difficult to know what pressing Enter would activate. This is a real, if quiet, exclusion: a sighted mouse user never noticed the gap because hover states worked correctly; a keyboard-only user hit it on every one of these screens.

## Does fixing this change anything for existing (mouse) users?

No — `focus-visible` (as opposed to plain `:focus`) only ever renders when the browser determines the element was focused via keyboard navigation, not via a mouse click. Mouse users see zero visual change from this fix; keyboard users gain a ring that was already present and working correctly on every other screen in the product.

## Consistency with the product's existing trust posture

This closes the one remaining inconsistency in an otherwise well-applied pattern — Task 12 and the Schemes screen already did this correctly; the earlier screens simply hadn't caught up. No new promise is made; an existing, already-correct standard is now applied everywhere it should have been from the start.
