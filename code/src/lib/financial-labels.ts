// Canonical value/label pairs for the free-text `source_type`/`category`/
// `asset_type`/`liability_type` fields (backend/app/schemas/financials.py —
// all plain strings, no DB enum, by deliberate backend design). Moved here
// from onboarding's own list-steps.tsx (MicrocopyAudit.md Phase 4) so
// Financials can look up the same friendly label onboarding already shows,
// instead of displaying the raw stored value verbatim — without Financials
// importing from an onboarding-scoped file.

export const INCOME_TYPES = [
  { value: "salary", label: "Salary / wages" },
  { value: "self_employment", label: "Self-employment" },
  { value: "rental", label: "Rental income" },
  { value: "investment", label: "Investment income" },
  { value: "pension", label: "Pension / annuity" },
  { value: "other", label: "Other" },
];

export const EXPENSE_CATEGORIES = [
  { value: "housing", label: "Housing (rent/mortgage)" },
  { value: "transport", label: "Transport" },
  { value: "food", label: "Food & groceries" },
  { value: "utilities", label: "Utilities" },
  { value: "healthcare", label: "Healthcare" },
  { value: "insurance", label: "Insurance" },
  { value: "entertainment", label: "Entertainment" },
  { value: "business", label: "Business" },
  { value: "other", label: "Other" },
];

export const LIQUID_ASSET_TYPES = [
  { value: "checking", label: "Checking account" },
  { value: "savings", label: "Savings account" },
  { value: "money_market", label: "Money market" },
];

export const INVESTMENT_TYPES = [
  { value: "brokerage", label: "Brokerage account" },
  { value: "retirement_401k", label: "401(k)" },
  { value: "retirement_ira", label: "IRA / Roth IRA" },
  { value: "real_estate", label: "Real estate" },
  { value: "other", label: "Other investment" },
];

export const LIABILITY_TYPES = [
  { value: "mortgage", label: "Mortgage" },
  { value: "auto_loan", label: "Auto loan" },
  { value: "student_loan", label: "Student loan" },
  { value: "credit_card", label: "Credit card" },
  { value: "personal_loan", label: "Personal loan" },
  { value: "other", label: "Other debt" },
];

function lookup(options: { value: string; label: string }[], value: string): string {
  const match = options.find((o) => o.value === value);
  if (match) return match.label;
  // Graceful fallback for a value outside the known list (e.g. free-typed
  // via a Life Event form) — "auto_loan" -> "Auto loan" — never shows a
  // raw snake_case identifier verbatim.
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function incomeTypeLabel(value: string): string {
  return lookup(INCOME_TYPES, value);
}

export function expenseCategoryLabel(value: string): string {
  return lookup(EXPENSE_CATEGORIES, value);
}

export function assetTypeLabel(value: string): string {
  const match =
    LIQUID_ASSET_TYPES.find((o) => o.value === value) ??
    INVESTMENT_TYPES.find((o) => o.value === value);
  return match ? match.label : lookup([], value);
}

export function liabilityTypeLabel(value: string): string {
  return lookup(LIABILITY_TYPES, value);
}
