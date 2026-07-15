import { useEffect, useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, type Goal } from "@/lib/mock-data";

type Props = {
  goal: Goal;
  onUpdate: (updated: Goal) => void;
};

function yearsUntil(targetDate: string): number {
  const ms = new Date(targetDate).getTime() - Date.now();
  return Math.max(0, ms / (365.25 * 24 * 60 * 60 * 1000));
}

function projectedCost(currentCost: number, years: number, rate: number): number {
  return currentCost * Math.pow(1 + rate, years);
}

// Milestone 2 Task 9. This projection is deliberately separate from the
// goal's Monte Carlo probability — see CalculationContextReview.md. It
// never calls calculate_goal_probability() and never changes goal.onTrack.
export function EducationPlanningSection({ goal, onUpdate }: Props) {
  const [globalRate, setGlobalRate] = useState<number | null>(null);
  const [ssyCallout, setSsyCallout] = useState<{ name: string; reason: string } | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [editingRate, setEditingRate] = useState(false);
  const [rateInput, setRateInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api.getAssumptions().then((a) => {
      if (!cancelled) setGlobalRate(a.inflation_rate);
    });

    api.getFamilyGoals().then(async (familyGoals) => {
      const match = familyGoals.find((g) => g.id === goal.id);
      if (!match || match.tagged_members.length === 0) return;
      for (const member of match.tagged_members) {
        const detail = await api.getFamilyMember(member.id);
        const ssy = detail.member.eligible_schemes.find((s) => s.code === "SSY");
        if (ssy && !cancelled) {
          setSsyCallout({ name: member.name ?? "This child", reason: ssy.reason });
          break;
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, [goal.id]);

  if (globalRate === null) {
    return null;
  }

  const effectiveRate = goal.customInflationRate ?? globalRate;
  const years = yearsUntil(goal.targetDate);
  const cost = projectedCost(goal.targetAmount, years, effectiveRate);
  const showPrompt = goal.customInflationRate == null && !dismissed;

  async function handleSaveRate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const parsed = Number(rateInput) / 100;
    if (Number.isNaN(parsed) || parsed < 0 || parsed > 0.5) {
      setError("Enter a rate between 0% and 50%.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api.updateGoal(goal.id, { customInflationRate: parsed });
      onUpdate(updated);
      setEditingRate(false);
    } catch {
      setError("We couldn't save this. Your goal itself is unaffected.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface/40 p-4 space-y-3">
      <p className="text-sm font-medium">Education cost projection</p>

      <p className="text-xs text-muted-foreground">
        Projected cost in {years.toFixed(0)} year{years.toFixed(0) === "1" ? "" : "s"}:{" "}
        <span className="font-medium text-foreground">{formatCurrency(cost)}</span>, using{" "}
        {goal.customInflationRate != null ? "your custom" : "the standard"}{" "}
        {(effectiveRate * 100).toFixed(1)}% annual inflation assumption.
      </p>

      <p className="text-xs text-muted-foreground">
        This changes what we project this will cost — it does not change your Monte Carlo odds of
        reaching your current target above.
      </p>

      {showPrompt && !editingRate && (
        <div className="rounded-lg border border-cyan/30 bg-cyan/5 p-3 space-y-2">
          <p className="text-xs">
            Tuition, fees, and related costs have historically climbed faster than general prices —
            a flat inflation number can understate what you'll actually need. Want to use a more
            accurate estimate for this goal?
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setEditingRate(true)}
              className="text-xs font-medium text-cyan hover:underline"
            >
              Set a custom rate
            </button>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Not now
            </button>
          </div>
        </div>
      )}

      {!showPrompt && !editingRate && (
        <button
          type="button"
          onClick={() => {
            setRateInput(
              goal.customInflationRate != null ? String(goal.customInflationRate * 100) : "",
            );
            setEditingRate(true);
          }}
          className="text-xs text-cyan hover:underline"
        >
          {goal.customInflationRate != null ? "Change custom rate" : "Set a custom rate"}
        </button>
      )}

      {editingRate && (
        <form onSubmit={handleSaveRate} className="space-y-2">
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">
              Custom annual inflation rate (%) — no suggested default; enter your own estimate
            </span>
            <input
              type="number"
              inputMode="decimal"
              step="0.1"
              min="0"
              max="50"
              value={rateInput}
              onChange={(e) => setRateInput(e.target.value)}
              placeholder="e.g. 8"
              required
              className="field-input w-full"
            />
          </label>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-glow hover:opacity-90 disabled:opacity-50 transition"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Save
            </button>
            <button
              type="button"
              onClick={() => {
                setEditingRate(false);
                setError(null);
              }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {ssyCallout && (
        <div role="status" className="rounded-lg border border-cyan/30 bg-cyan/5 p-3 flex gap-2">
          <Sparkles className="h-4 w-4 text-cyan shrink-0" aria-hidden="true" />
          <p className="text-xs">{ssyCallout.reason}</p>
        </div>
      )}
    </div>
  );
}
