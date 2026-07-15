import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, AlertCircle, ShieldCheck, Landmark, AlertTriangle, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import type { FamilyRecommendation, RecommendationConflict } from "@/lib/api";

export const Route = createFileRoute("/app/family/recommendations")({
  head: () => ({ meta: [{ title: "Family Recommendations — Northstar" }] }),
  staticData: { shellTitle: "Family Recommendations" },
  component: FamilyRecommendations,
});

function FamilyRecommendations() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["family-recommendations"],
    queryFn: () => api.getFamilyRecommendations(),
  });

  return (
    <div className="max-w-3xl space-y-6">
      <Link
        to="/app/family"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to Family
      </Link>

      {/* Always true, not conditional on any specific event
          (LifeEventIntegrationReview.md Phase 2 §4/§5) — recommendations are
          computed live on every read (ADR-005), so this never overclaims a
          causal link the system can't verify. */}
      <p className="text-xs text-muted-foreground">
        These always reflect your latest numbers, including anything you've recorded as a life
        event.
      </p>

      {isLoading && (
        <div className="surface-card p-6 animate-pulse space-y-4" aria-busy="true">
          <div className="h-4 w-40 rounded bg-muted" />
          <div className="h-14 rounded bg-muted/50" />
        </div>
      )}

      {isError && !isLoading && (
        <div className="surface-card p-8 text-center" role="alert">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-3" aria-hidden="true" />
          <p className="font-display text-base">We couldn't load your recommendations.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Your data is safe — this is just a loading problem.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Try again
          </button>
        </div>
      )}

      {data && !isLoading && !isError && <RecommendationsContent data={data} />}
    </div>
  );
}

function RecommendationsContent({
  data,
}: {
  data: { recommendations: FamilyRecommendation[]; conflicts: RecommendationConflict[] };
}) {
  if (data.recommendations.length === 0) {
    return (
      <div className="surface-card p-10 text-center">
        <p className="font-display text-lg">No recommendations right now.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          As you add family members and record their details, we'll surface anything worth acting on
          here — each one explaining why.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Every suggestion below explains why it's here, why now, and exactly what it's based on —
        nothing is ever shown without that context.
      </p>

      {data.conflicts.map((conflict) => (
        <div
          key={`${conflict.subject}-${conflict.reference_code}`}
          role="status"
          className="surface-card p-4 border border-warning/30 bg-warning/5 flex gap-3"
        >
          <AlertTriangle className="h-4 w-4 text-warning shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs text-muted-foreground">{conflict.note}</p>
        </div>
      ))}

      {data.recommendations.map((rec, i) => (
        <RecommendationCard key={`${rec.source}-${rec.recommendation_type}-${i}`} rec={rec} />
      ))}
    </div>
  );
}

const SOURCE_ICON = {
  insurance: ShieldCheck,
  schemes: Landmark,
  financial_health: Wallet,
} as const;

function RecommendationCard({ rec }: { rec: FamilyRecommendation }) {
  const Icon = SOURCE_ICON[rec.source];

  return (
    <div role="status" className="surface-card p-5 border border-cyan/30 bg-cyan/5 space-y-3">
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 text-cyan shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-2">
          <p className="text-sm font-medium">{rec.why}</p>
          <p className="text-xs text-muted-foreground">{rec.why_now}</p>
        </div>
      </div>

      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer select-none text-cyan hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded">
          What we used, and what we don't know yet
        </summary>
        <div className="mt-2 space-y-2 pl-1">
          <div>
            <p className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Based on</p>
            <ul className="list-disc list-inside">
              {rec.what_information_was_used.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          {rec.what_information_is_missing.length > 0 && (
            <div>
              <p className="uppercase tracking-wide text-[10px] text-muted-foreground/80">
                We don't yet know
              </p>
              <ul className="list-disc list-inside">
                {rec.what_information_is_missing.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
