# Design Review — Milestone 2.1-P3 (Accessibility Polish)

**Date:** 2026-07-07

## What changes

Purely additive `className` edits — the exact existing `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background` string (with a trailing `rounded` on inline/text-style controls, matching the existing convention for non-block elements) appended to 24 interactive elements across 6 files. No new component, no new utility class, no new design token.

## What does not change

- No layout, spacing, or visual hierarchy — the ring only renders on keyboard focus, invisible at all other times.
- No component API — `FamilyMemberForm`'s props/behavior are untouched; only its internal Save button's `className` gained the suffix.
- No business logic, no data fetching, no route structure.
- The shared `field-input` CSS utility (used by every text input/select app-wide) — explicitly out of scope, flagged separately in `DependencyValidation_M2.1-P3.md` as a broader, cross-cutting concern that would exceed "Family screens" scope and risks the kind of app-wide redesign this finding was explicitly told not to do.

## Why this is the right scope, not an under-fix

The Certification named Tasks 10/11 specifically; direct file inspection found the same gap in Tasks 5–8 as well. Fixing only the two originally-named files would have left a known, now-documented gap sitting unaddressed in three more screens for no principled reason — since the fix is identical, mechanical, and zero-risk in every case, there was no reason to artificially narrow the scope to only the two files the Certification happened to sample.

## Blast radius

6 files, all frontend, all `className`-only edits. `tsc`/`eslint` clean. No test file needed changes (no accessibility test suite exists in this project — verified via keyboard-only live walkthrough instead, per the user's "run keyboard-only verification" instruction).
