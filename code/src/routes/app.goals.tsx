import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Plus,
  Search,
  Target,
  GraduationCap,
  Home,
  Plane,
  TrendingUp,
  ShieldCheck,
  BarChart2,
  Loader2,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { formatCurrency, type Goal } from "@/lib/mock-data";
import { api } from "@/lib/api";
import { GoalSimPanel } from "@/components/dashboard/GoalSimPanel";

export const Route = createFileRoute("/app/goals")({
  head: () => ({ meta: [{ title: "Goals — Northstar" }] }),
  component: GoalsPage,
});

const categoryIcon = {
  retirement: ShieldCheck,
  education: GraduationCap,
  home: Home,
  travel: Plane,
  wealth: TrendingUp,
  emergency: Target,
} as const;

const CATEGORIES: { value: Goal["category"]; label: string }[] = [
  { value: "retirement", label: "Retirement" },
  { value: "education", label: "Education" },
  { value: "home", label: "Home purchase" },
  { value: "travel", label: "Travel / sabbatical" },
  { value: "wealth", label: "Wealth building" },
  { value: "emergency", label: "Emergency fund" },
];

const RISK_OPTIONS: { value: Goal["riskProfile"]; label: string; sub: string }[] = [
  { value: "conservative", label: "Conservative", sub: "30 / 70 — stability" },
  { value: "balanced", label: "Balanced", sub: "60 / 40 — moderate" },
  { value: "aggressive", label: "Aggressive", sub: "90 / 10 — growth" },
];

type NewGoalForm = {
  name: string;
  category: Goal["category"];
  targetAmount: string;
  monthlyContribution: string;
  yearsToGoal: string;
  riskProfile: Goal["riskProfile"];
};

const EMPTY_FORM: NewGoalForm = {
  name: "",
  category: "wealth",
  targetAmount: "50000",
  monthlyContribution: "500",
  yearsToGoal: "10",
  riskProfile: "balanced",
};

function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<"all" | "ontrack" | "atrisk">("all");
  const [form, setForm] = useState<NewGoalForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Goal | null>(null);

  useEffect(() => {
    api.getGoals()
      .then(setGoals)
      .finally(() => setLoading(false));
  }, []);

  const filtered = goals.filter((g) => {
    const matches = g.name.toLowerCase().includes(query.toLowerCase());
    const okFilter =
      filter === "all" || (filter === "ontrack" ? g.onTrack : !g.onTrack);
    return matches && okFilter;
  });

  const handleDelete = (id: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== id));
    setSelected(null);
  };

  const handleUpdate = (updated: Goal) => {
    setGoals((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
    setSelected(updated);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const targetDate = new Date();
      targetDate.setFullYear(targetDate.getFullYear() + Number(form.yearsToGoal));
      const created = await api.createGoal({
        name: form.name,
        category: form.category,
        targetAmount: Number(form.targetAmount),
        currentAmount: 0,
        targetDate: targetDate.toISOString().split("T")[0],
        monthlyContribution: Number(form.monthlyContribution),
        riskProfile: form.riskProfile,
      });
      setGoals((g) => [created, ...g]);
      setOpen(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create goal. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Goals">
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 w-full md:w-80">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search goals…"
              className="bg-transparent outline-none text-sm flex-1"
            />
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-1 text-sm">
            {(["all", "ontrack", "atrisk"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-md transition ${
                  filter === f ? "bg-accent text-foreground" : "text-muted-foreground"
                }`}
              >
                {f === "all" ? "All" : f === "ontrack" ? "On track" : "At risk"}
              </button>
            ))}
          </div>
          <button
            onClick={() => setOpen(true)}
            className="md:ml-auto inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
          >
            <Plus className="h-4 w-4" /> New goal
          </button>
        </div>

        {loading ? (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="surface-card p-5 h-48 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="surface-card p-12 text-center">
            <Target className="h-8 w-8 mx-auto text-muted-foreground" />
            <p className="mt-3 font-display text-xl">
              {goals.length === 0 ? "No goals yet" : "No goals match"}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {goals.length === 0
                ? "Add your first financial goal to get started."
                : "Try a different filter or add a new goal."}
            </p>
            {goals.length === 0 && (
              <button
                onClick={() => setOpen(true)}
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
              >
                <Plus className="h-4 w-4" /> Add goal
              </button>
            )}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtered.map((g) => {
              const Icon = categoryIcon[g.category];
              const pct = g.targetAmount > 0
                ? Math.min(100, Math.round((g.currentAmount / g.targetAmount) * 100))
                : 0;
              const years = Math.max(
                0,
                new Date(g.targetDate).getFullYear() - new Date().getFullYear(),
              );
              return (
                <motion.div
                  key={g.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ y: -2 }}
                  onClick={() => setSelected(g)}
                  className="surface-card p-5 cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan/30 grid place-items-center">
                        <Icon className="h-5 w-5 text-cyan" />
                      </div>
                      <div>
                        <p className="font-medium">{g.name}</p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {g.category} · {years > 0 ? `${years}y horizon` : "Funded"}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelected(g); }}
                      className="p-1 rounded hover:bg-accent text-muted-foreground"
                      title="Simulate"
                    >
                      <BarChart2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="mt-5">
                    <div className="flex items-baseline justify-between">
                      <p className="font-display text-2xl">{formatCurrency(g.currentAmount)}</p>
                      <p className="text-xs text-muted-foreground">of {formatCurrency(g.targetAmount)}</p>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8 }}
                        className={`h-full bg-gradient-to-r ${
                          g.onTrack ? "from-primary to-cyan" : "from-warning to-destructive"
                        }`}
                      />
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs">
                      <span
                        className={`px-2 py-0.5 rounded-full ${
                          g.onTrack ? "bg-success/15 text-success" : "bg-warning/15 text-warning"
                        }`}
                      >
                        {g.probability}% Monte Carlo
                      </span>
                      <span className="text-muted-foreground font-mono">
                        +{formatCurrency(g.monthlyContribution)}/mo
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      <AnimatePresence>
        {selected && (
          <GoalSimPanel
            key={selected.id}
            goal={selected}
            onClose={() => setSelected(null)}
            onDelete={handleDelete}
            onUpdate={handleUpdate}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-background/70 backdrop-blur grid place-items-center p-4"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg surface-card p-6 max-h-[90vh] overflow-y-auto"
            >
              <h2 className="font-display text-xl tracking-tight">New goal</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Define what you're saving for. We'll run the Monte Carlo automatically.
              </p>

              {formError && (
                <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {formError}
                </div>
              )}

              <form className="mt-5 space-y-4" onSubmit={handleCreate}>
                <label className="block">
                  <span className="text-xs text-muted-foreground">Goal name</span>
                  <input
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Retire at 60"
                    required
                    className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
                  />
                </label>

                <label className="block">
                  <span className="text-xs text-muted-foreground">Category</span>
                  <select
                    value={form.category}
                    onChange={(e) => setForm((f) => ({ ...f, category: e.target.value as Goal["category"] }))}
                    className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Target amount ($)</span>
                    <input
                      type="number"
                      value={form.targetAmount}
                      onChange={(e) => setForm((f) => ({ ...f, targetAmount: e.target.value }))}
                      placeholder="50000"
                      required
                      min="1"
                      className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs text-muted-foreground">Monthly savings ($)</span>
                    <input
                      type="number"
                      value={form.monthlyContribution}
                      onChange={(e) => setForm((f) => ({ ...f, monthlyContribution: e.target.value }))}
                      placeholder="500"
                      required
                      min="0"
                      className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="text-xs text-muted-foreground">Years to goal</span>
                  <input
                    type="number"
                    value={form.yearsToGoal}
                    onChange={(e) => setForm((f) => ({ ...f, yearsToGoal: e.target.value }))}
                    placeholder="10"
                    required
                    min="1"
                    max="50"
                    className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary"
                  />
                </label>

                <div className="space-y-1.5">
                  <span className="text-xs text-muted-foreground">Risk profile</span>
                  <div className="grid grid-cols-3 gap-2 mt-1">
                    {RISK_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setForm((f) => ({ ...f, riskProfile: opt.value }))}
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

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => { setOpen(false); setFormError(null); setForm(EMPTY_FORM); }}
                    className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-cyan text-sm font-medium text-primary-foreground shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
                    ) : (
                      "Create goal"
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </AppShell>
  );
}
