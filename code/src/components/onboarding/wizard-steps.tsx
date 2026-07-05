import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import type { Goal } from "@/lib/mock-data";

// ── Shared field components ───────────────────────────────────────────────────

export function InputField({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required,
  min,
  max,
  step,
  autoComplete,
  minLength,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  min?: string;
  max?: string;
  step?: string;
  autoComplete?: string;
  minLength?: number;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        min={min}
        max={max}
        step={step}
        autoComplete={autoComplete}
        minLength={minLength}
        className="field-input"
      />
    </div>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="field-input">
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function NavRow({
  onBack,
  submitLabel = "Continue",
  loading = false,
  onSkip,
}: {
  onBack?: () => void;
  submitLabel?: string;
  loading?: boolean;
  onSkip?: () => void;
}) {
  return (
    <div className="flex gap-3 pt-2">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-4 py-2.5 text-sm text-muted-foreground hover:border-border-strong hover:text-foreground transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </button>
      )}
      {onSkip && (
        <button
          type="button"
          onClick={onSkip}
          className="rounded-lg border border-border bg-surface px-4 py-2.5 text-sm text-muted-foreground hover:border-border-strong hover:text-foreground transition"
        >
          Skip
        </button>
      )}
      <button
        type="submit"
        disabled={loading}
        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {loading ? "Saving…" : submitLabel}
        {!loading && <ArrowRight className="h-4 w-4" />}
      </button>
    </div>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type ProfileFormState = {
  date_of_birth: string;
  gender: string;
  marital_status: string;
  dependents: string;
  country: string;
  state_province: string;
  employment_status: string;
  employer: string;
  occupation: string;
};

export type GoalFormState = {
  name: string;
  category: string;
  targetAmount: string;
  monthlyContribution: string;
  yearsToGoal: string;
  riskProfile: string;
};

export type AssumptionsFormState = {
  inflation_rate: string;
  retirement_age: string;
  social_security_monthly: string;
  tax_rate: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const GENDERS = [
  { value: "", label: "Prefer not to say" },
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "non_binary", label: "Non-binary" },
  { value: "other", label: "Other" },
];

const COUNTRIES = [
  { value: "US", label: "United States" },
  { value: "CA", label: "Canada" },
  { value: "GB", label: "United Kingdom" },
  { value: "AU", label: "Australia" },
  { value: "IN", label: "India" },
  { value: "other", label: "Other" },
];

const MARITAL_STATUSES = [
  { value: "single", label: "Single" },
  { value: "married", label: "Married / partnered" },
  { value: "divorced", label: "Divorced" },
  { value: "widowed", label: "Widowed" },
];

const EMPLOYMENT_STATUSES = [
  { value: "employed", label: "Employed" },
  { value: "self_employed", label: "Self-employed" },
  { value: "unemployed", label: "Unemployed" },
  { value: "retired", label: "Retired" },
  { value: "student", label: "Student" },
  { value: "other", label: "Other" },
];

export const CATEGORIES = [
  { value: "retirement", label: "Retirement" },
  { value: "education", label: "Education" },
  { value: "home", label: "Home purchase" },
  { value: "travel", label: "Travel / sabbatical" },
  { value: "wealth", label: "Wealth building" },
  { value: "emergency", label: "Emergency fund" },
];

export const RISK_OPTIONS = [
  { value: "conservative", label: "Conservative", sub: "30 / 70 — stability over growth" },
  { value: "balanced", label: "Balanced", sub: "60 / 40 — moderate risk" },
  { value: "aggressive", label: "Aggressive", sub: "90 / 10 — growth-focused" },
];

// ── Step 1: Personal info ─────────────────────────────────────────────────────

export function StepPersonal({
  form,
  onChange,
  onSubmit,
  onBack,
  onSkip,
  loading,
}: {
  form: ProfileFormState;
  onChange: (patch: Partial<ProfileFormState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Personal info</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Helps tailor projections to your tax region and life stage.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <InputField
          label="Date of birth"
          type="date"
          value={form.date_of_birth}
          onChange={(v) => onChange({ date_of_birth: v })}
          max={new Date(Date.now() - 18 * 365.25 * 86400000).toISOString().split("T")[0]}
        />
        <SelectField
          label="Gender"
          value={form.gender}
          onChange={(v) => onChange({ gender: v })}
          options={GENDERS}
        />
        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label="Country"
            value={form.country}
            onChange={(v) => onChange({ country: v })}
            options={COUNTRIES}
          />
          <InputField
            label="State / Province"
            value={form.state_province}
            onChange={(v) => onChange({ state_province: v })}
            placeholder="e.g. CA, NY"
          />
        </div>
        <NavRow onBack={onBack} onSkip={onSkip} loading={loading} />
      </form>
    </>
  );
}

// ── Step 2: Family ────────────────────────────────────────────────────────────

export function StepFamily({
  form,
  onChange,
  onSubmit,
  onBack,
  onSkip,
  loading,
}: {
  form: ProfileFormState;
  onChange: (patch: Partial<ProfileFormState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Family situation</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Dependents affect your projected living costs and insurance needs.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <SelectField
          label="Marital status"
          value={form.marital_status}
          onChange={(v) => onChange({ marital_status: v })}
          options={MARITAL_STATUSES}
        />
        <InputField
          label="Number of dependents"
          type="number"
          value={form.dependents}
          onChange={(v) => onChange({ dependents: v })}
          placeholder="0"
          min="0"
          max="20"
        />
        <NavRow onBack={onBack} onSkip={onSkip} loading={loading} />
      </form>
    </>
  );
}

// ── Step 3: Employment ────────────────────────────────────────────────────────

export function StepEmployment({
  form,
  onChange,
  onSubmit,
  onBack,
  onSkip,
  loading,
}: {
  form: ProfileFormState;
  onChange: (patch: Partial<ProfileFormState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Employment</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Used for income validation and occupation-specific benchmarks.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <SelectField
          label="Employment status"
          value={form.employment_status}
          onChange={(v) => onChange({ employment_status: v })}
          options={EMPLOYMENT_STATUSES}
        />
        <InputField
          label="Employer"
          value={form.employer}
          onChange={(v) => onChange({ employer: v })}
          placeholder="e.g. Acme Corp (optional)"
        />
        <InputField
          label="Occupation"
          value={form.occupation}
          onChange={(v) => onChange({ occupation: v })}
          placeholder="e.g. Software Engineer (optional)"
        />
        <NavRow onBack={onBack} onSkip={onSkip} loading={loading} />
      </form>
    </>
  );
}

// ── Step 9: First goal ────────────────────────────────────────────────────────

export function StepGoal({
  form,
  onChange,
  onSubmit,
  onBack,
  onSkip,
  loading,
}: {
  form: GoalFormState;
  onChange: (patch: Partial<GoalFormState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Your first goal</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        Give the simulator something to work with — you can add more later.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <InputField
          label="Goal name"
          value={form.name}
          onChange={(v) => onChange({ name: v })}
          placeholder="e.g. Retire at 55"
          required
        />
        <SelectField
          label="Category"
          value={form.category}
          onChange={(v) => onChange({ category: v })}
          options={CATEGORIES}
        />
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Target amount ($)"
            type="number"
            value={form.targetAmount}
            onChange={(v) => onChange({ targetAmount: v })}
            placeholder="500000"
            required
            min="1"
          />
          <InputField
            label="Monthly savings ($)"
            type="number"
            value={form.monthlyContribution}
            onChange={(v) => onChange({ monthlyContribution: v })}
            placeholder="500"
            required
            min="0"
          />
        </div>
        <InputField
          label="Years to goal"
          type="number"
          value={form.yearsToGoal}
          onChange={(v) => onChange({ yearsToGoal: v })}
          placeholder="20"
          required
          min="1"
          max="50"
        />
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Risk profile
          </label>
          <div className="grid grid-cols-3 gap-2">
            {RISK_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => onChange({ riskProfile: opt.value })}
                className={`rounded-lg border p-3 text-left transition-colors ${
                  form.riskProfile === opt.value
                    ? "border-primary bg-primary/10"
                    : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                <p className="text-xs font-medium">{opt.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{opt.sub}</p>
              </button>
            ))}
          </div>
        </div>
        <NavRow onBack={onBack} onSkip={onSkip} submitLabel="Save & continue" loading={loading} />
      </form>
    </>
  );
}

// ── Step 10: Assumptions ──────────────────────────────────────────────────────

export function StepAssumptions({
  form,
  onChange,
  onSubmit,
  onBack,
  onSkip,
  loading,
}: {
  form: AssumptionsFormState;
  onChange: (patch: Partial<AssumptionsFormState>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onBack: () => void;
  onSkip: () => void;
  loading: boolean;
}) {
  return (
    <>
      <h2 className="font-display text-2xl tracking-tight">Planning assumptions</h2>
      <p className="mt-1 text-sm text-muted-foreground mb-6">
        These defaults power every projection. You can refine them any time in Settings.
      </p>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Inflation rate (%)"
            type="number"
            value={form.inflation_rate}
            onChange={(v) => onChange({ inflation_rate: v })}
            placeholder="3"
            min="0"
            max="20"
            step="0.1"
          />
          <InputField
            label="Tax rate (%)"
            type="number"
            value={form.tax_rate}
            onChange={(v) => onChange({ tax_rate: v })}
            placeholder="22"
            min="0"
            max="60"
            step="0.5"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Target retirement age"
            type="number"
            value={form.retirement_age}
            onChange={(v) => onChange({ retirement_age: v })}
            placeholder="65"
            min="40"
            max="80"
          />
          <InputField
            label="Social Security / pension ($/mo)"
            type="number"
            value={form.social_security_monthly}
            onChange={(v) => onChange({ social_security_monthly: v })}
            placeholder="0"
            min="0"
          />
        </div>
        <div className="rounded-lg border border-border bg-surface/50 px-4 py-3">
          <p className="text-xs text-muted-foreground">
            Expected returns use built-in defaults: Conservative 5% · Balanced 7% · Aggressive 9%.
            These can be adjusted in Settings after onboarding.
          </p>
        </div>
        <NavRow onBack={onBack} onSkip={onSkip} submitLabel="Finish setup" loading={loading} />
      </form>
    </>
  );
}
