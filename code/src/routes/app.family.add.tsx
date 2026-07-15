import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { ArrowLeft, Sparkles } from "lucide-react";
import { useShellTitle } from "@/lib/shell-title";
import { api } from "@/lib/api";
import type { FamilyMemberFields, RelationshipType } from "@/lib/api";
import { FamilyMemberForm } from "@/components/family/FamilyMemberForm";

const searchSchema = z.object({
  type: z.enum(["parent", "other"]).default("other"),
});

export const Route = createFileRoute("/app/family/add")({
  head: () => ({ meta: [{ title: "Add a family member — Northstar" }] }),
  validateSearch: searchSchema,
  // Generic fallback for the SSR render (useShellTitle's useLayoutEffect
  // doesn't run server-side) — immediately replaced client-side by the
  // type-specific title via useShellTitle below.
  staticData: { shellTitle: "Add a family member" },
  component: AddFamilyMember,
});

// Net-new members only (POST) — matches the two persistent Quick Action
// cards on Family Home. Spouse/child are seeded as placeholders at
// onboarding and completed via /app/family/members/:id (PUT) instead;
// FamilyPlanningDesign.md's Family Home wireframe only offers "+ Add a
// parent"/"+ Add someone else" as net-new entry points, so this route only
// needs to support those two relationship types.
function AddFamilyMember() {
  const { type } = Route.useSearch();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedSchemes, setSavedSchemes] = useState<{ code: string; reason: string }[] | null>(null);

  const relationshipType: RelationshipType = type;

  async function handleSubmit(fields: FamilyMemberFields) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.createFamilyMember({
        relationship_type: relationshipType,
        ...fields,
      });
      await queryClient.invalidateQueries({ queryKey: ["family-home"] });
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

  const title =
    relationshipType === "parent" ? "Add a parent who depends on you" : "Add someone else";
  useShellTitle(title);

  return (
    <div className="max-w-lg">
      <Link
        to="/app/family"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition mb-6"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Back to Family
      </Link>

      {savedSchemes && savedSchemes.length > 0 && (
        <div
          role="status"
          className="surface-card p-4 mb-4 border border-cyan/30 bg-cyan/5 flex gap-3"
        >
          <Sparkles className="h-5 w-5 text-cyan shrink-0" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium">{savedSchemes[0].reason}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              We'll add this to your recommendations.
            </p>
            <Link to="/app/family" className="mt-2 inline-block text-xs text-cyan hover:underline">
              Back to Family →
            </Link>
          </div>
        </div>
      )}

      {!savedSchemes && (
        <FamilyMemberForm
          relationshipType={relationshipType}
          onSubmit={handleSubmit}
          submitting={submitting}
          submitError={submitError}
        />
      )}
    </div>
  );
}
