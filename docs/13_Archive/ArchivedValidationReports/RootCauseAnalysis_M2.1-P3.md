# Root Cause Analysis — Milestone 2.1-P3 (Accessibility Polish)

**Date:** 2026-07-07

## Why the gap exists

`focus-visible` styling was applied inconsistently as this milestone's screens were built one task at a time. Task 12 (Family Dashboard, built most recently and most carefully) applied it to every interactive element from the start. Earlier tasks (5 through 11) were built before that discipline was consistently established as the pattern to copy — each screen's author styled hover/click states correctly but didn't always add the keyboard-focus equivalent. This is inconsistent execution of an existing, known pattern, not a missing capability or a design gap — the correct CSS classes already existed in the codebase the whole time; they simply weren't copied to every element.

## Is this a design or logic defect?

**No.** Nothing about page structure, component boundaries, or interaction logic is wrong — every affected element is already a correct native `<button>`, `<Link>`, or `<summary>`, already keyboard-focusable and keyboard-activatable by the browser's own default behavior. The only gap is the **visible indicator** of that focus — a pure styling omission.

## Scope of the fix

24 interactive elements across 6 files, all receiving the exact same existing utility-class string:
- `app.family.insurance.tsx` — 6 elements + 1 `<summary>`
- `app.family.recommendations.tsx` — 2 elements + 1 `<summary>`
- `app.family.goals.tsx` — 5 elements
- `app.family.members.$id.tsx` — 7 elements
- `FamilyMemberForm.tsx` — 1 element (shared by 2 routes)
- `app.family.index.tsx` — 3 elements

## What this finding does not do

- Does not touch the shared `field-input` CSS utility (an app-wide concern, out of scope — see `DependencyValidation_M2.1-P3.md`).
- Does not reorder any DOM element, so focus/tab order is unchanged by construction — verified by the fact that every edit was a `className` addition only, never a structural JSX change.
- Does not touch any business logic, data fetching, or layout — every edit is additive CSS on an already-correct element.
