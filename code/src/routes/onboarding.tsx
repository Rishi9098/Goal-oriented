import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowRight, Check, Eye, EyeOff, Loader2, Sparkles } from "lucide-react";
import { auth, api, setTokens } from "@/lib/api";
import type { Asset, Expense, IncomeSource, Liability } from "@/lib/api";
import type { Goal } from "@/lib/mock-data";
import {
  StepPersonal,
  StepFamily,
  StepEmployment,
  StepGoal,
  StepAssumptions,
  InputField,
  type ProfileFormState,
  type GoalFormState,
  type AssumptionsFormState,
} from "@/components/onboarding/wizard-steps";
import {
  StepIncome,
  StepExpenses,
  StepLiquidAssets,
  StepInvestments,
  StepLiabilities,
} from "@/components/onboarding/list-steps";

export const Route = createFileRoute("/onboarding")({
  head: () => ({ meta: [{ title: "Get started — Northstar" }] }),
  component: Onboarding,
});

// ── Constants ─────────────────────────────────────────────────────────────────

const STEP_LABELS = [
  "Create account",
  "Personal info",
  "Family",
  "Employment",
  "Income",
  "Expenses",
  "Cash & savings",
  "Investments",
  "Debts",
  "First goal",
  "Assumptions",
  "Done",
];

const TOTAL_WIZARD_STEPS = 10; // steps 1-10 (excludes 0=account and 11=done)

// ── Initial state ─────────────────────────────────────────────────────────────

const DEFAULT_PROFILE: ProfileFormState = {
  date_of_birth: "",
  gender: "",
  marital_status: "single",
  dependents: "0",
  country: "",
  state_province: "",
  employment_status: "employed",
  employer: "",
  occupation: "",
};

const DEFAULT_GOAL: GoalFormState = {
  name: "",
  category: "retirement",
  targetAmount: "500000",
  monthlyContribution: "500",
  yearsToGoal: "20",
  riskProfile: "balanced",
};

const DEFAULT_ASSUMPTIONS: AssumptionsFormState = {
  inflation_rate: "3",
  retirement_age: "65",
  social_security_monthly: "0",
  tax_rate: "22",
};

// ── Root component ────────────────────────────────────────────────────────────

function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Step 0 — account
  const [account, setAccount] = useState({ fullName: "", email: "", password: "", confirm: "" });
  const [showPw, setShowPw] = useState(false);
  const [registering, setRegistering] = useState(false);

  // Steps 1-3 — profile
  const [profile, setProfile] = useState<ProfileFormState>(DEFAULT_PROFILE);

  // Steps 4-8 — financial lists
  const [incomeItems, setIncomeItems] = useState<IncomeSource[]>([]);
  const [expenseItems, setExpenseItems] = useState<Expense[]>([]);
  const [liquidAssets, setLiquidAssets] = useState<Asset[]>([]);
  const [investments, setInvestments] = useState<Asset[]>([]);
  const [liabilities, setLiabilities] = useState<Liability[]>([]);

  // Step 9 — goal
  const [goal, setGoal] = useState<GoalFormState>(DEFAULT_GOAL);

  // Step 10 — assumptions
  const [assumptions, setAssumptions] = useState<AssumptionsFormState>(DEFAULT_ASSUMPTIONS);

  // ── Navigation helpers ──────────────────────────────────────────────────────

  const advance = () => {
    setError(null);
    setStep((s) => s + 1);
  };

  const back = () => {
    setError(null);
    setStep((s) => s - 1);
  };

  const saveAndAdvance = async (profilePatch?: Record<string, unknown>) => {
    setSaving(true);
    try {
      await api.upsertProfile({ ...(profilePatch ?? {}), current_step: step + 1 });
    } catch {
      // profile save is best-effort; never block the wizard
    } finally {
      setSaving(false);
    }
    advance();
  };

  // ── Step handlers ───────────────────────────────────────────────────────────

  const handleAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (account.password !== account.confirm) { setError("Passwords do not match."); return; }
    if (account.password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setRegistering(true);
    try {
      await auth.register(account.email, account.password, account.fullName);
      const tokens = await auth.login(account.email, account.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      advance();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setRegistering(false);
    }
  };

  const handlePersonal = (e: React.FormEvent) => {
    e.preventDefault();
    void saveAndAdvance({
      date_of_birth: profile.date_of_birth || undefined,
      gender: profile.gender || undefined,
      country: profile.country || undefined,
      state_province: profile.state_province || undefined,
    });
  };

  const handleFamily = (e: React.FormEvent) => {
    e.preventDefault();
    void saveAndAdvance({
      marital_status: profile.marital_status || undefined,
      dependents: parseInt(profile.dependents) || 0,
    });
  };

  const handleEmployment = (e: React.FormEvent) => {
    e.preventDefault();
    void saveAndAdvance({
      employment_status: profile.employment_status || undefined,
      employer: profile.employer || undefined,
      occupation: profile.occupation || undefined,
    });
  };

  const handleGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.name.trim()) { setError("Please give your goal a name."); return; }
    setError(null);
    setSaving(true);
    try {
      const targetDate = new Date();
      targetDate.setFullYear(targetDate.getFullYear() + Number(goal.yearsToGoal));
      await api.createGoal({
        name: goal.name,
        category: goal.category as Goal["category"],
        targetAmount: Number(goal.targetAmount),
        currentAmount: 0,
        targetDate: targetDate.toISOString().split("T")[0],
        monthlyContribution: Number(goal.monthlyContribution),
        riskProfile: goal.riskProfile as Goal["riskProfile"],
      });
      await api.upsertProfile({ current_step: step + 1 }).catch(() => {});
      advance();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save goal.");
    } finally {
      setSaving(false);
    }
  };

  const handleAssumptions = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.upsertAssumptions({
        inflation_rate: parseFloat(assumptions.inflation_rate) / 100,
        tax_rate: parseFloat(assumptions.tax_rate) / 100,
        retirement_age: parseInt(assumptions.retirement_age),
        social_security_monthly: parseFloat(assumptions.social_security_monthly),
      });
      await api.upsertProfile({ onboarding_complete: true, current_step: 11 }).catch(() => {});
      advance();
    } catch {
      advance(); // proceed even if save fails
    } finally {
      setSaving(false);
    }
  };

  // ── List step helpers ───────────────────────────────────────────────────────

  const addIncome = async (data: { source_type: string; description?: string; annual_amount: number }) => {
    const item = await api.createIncome(data);
    setIncomeItems((prev) => [...prev, item]);
  };

  const removeIncome = async (id: string) => {
    await api.deleteIncome(id);
    setIncomeItems((prev) => prev.filter((i) => i.id !== id));
  };

  const addExpense = async (data: { category: string; description?: string; monthly_amount: number }) => {
    const item = await api.createExpense(data);
    setExpenseItems((prev) => [...prev, item]);
  };

  const removeExpense = async (id: string) => {
    await api.deleteExpense(id);
    setExpenseItems((prev) => prev.filter((i) => i.id !== id));
  };

  const addLiquid = async (data: { asset_type: string; institution?: string; description?: string; current_value: number }) => {
    const item = await api.createAsset(data);
    setLiquidAssets((prev) => [...prev, item]);
  };

  const removeLiquid = async (id: string) => {
    await api.deleteAsset(id);
    setLiquidAssets((prev) => prev.filter((i) => i.id !== id));
  };

  const addInvestment = async (data: { asset_type: string; institution?: string; description?: string; current_value: number }) => {
    const item = await api.createAsset(data);
    setInvestments((prev) => [...prev, item]);
  };

  const removeInvestment = async (id: string) => {
    await api.deleteAsset(id);
    setInvestments((prev) => prev.filter((i) => i.id !== id));
  };

  const addLiability = async (data: { liability_type: string; institution?: string; description?: string; balance: number; interest_rate?: number; monthly_payment?: number }) => {
    const item = await api.createLiability(data);
    setLiabilities((prev) => [...prev, item]);
  };

  const removeLiability = async (id: string) => {
    await api.deleteLiability(id);
    setLiabilities((prev) => prev.filter((i) => i.id !== id));
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen hero-bg flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-cyan shadow-glow" />
            <span className="font-display text-lg">Northstar</span>
          </div>
        </div>

        {/* Progress bar (shown for steps 1-10) */}
        {step >= 1 && step <= TOTAL_WIZARD_STEPS && (
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-medium text-foreground">{STEP_LABELS[step]}</span>
              <span className="text-xs text-muted-foreground">
                {step} / {TOTAL_WIZARD_STEPS}
              </span>
            </div>
            <div className="h-1.5 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-cyan transition-all duration-500 ease-out"
                style={{ width: `${(step / TOTAL_WIZARD_STEPS) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Card */}
        <div className="surface-card p-8">
          {error && (
            <div className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {step === 0 && (
            <AccountStep
              form={account}
              onChange={(patch) => setAccount((prev) => ({ ...prev, ...patch }))}
              onSubmit={handleAccount}
              loading={registering}
              showPw={showPw}
              onTogglePw={() => setShowPw((v) => !v)}
            />
          )}

          {step === 1 && (
            <StepPersonal
              form={profile}
              onChange={(patch) => setProfile((prev) => ({ ...prev, ...patch }))}
              onSubmit={handlePersonal}
              onBack={back}
              onSkip={() => void saveAndAdvance()}
              loading={saving}
            />
          )}

          {step === 2 && (
            <StepFamily
              form={profile}
              onChange={(patch) => setProfile((prev) => ({ ...prev, ...patch }))}
              onSubmit={handleFamily}
              onBack={back}
              onSkip={() => void saveAndAdvance()}
              loading={saving}
            />
          )}

          {step === 3 && (
            <StepEmployment
              form={profile}
              onChange={(patch) => setProfile((prev) => ({ ...prev, ...patch }))}
              onSubmit={handleEmployment}
              onBack={back}
              onSkip={() => void saveAndAdvance()}
              loading={saving}
            />
          )}

          {step === 4 && (
            <StepIncome
              items={incomeItems}
              onAdd={addIncome}
              onRemove={removeIncome}
              onNext={() => void saveAndAdvance()}
              onBack={back}
              nextLoading={saving}
            />
          )}

          {step === 5 && (
            <StepExpenses
              items={expenseItems}
              onAdd={addExpense}
              onRemove={removeExpense}
              onNext={() => void saveAndAdvance()}
              onBack={back}
              nextLoading={saving}
            />
          )}

          {step === 6 && (
            <StepLiquidAssets
              items={liquidAssets}
              onAdd={addLiquid}
              onRemove={removeLiquid}
              onNext={() => void saveAndAdvance()}
              onBack={back}
              nextLoading={saving}
            />
          )}

          {step === 7 && (
            <StepInvestments
              items={investments}
              onAdd={addInvestment}
              onRemove={removeInvestment}
              onNext={() => void saveAndAdvance()}
              onBack={back}
              nextLoading={saving}
            />
          )}

          {step === 8 && (
            <StepLiabilities
              items={liabilities}
              onAdd={addLiability}
              onRemove={removeLiability}
              onNext={() => void saveAndAdvance()}
              onBack={back}
              nextLoading={saving}
            />
          )}

          {step === 9 && (
            <StepGoal
              form={goal}
              onChange={(patch) => setGoal((prev) => ({ ...prev, ...patch }))}
              onSubmit={handleGoal}
              onBack={back}
              onSkip={() => void saveAndAdvance()}
              loading={saving}
            />
          )}

          {step === 10 && (
            <StepAssumptions
              form={assumptions}
              onChange={(patch) => setAssumptions((prev) => ({ ...prev, ...patch }))}
              onSubmit={handleAssumptions}
              onBack={back}
              onSkip={() => {
                void api.upsertProfile({ onboarding_complete: true, current_step: 11 }).catch(() => {});
                advance();
              }}
              loading={saving}
            />
          )}

          {step === 11 && (
            <DoneStep
              name={account.fullName}
              onContinue={() => navigate({ to: "/app" })}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Step 0: Account ───────────────────────────────────────────────────────────

function AccountStep({
  form,
  onChange,
  onSubmit,
  loading,
  showPw,
  onTogglePw,
}: {
  form: { fullName: string; email: string; password: string; confirm: string };
  onChange: (patch: Partial<{ fullName: string; email: string; password: string; confirm: string }>) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
  showPw: boolean;
  onTogglePw: () => void;
}) {
  return (
    <>
      <div className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-3 py-1 text-xs text-muted-foreground mb-4">
        <Sparkles className="h-3.5 w-3.5 text-cyan" /> 10-step setup
      </div>
      <h1 className="font-display text-2xl tracking-tight">Create your account</h1>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Start building your financial plan — free forever.
      </p>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <InputField
          label="Full name"
          value={form.fullName}
          onChange={(v) => onChange({ fullName: v })}
          placeholder="Alex Reyes"
          required
          autoComplete="name"
          minLength={2}
        />
        <InputField
          label="Email address"
          type="email"
          value={form.email}
          onChange={(v) => onChange({ email: v })}
          placeholder="you@domain.com"
          required
          autoComplete="email"
        />
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Password
          </label>
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5 focus-within:border-primary transition-colors">
            <input
              type={showPw ? "text" : "password"}
              value={form.password}
              onChange={(e) => onChange({ password: e.target.value })}
              placeholder="At least 8 characters"
              required
              minLength={8}
              autoComplete="new-password"
              className="flex-1 bg-transparent text-sm outline-none"
            />
            <button
              type="button"
              onClick={onTogglePw}
              className="text-muted-foreground hover:text-foreground transition-colors"
              tabIndex={-1}
            >
              {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <InputField
          label="Confirm password"
          type={showPw ? "text" : "password"}
          value={form.confirm}
          onChange={(v) => onChange({ confirm: v })}
          placeholder="Repeat your password"
          required
          autoComplete="new-password"
        />

        <button
          type="submit"
          disabled={loading}
          className="mt-2 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Creating account…
            </>
          ) : (
            <>
              Get started <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>

        <p className="text-center text-xs text-muted-foreground">
          Already have an account?{" "}
          <a href="/auth/sign-in" className="text-cyan hover:underline">
            Sign in
          </a>
        </p>
      </form>
    </>
  );
}

// ── Step 11: Done ─────────────────────────────────────────────────────────────

function DoneStep({
  name,
  onContinue,
}: {
  name: string;
  onContinue: () => void;
}) {
  return (
    <div className="text-center py-4">
      <div className="mx-auto h-14 w-14 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center shadow-glow mb-5">
        <Check className="h-6 w-6 text-primary-foreground" />
      </div>
      <h1 className="font-display text-2xl tracking-tight">
        You're all set{name ? `, ${name.split(" ")[0]}` : ""}!
      </h1>
      <p className="mt-2 text-sm text-muted-foreground max-w-xs mx-auto">
        Your financial profile is ready. The dashboard will now reflect your
        real numbers and run personalized projections.
      </p>
      <button
        onClick={onContinue}
        className="mt-8 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-6 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
      >
        Open my dashboard <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
