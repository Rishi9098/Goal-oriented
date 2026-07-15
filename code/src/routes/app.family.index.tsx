import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  UserPlus,
  Users as UsersIcon,
  CheckCircle2,
  AlertCircle,
  Target,
  ShieldCheck,
  Landmark,
  Sparkles,
  Clock,
  Wallet,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  FamilyDashboard,
  FamilyMemberSummary,
  FamilyRecommendation,
  RecommendationConflict,
} from "@/lib/api";
import { relationshipLabel, relationshipIcon } from "@/lib/family";
import { RecentLifeEventsCard } from "@/components/life-events/RecentLifeEventsCard";
import { LIFE_EVENT_TYPES } from "@/lib/life-events";

// Marriage/Birth of Child/Adoption/Divorce/Dependent Parent — derived from
// the Life Event catalog's own "Family" category (life-events.ts), not a
// second, hand-maintained list, so this never drifts from what Life Events
// itself considers a Family event (LifeEventIntegrationReview.md Phase 2).
const FAMILY_EVENT_TYPES = LIFE_EVENT_TYPES.filter((t) => t.categoryLabel === "Family").map(
  (t) => t.value,
);

export const Route = createFileRoute("/app/family/")({
  head: () => ({ meta: [{ title: "Family — Northstar" }] }),
  staticData: { shellTitle: "Family" },
  component: FamilyHome,
});

function FamilyHome() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["family-home"],
    queryFn: () => api.getFamilyHome(),
    staleTime: 30_000,
  });

  return (
    <div className="max-w-3xl space-y-6">
      {isLoading && <LoadingState />}

      {isError && !isLoading && <ErrorState onRetry={() => refetch()} retrying={isFetching} />}

      {data && !isLoading && !isError && (
        <FamilyContent household={data.household} members={data.members} />
      )}

      {/* Hidden when empty, matching Dashboard's FamilyCard's own existing
          "say nothing if there's nothing to say" rule (LifeEventIntegrationReview.md
          Phase 2). */}
      <RecentLifeEventsCard
        eventTypes={FAMILY_EVENT_TYPES}
        emptyState="hidden"
        title="Recent family life events"
      />

      <FamilyDashboardSection />

      <QuickActions />
      <FamilyGoalsLink />
      <FamilyInsuranceLink />
      <FamilySchemesLink />
      <FamilyRecommendationsLink />
      <ComingSoonSection />
    </div>
  );
}

function FamilyContent({
  household,
  members,
}: {
  household: { id: string; name: string };
  members: FamilyMemberSummary[];
}) {
  const isEmpty = members.length === 1 && members[0].relationship_type === "self";

  if (isEmpty) {
    return <EmptyState />;
  }

  return (
    <>
      <HouseholdSummary householdName={household.name} members={members} />
      <FamilyMembersList members={members} />
    </>
  );
}

// ── Household Summary ─────────────────────────────────────────────────────
// Answers "how many people am I planning for?" A literal tally of the
// relationship_type values the backend already returned — no independent
// bucketing or inference (ADR: DataSourceMigrationReport.md's lesson from
// PCA-2 applies here too).

const PLURAL_LABELS: Record<string, string> = {
  spouse: "Spouses",
  child: "Children",
  parent: "Parents",
  other: "Others",
};

function HouseholdSummary({
  householdName,
  members,
}: {
  householdName: string;
  members: FamilyMemberSummary[];
}) {
  const counts = new Map<string, number>();
  for (const member of members) {
    counts.set(member.relationship_type, (counts.get(member.relationship_type) ?? 0) + 1);
  }
  const breakdown = Array.from(counts.entries())
    .map(([type, count]) => {
      if (type === "self") return "You";
      const label =
        count > 1
          ? (PLURAL_LABELS[type] ?? `${relationshipLabel(type)}s`)
          : relationshipLabel(type);
      return count > 1 ? `${count} ${label}` : label;
    })
    .join(" · ");

  return (
    <div className="surface-card p-5 flex items-center gap-4">
      <div className="h-11 w-11 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center shrink-0">
        <UsersIcon className="h-5 w-5 text-primary-foreground" aria-hidden="true" />
      </div>
      <div>
        <p className="font-display text-lg">{householdName}</p>
        <p className="text-sm text-muted-foreground">
          {members.length} {members.length === 1 ? "person" : "people"} · {breakdown}
        </p>
      </div>
    </div>
  );
}

// ── Family Members ─────────────────────────────────────────────────────────
// Answers "who's in my household, and what's still incomplete?" Every field
// shown (name, relationship_type, is_complete) is exactly what GET /family
// already returns — nothing computed or inferred on this screen.

function FamilyMembersList({ members }: { members: FamilyMemberSummary[] }) {
  return (
    <div className="surface-card p-5">
      <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-4">
        Family members
      </p>
      <ul className="space-y-3">
        {members.map((member) => (
          <MemberCard key={member.id} member={member} />
        ))}
      </ul>
    </div>
  );
}

function MemberCard({ member }: { member: FamilyMemberSummary }) {
  const label = relationshipLabel(member.relationship_type);
  const displayName = member.name ?? `${label} — not yet named`;

  return (
    <li>
      <Link
        to="/app/family/members/$id"
        params={{ id: member.id }}
        className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
          member.is_complete
            ? "border-border hover:border-border-strong hover:bg-accent/40"
            : "border-dashed border-border-strong hover:bg-accent/40"
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xl shrink-0" aria-hidden="true">
            {relationshipIcon(member.relationship_type)}
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-medium truncate">
              {member.name ?? label}
              {member.relationship_type !== "self" && member.name && (
                <span className="text-muted-foreground font-normal"> · {label}</span>
              )}
            </h3>
            {!member.name && member.relationship_type !== "self" && (
              <p className="text-xs text-muted-foreground">Not yet named</p>
            )}
          </div>
        </div>
        <span className="sr-only">{`${displayName}, ${member.is_complete ? "complete" : "incomplete"}`}</span>
        {member.is_complete ? (
          <span className="flex items-center gap-1 text-xs text-emerald-400 shrink-0">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Complete
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-cyan shrink-0">
            <UserPlus className="h-4 w-4" aria-hidden="true" />+ Add details
          </span>
        )}
      </Link>
    </li>
  );
}

// ── Quick Actions ────────────────────────────────────────────────────────

function QuickActions() {
  return (
    <div className="surface-card p-5">
      <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-4">
        Quick actions
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Link
          to="/app/family/add"
          search={{ type: "parent" }}
          className="flex items-center gap-2 rounded-lg border border-dashed border-border-strong px-4 py-3 text-sm hover:bg-accent/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <UserPlus className="h-4 w-4 text-cyan shrink-0" aria-hidden="true" />
          Add a parent who depends on you
        </Link>
        <Link
          to="/app/family/add"
          search={{ type: "other" }}
          className="flex items-center gap-2 rounded-lg border border-dashed border-border-strong px-4 py-3 text-sm hover:bg-accent/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <UserPlus className="h-4 w-4 text-cyan shrink-0" aria-hidden="true" />
          Add someone else
        </Link>
      </div>
    </div>
  );
}

// ── Family Goals link ────────────────────────────────────────────────────
// Milestone 2 Task 8 — replaces the "Upcoming family goals" Coming Soon
// card now that GET /family/goals and the tagging endpoint exist.

function FamilyGoalsLink() {
  return (
    <Link
      to="/app/family/goals"
      className="surface-card p-5 flex items-center gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <Target className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium">Family Goals</p>
        <p className="text-xs text-muted-foreground">See which goals affect each family member</p>
      </div>
    </Link>
  );
}

// ── Family Insurance link ────────────────────────────────────────────────
// Milestone 2 Task 10 — replaces the "Insurance status" Coming Soon card
// now that GET /family/insurance and the policy endpoints exist.

function FamilyInsuranceLink() {
  return (
    <Link
      to="/app/family/insurance"
      className="surface-card p-5 flex items-center gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <ShieldCheck className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium">Family Insurance</p>
        <p className="text-xs text-muted-foreground">
          Who's covered by a health policy, and who isn't yet
        </p>
      </div>
    </Link>
  );
}

// ── Family Recommendations link ──────────────────────────────────────────
// Milestone 2 Task 11 — replaces the "AI recommendations" Coming Soon card,
// deliberately renamed: this is rule-based, calculation-lite logic (Task 3
// + Task 10's engines aggregated), not an AI/ML output, so it's never
// labeled "AI" here.

function FamilyRecommendationsLink() {
  return (
    <Link
      to="/app/family/recommendations"
      className="surface-card p-5 flex items-center gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <Sparkles className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium">Family Recommendations</p>
        <p className="text-xs text-muted-foreground">
          Every suggestion explains why, why now, and what it's based on
        </p>
      </div>
    </Link>
  );
}

// ── Government Schemes link ──────────────────────────────────────────────
// Milestone 2.1-P1 — replaces the "Government scheme eligibility" Coming
// Soon card now that GET /family/schemes exists (a direct passthrough of
// the certified eligibility engine, Task 3).

function FamilySchemesLink() {
  return (
    <Link
      to="/app/family/schemes"
      className="surface-card p-5 flex items-center gap-3 hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <Landmark className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium">Government Schemes</p>
        <p className="text-xs text-muted-foreground">
          Personalized matches for your family, bucketed by eligibility
        </p>
      </div>
    </Link>
  );
}

// ── Coming Soon ──────────────────────────────────────────────────────────
// Honest, clearly-secondary placeholders for sections that depend on later
// Milestone 2 tasks (11, 12) with no certified API yet — see
// BlockerReport.md. Never fabricated data; states plainly what's missing.
// "Upcoming family goals" (Task 8) and "Insurance status" (Task 10) both
// moved out of this list once each shipped — they're real now.

const COMING_SOON: { icon: typeof Target; title: string; blurb: string }[] = [
  {
    icon: Clock,
    title: "Recent changes",
    blurb: "A running history of what changed in your family details.",
  },
];

function ComingSoonSection() {
  return (
    <div>
      <p className="text-xs uppercase tracking-widest text-muted-foreground mb-3">Coming soon</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {COMING_SOON.map(({ icon: Icon, title, blurb }) => (
          <div
            key={title}
            className="rounded-lg border border-border/60 bg-surface/40 p-4 opacity-70"
          >
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {title}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{blurb}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Empty / Loading / Error states ──────────────────────────────────────

function EmptyState() {
  return (
    <div className="surface-card p-10 text-center">
      <div className="mx-auto h-12 w-12 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center mb-4">
        <UsersIcon className="h-6 w-6 text-primary-foreground" aria-hidden="true" />
      </div>
      <p className="font-display text-lg">It's just you right now.</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Add family members anytime — nothing about your plan requires it.
      </p>
      <Link
        to="/app/family/add"
        className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
        Add a family member
      </Link>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading your family information">
      <div className="surface-card p-5 animate-pulse">
        <div className="flex items-center gap-4">
          <div className="h-11 w-11 rounded-full bg-muted shrink-0" />
          <div className="space-y-2">
            <div className="h-4 w-32 rounded bg-muted" />
            <div className="h-3 w-48 rounded bg-muted" />
          </div>
        </div>
      </div>
      <div className="surface-card p-5 animate-pulse space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 rounded-lg bg-muted/50" />
        ))}
      </div>
      <span className="sr-only">Loading your family information — this won't take long.</span>
    </div>
  );
}

function ErrorState({ onRetry, retrying }: { onRetry: () => void; retrying: boolean }) {
  return (
    <div className="surface-card p-8 text-center" role="alert">
      <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-3" aria-hidden="true" />
      <p className="font-display text-base">We couldn't load your family information.</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Your family details are safe — this is just a loading problem.
      </p>
      <button
        type="button"
        onClick={onRetry}
        disabled={retrying}
        className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {retrying ? "Trying again…" : "Try again"}
      </button>
    </div>
  );
}

// ── Family Dashboard (Milestone 2 Task 12) ──────────────────────────────
// Six single-question cards + the Task 11 recommendations feed. Pure
// composition: every number is the source screen's own number (see
// backend's IntegrationIntegrityReview_Task12.md). Cards link to their
// source screen; the dependents card's source is this page itself, so it
// is a plain display card rather than a self-link.

function FamilyDashboardSection() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["family-dashboard"],
    queryFn: () => api.getFamilyDashboard(),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-3">
      <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
        Family dashboard
      </p>

      {isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="surface-card p-4 animate-pulse">
              <div className="h-3 w-24 rounded bg-muted mb-3" />
              <div className="h-5 w-32 rounded bg-muted/50" />
            </div>
          ))}
        </div>
      )}

      {isError && !isLoading && (
        <div className="surface-card p-6 text-center" role="alert">
          <p className="text-sm text-muted-foreground">
            We couldn't load your family dashboard. Everything else on this page still works.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Try again
          </button>
        </div>
      )}

      {data && !isLoading && !isError && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <DependentsCard card={data.dependents} />
            <EducationCard card={data.education} />
            <CoverageCard card={data.coverage} />
            <ParentsCard card={data.parents} />
            <RetirementCard card={data.retirement} />
            <EmergencyCard card={data.emergency} />
          </div>
          <DashboardRecommendationsFeed
            recommendations={data.recommendations}
            conflicts={data.conflicts}
            unavailable={data.recommendations_unavailable}
          />
        </>
      )}
    </div>
  );
}

function formatINR(amount: number): string {
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function CardShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="surface-card p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">{title}</p>
      {children}
    </div>
  );
}

function LinkCardShell({
  title,
  to,
  warning,
  children,
}: {
  title: string;
  to: string;
  warning?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className={`surface-card p-4 block transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
        warning ? "border border-warning/40" : ""
      }`}
    >
      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">{title}</p>
      {children}
    </Link>
  );
}

function UnavailableCard({ title }: { title: string }) {
  return (
    <CardShell title={title}>
      <p className="text-xs text-muted-foreground">Temporarily unavailable</p>
    </CardShell>
  );
}

function DependentsCard({ card }: { card: FamilyDashboard["dependents"] }) {
  if (!card) return <UnavailableCard title="Who depends on me?" />;
  const parts: string[] = [];
  if (card.children > 0) parts.push(`${card.children} ${card.children === 1 ? "kid" : "kids"}`);
  if (card.parents > 0) parts.push(`${card.parents} ${card.parents === 1 ? "parent" : "parents"}`);
  if (card.spouse > 0) parts.push("spouse");
  if (card.others > 0) parts.push(`${card.others} ${card.others === 1 ? "other" : "others"}`);
  return (
    <CardShell title="Who depends on me?">
      <p className="text-sm font-medium">
        {parts.length > 0 ? parts.join(" · ") : "Just you right now"}
      </p>
    </CardShell>
  );
}

function EducationCard({ card }: { card: FamilyDashboard["education"] }) {
  if (!card) {
    return (
      <LinkCardShell title="Education costs ahead" to="/app/family/goals">
        <p className="text-xs text-muted-foreground">No upcoming education goals</p>
      </LinkCardShell>
    );
  }
  const year = new Date(card.target_date).getFullYear();
  const who = card.tagged_member_names.length > 0 ? `${card.tagged_member_names.join(", ")}: ` : "";
  return (
    <LinkCardShell title="Education costs ahead" to="/app/family/goals">
      <p className="text-sm font-medium">
        {who}
        {card.goal_name}
      </p>
      <p className="text-xs text-muted-foreground mt-0.5">
        {formatINR(card.target_amount)} by {year}
      </p>
    </LinkCardShell>
  );
}

function CoverageCard({ card }: { card: FamilyDashboard["coverage"] }) {
  if (!card) return <UnavailableCard title="Insurance coverage" />;
  return (
    <LinkCardShell title="Insurance coverage" to="/app/family/insurance">
      <p className="text-sm font-medium">
        {card.covered_members} of {card.total_members} people covered
      </p>
    </LinkCardShell>
  );
}

function ParentsCard({ card }: { card: FamilyDashboard["parents"] }) {
  if (!card) return <UnavailableCard title="Parents" />;
  if (card.uncovered_parent_names.length === 0) {
    return (
      <LinkCardShell title="Parents" to="/app/family/insurance">
        <p className="text-xs text-muted-foreground">No insurance gaps we know of</p>
      </LinkCardShell>
    );
  }
  return (
    <LinkCardShell title="Parents" to="/app/family/insurance" warning>
      <p className="text-sm font-medium flex items-center gap-1.5">
        <AlertCircle className="h-3.5 w-3.5 text-warning shrink-0" aria-hidden="true" />
        {card.uncovered_parent_names.join(", ")}: no own insurance
      </p>
    </LinkCardShell>
  );
}

function RetirementCard({ card }: { card: FamilyDashboard["retirement"] }) {
  if (!card) {
    return (
      <LinkCardShell title="Retirement readiness" to="/app/goals">
        <p className="text-xs text-muted-foreground">No retirement goal yet</p>
      </LinkCardShell>
    );
  }
  return (
    <LinkCardShell title="Retirement readiness" to="/app/goals">
      <p className="text-sm font-medium">
        {Math.round(card.probability)}% {card.on_track ? "on track" : "— needs attention"}
      </p>
      <p className="text-xs text-muted-foreground mt-0.5">{card.goal_name}</p>
    </LinkCardShell>
  );
}

function EmergencyCard({ card }: { card: FamilyDashboard["emergency"] }) {
  if (!card) return <UnavailableCard title="Emergency readiness" />;
  if (card.monthly_expenses <= 0) {
    return (
      <LinkCardShell title="Emergency readiness" to="/app/goals">
        <p className="text-xs text-muted-foreground">Add income & expenses to see this</p>
      </LinkCardShell>
    );
  }
  // Display arithmetic only, per Task 9's precedent — the backend passes
  // through get_dashboard()'s authoritative figures and computes nothing.
  const months = card.liquid_assets / card.monthly_expenses;
  return (
    <LinkCardShell title="Emergency readiness" to="/app/goals">
      <p className="text-sm font-medium">{months.toFixed(1)} months covered</p>
    </LinkCardShell>
  );
}

const FEED_SOURCE_ICON = {
  insurance: ShieldCheck,
  schemes: Landmark,
  financial_health: Wallet,
} as const;

function DashboardRecommendationsFeed({
  recommendations,
  conflicts,
  unavailable,
}: {
  recommendations: FamilyRecommendation[];
  conflicts: RecommendationConflict[];
  unavailable: boolean;
}) {
  if (unavailable) {
    return (
      <div className="surface-card p-4" role="status">
        <p className="text-xs text-muted-foreground">
          We couldn't check for recommendations right now — the cards above are unaffected.
        </p>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {conflicts.map((conflict) => (
        <div
          key={`${conflict.subject}-${conflict.reference_code}`}
          role="status"
          className="surface-card p-3 border border-warning/30 bg-warning/5 text-xs text-muted-foreground"
        >
          {conflict.note}
        </div>
      ))}
      {recommendations.map((rec, i) => {
        const Icon = FEED_SOURCE_ICON[rec.source];
        return (
          <Link
            key={`${rec.source}-${rec.recommendation_type}-${i}`}
            to="/app/family/recommendations"
            className="surface-card p-4 flex items-start gap-3 border border-cyan/20 hover:border-cyan/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <Icon className="h-4 w-4 text-cyan shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="text-sm">{rec.why}</p>
              <p className="text-xs text-cyan mt-1">See full detail →</p>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
