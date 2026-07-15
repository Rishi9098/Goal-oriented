import { createFileRoute, Link } from "@tanstack/react-router";
import { type ReactNode, useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  History,
  Landmark,
  Loader2,
  Pencil,
  PiggyBank,
  Receipt,
  Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Asset, Expense, FinancialAssumptions, IncomeSource, Liability } from "@/lib/api";
import { formatCurrency } from "@/lib/mock-data";
import {
  incomeTypeLabel,
  expenseCategoryLabel,
  assetTypeLabel,
  liabilityTypeLabel,
} from "@/lib/financial-labels";

export const Route = createFileRoute("/app/financials")({
  head: () => ({ meta: [{ title: "Financials — Northstar" }] }),
  staticData: { shellTitle: "Financials" },
  component: FinancialsPage,
});

// Milestone 1 Task 2 (Milestone1ImplementationSpecification_FINAL.md §6) made
// this page read-only. Task 3 adds editing for Income only — Expenses,
// Assets, and Liabilities remain read-only display until their own tasks.

type FetchState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: T };

function useFetch<T>(fetcher: () => Promise<T>): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Failed to load.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- each call site passes a stable fetcher reference (an api.* function), not a value that changes across renders
  }, []);

  return state;
}

function SectionShell({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: ReactNode;
}) {
  return (
    <div className="surface-card overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
          {title}
        </p>
      </div>
      {children}
    </div>
  );
}

function SectionLoading() {
  return (
    <div className="divide-y divide-border">
      {[1, 2, 3].map((i) => (
        <div key={i} className="px-6 py-4 h-14 animate-pulse bg-surface/40" />
      ))}
    </div>
  );
}

function SectionError({ message }: { message: string }) {
  return (
    <div className="px-6 py-6 flex items-center gap-2 text-sm text-red-400 bg-red-500/5">
      <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
      {message}
    </div>
  );
}

function SectionEmpty({ message }: { message: string }) {
  return <div className="px-6 py-10 text-center text-sm text-muted-foreground">{message}</div>;
}

function Row({
  primary,
  secondary,
  amount,
}: {
  primary: string;
  secondary?: string;
  amount: string;
}) {
  return (
    <div className="px-6 py-4 grid grid-cols-[1fr_auto] gap-4 items-center">
      <div className="min-w-0">
        <p className="text-sm font-medium truncate">{primary}</p>
        {secondary && <p className="text-xs text-muted-foreground truncate mt-0.5">{secondary}</p>}
      </div>
      <span className="text-sm font-medium tabular-nums shrink-0">{amount}</span>
    </div>
  );
}

// Income editing (Milestone 1 Task 3). This section manages its own list
// state, rather than the shared read-only `useFetch` hook, so a successful
// PATCH's response can be written directly into that state — see
// `handleSaved` below for exactly how the page stays fresh with no re-fetch
// and no stale UI.
function IncomeSection() {
  const [state, setState] = useState<FetchState<IncomeSource[]>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getIncome()
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Failed to load.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The PATCH response IS the freshest possible record — it reflects
  // exactly what the server just persisted. Splicing it into local state
  // by id, in place of a full list re-fetch, is what keeps this row
  // correct with zero risk of showing a stale value.
  function handleSaved(updated: IncomeSource) {
    setState((prev) =>
      prev.status === "loaded"
        ? { status: "loaded", data: prev.data.map((r) => (r.id === updated.id ? updated : r)) }
        : prev,
    );
  }

  return (
    <SectionShell title="Income" icon={Wallet}>
      {state.status === "loading" && <SectionLoading />}
      {state.status === "error" && <SectionError message={state.message} />}
      {state.status === "loaded" &&
        (state.data.length === 0 ? (
          <SectionEmpty message="No income sources yet." />
        ) : (
          <div className="divide-y divide-border">
            {state.data.map((income) => (
              <EditableIncomeRow key={income.id} income={income} onSaved={handleSaved} />
            ))}
          </div>
        ))}
    </SectionShell>
  );
}

type IncomeEditForm = {
  description: string;
  annualAmount: string;
};

function EditableIncomeRow({
  income,
  onSaved,
}: {
  income: IncomeSource;
  onSaved: (updated: IncomeSource) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<IncomeEditForm>({
    description: income.description ?? "",
    annualAmount: String(income.annual_amount),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setForm({ description: income.description ?? "", annualAmount: String(income.annual_amount) });
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateIncome(income.id, {
        description: form.description.trim() === "" ? undefined : form.description,
        annual_amount: Number(form.annualAmount),
      });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      // Per Milestone1ImplementationSpecification_FINAL.md §10: the form
      // stays open and the user's edited values are preserved on failure —
      // never silently closed or discarded.
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="px-6 py-4 grid grid-cols-[1fr_auto_auto] gap-4 items-center">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{incomeTypeLabel(income.source_type)}</p>
          {income.description && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">{income.description}</p>
          )}
        </div>
        <span className="text-sm font-medium tabular-nums shrink-0">
          {formatCurrency(income.annual_amount)}/yr
        </span>
        <button
          type="button"
          onClick={startEdit}
          aria-label={`Edit ${incomeTypeLabel(income.source_type)} income source`}
          title="Edit"
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition shrink-0"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="px-6 py-4 space-y-3 bg-surface/40">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Source type</span>
          <input
            value={incomeTypeLabel(income.source_type)}
            disabled
            aria-label="Source type (cannot be changed)"
            className="field-input w-full opacity-50 cursor-not-allowed"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Annual amount ($)</span>
          <input
            type="number"
            value={form.annualAmount}
            onChange={(e) => setForm((f) => ({ ...f, annualAmount: e.target.value }))}
            min="0.01"
            max="100000000"
            step="0.01"
            required
            className="field-input w-full"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Description</span>
        <input
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
        >
          {saving ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
            </>
          ) : (
            <>
              <Check className="h-3.5 w-3.5" /> Save changes
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// Expense editing (Milestone 1 Task 4). Same local-list-state-plus-splice
// strategy as Income (Task 3): the PATCH response is the freshest possible
// record, so it replaces the matching row in place — no re-fetch, no
// whole-page refresh, no stale UI. See `handleSaved` below.
function ExpensesSection() {
  const [state, setState] = useState<FetchState<Expense[]>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getExpenses()
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Failed to load.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSaved(updated: Expense) {
    setState((prev) =>
      prev.status === "loaded"
        ? { status: "loaded", data: prev.data.map((r) => (r.id === updated.id ? updated : r)) }
        : prev,
    );
  }

  return (
    <SectionShell title="Expenses" icon={Receipt}>
      {state.status === "loading" && <SectionLoading />}
      {state.status === "error" && <SectionError message={state.message} />}
      {state.status === "loaded" &&
        (state.data.length === 0 ? (
          <SectionEmpty message="No expenses yet." />
        ) : (
          <div className="divide-y divide-border">
            {state.data.map((expense) => (
              <EditableExpenseRow key={expense.id} expense={expense} onSaved={handleSaved} />
            ))}
          </div>
        ))}
    </SectionShell>
  );
}

type ExpenseEditForm = {
  description: string;
  monthlyAmount: string;
};

function EditableExpenseRow({
  expense,
  onSaved,
}: {
  expense: Expense;
  onSaved: (updated: Expense) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<ExpenseEditForm>({
    description: expense.description ?? "",
    monthlyAmount: String(expense.monthly_amount),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setForm({
      description: expense.description ?? "",
      monthlyAmount: String(expense.monthly_amount),
    });
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateExpense(expense.id, {
        description: form.description.trim() === "" ? undefined : form.description,
        monthly_amount: Number(form.monthlyAmount),
      });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      // Per Milestone1ImplementationSpecification_FINAL.md §10: the form
      // stays open and the user's edited values are preserved on failure —
      // covers 404 (row deleted concurrently), 422 (validation), and
      // network failures alike, since all three reach this catch block.
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="px-6 py-4 grid grid-cols-[1fr_auto_auto] gap-4 items-center">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{expenseCategoryLabel(expense.category)}</p>
          {expense.description && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">{expense.description}</p>
          )}
        </div>
        <span className="text-sm font-medium tabular-nums shrink-0">
          {formatCurrency(expense.monthly_amount)}/mo
        </span>
        <button
          type="button"
          onClick={startEdit}
          aria-label={`Edit ${expenseCategoryLabel(expense.category)} expense`}
          title="Edit"
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition shrink-0"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="px-6 py-4 space-y-3 bg-surface/40">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Category</span>
          <input
            value={expenseCategoryLabel(expense.category)}
            disabled
            aria-label="Category (cannot be changed)"
            className="field-input w-full opacity-50 cursor-not-allowed"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Monthly amount ($)</span>
          <input
            type="number"
            value={form.monthlyAmount}
            onChange={(e) => setForm((f) => ({ ...f, monthlyAmount: e.target.value }))}
            min="0"
            max="10000000"
            step="0.01"
            required
            className="field-input w-full"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Description</span>
        <input
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
        >
          {saving ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
            </>
          ) : (
            <>
              <Check className="h-3.5 w-3.5" /> Save changes
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// Asset editing (Milestone 1 Task 5). Same local-list-state-plus-splice
// strategy as Income (Task 3) and Expenses (Task 4): the PATCH response
// replaces the matching row in place — no re-fetch, no whole-page refresh,
// no stale UI. See `handleSaved` below. `PATCH /financials/assets/{id}`
// already existed before this milestone; no backend or API-client change
// was needed for this task.
function AssetsSection() {
  const [state, setState] = useState<FetchState<Asset[]>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getAssets()
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Failed to load.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSaved(updated: Asset) {
    setState((prev) =>
      prev.status === "loaded"
        ? { status: "loaded", data: prev.data.map((r) => (r.id === updated.id ? updated : r)) }
        : prev,
    );
  }

  return (
    <SectionShell title="Assets" icon={PiggyBank}>
      {state.status === "loading" && <SectionLoading />}
      {state.status === "error" && <SectionError message={state.message} />}
      {state.status === "loaded" &&
        (state.data.length === 0 ? (
          <SectionEmpty message="No assets yet." />
        ) : (
          <div className="divide-y divide-border">
            {state.data.map((asset) => (
              <EditableAssetRow key={asset.id} asset={asset} onSaved={handleSaved} />
            ))}
          </div>
        ))}
    </SectionShell>
  );
}

type AssetEditForm = {
  institution: string;
  description: string;
  currentValue: string;
};

function EditableAssetRow({ asset, onSaved }: { asset: Asset; onSaved: (updated: Asset) => void }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<AssetEditForm>({
    institution: asset.institution ?? "",
    description: asset.description ?? "",
    currentValue: String(asset.current_value),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setForm({
      institution: asset.institution ?? "",
      description: asset.description ?? "",
      currentValue: String(asset.current_value),
    });
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateAsset(asset.id, {
        institution: form.institution.trim() === "" ? undefined : form.institution,
        description: form.description.trim() === "" ? undefined : form.description,
        current_value: Number(form.currentValue),
      });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      // Per Milestone1ImplementationSpecification_FINAL.md §10: the form
      // stays open and the user's edited values are preserved on failure —
      // covers 404 (row deleted concurrently), 422 (validation), and
      // network failures alike, since all three reach this catch block.
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="px-6 py-4 grid grid-cols-[1fr_auto_auto] gap-4 items-center">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{assetTypeLabel(asset.asset_type)}</p>
          {(asset.institution ?? asset.description) && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {asset.institution ?? asset.description}
            </p>
          )}
        </div>
        <span className="text-sm font-medium tabular-nums shrink-0">
          {formatCurrency(asset.current_value)}
        </span>
        <button
          type="button"
          onClick={startEdit}
          aria-label={`Edit ${assetTypeLabel(asset.asset_type)} asset`}
          title="Edit"
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition shrink-0"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="px-6 py-4 space-y-3 bg-surface/40">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Asset type</span>
          <input
            value={assetTypeLabel(asset.asset_type)}
            disabled
            aria-label="Asset type (cannot be changed)"
            className="field-input w-full opacity-50 cursor-not-allowed"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Current value ($)</span>
          <input
            type="number"
            value={form.currentValue}
            onChange={(e) => setForm((f) => ({ ...f, currentValue: e.target.value }))}
            min="0"
            max="1000000000"
            step="0.01"
            required
            className="field-input w-full"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Institution</span>
        <input
          value={form.institution}
          onChange={(e) => setForm((f) => ({ ...f, institution: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Description</span>
        <input
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
        >
          {saving ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
            </>
          ) : (
            <>
              <Check className="h-3.5 w-3.5" /> Save changes
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// Liability editing (Milestone 1 Task 6). Same local-list-state-plus-splice
// strategy as Income/Expenses/Assets (Tasks 3-5): the PATCH response
// replaces the matching row in place — no re-fetch, no whole-page refresh,
// no stale UI. See `handleSaved` below. `PATCH /financials/liabilities/{id}`
// already existed before this milestone; no backend or API-client change
// was needed for this task.
//
// Editable fields: institution, description, balance (the FINAL spec's and
// the backend's actual field name — not "current_balance"), interest_rate,
// and monthly_payment. `monthly_payment` is included even though it wasn't
// named in this task's own field list, because
// Milestone1ImplementationSpecification_FINAL.md §2/§8 — the sole source of
// truth for this task — explicitly lists it as editable alongside the
// other four; omitting it here would leave the row un-editable for a field
// the frozen spec already requires.
function LiabilitiesSection() {
  const [state, setState] = useState<FetchState<Liability[]>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getLiabilities()
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", data });
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: e instanceof Error ? e.message : "Failed to load.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSaved(updated: Liability) {
    setState((prev) =>
      prev.status === "loaded"
        ? { status: "loaded", data: prev.data.map((r) => (r.id === updated.id ? updated : r)) }
        : prev,
    );
  }

  return (
    <SectionShell title="Liabilities" icon={Landmark}>
      {state.status === "loading" && <SectionLoading />}
      {state.status === "error" && <SectionError message={state.message} />}
      {state.status === "loaded" &&
        (state.data.length === 0 ? (
          <SectionEmpty message="No liabilities yet." />
        ) : (
          <div className="divide-y divide-border">
            {state.data.map((liability) => (
              <EditableLiabilityRow
                key={liability.id}
                liability={liability}
                onSaved={handleSaved}
              />
            ))}
          </div>
        ))}
    </SectionShell>
  );
}

type LiabilityEditForm = {
  institution: string;
  description: string;
  balance: string;
  // Displayed and edited as a whole-number percentage (e.g. "6.25" for
  // 6.25%); converted to the backend's stored decimal fraction (0.0625) on
  // save, rounded to 4 decimal places to avoid floating-point drift — the
  // same convention Milestone1ImplementationSpecification_FINAL.md §0.9/§8
  // uses for Planning Assumptions' percentage fields. Blank means "not
  // entered" (null), distinct from "0%".
  interestRatePercent: string;
  monthlyPayment: string;
};

function round4(n: number): number {
  return Math.round(n * 10000) / 10000;
}

function EditableLiabilityRow({
  liability,
  onSaved,
}: {
  liability: Liability;
  onSaved: (updated: Liability) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<LiabilityEditForm>({
    institution: liability.institution ?? "",
    description: liability.description ?? "",
    balance: String(liability.balance),
    interestRatePercent:
      liability.interest_rate != null ? String(round4(liability.interest_rate * 100)) : "",
    monthlyPayment: String(liability.monthly_payment ?? 0),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setForm({
      institution: liability.institution ?? "",
      description: liability.description ?? "",
      balance: String(liability.balance),
      interestRatePercent:
        liability.interest_rate != null ? String(round4(liability.interest_rate * 100)) : "",
      monthlyPayment: String(liability.monthly_payment ?? 0),
    });
    setError(null);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateLiability(liability.id, {
        institution: form.institution.trim() === "" ? undefined : form.institution,
        description: form.description.trim() === "" ? undefined : form.description,
        balance: Number(form.balance),
        interest_rate:
          form.interestRatePercent.trim() === ""
            ? undefined
            : round4(Number(form.interestRatePercent) / 100),
        monthly_payment: Number(form.monthlyPayment),
      });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      // Per Milestone1ImplementationSpecification_FINAL.md §10: the form
      // stays open and the user's edited values are preserved on failure —
      // covers 404 (row deleted concurrently), 422 (validation), and
      // network failures alike, since all three reach this catch block.
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    const rate =
      liability.interest_rate != null ? ` · ${(liability.interest_rate * 100).toFixed(2)}%` : "";
    return (
      <div className="px-6 py-4 grid grid-cols-[1fr_auto_auto] gap-4 items-center">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {liabilityTypeLabel(liability.liability_type)}
          </p>
          {(liability.institution ?? liability.description ?? rate) && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {(liability.institution ?? liability.description ?? "") + rate || "—"}
            </p>
          )}
        </div>
        <span className="text-sm font-medium tabular-nums shrink-0">
          {formatCurrency(liability.balance)}
        </span>
        <button
          type="button"
          onClick={startEdit}
          aria-label={`Edit ${liabilityTypeLabel(liability.liability_type)} liability`}
          title="Edit"
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition shrink-0"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="px-6 py-4 space-y-3 bg-surface/40">
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Liability type</span>
          <input
            value={liabilityTypeLabel(liability.liability_type)}
            disabled
            aria-label="Liability type (cannot be changed)"
            className="field-input w-full opacity-50 cursor-not-allowed"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Balance ($)</span>
          <input
            type="number"
            value={form.balance}
            onChange={(e) => setForm((f) => ({ ...f, balance: e.target.value }))}
            min="0"
            max="1000000000"
            step="0.01"
            required
            className="field-input w-full"
          />
        </label>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Interest rate (%)</span>
          <input
            type="number"
            value={form.interestRatePercent}
            onChange={(e) => setForm((f) => ({ ...f, interestRatePercent: e.target.value }))}
            min="0"
            max="100"
            step="0.01"
            placeholder="Not set"
            className="field-input w-full"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Monthly payment ($)</span>
          <input
            type="number"
            value={form.monthlyPayment}
            onChange={(e) => setForm((f) => ({ ...f, monthlyPayment: e.target.value }))}
            min="0"
            max="10000000"
            step="0.01"
            required
            className="field-input w-full"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Institution</span>
        <input
          value={form.institution}
          onChange={(e) => setForm((f) => ({ ...f, institution: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Description</span>
        <input
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          maxLength={255}
          className="field-input w-full"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
        >
          {saving ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
            </>
          ) : (
            <>
              <Check className="h-3.5 w-3.5" /> Save changes
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// Six fields per Milestone1ImplementationSpecification_FINAL.md §2/§6.5:
// inflation_rate, the three expected_return_* tiers, retirement_age, and
// social_security_monthly. `tax_rate` is deliberately excluded — it is
// marked deprecated in the backend model and this milestone does not build
// new UI around it (see the spec's §20, Rejected Decision 3).
function AssumptionsSection() {
  const state = useFetch(api.getAssumptions);
  return (
    <SectionShell title="Planning Assumptions" icon={Landmark}>
      {state.status === "loading" && <SectionLoading />}
      {state.status === "error" && <SectionError message={state.message} />}
      {state.status === "loaded" && <AssumptionsGrid assumptions={state.data} />}
    </SectionShell>
  );
}

function AssumptionsGrid({ assumptions }: { assumptions: FinancialAssumptions }) {
  const fields: { label: string; value: string }[] = [
    { label: "Inflation rate", value: `${(assumptions.inflation_rate * 100).toFixed(1)}%` },
    {
      label: "Expected return — Conservative",
      value: `${(assumptions.expected_return_conservative * 100).toFixed(1)}%`,
    },
    {
      label: "Expected return — Balanced",
      value: `${(assumptions.expected_return_balanced * 100).toFixed(1)}%`,
    },
    {
      label: "Expected return — Aggressive",
      value: `${(assumptions.expected_return_aggressive * 100).toFixed(1)}%`,
    },
    { label: "Target retirement age", value: `${assumptions.retirement_age}` },
    {
      label: "Social Security / pension",
      value: `${formatCurrency(assumptions.social_security_monthly)}/mo`,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 divide-x divide-y divide-border">
      {fields.map((f) => (
        <div key={f.label} className="px-6 py-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{f.label}</p>
          <p className="text-lg font-display mt-1 tabular-nums">{f.value}</p>
        </div>
      ))}
    </div>
  );
}

function FinancialsPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted-foreground">
          Keep your income, expenses, assets, and liabilities current so every number on your
          Dashboard reflects real life.
        </p>
      </div>

      {/* LifeEventIntegrationReview.md Phase 2 — a raise, a new loan, a home
          sale, etc. usually touch several of the rows below at once; Life
          Events records all of them together (and can undo them together). */}
      <Link
        to="/app/life-events"
        className="surface-card p-4 flex items-center gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <History className="h-4 w-4 text-cyan shrink-0" aria-hidden="true" />
        <p className="text-sm">
          Something changed in your life — a raise, a new loan, a move?{" "}
          <span className="text-cyan">Record it as a life event</span> and we'll update everything
          it affects at once.
        </p>
      </Link>

      <IncomeSection />
      <ExpensesSection />
      <AssetsSection />
      <LiabilitiesSection />
      <AssumptionsSection />
    </div>
  );
}
