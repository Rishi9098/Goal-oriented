import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Check, Loader2, Pencil, X } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { auth } from "@/lib/api";
import { api } from "@/lib/api";

export const Route = createFileRoute("/app/profile")({
  head: () => ({ meta: [{ title: "Profile — Northstar" }] }),
  component: Profile,
});

type FormState = {
  fullName: string;
  email: string;
  household: string;
  riskProfile: string;
};

type Status = "idle" | "saving" | "saved" | "error";

const RISK_OPTIONS = [
  { value: "conservative", label: "Conservative (30/70)" },
  { value: "balanced", label: "Balanced (60/40)" },
  { value: "aggressive", label: "Aggressive (90/10)" },
];

const HOUSEHOLD_OPTIONS = [
  "1 adult",
  "2 adults",
  "2 adults, 1 child",
  "2 adults, 2 children",
  "2 adults, 3+ children",
  "Single parent, 1 child",
  "Single parent, 2+ children",
];

function initials(name: string) {
  return name
    .trim()
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function Profile() {
  const [form, setForm] = useState<FormState>({
    fullName: "",
    email: "",
    household: "2 adults, 1 child",
    riskProfile: "balanced",
  });
  const [saved, setSaved] = useState<FormState | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    auth.me().then((user) => {
      const initial: FormState = {
        fullName: user.full_name ?? "",
        email: user.email,
        household: "2 adults, 1 child",
        riskProfile: "balanced",
      };
      setForm(initial);
      setSaved(initial);
      setLoading(false);
    });
  }, []);

  const isDirty =
    saved !== null &&
    (form.fullName !== saved.fullName ||
      form.email !== saved.email ||
      form.household !== saved.household ||
      form.riskProfile !== saved.riskProfile);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (status === "saved") setStatus("idle");
  };

  const handleReset = () => {
    if (saved) setForm(saved);
    setStatus("idle");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty) return;
    setStatus("saving");
    try {
      await auth.updateMe({ full_name: form.fullName });
      await api.upsertProfile({
        marital_status: form.household.includes("Single parent") ? "single" : undefined,
        dependents: (() => {
          const m = form.household.match(/(\d+)\s*child/);
          return m ? parseInt(m[1]) : 0;
        })(),
      });
      setSaved(form);
      setStatus("saved");
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
    }
  };

  if (loading) {
    return (
      <AppShell title="Profile">
        <div className="flex items-center justify-center h-48 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      </AppShell>
    );
  }

  const avatarText = initials(form.fullName) || "?";
  const riskLabel =
    RISK_OPTIONS.find((o) => o.value === form.riskProfile)?.label ??
    form.riskProfile;

  return (
    <AppShell title="Profile">
      <div className="max-w-2xl space-y-6">
        {/* Avatar header */}
        <div className="surface-card p-6 flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center text-2xl font-medium text-primary-foreground shrink-0 select-none">
            {avatarText}
          </div>
          <div>
            <p className="font-display text-xl">
              {form.fullName || "Your Name"}
            </p>
            <p className="text-sm text-muted-foreground">
              {form.email} · {riskLabel}
            </p>
          </div>
        </div>

        {/* Editable form */}
        <form onSubmit={handleSubmit} noValidate>
          <div className="surface-card p-6 space-y-5">
            <div className="flex items-center justify-between mb-1">
              <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
                Personal details
              </p>
              {status === "saved" && (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <Check className="h-3.5 w-3.5" /> Saved
                </span>
              )}
              {status === "error" && (
                <span className="text-xs text-red-400">Failed to save</span>
              )}
            </div>

            <Field label="Full name">
              <input
                name="fullName"
                value={form.fullName}
                onChange={handleChange}
                placeholder="Alex Reyes"
                className="field-input"
                required
                minLength={2}
              />
            </Field>

            <Field label="Email address">
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="field-input"
                required
              />
            </Field>

            <Field label="Household">
              <select
                name="household"
                value={form.household}
                onChange={handleChange}
                className="field-input"
              >
                {HOUSEHOLD_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Risk profile">
              <select
                name="riskProfile"
                value={form.riskProfile}
                onChange={handleChange}
                className="field-input"
              >
                {RISK_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </Field>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              {isDirty && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:border-border-strong hover:text-foreground transition"
                >
                  <X className="h-3.5 w-3.5" />
                  Discard
                </button>
              )}
              <button
                type="submit"
                disabled={!isDirty || status === "saving"}
                className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {status === "saving" ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Saving…
                  </>
                ) : (
                  <>
                    <Pencil className="h-3.5 w-3.5" />
                    Save changes
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </AppShell>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}
