import { useRef, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, AlertCircle, Sparkles, Pencil, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { FamilyMemberFields, RelationshipType } from "@/lib/api";
import { FamilyMemberForm } from "@/components/family/FamilyMemberForm";
import { relationshipLabel } from "@/lib/family";

export const Route = createFileRoute("/app/family/members/$id")({
  head: () => ({ meta: [{ title: "Family member — Northstar" }] }),
  staticData: { shellTitle: "Family member" },
  component: FamilyMemberDetail,
});

function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function policyTypeLabel(type: string): string {
  return type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Completing an incomplete placeholder and editing an already-complete
// member share the exact same form (Task 6) and the exact same PUT call —
// only the surrounding chrome differs (no "view" state exists yet for an
// incomplete member, so its form has no view mode to return to).
function FamilyMemberDetail() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedSchemes, setSavedSchemes] = useState<{ code: string; reason: string }[] | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const removeButtonRef = useRef<HTMLButtonElement>(null);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["family-member", id],
    queryFn: () => api.getFamilyMember(id),
  });

  async function handleSubmit(fields: FamilyMemberFields) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.updateFamilyMember(id, fields);
      await queryClient.invalidateQueries({ queryKey: ["family-home"] });
      await queryClient.invalidateQueries({ queryKey: ["family-member", id] });
      if (result.eligible_schemes.length > 0) {
        setSavedSchemes(result.eligible_schemes);
      } else {
        navigate({ to: "/app/family" });
      }
    } catch {
      setSubmitError("We couldn't save their details. Your other family information is safe.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove() {
    setRemoving(true);
    setRemoveError(null);
    try {
      await api.deleteFamilyMember(id);
      await queryClient.invalidateQueries({ queryKey: ["family-home"] });
      navigate({ to: "/app/family" });
    } catch {
      setRemoveError("We couldn't remove them. Your other family information is safe.");
      setRemoving(false);
    }
  }

  function cancelRemove() {
    setConfirmRemove(false);
    removeButtonRef.current?.focus();
  }

  const member = data?.member;
  const showForm = member && (isEditing || !member.is_complete) && !savedSchemes;

  return (
    <div className="max-w-lg">
      <Link
        to="/app/family"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to Family
      </Link>

      {isLoading && (
        <div className="surface-card p-6 animate-pulse space-y-4" aria-busy="true">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="h-10 rounded bg-muted/50" />
          <div className="h-10 rounded bg-muted/50" />
        </div>
      )}

      {isError && !isLoading && (
        <div className="surface-card p-8 text-center" role="alert">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400 mb-3" aria-hidden="true" />
          <p className="font-display text-base">We couldn't load this person's details.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Your family details are safe — this is just a loading problem.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {isFetching ? "Trying again…" : "Try again"}
          </button>
        </div>
      )}

      {member && !isLoading && !isError && (
        <>
          {member.relationship_type === "self" ? (
            <div className="surface-card p-6 text-sm text-muted-foreground">
              Your own details are managed from{" "}
              <Link
                to="/app/profile"
                className="text-cyan hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
              >
                Profile
              </Link>
              , not here.
            </div>
          ) : savedSchemes && savedSchemes.length > 0 ? (
            <div
              role="status"
              className="surface-card p-4 border border-cyan/30 bg-cyan/5 flex gap-3"
            >
              <Sparkles className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium">{savedSchemes[0].reason}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  We'll add this to your recommendations.
                </p>
                <Link
                  to="/app/family"
                  className="mt-2 inline-block text-xs text-cyan hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
                >
                  Back to Family →
                </Link>
              </div>
            </div>
          ) : showForm ? (
            <>
              <FamilyMemberForm
                relationshipType={member.relationship_type as RelationshipType}
                initial={member}
                onSubmit={handleSubmit}
                submitting={submitting}
                submitError={submitError}
              />
              {member.is_complete && (
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="mt-3 text-xs text-muted-foreground hover:text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
                >
                  Cancel
                </button>
              )}
            </>
          ) : (
            <div className="space-y-5">
              <div className="surface-card p-6">
                <h1 className="font-display text-xl">{member.name}</h1>
                <p className="text-sm text-muted-foreground">
                  {relationshipLabel(member.relationship_type)}
                </p>
                {formatDate(member.date_of_birth) && (
                  <p className="mt-2 text-sm">
                    <span className="text-muted-foreground">Date of birth: </span>
                    {formatDate(member.date_of_birth)}
                  </p>
                )}
              </div>

              <div className="surface-card p-5">
                <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-3">
                  Goals involving {member.name}
                </p>
                {data.tagged_goals.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No goals tagged yet.</p>
                ) : (
                  <ul className="space-y-2">
                    {data.tagged_goals.map((g) => (
                      <li key={g.id} className="text-sm">
                        {g.name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="surface-card p-5">
                <p className="font-display text-sm uppercase tracking-widest text-muted-foreground mb-3">
                  Health coverage
                </p>
                {data.coverage.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Not yet covered under any policy.</p>
                ) : (
                  <ul className="space-y-2">
                    {data.coverage.map((c) => (
                      <li key={c.health_policy_id} className="text-sm">
                        {policyTypeLabel(c.policy_type)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                  Edit details
                </button>

                {!confirmRemove ? (
                  <button
                    ref={removeButtonRef}
                    type="button"
                    onClick={() => setConfirmRemove(true)}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-red-400 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Remove from household
                  </button>
                ) : (
                  <div className="flex items-center gap-3">
                    <p className="text-xs text-muted-foreground">Are you sure?</p>
                    <button
                      type="button"
                      onClick={handleRemove}
                      disabled={removing}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-1.5 text-xs text-red-400 font-medium hover:bg-red-500/20 disabled:opacity-50 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                    >
                      {removing && (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                      )}
                      Yes, remove
                    </button>
                    <button
                      type="button"
                      onClick={cancelRemove}
                      className="text-xs text-muted-foreground hover:text-foreground transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {removeError && (
                <p role="alert" className="text-sm text-red-400">
                  {removeError}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
