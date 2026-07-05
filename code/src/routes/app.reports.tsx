import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Download, Loader2, TrendingUp, Target, DollarSign, Activity } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";
import type { ReportSummary } from "@/lib/api";

export const Route = createFileRoute("/app/reports")({
  head: () => ({ meta: [{ title: "Reports — Northstar" }] }),
  component: Reports,
});

function fmt(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}k`;
  return `$${n.toFixed(0)}`;
}

function pctColor(p: number): string {
  if (p >= 80) return "text-emerald-400";
  if (p >= 60) return "text-amber-400";
  return "text-red-400";
}

function pctBar(p: number): string {
  if (p >= 80) return "bg-emerald-500";
  if (p >= 60) return "bg-amber-500";
  return "bg-red-500";
}

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    retirement: "Retirement",
    home: "Home",
    education: "Education",
    emergency: "Emergency",
    travel: "Travel",
    other: "Other",
  };
  return map[cat] ?? cat;
}

function Reports() {
  const [data, setData] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getReportSummary()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load report"))
      .finally(() => setLoading(false));
  }, []);

  const generatedDate = data
    ? new Date(data.generated_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  return (
    <AppShell title="Reports">
      <div className="space-y-6">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">
              {loading ? "Loading report…" : `Generated ${generatedDate}`}
            </p>
          </div>
          <button
            onClick={() => window.print()}
            disabled={loading || !!error}
            className="inline-flex items-center gap-2 rounded-lg border border-border-strong bg-surface px-4 py-2 text-sm hover:border-primary transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" /> Export PDF
          </button>
        </div>

        {loading && (
          <div className="surface-card p-12 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
          </div>
        )}

        {error && (
          <div className="surface-card p-6 border-red-500/30 bg-red-500/5 text-red-400 text-sm">
            {error}
          </div>
        )}

        {data && (
          <>
            {/* Summary stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={DollarSign}
                label="Net Worth"
                value={fmt(data.net_worth)}
                sub={`${fmt(data.invested)} invested`}
              />
              <StatCard
                icon={Activity}
                label="Plan Health"
                value={`${data.plan_health_score}`}
                sub="out of 100"
                valueClass={pctColor(data.plan_health_score)}
              />
              <StatCard
                icon={Target}
                label="Goals On Track"
                value={`${data.goals_on_track} / ${data.goal_count}`}
                sub={data.goal_count > 0 ? `${Math.round((data.goals_on_track / data.goal_count) * 100)}% success rate` : "No goals yet"}
              />
              <StatCard
                icon={TrendingUp}
                label="Monthly Savings"
                value={fmt(data.monthly_income - data.monthly_expenses)}
                sub={`${data.monthly_savings_rate.toFixed(0)}% savings rate`}
              />
            </div>

            {/* Goals table */}
            <div className="surface-card overflow-hidden">
              <div className="px-6 py-4 border-b border-border">
                <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
                  Goal Breakdown
                </p>
              </div>

              {data.goals.length === 0 ? (
                <div className="px-6 py-10 text-center text-sm text-muted-foreground">
                  No goals yet — add goals to see your plan breakdown.
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {data.goals.map((g) => (
                    <div key={g.id} className="px-6 py-4 grid grid-cols-[1fr_auto] gap-4 items-center">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm truncate">{g.name}</span>
                          <span className="shrink-0 text-xs text-muted-foreground px-1.5 py-0.5 rounded bg-surface border border-border">
                            {categoryLabel(g.category)}
                          </span>
                          {g.on_track ? (
                            <span className="shrink-0 text-xs text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                              On track
                            </span>
                          ) : (
                            <span className="shrink-0 text-xs text-amber-400 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
                              Needs attention
                            </span>
                          )}
                        </div>

                        {/* Progress bar */}
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 rounded-full bg-surface-elevated overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${pctBar(g.probability)}`}
                              style={{ width: `${g.probability}%` }}
                            />
                          </div>
                          <span className={`text-xs font-medium tabular-nums ${pctColor(g.probability)}`}>
                            {g.probability.toFixed(0)}%
                          </span>
                        </div>

                        <p className="mt-1.5 text-xs text-muted-foreground">
                          {fmt(g.current_amount)} saved · {fmt(g.target_amount)} target ·{" "}
                          {fmt(g.monthly_contribution)}/mo ·{" "}
                          {new Date(g.target_date).getFullYear()}
                        </p>
                      </div>

                      <div className="text-right shrink-0">
                        <p className="text-sm font-medium">{fmt(g.target_amount)}</p>
                        <p className="text-xs text-muted-foreground">
                          {Math.round((g.current_amount / g.target_amount) * 100)}% funded
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Cash flow strip */}
            {(data.monthly_income > 0 || data.monthly_expenses > 0) && (
              <div className="surface-card p-6 grid grid-cols-3 divide-x divide-border text-center">
                <div className="px-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Monthly Income</p>
                  <p className="font-display text-xl">{fmt(data.monthly_income)}</p>
                </div>
                <div className="px-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Monthly Expenses</p>
                  <p className="font-display text-xl">{fmt(data.monthly_expenses)}</p>
                </div>
                <div className="px-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Net Savings</p>
                  <p className="font-display text-xl text-emerald-400">
                    {fmt(data.monthly_income - data.monthly_expenses)}
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  valueClass = "",
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub: string;
  valueClass?: string;
}) {
  return (
    <div className="surface-card p-5 space-y-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs uppercase tracking-widest">{label}</span>
      </div>
      <p className={`font-display text-2xl ${valueClass}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{sub}</p>
    </div>
  );
}
