# Microcopy Implementation Report — Phase 4

**Scope:** Exactly what `MicrocopyAudit.md` found — every fix is a display-layer wording change reusing data the frontend or backend already returns. No backend file, endpoint, or schema touched.

---

## Files Changed

| File | Change |
|---|---|
| `code/src/lib/life-events.ts` | Added `entityTableLabel()`, `summarizeAffectedAreas()`, `undoConflictSentence()` (§1.1/1.2 of the audit). Added a distinct `INCOME_TYPE_FIELD` helper alongside the existing `ASSET_TYPE_FIELD`, fixing two fields that showed asset examples in an income-type field (§1.6). Gave New Loan's `liability_type` its own direct field definition instead of misusing `ASSET_TYPE_FIELD` (§1.7). Renamed two event labels: "Dependent Parent" → "Caring for a Parent", "Major Medical Event" → "Medical Emergency" (§1.9) — `event_type` values sent to the backend are unchanged. |
| `code/src/lib/financial-labels.ts` | **New.** `INCOME_TYPES`, `EXPENSE_CATEGORIES`, `LIQUID_ASSET_TYPES`, `INVESTMENT_TYPES`, `LIABILITY_TYPES` relocated here from `onboarding/list-steps.tsx`, plus four label-lookup helpers with a graceful fallback for values outside the known list (§1.5). |
| `code/src/components/onboarding/list-steps.tsx` | Now imports the five lists from `lib/financial-labels.ts` instead of defining its own copy. (Also picked up a same-file `eslint --fix` pass reformatting ~240 lines of pre-existing, unrelated Prettier violations — verified via a whitespace-stripped diff to be formatting-only; the only semantic change is the import block itself.) |
| `code/src/routes/app.financials.tsx` | Income/Expense/Asset/Liability sections now render `incomeTypeLabel(income.source_type)` etc. instead of the raw stored value, in both the display row and the `aria-label`s and disabled "cannot be changed" preview inputs. |
| `code/src/routes/app.life-events.tsx` | `StatusPill`: "Applied"/"Undone" → "Recorded"/"Reversed". History row subtitle now uses `summarizeAffectedAreas()` instead of "N records affected". Undo-conflict list now uses `undoConflictSentence()` instead of showing `entity_table` and the raw backend reason string directly. |
| `code/src/components/life-events/RecordLifeEventDialog.tsx` | Preview effects text now reads "This will update your income." instead of "This will affect 1 record across income_sources."; a zero-effect case gets its own distinct, honest message instead of "0 records". |
| `code/src/routes/app.copilot.tsx` | Removed the internal model badge ("GPT-Planner · 4o") → "Powered by AI" (§1.8). |
| `code/src/routes/app.reports.tsx` | "Export PDF" → "Print / Save as PDF" (§1.10), honestly reflecting the `window.print()` call behind it. |

## Files Not Changed (and why)

| File / area | Reason |
|---|---|
| `backend/**` (all) | Every fix is a frontend display-layer translation of values the API already returns (`entity_table`, the three fixed undo-conflict reason strings, free-text `source_type`/`category`/`asset_type`/`liability_type` values). Confirmed via `ruff`/`mypy` re-run and `git status` — zero backend files in this phase's diff. |
| `app.reports.tsx`'s "success rate" wording, and every other Reports/Dashboard/Goals terminology difference | Explicitly deferred to Phase 6 (Cross-module Consistency) per `MicrocopyAudit.md` §2 — a consistency problem between two correct, non-technical phrasings, not a jargon problem. |
| The `liability_type`/other free-text field *types* themselves (still plain text inputs, not dropdowns) | Explicitly deferred to Phase 5 (Automation) per `MicrocopyAudit.md` §2 — changing what kind of input a field offers is a "reduce typing effort" change, not a wording change. |

## Implementation Summary

1. Found every issue by grepping the actual rendered JSX for suspicious patterns (`entity_table`, `record(s) affected`, raw `.source_type`/`.category`/`.asset_type`/`.liability_type` display, snake_case-flavored placeholder text), then verifying each hit against its real, current context before changing anything — no fix in this phase was speculative.
2. Every mapping function (`entityTableLabel`, `undoConflictSentence`) is built against an exhaustively verified, finite set of real backend values (the 9 real `_ENTITY_MODELS` table names; the exact 3 strings `undo_life_event()` can return, re-confirmed directly against `life_event_service.py` in this phase, not assumed from memory) — with a graceful fallback for anything outside that set, so a future backend addition degrades to "readable but untranslated," never a crash or a `undefined`.
3. `lib/financial-labels.ts` was created rather than having Financials import from an onboarding-scoped file, to avoid a backwards module dependency (a shared, feature-appropriate financial-taxonomy concern belongs in `lib/`, not inside `components/onboarding/`).
4. Two additional, previously-undiscovered bugs were found in the course of this audit and fixed as part of the same class of issue: Job Change's and Inheritance's income-type fields, and New Loan's liability-type field, were all showing *asset*-type example text (a copy-paste artifact from reusing `ASSET_TYPE_FIELD` for the wrong domain) — not something `ProductDesignAuthorityReview.md` had flagged, found only by reading the actual field definitions directly.

## Manual Validation

Performed live in Chrome against the running dev build (`localhost:8080`, backend `localhost:8010`):

- **Financials:** Every section now shows a friendly label — "Salary / wages" (was "salary"), "Housing (rent/mortgage)" (was "housing"), "Checking account" (was "checking"), "Mortgage" (was "mortgage" — already matched its own label in this one case, but now goes through the same lookup as everything else for consistency).
- **Life Events history:** Both existing events now show "Reversed" (not "Undone") and a human summary — "Updated your income and your goals" / "Updated your income" — confirming `summarizeAffectedAreas()` correctly handles both the one-item and two-item ("X and Y") cases with real data.
- **Life Events picker:** "Caring for a Parent" confirmed rendering correctly in the Family category (screenshot).
- **Undo-conflict sentence** (`undoConflictSentence`): validated by direct code inspection and exact-string verification against the backend's three real reason strings, rather than a full live reproduction of the conflict scenario (recording an event, independently editing the same row elsewhere, then attempting undo) — a reasonable, proportionate check for a pure text-mapping change that doesn't alter the surrounding conditional logic deciding *whether* to show a conflict, only *what the text says* once one is already shown. This exact conflict-detection logic itself was already exhaustively covered by the backend's own test suite (`test_life_event_hardening.py`) earlier in this session.
- Console checked for new errors: none introduced (tracking reset between navigations, consistent with the same benign, pre-existing Grammarly-extension warning observed in every prior phase).

## Automated Validation

- `npx tsc --noEmit` — clean, zero errors.
- `npx eslint` on all eight changed/new files — 41 issues found, all Prettier-only; the large majority (37) were pre-existing, unrelated formatting debt in `list-steps.tsx` untouched by prior sessions. Resolved via `eslint --fix`, then verified safe via a whitespace-stripped diff (`tr -d '[:space:]'` before/after) confirming the only semantic change in that file is the new import block — everything else byte-identical once formatting is discounted.
- `npm run build` (full Vite + Nitro production build) — succeeded.
- Backend: `ruff check app/` and `mypy --strict app/` — both clean (87 source files, no issues); zero backend files in this phase's diff.
- Backend test suite: not re-run — zero backend code changed; the existing 673-pass baseline remains valid.

## Regression Risk

**Low.** Every label-lookup function has a graceful, non-throwing fallback for a value it doesn't recognize (`lookup()` in `financial-labels.ts`; the `?? "your plan"` / `?? reason` fallbacks in `life-events.ts`), so no existing data — including any free-text value a user already entered before this phase existed — can produce a blank or broken render. The `list-steps.tsx` relocation was verified byte-for-byte equivalent (beyond the intended import change) via diff. The `StatusPill`/history/preview text changes are pure string literals with no branching logic altered.

## Performance Impact

None. Every change is either a compile-time constant lookup (`Record<string, string>` access) or a string-building function over data already in memory — no new network request, no new query, no additional render pass.

## Backward Compatibility

Fully preserved. No prop, route, or type signature changed shape. `list-steps.tsx`'s public component exports (`StepIncome`, `StepExpenses`, etc.) are unchanged — only their internal constants moved to an imported module.

## Outstanding Risks

1. The undo-conflict sentence path was validated by code/string inspection rather than a full live UI reproduction (see Manual Validation) — a deliberate, proportionate choice given the underlying conditional logic is untouched and already covered by backend tests, but noted here rather than silently assumed perfect.
2. `undoConflictSentence()`'s fallback (`${subject}: ${reason}`) will still show a raw backend string if a fourth conflict reason is ever added to `life_event_service.py` without a corresponding update to `UNDO_CONFLICT_REASON_PREDICATES` — an intentional, safe degradation (never crashes, never shows `undefined`), but worth remembering if the backend's undo-conflict reasons ever expand.
3. Two consistency-flavored findings from this audit (§2: "success rate" vs. "% likely" wording, and free-text vs. dropdown field types) were deliberately deferred to Phases 6 and 5 respectively — tracked, not forgotten, but not yet resolved.

## Ready for Next Phase

**Yes.** Phase 4's scope is closed and validated. Continuing automatically to Phase 5 (Automation) per the mission's instruction not to pause between phases.
