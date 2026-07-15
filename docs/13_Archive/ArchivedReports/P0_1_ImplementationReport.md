# P0-1 IMPLEMENTATION REPORT — Onboarding Silent Data Loss

**Role:** Senior Product Engineer
**Scope:** Fix `UXValidationReport.md`'s P0-1 finding only. No onboarding redesign, no backend changes, no Financials changes.

---

## Problem

Five onboarding steps — Income, Expenses, Cash & Savings, Investments, Debts — each show a mini "Add" form (Type/Amount/Description + a small "+ Add" button) directly above a large primary "Continue"/"Skip" button. Typing a real amount (e.g., a $185,000 salary) and clicking the primary button instead of "+ Add" silently discarded the typed value with zero warning, because the two buttons were fully independent: "+ Add" submitted the mini-form's local state; "Continue"/"Skip" only checked whether an item had already been added (`items.length > 0`) and had no awareness of whatever was currently typed.

## Chosen Solution: Auto-save on Continue

Of the three options the report offered (disable Continue, warn with a message, auto-save), **auto-save** was the smallest, most seamless fit:

- **Disable Continue** would require new copy explaining *why* the button is disabled, and a way to un-stick a user who typed something invalid — more surface area than needed.
- **A warning dialog** adds a click and a new UI element (modal/toast) not otherwise present in this flow.
- **Auto-save** requires no new UI at all. It reuses the exact `onAdd` call each step already makes when "+ Add" is clicked, just triggered from the "Continue" handler too when there's a valid pending amount. Zero new copy, zero new components, zero added round-trips beyond the one save that would have to happen anyway.

## Implementation

For each of the four step components (`StepIncome`, `StepExpenses`, `AssetStep` — shared by both `StepLiquidAssets` and `StepInvestments` — and `StepLiabilities`), the `onNext` handler passed to `ListNavRow` was changed from the raw `onNext` prop to a new `handleNext`:

```ts
const pendingAmount = Number(form.annual_amount); // (or current_value / balance / monthly_amount)
const hasPendingEntry = pendingAmount > 0;

const handleNext = async () => {
  if (hasPendingEntry) {
    setError(null);
    setAdding(true);
    try {
      await onAdd({ ...same payload shape handleAdd already builds... });
      setForm({ ...reset to blank... });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add.");
      setAdding(false);
      return; // stay on this step — the typed value is still in the form, nothing is lost
    }
    setAdding(false);
  }
  onNext();
};
```

`ListNavRow`'s props were also updated:
- `hasItems={items.length > 0 || hasPendingEntry}` — the button now correctly reads "Continue" the instant a valid amount is typed, instead of misleadingly reading "Skip" while real data sits in the form (the report specifically called out "Skip" as actively misleading in this state).
- `loading={nextLoading || adding}` — the button shows its existing spinner/disabled state during the brief auto-save, reusing the exact same `Loader2` treatment already used elsewhere on this component.

If the amount field is empty or zero, `handleNext` skips straight to `onNext()` — this is the legitimate "nothing to add" case and behaves exactly as before.

## Files Changed

- `code/src/components/onboarding/list-steps.tsx` — the only file touched. Four edits, one per list-based step (`StepIncome`, `StepExpenses`, `AssetStep`, `StepLiabilities`), each adding a `handleNext` wrapper and updating its `ListNavRow` props. No other file was modified — no backend code, no Financials code, no other onboarding steps (Account, Personal, Family, Employment, Goal, Assumptions) were touched, since none of them share this "Add form + separate Continue" pattern.

## Why This Meets the Requirements

- **Prevents silent data loss:** a valid typed amount is now always persisted before the wizard advances, on all five affected steps.
- **Does not slow onboarding:** no new click, no new screen, no new confirmation step. A user who already clicks "+ Add" (the correct path) sees zero behavior change. A user who doesn't gets the exact same save that "+ Add" would have performed, now triggered by Continue instead of being skipped.
- **No backend changes:** reuses the existing `onAdd` prop (`createIncome`/`createExpense`/`createAsset`/`createLiability`), already wired from `onboarding.tsx` to these components.
- **Consistent with existing UI:** no new components, colors, copy, or interaction patterns — the fix only changes *when* the already-existing add logic fires, plus corrects the existing "Continue"/"Skip" label logic to already-defined rules.

## Manual Verification

Reproduced the exact scenario from `UXValidationReport.md` live, against a fresh throwaway account (`p0verify@example.com`, created and deleted for this test), for every affected step — type an amount, do **not** click "+ Add", click the primary button, then navigate Back to confirm the entry survived:

| Step | Typed | Button label before click | Result after clicking Continue, then Back |
|---|---|---|---|
| Income | `185000` | Correctly showed "Continue" (not "Skip") | ✅ "Salary / wages — $185,000/yr" present as a saved row |
| Expenses | `3200` | "Continue" | ✅ "Housing (rent/mortgage) — $3,200/mo" present |
| Cash & Savings | `45000` | "Continue" | ✅ "Checking account — $45,000" present |
| Investments | `60000` | "Continue" | ✅ "Brokerage account — $60,000" present |
| Debts | `310000` | "Continue" | ✅ "Mortgage — $310,000" present |

All five: **salary (and every other typed amount) is still present — the user is no longer silently warned-by-absence.** No case required the fallback "user is warned" branch, since auto-save succeeded in every live test (the backend calls involved — income/expense/asset/liability creation — are the same already-shipped, already-tested endpoints from Milestone 1).

Additional checks:
- `npx tsc --noEmit` — clean, no new type errors.
- `npm run build` — succeeds.
- Full backend suite (`pytest`, 382 tests) — all pass, confirming no backend regression (none was expected, since no backend file was touched — this run exists only to prove the surrounding repo state is intact).
- Spot-checked the legitimate "nothing to add" path (e.g., the Investments step with a blank amount field) still advances immediately via "Skip" with no attempted save — unaffected by this change.

## Regression Risk

**Low.** The change is additive to the `onNext` handler only; the explicit "+ Add" button and its `handleAdd` function are completely untouched, so the primary, already-tested creation path is unaffected. The one new code path (auto-save from Continue) reuses the identical `onAdd` call and payload construction `handleAdd` already used, so no new validation or request shape was introduced. The only new behavior is a brief loading state on Continue when a valid amount is pending — already covered visually by the existing `loading`/spinner treatment on that button.

## Ready For UX Revalidation?

**Yes.** This closes P0-1 exactly as scoped — silent data loss is eliminated on all five affected onboarding steps, without touching the backend, Financials, or any other onboarding step, and without introducing new UI. Recommend re-running the same live walkthrough used in `UXValidationReport.md` (Income → Expenses → Assets → Investments → Debts → Dashboard) to confirm the Dashboard no longer shows a false `$0` income / `4/100` health score for an account seeded this way.
