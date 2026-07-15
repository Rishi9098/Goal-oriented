import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, AlertCircle, CheckCircle2, Clock } from "lucide-react";
import { api } from "@/lib/api";
import type { SchemeEligibilityItem } from "@/lib/api";

export const Route = createFileRoute("/app/family/schemes")({
  head: () => ({ meta: [{ title: "Government Schemes — Northstar" }] }),
  staticData: { shellTitle: "Government Schemes" },
  component: FamilySchemes,
});

function FamilySchemes() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["family-schemes"],
    queryFn: () => api.getFamilySchemes(),
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

      {isLoading && (
        <div className="surface-card p-6 animate-pulse space-y-4" aria-busy="true">
          <div className="h-4 w-40 rounded bg-muted" />
          <div className="h-14 rounded bg-muted/50" />
        </div>
      )}

      {isError && !isLoading && (
        <div className="surface-card p-8 text-center" role="alert">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-3" aria-hidden="true" />
          <p className="font-display text-base">We couldn't load your family's schemes.</p>
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

      {data && !isLoading && !isError && <SchemesContent data={data} />}
    </div>
  );
}

function SchemesContent({
  data,
}: {
  data: {
    eligible: SchemeEligibilityItem[];
    potentially_eligible: SchemeEligibilityItem[];
    not_eligible: SchemeEligibilityItem[];
  };
}) {
  const hasAny =
    data.eligible.length > 0 ||
    data.potentially_eligible.length > 0 ||
    data.not_eligible.length > 0;

  if (!hasAny) {
    return (
      <div className="surface-card p-10 text-center">
        <p className="font-display text-lg">No schemes matched yet.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          As you add family members and their details, we'll check your family's eligibility against
          government schemes here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Personalized to your family's recorded ages and details — never a flat list to sort through
        yourself.
      </p>

      {data.eligible.length > 0 && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
            Eligible now
          </h2>
          {data.eligible.map((item, i) => (
            <SchemeCard key={`eligible-${item.scheme_code}-${i}`} item={item} tone="eligible" />
          ))}
        </section>
      )}

      {data.potentially_eligible.length > 0 && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <Clock className="h-4 w-4 text-warning" aria-hidden="true" />
            Potentially eligible
          </h2>
          {data.potentially_eligible.map((item, i) => (
            <SchemeCard
              key={`potential-${item.scheme_code}-${i}`}
              item={item}
              tone="potentially_eligible"
            />
          ))}
        </section>
      )}

      {data.not_eligible.length > 0 && (
        <details className="surface-card p-4">
          <summary className="cursor-pointer select-none text-sm text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded">
            Not eligible — show {data.not_eligible.length} more
          </summary>
          <div className="mt-3 space-y-2">
            {data.not_eligible.map((item, i) => (
              <SchemeCard
                key={`not-eligible-${item.scheme_code}-${i}`}
                item={item}
                tone="not_eligible"
              />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

const TONE_STYLES = {
  eligible: "border-emerald-400/30 bg-emerald-400/5",
  potentially_eligible: "border-warning/30 bg-warning/5",
  not_eligible: "border-border bg-surface/40",
} as const;

function SchemeCard({
  item,
  tone,
}: {
  item: SchemeEligibilityItem;
  tone: keyof typeof TONE_STYLES;
}) {
  return (
    <div className={`rounded-lg border p-4 ${TONE_STYLES[tone]}`}>
      <p className="text-sm font-medium">
        {item.scheme_name}
        {item.member_name && (
          <span className="text-muted-foreground font-normal"> — for {item.member_name}</span>
        )}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>
    </div>
  );
}
