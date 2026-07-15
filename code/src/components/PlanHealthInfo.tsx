import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { api } from "@/lib/api";
import type { Goal } from "@/lib/mock-data";

type Props = {
  score: number;
  goalCount: number;
  /** The sidebar's own compact trigger vs. Reports' small "i" icon trigger. */
  trigger: React.ReactNode;
};

// PlanHealthUXReview.md Phase 3 — compute_plan_health() itself is untouched;
// this only explains what the number already means. Shared between the
// sidebar mini-card and Reports' stat card so the wording never drifts
// between the two places the score actually appears.
export function PlanHealthInfo({ score, goalCount, trigger }: Props) {
  const [open, setOpen] = useState(false);

  // Lazy — matches the Command Palette's own existing "don't fetch until
  // opened" rule (GlobalShellArchitecture.md §5). Only needed to name which
  // goals are dragging the score down; the score itself never comes from
  // this call, only from the already-fetched dashboard/report data passed
  // in as `score`.
  const { data: goals } = useQuery({
    queryKey: ["goals"],
    queryFn: () => api.getGoals(),
    enabled: open && goalCount > 0,
    staleTime: 60_000,
  });

  const laggingGoals: Goal[] = (goals ?? [])
    .filter((g) => !g.onTrack)
    .sort((a, b) => a.probability - b.probability)
    .slice(0, 3);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{trigger}</PopoverTrigger>
      <PopoverContent align="start" className="w-80 text-sm">
        <p className="font-medium text-foreground">What is Plan Health?</p>
        <p className="mt-1.5 text-xs text-muted-foreground">
          A weighted average of how likely you are to reach each of your goals, based on your
          current savings and timeline — not a grade on your overall finances.
        </p>

        {goalCount === 0 ? (
          <p className="mt-3 text-xs text-muted-foreground">
            You haven't added any goals yet, so there's nothing to measure yet — this isn't a
            failing score, there's just no goal for it to reflect.
          </p>
        ) : (
          <>
            {laggingGoals.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <p className="text-xs font-medium text-foreground">What's holding it back</p>
                {laggingGoals.map((g) => (
                  <p key={g.id} className="text-xs text-muted-foreground">
                    {g.name} — {g.probability}% likely
                  </p>
                ))}
              </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              Increasing contributions, adjusting a timeline, or changing a risk profile on the
              goals above can raise this score.
            </p>
          </>
        )}

        <Link
          to="/app/goals"
          onClick={() => setOpen(false)}
          className="mt-3 inline-flex items-center gap-1 text-xs text-cyan hover:underline"
        >
          Review your goals <ArrowRight className="h-3 w-3" />
        </Link>
      </PopoverContent>
    </Popover>
  );
}
