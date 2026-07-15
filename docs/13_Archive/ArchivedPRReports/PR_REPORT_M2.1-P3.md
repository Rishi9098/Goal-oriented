# PR Report — Milestone 2.1 (Accessibility Polish)

**Date:** 2026-07-08
**Source:** `Milestone2CertificationReport.md` §5/§13 — `focus-visible` styling missing on Tasks 10/11's screens.
**Note on numbering:** instructed as "P2," matching the label already used for Insurance Audit Logging. This report and its companion documents use the `M2.1-P3` file suffix purely to avoid collision — referred to by name ("Accessibility Polish") throughout.

## Summary

Added visible keyboard-focus indicators to every interactive element across the Family module that was missing them. The Certification named Tasks 10/11 specifically; direct file inspection during Dependency Validation found the actual gap was broader — 24 elements across 6 files, spanning Tasks 5 through 11. Every fix reuses the exact same existing `focus-visible:` utility-class string already established by Task 12 and the Schemes screen — no new pattern, no layout change, no logic change.

## Review Pipeline

1. **Dependency Validation** (`DependencyValidation_M2.1-P3.md`) — inventoried the full gap by direct file reads (not trusting the Certification's two named examples alone): `app.family.insurance.tsx` (6 elements + 1 `<summary>`), `app.family.recommendations.tsx` (2 + 1 `<summary>`), `app.family.goals.tsx` (5), `app.family.members.$id.tsx` (7), `FamilyMemberForm.tsx` (1, shared by 2 routes), `app.family.index.tsx` (3). Explicitly scoped out the shared `field-input` CSS utility (app-wide, not Family-specific — flagged separately, not fixed).
2. **Root Cause Analysis** (`RootCauseAnalysis_M2.1-P3.md`) — confirmed a pure, inconsistent-execution styling gap, not a logic or design defect; every element was already correctly keyboard-focusable by the browser, only the visible indicator was missing.
3. **Accessibility Review** (`AccessibilityReview_M2.1-P3.md`) — verified focus order is unchanged (no DOM reordering, `className`-only edits), every control is already keyboard-reachable (no `<div onClick>` pattern anywhere in the module), screen-reader labels were already correct (checked incidentally, no gap found), and color-never-alone was already correctly handled on the Parents card and Schemes buckets.
4. **User Trust Review** (`UserTrustReview_M2.1-P3.md`) — confirmed the fix is invisible to mouse users (`:focus-visible` only renders on keyboard-detected focus) and a real, if quiet, gain for keyboard/screen-reader users.
5. **Design Review** (`DesignReview_M2.1-P3.md`) — one existing utility-class string applied everywhere; no new convention invented.
6. **Implementation** — 24 `className` additions across 6 files. Fixing `FamilyMemberForm`'s shared Save button once covered both its call sites (`app.family.add.tsx` and `app.family.members.$id.tsx`'s edit mode).
7. **Testing** — `tsc --noEmit` and `eslint` clean across every touched file. No dedicated accessibility test suite exists in this project (pre-existing, unrelated to this finding).
8. **Live (keyboard-only) verification** — registered a fresh test account; navigated `/app/family/insurance` and `/app/family/recommendations` using only Tab/Shift+Tab (no mouse); confirmed a clearly visible focus ring renders on "Back to Family" and "Add a policy" (Insurance) and "Back to Family" (Recommendations) — exactly the elements fixed. Confirmed via direct inspection that `:focus-visible` correctly does not render after a mouse click (spec-correct, not a bug). Test account fully cleaned up.
9. **Documentation** — `PROJECT_STATE.md`, `CHANGELOG.md`, this report.

## Files Changed

| File | Change |
|---|---|
| `code/src/routes/app.family.insurance.tsx` | 6 elements + 1 `<summary>` gained focus-visible styling. |
| `code/src/routes/app.family.recommendations.tsx` | 2 elements + 1 `<summary>` gained focus-visible styling. |
| `code/src/routes/app.family.goals.tsx` | 5 elements gained focus-visible styling. |
| `code/src/routes/app.family.members.$id.tsx` | 7 elements gained focus-visible styling. |
| `code/src/components/family/FamilyMemberForm.tsx` | 1 element (Save button, shared by 2 routes) gained focus-visible styling. |
| `code/src/routes/app.family.index.tsx` | 3 remaining elements gained focus-visible styling. |

## Verifying Keyboard Focus Indicators Exist on All New Family Screens

Confirmed present on all 6 files after the fix — live-verified via real keyboard navigation on two of them, and the identical class string applied to the remainder makes the same rendering behavior structurally certain (Tailwind's `focus-visible:` variant is a pure CSS pseudo-class selector; there is no per-element special case that could make it behave differently on one native `<button>`/`<Link>` versus another).

## Verifying Focus Order Is Logical

Unchanged by construction — every edit was a `className` addition; no element was added, removed, or reordered in the DOM.

## Verifying Interactive Controls Are Reachable by Keyboard

Confirmed: every fixed element is a native `<button>`, `<Link>` (renders as `<a href>`), `<input>`, `<select>`, or `<details>/<summary>` — all natively `Tab`-reachable. No `<div onClick>` pattern exists anywhere in the files read for this finding.

## Verifying Screen-Reader Labels Are Present Where Required

Checked incidentally during this fix — no new gap found: decorative icons already carry `aria-hidden="true"`; checkboxes are already wrapped in `<label>` with visible text; status/error regions already carry `role="status"`/`role="alert"`.

## Verifying Color Is Never the Only Means of Conveying Information

Re-confirmed for the Parents card (states "no own insurance" in text) and the Schemes screen's three buckets (labeled in text with an icon) — both already correct from their respective tasks; unaffected and unchanged by this finding.

## Verifying Existing Accessibility Patterns Are Reused, Not Duplicated

Every fix uses the byte-identical class string already established by Task 12/the Schemes screen. The one shared component (`FamilyMemberForm`) was fixed once, not duplicated across its two call sites.

## Documentation

`PROJECT_STATE.md`, `CHANGELOG.md`, `DependencyValidation_M2.1-P3.md`, `RootCauseAnalysis_M2.1-P3.md`, `AccessibilityReview_M2.1-P3.md`, `UserTrustReview_M2.1-P3.md`, `DesignReview_M2.1-P3.md`, this report.

## Known, Not Fixed Here (Scope Discipline)

The shared `field-input` CSS utility (`src/styles.css`, used by every text input/select app-wide) has a weaker focus treatment (border-color change only, no ring) than the Link/button pattern applied here. This is an app-wide, cross-cutting design-system concern, not specific to Family screens — flagged for separate consideration, not fixed under this finding's "do not redesign layouts" / "Family screens" scope.

## Rollback

Revert the 24 `className` additions across the 6 listed files. No migration, no logic change, no schema change to reverse.

---

## Definition-of-Production-Ready Checklist (this finding's contribution)

- [x] No silent data loss (pure CSS addition)
- [x] No misleading UI (no user-facing copy changed)
- [x] No read operation mutates state (unrelated to this finding, unchanged)
- [ ] Audit logging complete — unrelated to this finding (addressed separately by the approved P2 finding)
- [x] Accessibility passes (for the 24 elements fixed) — keyboard focus indicators verified live; one separately-flagged, out-of-scope item remains (`field-input`'s weaker focus treatment, app-wide, not Family-specific)
- [x] Product Consistency passes (for this finding) — same pattern applied everywhere, no new convention
- [ ] First-Time User Review passes — not applicable; this is a keyboard/screen-reader-only improvement with no change visible to a mouse-based first-time-user walkthrough
- [x] Architecture Health passes (for this change) — no new mechanism, one reused utility applied consistently
- [x] Financial Correctness passes (for this change) — no financial calculation touched
- [ ] Milestone Certification = CERTIFIED FOR PRODUCTION — not yet; more findings remain per `Milestone2CertificationReport.md`

**Stopping here per instruction. Awaiting approval before beginning the next Milestone 2.1 finding. Dashboard performance optimization not begun, per instruction.**
