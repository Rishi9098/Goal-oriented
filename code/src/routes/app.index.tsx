import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  ArrowRight,
  ArrowUpRight,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";
import { formatCurrency, type Goal } from "@/lib/mock-data";
import { NetWorthProjection } from "@/components/dashboard/NetWorthProjection";
import { NetWorthBreakdown } from "@/components/dashboard/NetWorthBreakdown";

export const Route = createFileRoute("/app/")({
  head: () => ({ meta: [{ title: "Dashboard — Northstar" }] }),
  component: Dashboard,
});

function Stat({
  label,
  value,
  delta,
  positive,
}: {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
}) {
  return (
    <div className="surface-card p-5">
      <p className="text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-2 font-display text-2xl md:text-3xl">{value}</p>
      {delta && (
        <p
          className={`mt-1 text-xs inline-flex items-center gap-1 ${
            positive ? "text-success" : "text-warning"
          }`}
        >
          <ArrowUpRight className="h-3 w-3" /> {delta}
        </p>
      )}
    </div>
  );
}

function StatSkeleton() {
  return (
    <div className="surface-card p-5 animate-pulse">
      <div className="h-3 w-20 rounded bg-muted" />
      <div className="mt-2 h-8 w-32 rounded bg-muted" />
    </div>
  );
}

function Dashboard() {
  const { data: dashData, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.getDashboard(),
    staleTime: 60_000,
  });

  const { data: userGoals = [], isLoading: goalsLoading } = useQuery({
    queryKey: ["goals"],
    queryFn: (): Promise<Goal[]> => api.getGoals(),
    staleTime: 60_000,
  });

  const loading = dashLoading || goalsLoading;
  const suggestions = dashData?.suggestions ?? [];

  return (
    <AppShell title="Overview">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="space-y-6"
      >
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {loading ? (
            <>
              <StatSkeleton />
              <StatSkeleton />
              <StatSkeleton />
              <StatSkeleton />
            </>
          ) : (
            <>
              <Stat
                label="Net worth"
                value={formatCurrency(dashData?.net_worth ?? 0)}
                delta={dashData?.net_worth_delta_pct ? `+${dashData.net_worth_delta_pct}% YTD` : undefined}
                positive
              />
              <Stat label="Invested" value={formatCurrency(dashData?.invested ?? 0)} />
              <Stat label="Liquid" value={formatCurrency(dashData?.liquid_assets ?? 0)} />
              <Stat
                label="Monthly savings"
                value={formatCurrency(
                  Math.max(0, (dashData?.monthly_income ?? 0) - (dashData?.monthly_expenses ?? 0)),
                )}
                delta={dashData?.monthly_savings_rate ? `${dashData.monthly_savings_rate}% of income` : undefined}
                positive={true}
              />
            </>
          )}
        </div>

        {/* Cash flow strip */}
        {!loading && dashData && (dashData.monthly_income > 0 || dashData.monthly_expenses > 0) && (
          <div className="surface-card p-4">
            <div className="grid grid-cols-3 divide-x divide-border">
              <div className="pr-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">Monthly income</p>
                <p className="mt-1 font-display text-xl text-success">{formatCurrency(dashData.monthly_income)}</p>
              </div>
              <div className="px-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">Monthly expenses</p>
                <p className="mt-1 font-display text-xl text-warning">{formatCurrency(dashData.monthly_expenses)}</p>
              </div>
              <div className="pl-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">Net savings</p>
                <p className="mt-1 font-display text-xl">
                  {formatCurrency(Math.max(0, dashData.monthly_income - dashData.monthly_expenses))}
                  <span className="ml-1.5 text-sm font-normal text-muted-foreground">
                    / mo
                  </span>
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-4">
          {/* Net worth projection */}
          <div className="surface-card p-5 lg:col-span-2 flex flex-col">
            <div className="mb-4 flex items-baseline justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest text-muted-foreground">
                  Net worth projection
                </p>
                {dashData && (
                  <p className="mt-1 font-display text-2xl">{formatCurrency(dashData.net_worth)}</p>
                )}
              </div>
              <p className="text-xs text-muted-foreground">3 scenarios · 30-year horizon</p>
            </div>
            {loading || !dashData ? (
              <div className="h-52 animate-pulse rounded-lg bg-muted/40" />
            ) : (
              <NetWorthProjection
                netWorth={dashData.net_worth}
                monthlySavings={Math.max(0, dashData.monthly_income - dashData.monthly_expenses)}
              />
            )}
          </div>

          {/* Net worth breakdown */}
          <div className="surface-card p-5">
            <p className="mb-4 text-xs uppercase tracking-widest text-muted-foreground">
              Wealth breakdown
            </p>
            {loading || !dashData ? (
              <div className="h-48 animate-pulse rounded-lg bg-muted/40" />
            ) : (
              <NetWorthBreakdown
                liquid={dashData.liquid_assets}
                invested={dashData.invested}
                liabilities={dashData.liabilities}
                netWorth={dashData.net_worth}
              />
            )}
          </div>
        </div>

        {/* Goals + Copilot */}
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="surface-card p-5 lg:col-span-2">
            <div className="flex items-center justify-between">
              <p className="font-display text-lg">Goals</p>
              <Link to="/app/goals" className="text-xs text-cyan hover:underline inline-flex items-center gap-1">
                Manage goals <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {loading ? (
              <div className="mt-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 rounded-lg bg-muted/50 animate-pulse" />
                ))}
              </div>
            ) : userGoals.length === 0 ? (
              <div className="mt-6 py-8 text-center">
                <p className="text-sm text-muted-foreground">No goals yet.</p>
                <Link
                  to="/app/goals"
                  className="mt-3 inline-flex items-center gap-1 text-xs text-cyan hover:underline"
                >
                  Add your first goal <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {userGoals.slice(0, 4).map((g) => {
                  const pct = g.targetAmount > 0
                    ? Math.min(100, Math.round((g.currentAmount / g.targetAmount) * 100))
                    : 0;
                  return (
                    <div
                      key={g.id}
                      className="rounded-lg border border-border bg-background/40 p-4 hover:border-border-strong transition"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{g.name}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatCurrency(g.currentAmount)} of {formatCurrency(g.targetAmount)} ·{" "}
                            {new Date(g.targetDate).getFullYear()}
                          </p>
                        </div>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            g.onTrack ? "bg-success/15 text-success" : "bg-warning/15 text-warning"
                          }`}
                        >
                          {g.probability}% likely
                        </span>
                      </div>
                      <div className="mt-3 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full bg-gradient-to-r ${
                            g.onTrack ? "from-primary to-cyan" : "from-warning to-destructive"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="surface-card p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan" />
              <p className="font-display text-lg">AI Copilot</p>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {suggestions.length > 0
                ? `${suggestions.length} recommendation${suggestions.length > 1 ? "s" : ""}`
                : "Analyzing your plan"}
            </p>
            <div className="mt-4 space-y-3">
              {suggestions.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  Add goals to get personalized recommendations.
                </p>
              ) : (
                suggestions.map((s) => {
                  const Icon =
                    s.severity === "warning"
                      ? AlertTriangle
                      : s.severity === "success"
                        ? CheckCircle2
                        : Info;
                  const color =
                    s.severity === "warning"
                      ? "text-warning"
                      : s.severity === "success"
                        ? "text-success"
                        : "text-cyan";
                  return (
                    <div key={s.id} className="rounded-lg border border-border bg-background/40 p-3">
                      <div className="flex gap-2">
                        <Icon className={`h-4 w-4 mt-0.5 ${color}`} />
                        <div>
                          <p className="text-sm font-medium">{s.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">{s.impact}</p>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            <Link
              to="/app/copilot"
              className="mt-4 w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm hover:bg-accent transition"
            >
              <TrendingUp className="h-4 w-4" /> Open copilot
            </Link>
          </div>
        </div>
      </motion.div>
    </AppShell>
  );
}
