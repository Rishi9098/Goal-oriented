import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Download, TrendingUp, Target, DollarSign, Activity, History, Info } from "lucide-react";
import { api } from "@/lib/api";
import type { LifeEventRecord, ReportSummary } from "@/lib/api";
import { findLifeEventType } from "@/lib/life-events";
import { formatCurrency } from "@/lib/mock-data";
import { PlanHealthInfo } from "@/components/PlanHealthInfo";

export const Route = createFileRoute("/app/reports")({
  head: () => ({ meta: [{ title: "Reports — Northstar" }] }),
  staticData: { shellTitle: "Reports" },
  component: Reports,
});

// Same three semantic tokens Dashboard/Goals already use for goal status
// (ConsistencyAudit.md Phase 6 §2.2) — only the color vocabulary is shared;
// the finer three-way 80/60 split stays specific to this denser report view.
function pctColor(p: number): string {
  if (p >= 80) return "text-success";
  if (p >= 60) return "text-warning";
  return "text-destructive";
}

function pctBar(p: number): string {
  if (p >= 80) return "bg-success";
  if (p >= 60) return "bg-warning";
  return "bg-destructive";
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
  // Life Events This Year (LifeEventIntegrationReview.md Phase 2) — its own
  // independent fetch, matching this file's existing per-section pattern
  // (FE-005: this page already bypasses a shared query cache; not
  // reintroduced or fixed here, out of scope for this phase). Reuses
  // GET /life-events's own start_date/end_date filter — no new endpoint.
  const [yearEvents, setYearEvents] = useState<LifeEventRecord[] | null>(null);
  const reportYear = new Date().getFullYear();

  useEffect(() => {
    api
      .getReportSummary()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load report"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api
      .getLifeEvents({
        start_date: `${reportYear}-01-01`,
        end_date: `${reportYear}-12-31`,
        limit: 100,
      })
      .then((result) => setYearEvents(result.items))
      .catch(() => setYearEvents([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reportYear is derived once from the current date, not a changing prop/state value this effect needs to re-run for
  }, []);

  const generatedDate = data
    ? new Date(data.generated_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  return (
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
          <Download className="h-4 w-4" /> Print / Save as PDF
        </button>
      </div>

      {/* PerformanceUXAudit.md Phase 9 — content-shaped skeleton, matching
          the loaded layout below, instead of a generic spinner that gives
          no sense of what's arriving or how much of it there is. */}
      {loading && (
        <div className="space-y-6" aria-busy="true" aria-label="Loading report">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="surface-card p-5 space-y-3 animate-pulse">
                <div className="h-3 w-20 rounded bg-muted/40" />
                <div className="h-6 w-16 rounded bg-muted/40" />
                <div className="h-3 w-24 rounded bg-muted/40" />
              </div>
            ))}
          </div>
          <div className="surface-card overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <div className="h-3 w-32 rounded bg-muted/40 animate-pulse" />
            </div>
            <div className="divide-y divide-border">
              {[1, 2, 3].map((i) => (
                <div key={i} className="px-6 py-4 h-16 animate-pulse bg-surface/40" />
              ))}
            </div>
          </div>
          <div className="surface-card p-6 grid grid-cols-3 divide-x divide-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-4 space-y-2">
                <div className="h-3 w-24 mx-auto rounded bg-muted/40 animate-pulse" />
                <div className="h-6 w-20 mx-auto rounded bg-muted/40 animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="surface-card p-6 border-red-500/30 bg-red-500/10 text-red-400 text-sm">
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
              value={formatCurrency(data.net_worth)}
              sub={`${formatCurrency(data.invested)} invested`}
            />
            <StatCard
              icon={Activity}
              label="Plan Health"
              value={`${data.plan_health_score}`}
              sub="out of 100"
              valueClass={pctColor(data.plan_health_score)}
              info={
                <PlanHealthInfo
                  score={data.plan_health_score}
                  goalCount={data.goal_count}
                  trigger={
                    <button
                      type="button"
                      aria-label="What is Plan Health?"
                      className="ml-auto text-muted-foreground hover:text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                    >
                      <Info className="h-3.5 w-3.5" />
                    </button>
                  }
                />
              }
            />
            <StatCard
              icon={Target}
              label="Goals On Track"
              value={`${data.goals_on_track} / ${data.goal_count}`}
              sub={
                data.goal_count > 0
                  ? `${Math.round((data.goals_on_track / data.goal_count) * 100)}% success rate`
                  : "No goals yet"
              }
            />
            <StatCard
              icon={TrendingUp}
              label="Monthly Savings"
              value={formatCurrency(data.monthly_income - data.monthly_expenses)}
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
                  <div
                    key={g.id}
                    className="px-6 py-4 grid grid-cols-[1fr_auto] gap-4 items-center"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm truncate">{g.name}</span>
                        <span className="shrink-0 text-xs text-muted-foreground px-1.5 py-0.5 rounded bg-surface border border-border">
                          {categoryLabel(g.category)}
                        </span>
                        {g.on_track ? (
                          <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-success/15 text-success">
                            On track
                          </span>
                        ) : (
                          <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-warning/15 text-warning">
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
                        <span
                          className={`text-xs font-medium tabular-nums ${pctColor(g.probability)}`}
                        >
                          {g.probability.toFixed(0)}% likely
                        </span>
                      </div>

                      <p className="mt-1.5 text-xs text-muted-foreground">
                        {formatCurrency(g.current_amount)} saved · {formatCurrency(g.target_amount)}{" "}
                        target · {formatCurrency(g.monthly_contribution)}/mo ·{" "}
                        {new Date(g.target_date).getFullYear()}
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <p className="text-sm font-medium">{formatCurrency(g.target_amount)}</p>
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
                <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">
                  Monthly Income
                </p>
                <p className="font-display text-xl">{formatCurrency(data.monthly_income)}</p>
              </div>
              <div className="px-4">
                <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">
                  Monthly Expenses
                </p>
                <p className="font-display text-xl">{formatCurrency(data.monthly_expenses)}</p>
              </div>
              <div className="px-4">
                <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">
                  Net Savings
                </p>
                <p className="font-display text-xl text-success">
                  {formatCurrency(data.monthly_income - data.monthly_expenses)}
                </p>
              </div>
            </div>
          )}

          {/* Life Events This Year (LifeEventIntegrationReview.md Phase 2) */}
          {yearEvents && yearEvents.length > 0 && (
            <div className="surface-card overflow-hidden">
              <div className="px-6 py-4 border-b border-border flex items-center gap-2">
                <History className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
                  Life Events This Year
                </p>
              </div>
              <div className="divide-y divide-border">
                {yearEvents.map((event) => (
                  <div key={event.id} className="px-6 py-3 flex items-center justify-between gap-4">
                    <p className="text-sm font-medium">
                      {findLifeEventType(event.event_type)?.label ?? event.event_type}
                    </p>
                    <p className="text-xs text-muted-foreground shrink-0">
                      {new Date(event.occurred_on).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                  </div>
                ))}
              </div>
              <div className="px-6 py-3 border-t border-border">
                <Link to="/app/life-events" className="text-sm text-cyan hover:underline">
                  View full history
                </Link>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  valueClass = "",
  info,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub: string;
  valueClass?: string;
  /** Only Plan Health uses this (PlanHealthUXReview.md Phase 3) — every other stat card is self-explanatory. */
  info?: React.ReactNode;
}) {
  return (
    <div className="surface-card p-5 space-y-3">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs uppercase tracking-widest">{label}</span>
        {info}
      </div>
      <p className={`font-display text-2xl ${valueClass}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{sub}</p>
    </div>
  );
}
