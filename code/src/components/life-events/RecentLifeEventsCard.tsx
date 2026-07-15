import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, History } from "lucide-react";
import { api } from "@/lib/api";
import { findLifeEventType } from "@/lib/life-events";

function eventLabel(eventType: string): string {
  return findLifeEventType(eventType)?.label ?? eventType;
}

function formatRecentDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

type Props = {
  /** Only fetch/show events whose event_type is in this list (e.g. Family's category). Omit for "all types". */
  eventTypes?: string[];
  limit?: number;
  /** Dashboard wants a "record your first one" nudge when there's nothing yet; Family wants to render nothing at all (matches FamilyCard's own existing rule) when there's nothing relevant to say. */
  emptyState?: "prompt" | "hidden";
  title?: string;
};

// Reused on Dashboard (all recent events) and Family (Family-category events
// only) — one component, one fetch shape, so "what did I record recently"
// answers the same way everywhere it appears (LifeEventIntegrationReview.md
// Phase 2 §4). Reads GET /life-events exactly as the Life Events page
// itself does — no new endpoint, no new calculation.
export function RecentLifeEventsCard({
  eventTypes,
  limit = 3,
  emptyState = "hidden",
  title = "Recent life events",
}: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["recent-life-events", eventTypes?.join(",") ?? "all", limit],
    queryFn: () => api.getLifeEvents({ limit }),
    staleTime: 30_000,
  });

  if (isLoading) return null;

  const items = (data?.items ?? []).filter(
    (item) => !eventTypes || eventTypes.includes(item.event_type),
  );

  if (items.length === 0) {
    if (emptyState === "hidden") return null;
    return (
      <Link
        to="/app/life-events"
        className="surface-card p-4 flex items-center justify-between gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <div className="flex items-center gap-3">
          <History className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-muted-foreground">
              Nothing recorded yet — log a raise, a move, a new family member
            </p>
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
      </Link>
    );
  }

  return (
    <Link
      to="/app/life-events"
      className="surface-card p-4 flex items-center justify-between gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <div className="flex items-center gap-3 min-w-0">
        <History className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-muted-foreground truncate">
            {items
              .map(
                (item) => `${eventLabel(item.event_type)} · ${formatRecentDate(item.occurred_on)}`,
              )
              .join("  ·  ")}
          </p>
        </div>
      </div>
      <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
    </Link>
  );
}
