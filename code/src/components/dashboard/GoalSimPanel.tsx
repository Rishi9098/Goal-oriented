import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  X,
  Play,
  Zap,
  Loader2,
  Trash2,
  AlertTriangle,
  ChevronRight,
  ShieldCheck,
  GraduationCap,
  Home,
  Plane,
  TrendingUp,
  Target,
  Pencil,
  Check,
} from "lucide-react";
import { api, type SimulationResult, type OptimizationResult } from "@/lib/api";
import { formatCurrency, type Goal } from "@/lib/mock-data";

const CATEGORIES: { value: Goal["category"]; label: string }[] = [
  { value: "retirement", label: "Retirement" },
  { value: "education", label: "Education" },
  { value: "home", label: "Home purchase" },
  { value: "travel", label: "Travel / sabbatical" },
  { value: "wealth", label: "Wealth building" },
  { value: "emergency", label: "Emergency fund" },
];

const RISK_OPTIONS: { value: Goal["riskProfile"]; label: string }[] = [
  { value: "conservative", label: "Conservative (30/70)" },
  { value: "balanced", label: "Balanced (60/40)" },
  { value: "aggressive", label: "Aggressive (90/10)" },
];

const ICON_MAP = {
  retirement: ShieldCheck,
  education: GraduationCap,
  home: Home,
  travel: Plane,
  wealth: TrendingUp,
  emergency: Target,
} as const;

type SimState =
  | { type: "idle" }
  | { type: "running" }
  | { type: "done"; result: SimulationResult }
  | { type: "error"; message: string };

type OptState =
  | { type: "idle" }
  | { type: "loading" }
  | { type: "done"; result: OptimizationResult }
  | { type: "error"; message: string };

type Props = {
  goal: Goal;
  onClose: () => void;
  onDelete: (id: string) => void;
  onUpdate: (updated: Goal) => void;
};

function probColor(p: number): string {
  if (p >= 70) return "text-success";
  if (p >= 50) return "text-warning";
  return "text-destructive";
}

function probBg(p: number): string {
  if (p >= 70) return "bg-success/15 text-success";
  if (p >= 50) return "bg-warning/15 text-warning";
  return "bg-destructive/15 text-destructive";
}

type EditForm = {
  name: string;
  category: Goal["category"];
  targetAmount: string;
  currentAmount: string;
  monthlyContribution: string;
  yearsToGoal: string;
  riskProfile: Goal["riskProfile"];
};

function goalToEditForm(g: Goal): EditForm {
  const years = Math.max(
    1,
    new Date(g.targetDate).getFullYear() - new Date().getFullYear(),
  );
  return {
    name: g.name,
    category: g.category,
    targetAmount: String(g.targetAmount),
    currentAmount: String(g.currentAmount),
    monthlyContribution: String(g.monthlyContribution),
    yearsToGoal: String(years),
    riskProfile: g.riskProfile,
  };
}

export function GoalSimPanel({ goal, onClose, onDelete, onUpdate }: Props) {
  const [sim, setSim] = useState<SimState>({ type: "idle" });
  const [opt, setOpt] = useState<OptState>({ type: "idle" });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<EditForm>(() => goalToEditForm(goal));
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const Icon = ICON_MAP[goal.category];
  const pct =
    goal.targetAmount > 0
      ? Math.min(100, Math.round((goal.currentAmount / goal.targetAmount) * 100))
      : 0;
  const years = Math.max(
    0,
    new Date(goal.targetDate).getFullYear() - new Date().getFullYear(),
  );

  async function runSim() {
    setSim({ type: "running" });
    try {
      const result = await api.simulate({
        goalId: goal.id,
        initialAmount: goal.currentAmount,
        monthlyContribution: goal.monthlyContribution,
        yearsToGoal: Math.max(0.5, years),
        riskProfile: goal.riskProfile,
        numSimulations: 10_000,
      });
      setSim({ type: "done", result });
    } catch (e) {
      setSim({ type: "error", message: e instanceof Error ? e.message : "Simulation failed." });
    }
  }

  async function runOpt() {
    setOpt({ type: "loading" });
    try {
      const result = await api.optimize({ goalId: goal.id });
      setOpt({ type: "done", result });
    } catch (e) {
      setOpt({ type: "error", message: e instanceof Error ? e.message : "Optimization failed." });
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await api.deleteGoal(goal.id);
      onDelete(goal.id);
    } catch {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setEditError(null);
    try {
      const targetDate = new Date();
      targetDate.setFullYear(targetDate.getFullYear() + Number(editForm.yearsToGoal));
      const updated = await api.updateGoal(goal.id, {
        name: editForm.name,
        category: editForm.category,
        targetAmount: Number(editForm.targetAmount),
        currentAmount: Number(editForm.currentAmount),
        monthlyContribution: Number(editForm.monthlyContribution),
        targetDate: targetDate.toISOString().split("T")[0],
        riskProfile: editForm.riskProfile,
      });
      onUpdate(updated);
      setEditing(false);
      setSim({ type: "idle" });
      setOpt({ type: "idle" });
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-background/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 28, stiffness: 260 }}
        onClick={(e) => e.stopPropagation()}
        className="absolute inset-y-0 right-0 w-full max-w-md border-l border-border bg-[oklch(0.19_0.035_260)] flex flex-col overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-border sticky top-0 bg-[oklch(0.19_0.035_260)] z-10">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan/30 grid place-items-center shrink-0">
              <Icon className="h-5 w-5 text-cyan" />
            </div>
            <div>
              <p className="font-display font-semibold leading-tight">{goal.name}</p>
              <p className="text-xs text-muted-foreground capitalize mt-0.5">
                {goal.category}
                {years > 0 ? ` · ${years}y horizon` : " · Target reached"}
                {" · "}
                <span className="capitalize">{goal.riskProfile}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => { setEditing((v) => !v); setEditError(null); setEditForm(goalToEditForm(goal)); }}
              className={`rounded-lg p-1.5 transition ${editing ? "text-cyan bg-cyan/10" : "text-muted-foreground hover:bg-accent hover:text-foreground"}`}
              title={editing ? "Cancel edit" : "Edit goal"}
            >
              <Pencil className="h-4 w-4" />
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <AnimatePresence>
          {editing && (
            <motion.form
              key="edit-form"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              onSubmit={handleSaveEdit}
              className="border-b border-border overflow-hidden"
            >
              <div className="p-5 space-y-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">Edit goal</p>

                {editError && (
                  <p className="text-xs text-red-400">{editError}</p>
                )}

                <label className="block space-y-1">
                  <span className="text-xs text-muted-foreground">Goal name</span>
                  <input
                    value={editForm.name}
                    onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                    required
                    className="field-input w-full"
                  />
                </label>

                <label className="block space-y-1">
                  <span className="text-xs text-muted-foreground">Category</span>
                  <select
                    value={editForm.category}
                    onChange={(e) => setEditForm((f) => ({ ...f, category: e.target.value as Goal["category"] }))}
                    className="field-input w-full"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="block space-y-1">
                    <span className="text-xs text-muted-foreground">Target ($)</span>
                    <input
                      type="number"
                      value={editForm.targetAmount}
                      onChange={(e) => setEditForm((f) => ({ ...f, targetAmount: e.target.value }))}
                      min="1"
                      required
                      className="field-input w-full"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs text-muted-foreground">Saved so far ($)</span>
                    <input
                      type="number"
                      value={editForm.currentAmount}
                      onChange={(e) => setEditForm((f) => ({ ...f, currentAmount: e.target.value }))}
                      min="0"
                      required
                      className="field-input w-full"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs text-muted-foreground">Monthly ($)</span>
                    <input
                      type="number"
                      value={editForm.monthlyContribution}
                      onChange={(e) => setEditForm((f) => ({ ...f, monthlyContribution: e.target.value }))}
                      min="0"
                      required
                      className="field-input w-full"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs text-muted-foreground">Years to goal</span>
                    <input
                      type="number"
                      value={editForm.yearsToGoal}
                      onChange={(e) => setEditForm((f) => ({ ...f, yearsToGoal: e.target.value }))}
                      min="1"
                      max="50"
                      required
                      className="field-input w-full"
                    />
                  </label>
                </div>

                <label className="block space-y-1">
                  <span className="text-xs text-muted-foreground">Risk profile</span>
                  <select
                    value={editForm.riskProfile}
                    onChange={(e) => setEditForm((f) => ({ ...f, riskProfile: e.target.value as Goal["riskProfile"] }))}
                    className="field-input w-full"
                  >
                    {RISK_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </label>

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => { setEditing(false); setEditError(null); }}
                    className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
                  >
                    {saving ? (
                      <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…</>
                    ) : (
                      <><Check className="h-3.5 w-3.5" /> Save changes</>
                    )}
                  </button>
                </div>
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        <div className="flex flex-col gap-6 p-5">
          {/* Progress */}
          <div>
            <div className="flex items-baseline justify-between mb-2">
              <p className="font-display text-2xl">{formatCurrency(goal.currentAmount)}</p>
              <p className="text-sm text-muted-foreground">of {formatCurrency(goal.targetAmount)}</p>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.8 }}
                className={`h-full bg-gradient-to-r ${
                  goal.onTrack ? "from-primary to-cyan" : "from-warning to-destructive"
                }`}
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs">
              <span className={`px-2 py-0.5 rounded-full ${probBg(goal.probability)}`}>
                {goal.probability}% current probability
              </span>
              <span className="text-muted-foreground">{pct}% funded · +{formatCurrency(goal.monthlyContribution)}/mo</span>
            </div>
          </div>

          {/* Simulation section */}
          <div className="rounded-xl border border-border bg-surface/40 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Monte Carlo simulation</p>
              <button
                onClick={runSim}
                disabled={sim.type === "running"}
                className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-glow disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
              >
                {sim.type === "running" ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Running…</>
                ) : (
                  <><Play className="h-3.5 w-3.5" /> Run 10,000 paths</>
                )}
              </button>
            </div>

            <AnimatePresence mode="wait">
              {sim.type === "done" && (
                <motion.div
                  key="sim-result"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-3"
                >
                  <div className="text-center">
                    <p className={`font-display text-4xl font-bold ${probColor(sim.result.success_rate)}`}>
                      {sim.result.success_rate.toFixed(1)}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">probability of reaching your goal</p>
                  </div>
                  <div className="space-y-2">
                    {(["p10", "p50", "p90"] as const).map((k) => {
                      const v = sim.result.percentiles[k];
                      const label = k === "p10" ? "Pessimistic (p10)" : k === "p50" ? "Median (p50)" : "Optimistic (p90)";
                      const barPct = Math.min(100, (v / sim.result.percentiles.p90) * 100);
                      return (
                        <div key={k}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-muted-foreground">{label}</span>
                            <span className="font-medium font-mono">{formatCurrency(v)}</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-primary to-cyan"
                              style={{ width: `${barPct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-foreground text-right">
                    10,000 log-normal paths · {goal.riskProfile} returns
                  </p>
                </motion.div>
              )}
              {sim.type === "error" && (
                <motion.div
                  key="sim-error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-2 text-xs text-destructive"
                >
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  {sim.message}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Optimizer section */}
          <div className="rounded-xl border border-border bg-surface/40 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Optimization</p>
              <button
                onClick={runOpt}
                disabled={opt.type === "loading"}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {opt.type === "loading" ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Optimizing…</>
                ) : (
                  <><Zap className="h-3.5 w-3.5 text-cyan" /> Optimize toward 80%</>
                )}
              </button>
            </div>

            <AnimatePresence mode="wait">
              {opt.type === "done" && (
                <motion.div
                  key="opt-result"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-3"
                >
                  <p className="text-xs text-muted-foreground">
                    Starting from{" "}
                    <span className={`font-medium ${probColor(opt.result.current_probability)}`}>
                      {opt.result.current_probability.toFixed(1)}%
                    </span>{" "}
                    — {opt.result.suggestions.length} suggestion
                    {opt.result.suggestions.length !== 1 ? "s" : ""}
                  </p>
                  {opt.result.suggestions.map((s, i) => (
                    <div key={i} className="rounded-lg border border-border bg-background/40 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium">{s.description}</p>
                        <span className="shrink-0 text-xs text-success font-medium whitespace-nowrap">
                          → {s.projected_probability.toFixed(0)}%
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{s.impact_summary}</p>
                      {s.risk_profile_change && (
                        <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
                          <ChevronRight className="h-3 w-3" />
                          Switch to {s.risk_profile_change}
                        </span>
                      )}
                    </div>
                  ))}
                </motion.div>
              )}
              {opt.type === "error" && (
                <motion.div
                  key="opt-error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-2 text-xs text-destructive"
                >
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  {opt.message}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Delete */}
          <div className="mt-auto pt-2 border-t border-border">
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="flex items-center gap-2 text-xs text-muted-foreground hover:text-destructive transition"
              >
                <Trash2 className="h-3.5 w-3.5" /> Delete this goal
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <p className="text-xs text-muted-foreground">Are you sure?</p>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-1.5 text-xs text-destructive font-medium hover:bg-destructive/20 disabled:opacity-50 transition"
                >
                  {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                  Yes, delete
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="text-xs text-muted-foreground hover:text-foreground transition"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      </motion.aside>
    </motion.div>
  );
}
