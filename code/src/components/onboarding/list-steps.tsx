import { useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, Plus, Trash2 } from "lucide-react";
import type { Asset, Expense, IncomeSource, Liability } from "@/lib/api";
import {
  INCOME_TYPES,
  EXPENSE_CATEGORIES,
  LIQUID_ASSET_TYPES,
  INVESTMENT_TYPES,
  LIABILITY_TYPES,
} from "@/lib/financial-labels";
import { InputField, SelectField } from "./wizard-steps";

// ── Currency formatter ────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

// Value/label pairs now live in lib/financial-labels.ts (MicrocopyAudit.md
// Phase 4) so Financials can look up the same friendly labels shown here,
// instead of displaying a raw stored value verbatim.

// ── Shared list display ───────────────────────────────────────────────────────

type ListRow = { id: string; label: string; sublabel?: string | null; amount: string };

function ItemList({
  rows,
  onRemove,
}: {
  rows: ListRow[];
  onRemove: (id: string) => Promise<void>;
}) {
  const [removing, setRemoving] = useState<string | null>(null);

  const handleRemove = async (id: string) => {
    setRemoving(id);
    try {
      await onRemove(id);
    } finally {
      setRemoving(null);
    }
  };

  if (rows.length === 0) return null;

  return (
    <ul className="space-y-2 mb-4">
      {rows.map((row) => (
        <li
          key={row.id}
          className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2.5"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{row.label}</p>
            {row.sublabel && (
              <p className="text-xs text-muted-foreground truncate">{row.sublabel}</p>
            )}
          </div>
          <div className="flex items-center gap-3 ml-3 shrink-0">
            <span className="text-sm font-medium text-cyan">{row.amount}</span>
            <button
              type="button"
              disabled={removing === row.id}
              onClick={() => handleRemove(row.id)}
              className="text-muted-foreground hover:text-destructive transition disabled:opacity-40"
            >
              {removing === row.id ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function AddFormShell({
  label,
  error,
  adding,
  children,
}: {
  label: string;
  error: string | null;
  adding: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface/50 p-4 space-y-3 mb-5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {children}
      <button
        type="submit"
        disabled={adding}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong transition disabled:opacity-50"
      >
        {adding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
        Add
      </button>
    </div>
  );
}

function ListNavRow({
  onBack,
  onNext,
  hasItems,
  loading,
}: {
  onBack: () => void;
  onNext: () => void;
  hasItems: boolean;
  loading: boolean;
}) {
  return (
    <div className="flex gap-3">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-4 py-2.5 text-sm text-muted-foreground hover:border-border-strong hover:text-foreground transition"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={loading}
        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50"
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {hasItems ? "Continue" : "Skip"}
        {!loading && <ArrowRight className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ── Step 4: Income ────────────────────────────────────────────────────────────

type IncomeForm = { source_type: string; description: string; annual_amount: string };

export function StepIncome({
  items,
  onAdd,
  onRemove,
  onNext,
  onBack,
  nextLoading,
}: {
  items: IncomeSource[];
  onAdd: (data: {
    source_type: string;
    description?: string;
    annual_amount: number;
  }) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  onNext: () => void;
  onBack: () => void;
  nextLoading: boolean;
}) {
  const [form, setForm] = useState<IncomeForm>({
    source_type: "salary",
    description: "",
    annual_amount: "",
  });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(form.annual_amount);
    if (!amount || amount <= 0) {
      setError("Enter a valid annual amount.");
      return;
    }
    setError(null);
    setAdding(true);
    try {
      await onAdd({
        source_type: form.source_type,
        description: form.description || undefined,
        annual_amount: amount,
      });
      setForm({ source_type: "salary", description: "", annual_amount: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add.");
    } finally {
      setAdding(false);
    }
  };

  // A typed-but-not-yet-added amount must never be silently discarded by
  // Continue/Skip — auto-save it first, then advance (or stay put and show
  // the error if the save itself fails).
  const pendingAmount = Number(form.annual_amount);
  const hasPendingEntry = pendingAmount > 0;

  const handleNext = async () => {
    if (hasPendingEntry) {
      setError(null);
      setAdding(true);
      try {
        await onAdd({
          source_type: form.source_type,
          description: form.description || undefined,
          annual_amount: pendingAmount,
        });
        setForm({ source_type: "salary", description: "", annual_amount: "" });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to add.");
        setAdding(false);
        return;
      }
      setAdding(false);
    }
    onNext();
  };

  const rows: ListRow[] = items.map((i) => ({
    id: i.id,
    label: INCOME_TYPES.find((t) => t.value === i.source_type)?.label ?? i.source_type,
    sublabel: i.description,
    amount: `${fmt(i.annual_amount)}/yr`,
  }));

  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Income sources</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-5">
        Add each annual income stream. Powers your savings rate projections.
      </p>
      <ItemList rows={rows} onRemove={onRemove} />
      <form onSubmit={handleAdd}>
        <AddFormShell label="Add income source" error={error} adding={adding}>
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Type"
              value={form.source_type}
              onChange={(v) => setForm((f) => ({ ...f, source_type: v }))}
              options={INCOME_TYPES}
            />
            <InputField
              label="Annual amount ($)"
              type="number"
              value={form.annual_amount}
              onChange={(v) => setForm((f) => ({ ...f, annual_amount: v }))}
              placeholder="80000"
              min="1"
            />
          </div>
          <InputField
            label="Description (optional)"
            value={form.description}
            onChange={(v) => setForm((f) => ({ ...f, description: v }))}
            placeholder="e.g. Software Engineer salary"
          />
        </AddFormShell>
      </form>
      <ListNavRow
        onBack={onBack}
        onNext={handleNext}
        hasItems={items.length > 0 || hasPendingEntry}
        loading={nextLoading || adding}
      />
    </>
  );
}

// ── Step 5: Expenses ──────────────────────────────────────────────────────────

type ExpenseForm = { category: string; description: string; monthly_amount: string };

export function StepExpenses({
  items,
  onAdd,
  onRemove,
  onNext,
  onBack,
  nextLoading,
}: {
  items: Expense[];
  onAdd: (data: {
    category: string;
    description?: string;
    monthly_amount: number;
  }) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  onNext: () => void;
  onBack: () => void;
  nextLoading: boolean;
}) {
  const [form, setForm] = useState<ExpenseForm>({
    category: "housing",
    description: "",
    monthly_amount: "",
  });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(form.monthly_amount);
    if (!amount || amount < 0) {
      setError("Enter a valid monthly amount.");
      return;
    }
    setError(null);
    setAdding(true);
    try {
      await onAdd({
        category: form.category,
        description: form.description || undefined,
        monthly_amount: amount,
      });
      setForm({ category: "housing", description: "", monthly_amount: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add.");
    } finally {
      setAdding(false);
    }
  };

  // A typed-but-not-yet-added amount must never be silently discarded by
  // Continue/Skip — auto-save it first, then advance (or stay put and show
  // the error if the save itself fails).
  const pendingAmount = Number(form.monthly_amount);
  const hasPendingEntry = pendingAmount > 0;

  const handleNext = async () => {
    if (hasPendingEntry) {
      setError(null);
      setAdding(true);
      try {
        await onAdd({
          category: form.category,
          description: form.description || undefined,
          monthly_amount: pendingAmount,
        });
        setForm({ category: "housing", description: "", monthly_amount: "" });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to add.");
        setAdding(false);
        return;
      }
      setAdding(false);
    }
    onNext();
  };

  const rows: ListRow[] = items.map((i) => ({
    id: i.id,
    label: EXPENSE_CATEGORIES.find((c) => c.value === i.category)?.label ?? i.category,
    sublabel: i.description,
    amount: `${fmt(i.monthly_amount)}/mo`,
  }));

  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Monthly expenses</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-5">
        Add your regular monthly costs. Used to calculate your savings capacity.
      </p>
      <ItemList rows={rows} onRemove={onRemove} />
      <form onSubmit={handleAdd}>
        <AddFormShell label="Add expense" error={error} adding={adding}>
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Category"
              value={form.category}
              onChange={(v) => setForm((f) => ({ ...f, category: v }))}
              options={EXPENSE_CATEGORIES}
            />
            <InputField
              label="Monthly amount ($)"
              type="number"
              value={form.monthly_amount}
              onChange={(v) => setForm((f) => ({ ...f, monthly_amount: v }))}
              placeholder="2000"
              min="0"
            />
          </div>
          <InputField
            label="Description (optional)"
            value={form.description}
            onChange={(v) => setForm((f) => ({ ...f, description: v }))}
            placeholder="e.g. Rent"
          />
        </AddFormShell>
      </form>
      <ListNavRow
        onBack={onBack}
        onNext={handleNext}
        hasItems={items.length > 0 || hasPendingEntry}
        loading={nextLoading || adding}
      />
    </>
  );
}

// ── Step 6: Liquid assets ─────────────────────────────────────────────────────

type AssetForm = {
  asset_type: string;
  institution: string;
  description: string;
  current_value: string;
};

function AssetStep({
  title,
  subtitle,
  types,
  items,
  onAdd,
  onRemove,
  onNext,
  onBack,
  nextLoading,
}: {
  title: string;
  subtitle: string;
  types: { value: string; label: string }[];
  items: Asset[];
  onAdd: (data: {
    asset_type: string;
    institution?: string;
    description?: string;
    current_value: number;
  }) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  onNext: () => void;
  onBack: () => void;
  nextLoading: boolean;
}) {
  const [form, setForm] = useState<AssetForm>({
    asset_type: types[0].value,
    institution: "",
    description: "",
    current_value: "",
  });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = Number(form.current_value);
    if (!value || value < 0) {
      setError("Enter a valid account balance.");
      return;
    }
    setError(null);
    setAdding(true);
    try {
      await onAdd({
        asset_type: form.asset_type,
        institution: form.institution || undefined,
        description: form.description || undefined,
        current_value: value,
      });
      setForm({ asset_type: types[0].value, institution: "", description: "", current_value: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add.");
    } finally {
      setAdding(false);
    }
  };

  // A typed-but-not-yet-added balance must never be silently discarded by
  // Continue/Skip — auto-save it first, then advance (or stay put and show
  // the error if the save itself fails).
  const pendingValue = Number(form.current_value);
  const hasPendingEntry = pendingValue > 0;

  const handleNext = async () => {
    if (hasPendingEntry) {
      setError(null);
      setAdding(true);
      try {
        await onAdd({
          asset_type: form.asset_type,
          institution: form.institution || undefined,
          description: form.description || undefined,
          current_value: pendingValue,
        });
        setForm({
          asset_type: types[0].value,
          institution: "",
          description: "",
          current_value: "",
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to add.");
        setAdding(false);
        return;
      }
      setAdding(false);
    }
    onNext();
  };

  const rows: ListRow[] = items.map((i) => ({
    id: i.id,
    label: `${types.find((t) => t.value === i.asset_type)?.label ?? i.asset_type}${i.institution ? ` — ${i.institution}` : ""}`,
    sublabel: i.description,
    amount: fmt(i.current_value),
  }));

  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-5">{subtitle}</p>
      <ItemList rows={rows} onRemove={onRemove} />
      <form onSubmit={handleAdd}>
        <AddFormShell label="Add account" error={error} adding={adding}>
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Type"
              value={form.asset_type}
              onChange={(v) => setForm((f) => ({ ...f, asset_type: v }))}
              options={types}
            />
            <InputField
              label="Current balance ($)"
              type="number"
              value={form.current_value}
              onChange={(v) => setForm((f) => ({ ...f, current_value: v }))}
              placeholder="10000"
              min="0"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <InputField
              label="Institution (optional)"
              value={form.institution}
              onChange={(v) => setForm((f) => ({ ...f, institution: v }))}
              placeholder="e.g. Chase"
            />
            <InputField
              label="Label (optional)"
              value={form.description}
              onChange={(v) => setForm((f) => ({ ...f, description: v }))}
              placeholder="e.g. Emergency fund"
            />
          </div>
        </AddFormShell>
      </form>
      <ListNavRow
        onBack={onBack}
        onNext={handleNext}
        hasItems={items.length > 0 || hasPendingEntry}
        loading={nextLoading || adding}
      />
    </>
  );
}

export function StepLiquidAssets(
  props: Omit<Parameters<typeof AssetStep>[0], "title" | "subtitle" | "types">,
) {
  return (
    <AssetStep
      title="Cash & savings"
      subtitle="Checking, savings, and money market accounts."
      types={LIQUID_ASSET_TYPES}
      {...props}
    />
  );
}

export function StepInvestments(
  props: Omit<Parameters<typeof AssetStep>[0], "title" | "subtitle" | "types">,
) {
  return (
    <AssetStep
      title="Investments"
      subtitle="Brokerage accounts, 401(k), IRA, and other investment holdings."
      types={INVESTMENT_TYPES}
      {...props}
    />
  );
}

// ── Step 8: Liabilities ───────────────────────────────────────────────────────

type LiabilityForm = {
  liability_type: string;
  institution: string;
  description: string;
  balance: string;
  interest_rate: string;
  monthly_payment: string;
};

export function StepLiabilities({
  items,
  onAdd,
  onRemove,
  onNext,
  onBack,
  nextLoading,
}: {
  items: Liability[];
  onAdd: (data: {
    liability_type: string;
    institution?: string;
    description?: string;
    balance: number;
    interest_rate?: number;
    monthly_payment?: number;
  }) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  onNext: () => void;
  onBack: () => void;
  nextLoading: boolean;
}) {
  const [form, setForm] = useState<LiabilityForm>({
    liability_type: "mortgage",
    institution: "",
    description: "",
    balance: "",
    interest_rate: "",
    monthly_payment: "",
  });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const balance = Number(form.balance);
    if (!balance || balance < 0) {
      setError("Enter a valid balance.");
      return;
    }
    setError(null);
    setAdding(true);
    try {
      await onAdd({
        liability_type: form.liability_type,
        institution: form.institution || undefined,
        description: form.description || undefined,
        balance,
        interest_rate: form.interest_rate ? Number(form.interest_rate) / 100 : undefined,
        monthly_payment: form.monthly_payment ? Number(form.monthly_payment) : undefined,
      });
      setForm({
        liability_type: "mortgage",
        institution: "",
        description: "",
        balance: "",
        interest_rate: "",
        monthly_payment: "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add.");
    } finally {
      setAdding(false);
    }
  };

  // A typed-but-not-yet-added balance must never be silently discarded by
  // Continue/Skip — auto-save it first, then advance (or stay put and show
  // the error if the save itself fails).
  const pendingBalance = Number(form.balance);
  const hasPendingEntry = pendingBalance > 0;

  const handleNext = async () => {
    if (hasPendingEntry) {
      setError(null);
      setAdding(true);
      try {
        await onAdd({
          liability_type: form.liability_type,
          institution: form.institution || undefined,
          description: form.description || undefined,
          balance: pendingBalance,
          interest_rate: form.interest_rate ? Number(form.interest_rate) / 100 : undefined,
          monthly_payment: form.monthly_payment ? Number(form.monthly_payment) : undefined,
        });
        setForm({
          liability_type: "mortgage",
          institution: "",
          description: "",
          balance: "",
          interest_rate: "",
          monthly_payment: "",
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to add.");
        setAdding(false);
        return;
      }
      setAdding(false);
    }
    onNext();
  };

  const rows: ListRow[] = items.map((i) => ({
    id: i.id,
    label: `${LIABILITY_TYPES.find((t) => t.value === i.liability_type)?.label ?? i.liability_type}${i.institution ? ` — ${i.institution}` : ""}`,
    sublabel: i.monthly_payment ? `${fmt(i.monthly_payment)}/mo payment` : null,
    amount: fmt(i.balance),
  }));

  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Debts & liabilities</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-5">
        Mortgages, loans, and credit card balances that affect your net worth.
      </p>
      <ItemList rows={rows} onRemove={onRemove} />
      <form onSubmit={handleAdd}>
        <AddFormShell label="Add debt" error={error} adding={adding}>
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Type"
              value={form.liability_type}
              onChange={(v) => setForm((f) => ({ ...f, liability_type: v }))}
              options={LIABILITY_TYPES}
            />
            <InputField
              label="Balance ($)"
              type="number"
              value={form.balance}
              onChange={(v) => setForm((f) => ({ ...f, balance: v }))}
              placeholder="250000"
              min="0"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <InputField
              label="Interest rate (% p.a.)"
              type="number"
              value={form.interest_rate}
              onChange={(v) => setForm((f) => ({ ...f, interest_rate: v }))}
              placeholder="6.5"
              min="0"
              max="100"
              step="0.1"
            />
            <InputField
              label="Monthly payment ($)"
              type="number"
              value={form.monthly_payment}
              onChange={(v) => setForm((f) => ({ ...f, monthly_payment: v }))}
              placeholder="1500"
              min="0"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <InputField
              label="Institution (optional)"
              value={form.institution}
              onChange={(v) => setForm((f) => ({ ...f, institution: v }))}
              placeholder="e.g. Wells Fargo"
            />
            <InputField
              label="Label (optional)"
              value={form.description}
              onChange={(v) => setForm((f) => ({ ...f, description: v }))}
              placeholder="e.g. Primary mortgage"
            />
          </div>
        </AddFormShell>
      </form>
      <ListNavRow
        onBack={onBack}
        onNext={handleNext}
        hasItems={items.length > 0 || hasPendingEntry}
        loading={nextLoading || adding}
      />
    </>
  );
}
