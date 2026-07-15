import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, AlertCircle, Users as UsersIcon, Target } from "lucide-react";
import { api } from "@/lib/api";
import type { FamilyGoalSummary, FamilyMemberSummary } from "@/lib/api";
import { relationshipLabel } from "@/lib/family";

export const Route = createFileRoute("/app/family/goals")({
  head: () => ({ meta: [{ title: "Family Goals — Northstar" }] }),
  staticData: { shellTitle: "Family Goals" },
  component: FamilyGoals,
});

function FamilyGoals() {
  const goalsQuery = useQuery({
    queryKey: ["family-goals"],
    queryFn: () => api.getFamilyGoals(),
  });
  const membersQuery = useQuery({
    queryKey: ["family-home"],
    queryFn: () => api.getFamilyHome(),
  });

  const isLoading = goalsQuery.isLoading || membersQuery.isLoading;
  const isError = goalsQuery.isError || membersQuery.isError;

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
          <div className="h-14 rounded bg-muted/50" />
        </div>
      )}

      {isError && !isLoading && (
        <div className="surface-card p-8 text-center" role="alert">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-3" aria-hidden="true" />
          <p className="font-display text-base">We couldn't load your family goals.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Your goals are safe — this is just a loading problem.
          </p>
          <button
            type="button"
            onClick={() => {
              goalsQuery.refetch();
              membersQuery.refetch();
            }}
            className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Try again
          </button>
        </div>
      )}

      {goalsQuery.data && membersQuery.data && !isLoading && !isError && (
        <FamilyGoalsContent goals={goalsQuery.data} members={membersQuery.data.members} />
      )}
    </div>
  );
}

function FamilyGoalsContent({
  goals,
  members,
}: {
  goals: FamilyGoalSummary[];
  members: FamilyMemberSummary[];
}) {
  if (goals.length === 0) {
    return (
      <div className="surface-card p-10 text-center">
        <div className="mx-auto h-12 w-12 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center mb-4">
          <Target className="h-6 w-6 text-primary-foreground" aria-hidden="true" />
        </div>
        <p className="font-display text-lg">No goals yet.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Create a goal first, then come back here to say who it affects.
        </p>
        <Link
          to="/app/goals"
          className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          Go to Goals
        </Link>
      </div>
    );
  }

  const untagged = goals.filter((g) => g.tagged_members.length === 0);
  const sections = members
    .map((member) => ({
      member,
      goals: goals.filter((g) => g.tagged_members.some((t) => t.id === member.id)),
    }))
    .filter((section) => section.goals.length > 0);

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Say who each goal affects — it still belongs to your account, but this helps you see your
        plan the way your family actually experiences it.
      </p>

      {sections.map(({ member, goals: memberGoals }) => (
        <div key={member.id} className="surface-card p-5">
          <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-4">
            {member.name ?? relationshipLabel(member.relationship_type)}
          </p>
          <div className="space-y-3">
            {memberGoals.map((goal) => (
              <GoalTagRow key={`${member.id}-${goal.id}`} goal={goal} members={members} />
            ))}
          </div>
        </div>
      ))}

      <div className="surface-card p-5">
        <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-4">
          Not yet tagged
        </p>
        {untagged.length === 0 ? (
          <p className="text-sm text-muted-foreground">Every goal has been tagged.</p>
        ) : (
          <div className="space-y-3">
            {untagged.map((goal) => (
              <GoalTagRow key={`untagged-${goal.id}`} goal={goal} members={members} />
            ))}
          </div>
        )}
      </div>

      <Link
        to="/app/goals"
        className="inline-flex items-center gap-1.5 text-sm text-cyan hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
      >
        + Create a new goal
      </Link>
    </div>
  );
}

function disclosureText(names: string[]): string {
  const joined =
    names.length === 1
      ? names[0]
      : names.length === 2
        ? `${names[0]} and ${names[1]}`
        : `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
  return `This goal belongs to your account. ${joined} can see it if you share access, but their own contributions aren't tracked separately yet.`;
}

function GoalTagRow({
  goal,
  members,
}: {
  goal: FamilyGoalSummary;
  members: FamilyMemberSummary[];
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(goal.tagged_members.map((m) => m.id)),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.setGoalFamilyTags(goal.id, Array.from(selected));
      await queryClient.invalidateQueries({ queryKey: ["family-goals"] });
      setEditing(false);
    } catch {
      setError("We couldn't save these tags. Your goal itself is untouched.");
    } finally {
      setSaving(false);
    }
  }

  const tagNames = goal.tagged_members.map((m) => m.name ?? relationshipLabel(m.relationship_type));

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{goal.name}</p>
          <p className="text-xs text-muted-foreground">
            ${goal.target_amount.toLocaleString()} · {goal.probability.toFixed(0)}% on track
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (!editing) {
              // Re-sync from the latest server state every time the editor
              // opens — this component instance can stay mounted across a
              // tag change made elsewhere (e.g. the same goal's row under a
              // different member's section), so `selected` must not just be
              // the value captured at first mount.
              setSelected(new Set(goal.tagged_members.map((m) => m.id)));
              setError(null);
            }
            setEditing((v) => !v);
          }}
          className="flex items-center gap-1.5 text-xs text-cyan hover:underline shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
        >
          <UsersIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {editing ? "Cancel" : "Tag family members"}
        </button>
      </div>

      {tagNames.length > 0 && !editing && (
        <p className="mt-2 text-xs text-muted-foreground">{disclosureText(tagNames)}</p>
      )}

      {editing && (
        <div className="mt-4 space-y-3">
          <fieldset>
            <legend className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Who does this affect?
            </legend>
            <div className="space-y-2">
              {members.map((member) => (
                <label key={member.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.has(member.id)}
                    onChange={() => toggle(member.id)}
                    className="h-4 w-4 rounded border-border"
                  />
                  {member.name ?? relationshipLabel(member.relationship_type)}
                </label>
              ))}
            </div>
          </fieldset>

          {selected.size > 0 && (
            <p className="text-xs text-muted-foreground">
              {disclosureText(
                members
                  .filter((m) => selected.has(m.id))
                  .map((m) => m.name ?? relationshipLabel(m.relationship_type)),
              )}
            </p>
          )}

          {error && (
            <p role="alert" className="text-xs text-red-400">
              {error}
            </p>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-1.5 text-xs font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      )}
    </div>
  );
}
