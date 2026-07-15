# Microcopy Audit — Phase 4

**Date:** 2026-07-12
**Method:** Systematic grep across every route and component for backend/technical vocabulary leaking into user-facing text (raw table names, audit-log status words, snake_case values, developer-facing model names), followed by direct verification of each hit against its rendered context — not a guess, every finding below was confirmed live in code before being fixed.

---

## 1. Findings and fixes

### 1.1 Raw backend table names shown verbatim (most severe finding)

**Where:** `RecordLifeEventDialog.tsx`'s Preview effects text, and `app.life-events.tsx`'s undo-conflict list.

**Before:** `"This will affect 1 record across income_sources."` / `"income_sources: Row has changed since this event was recorded"` — the literal Postgres table name (`life_event_service.py`'s `_ENTITY_MODELS` registry key), plural and snake_case, shown directly to a user with no translation.

**Fix:** Added `entityTableLabel()` and `summarizeAffectedAreas()` to `lib/life-events.ts`, mapping all nine real entity tables (`income_sources`, `expenses`, `assets`, `liabilities`, `goals`, `household_members`, `dependents`, `user_profiles`, `financial_assumptions`) to short, human phrases ("your income," "your debts," "your family," etc.), joined naturally ("your income and your assets" / "your income, your assets, and your goals"). Now: `"This will update your income."`

### 1.2 Undo conflict reasons shown verbatim

**Before:** The three fixed strings `undo_life_event()` can return (`"Row has changed since this event was recorded"`, `"Row no longer exists"`, `"Unrecognized entity table — cannot verify it is safe to undo"`) were displayed exactly as the backend wrote them — audit-log language, not something a person going through a real financial decision should read.

**Fix:** `undoConflictSentence(entityTable, reason)` combines the same entity-table label as §1.1 with a natural-language predicate for each of the three known reasons (verified directly against `life_event_service.py` — not guessed), with a safe fallback to the raw string for any future reason this list doesn't yet know about. Now: `"Your income has changed since you recorded this."`

### 1.3 Status pills using audit-log verbs

**Where:** `app.life-events.tsx`'s `StatusPill`.

**Before:** `"Applied"` / `"Undone"` — database-transaction language.
**Fix:** `"Recorded"` / `"Reversed"` — what actually happened, in plain English.

### 1.4 History row summary counting "records"

**Before:** `"12 Jul 2026 · 2 records affected"` — the word "record" here means a database row, not a financial record a user would recognize.
**Fix:** Reuses the same `summarizeAffectedAreas()` from §1.1 — `"12 Jul 2026 · Updated your income"`.

### 1.5 Free-text financial values shown raw, not by their friendly label

**Where:** `app.financials.tsx` — Income, Expense, Asset, and Liability sections all displayed `income.source_type` / `expense.category` / `asset.asset_type` / `liability.liability_type` directly (e.g. `"salary"`, `"auto_loan"`), even though onboarding's own list-steps.tsx already had a friendly label for every one of these values (`"Salary / wages"`, `"Auto loan"`) — it just never left the onboarding screen.

**Fix:** Moved the five value/label lists (`INCOME_TYPES`, `EXPENSE_CATEGORIES`, `LIQUID_ASSET_TYPES`, `INVESTMENT_TYPES`, `LIABILITY_TYPES`) out of `components/onboarding/list-steps.tsx` into a new, correctly-shared `lib/financial-labels.ts` (avoiding the alternative of Financials importing from an onboarding-scoped file), with one lookup helper per field and a graceful fallback (`"auto_loan"` → `"Auto loan"`) for any value outside the known list — since these fields are genuinely free text on the backend (no DB enum), a value typed via a Life Event form that isn't in the canonical list must still degrade to *something* readable, never a raw, untranslated string. `list-steps.tsx` now imports from the same shared file instead of defining its own copy — one source of truth, not two lists that could drift.

### 1.6 A field showing the wrong domain's example values

**Where:** Job Change's "New income type" field and Inheritance's "Income type" field, both in `lib/life-events.ts`.

**Before:** Both reused the generic `ASSET_TYPE_FIELD` helper, which hardcodes the placeholder `"e.g. savings, checking, real_estate, stocks"` — asset examples, shown inside an *income* type field. A real, live mismatch, not a hypothetical one.
**Fix:** Added a distinct `INCOME_TYPE_FIELD` helper with its own, domain-correct placeholder (`"e.g. Salary, Freelance, Rental, Dividends"`), used only by the two income-type fields; the four genuine asset-type fields keep `ASSET_TYPE_FIELD` unchanged.

### 1.7 New Loan's liability-type field showing asset examples

**Before:** Also misused `ASSET_TYPE_FIELD` — the visible placeholder inside the input read `"e.g. savings, checking, real_estate, stocks"` (asset examples) for a field asking for a *liability* type, while the domain-correct example (`"e.g. auto_loan, personal_loan, mortgage"`) was relegated to small helper-text below the field and was itself still snake_case-flavored.
**Fix:** Given its own direct field definition (no longer sharing the mismatched helper) with placeholder `"e.g. Car loan, Personal loan, Mortgage"` — both domain-correct and free of snake_case.

### 1.8 Internal model name exposed to end users

**Where:** AI Copilot's header, `"GPT-Planner · 4o"`.
**Fix:** `"Powered by AI"` — a consumer financial product has no reason to expose an internal model codename, and a specific version string is also simply inaccurate the moment the backend's model choice changes.

### 1.9 Overly clinical/formal event names

**Where:** The Life Event catalog's own display labels (not the `event_type` values sent to the backend, which are unchanged).
**Fix:** `"Dependent Parent"` → `"Caring for a Parent"`; `"Major Medical Event"` → `"Medical Emergency"` — what a person would actually type into a search bar, not Census-form/clinical terminology.

### 1.10 A button label overpromising its actual behavior

**Where:** Reports' `"Export PDF"` button, which calls `window.print()` — the browser's native print dialog, not a generated PDF file.
**Fix:** `"Print / Save as PDF"` — honest about what actually happens (most browsers' print dialog offers "Save as PDF" as a destination, which is the real mechanism here).

---

## 2. Findings deliberately deferred to a later phase (not fixed here, and why)

- **"success rate" (Reports) vs. "% likely" (Dashboard/Goals/Life Events)** — the same concept, worded two different ways on two different screens. This is a *consistency* problem (the words themselves aren't technical or wrong), not a jargon problem — it belongs to Phase 6 (Cross-module Consistency), where it's tracked, not silently fixed here under a different phase's mandate.
- **New Loan's `liability_type` remains free text**, not a dropdown of preset categories, even after §1.7's placeholder fix. Converting the field type itself (not just its wording) is a *reduce typing effort / smarter selection* change — squarely Phase 5 (Automation)'s mandate, not a wording fix. Flagged there.
- **Every other Life Event free-text field** (`asset_type`, `expense category` typed via a life event, etc.) has the same underlying "free text, not a preset list" shape as `liability_type`. Not touched here for the same reason — this phase only fixes what's *said*, not what *kind of input* is offered.

## 3. Methodology note

Every fix above reuses data the frontend or backend already computes and returns — `entityTableLabel`/`summarizeAffectedAreas`/`undoConflictSentence` are pure display-layer translations of values the API already sends (`entity_table`, the three fixed conflict-reason strings), and `lib/financial-labels.ts`'s lists are the exact same lists already in production use inside onboarding, only relocated to a shared module, never duplicated. No backend file, endpoint, or schema was touched.
