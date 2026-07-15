# Dependency Validation — Milestone 2.1-P3 (Accessibility Polish)

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §5/§13 — `focus-visible` styling missing on Tasks 10/11's screens.
**Note on numbering:** the user's instruction labeled this finding "P2," matching the same label already used for Insurance Audit Logging. This document uses the file suffix `P3` (the next sequential slot in this sprint's own numbering) purely to avoid filename collision — the finding itself is referred to by name ("Accessibility Polish") throughout, not by number, to avoid confusion with the approved P2 (audit logging) finding.

## Checklist

| Requirement | Status |
|---|---|
| Existing focus-visible pattern to reuse | ✅ `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background` (plus `rounded` on inline/text-style controls so the ring renders correctly) — already used throughout Task 12's dashboard section and the Task 12.1-P1 Schemes screen. This exact string is reused everywhere in this fix; no new pattern invented. |
| Full inventory of the actual gap (verified by direct file reads, not just the Certification's named examples) | The Certification named Tasks 10/11 specifically. Direct inspection found the same gap is **broader**: `app.family.goals.tsx` (Task 8, 5 gaps), `app.family.members.$id.tsx` (Task 7, 7 gaps), `FamilyMemberForm.tsx` (Task 6, shared by both the add and edit flows, 1 gap), and even 3 elements on `app.family.index.tsx` (Task 5/12, mostly already covered) were also missing it. 24 total interactive elements across 6 files. |
| Existing components to check for accidental duplication | `LinkCardShell` (Task 12) already has focus-visible built into its own definition — confirmed via direct read, not modified. `FamilyMemberForm`'s Save button is shared by two routes (`app.family.add.tsx` and `app.family.members.$id.tsx`'s edit mode) — fixing it once in the shared component covers both call sites, avoiding a duplicate fix. |
| A separate, out-of-scope observation surfaced during investigation | The shared `field-input` CSS utility (`src/styles.css`, used by every text `<input>`/`<select>` app-wide) sets `outline: none` and shows only a border-color change on focus — weaker than the ring treatment used on links/buttons, but this is an **app-wide, cross-cutting CSS concern**, not specific to Family screens, and changing it would be a broader design-system change outside this finding's scope ("do not redesign layouts," reuse existing components). Flagged as a separately-trackable item, not fixed here. |

## Conclusion

**No blocker.** Every fix is the same, already-proven utility-class addition applied to elements that already have working styling otherwise — pure CSS addition, zero logic change, zero layout change. Proceeding to Root Cause Analysis.
