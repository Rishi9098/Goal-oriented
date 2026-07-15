# Automation Audit — Phase 5

**Date:** 2026-07-12
**Scope:** Reduce clicks and typing in the Life Event forms — the highest-friction, highest-frequency data-entry surface in the product — without ever removing a choice the user could otherwise make. Every change below is additive: nothing that was previously typeable becomes un-typeable, nothing that was previously selectable becomes un-selectable.

---

## 1. Carried over from Phase 4

`MicrocopyAudit.md` §2 explicitly deferred one finding here: New Loan's `liability_type` (and the same-shaped `asset_type`/income-type fields elsewhere in the catalog) are free-text inputs with no assistance, even though a canonical, already-in-production list of values exists for every one of them (`lib/financial-labels.ts`, itself created in Phase 4 by extracting onboarding's own lists). This audit resolves that.

## 2. Findings

### 2.1 Free-text taxonomy fields offer no assistance at all

**Where:** Every "type" field across the Life Event catalog that maps to a known taxonomy — `liability_type` (New Loan), `asset_type` (Bonus, Inheritance, New Loan's linked purchase, Home Sale/Business Sale's proceeds), `new_source_type` (Job Change), `income_source_type` (Inheritance).

**Problem:** All are plain `<input type="text">` fields. A user must recall and type an exact value from memory, with only a placeholder example as a hint.

**Constraint:** These fields are genuinely free text on the backend (`source_type`/`category`/`asset_type`/`liability_type`: `str, max_length=50`, no DB enum) — a real reason exists to allow values outside the canonical list (e.g. a genuinely unusual asset or debt type), so **converting to a closed `<select>` would remove real user control**, which this phase's own rule forbids.

**Fix:** A native HTML `<datalist>` — the browser's own built-in autocomplete-suggestion mechanism. It shows the canonical list as suggestions the moment the user starts typing, is selectable in one click/keystroke, and — critically — **never restricts what can actually be typed and submitted**. This is the one mechanism that satisfies both "reduce typing" and "never reduce control" simultaneously, with zero new frontend state or backend surface.

### 2.2 Entity dropdowns force a choice even when there's only one real answer

**Where:** Every `entity`/`multi-entity` field across the catalog (income source, asset, liability, goal, household member pickers).

**Problem:** A user with exactly one income source still has to open "Income source," see one option, and click it — for every Salary Raise, every Job Change, forever, no matter how many income sources they'll ever have. This is pure ceremony: there is only one possible correct answer, and the system already knows it.

**Fix:** When a given entity field has exactly one available option, pre-select it (or, for `multi-entity`, pre-check it) as soon as the option list loads — but the field remains a fully live, editable dropdown/checkbox, not a locked or hidden value. If the user later has two income sources, the same field simply stops auto-selecting (more than one real answer exists, so the system asks, exactly as it should). **User control is never reduced**: the pre-filled value is not read-only, is never hidden, and a user who somehow doesn't want the (only) pre-selected option can still change it before submitting — this only removes the requirement to act when there was never a real decision to make.

## 3. Decision

1. Add `suggestions?: string[]` to the `"text"` field kind in `lib/life-events.ts`'s type system. Populate it for every taxonomy-mapped text field, sourced from the exact same `lib/financial-labels.ts` lists Financials and onboarding already use (one source of truth, not a fourth copy of these values).
2. Render a `<datalist>` in `life-event-field-inputs.tsx` whenever `field.suggestions` is present, wired via the input's `list` attribute — a standard, zero-dependency HTML mechanism already supported by every browser this product targets.
3. Add one `useEffect` to `RecordLifeEventDialog.tsx` that, whenever the selected event type or the loaded entity options change, pre-selects any `entity`/`multi-entity` field with exactly one available option and no value chosen yet.

## 4. What this phase explicitly does not do

- Does not convert any free-text field to a closed `<select>` — every one of them keeps full free-text capability; the canonical list is offered as *assistance*, never as a *restriction*.
- Does not pre-select or pre-fill anything when more than one real option exists — auto-selection only ever resolves a field that has exactly one possible answer, never guesses among several.
- Does not touch the backend, any endpoint, or any calculation — every list reused here (`GET /life-events`'s entity option data, `lib/financial-labels.ts`) already exists; this phase only changes when/how the frontend uses it.
- Does not attempt the deeper automation ideas from `ProductDesignAuthorityReview.md` (computing net proceeds from a sale price, proposing a lump-sum/financing split, suggesting a raise-based goal contribution bump) — those require either new computation logic (out of scope: "never introduce another calculation engine") or a materially larger form-flow redesign; this phase targets the highest-leverage, lowest-risk, purely-mechanical friction instead.
