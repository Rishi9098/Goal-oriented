import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, AlertCircle, ShieldCheck, Plus, Users as UsersIcon } from "lucide-react";
import { api } from "@/lib/api";
import type {
  FamilyMemberSummary,
  HealthPolicy,
  InsuranceRecommendation,
  PolicyType,
} from "@/lib/api";
import { relationshipLabel } from "@/lib/family";

export const Route = createFileRoute("/app/family/insurance")({
  head: () => ({ meta: [{ title: "Family Insurance — Northstar" }] }),
  staticData: { shellTitle: "Family Insurance" },
  component: FamilyInsurance,
});

const POLICY_TYPE_LABEL: Record<PolicyType, string> = {
  family_floater: "Family floater",
  individual: "Individual policy",
  senior_citizen_standalone: "Standalone senior citizen policy",
};

function formatINR(n: number): string {
  return `₹${n.toLocaleString("en-IN")}`;
}

function FamilyInsurance() {
  const insuranceQuery = useQuery({
    queryKey: ["family-insurance"],
    queryFn: () => api.getFamilyInsurance(),
  });
  const membersQuery = useQuery({
    queryKey: ["family-home"],
    queryFn: () => api.getFamilyHome(),
  });

  const isLoading = insuranceQuery.isLoading || membersQuery.isLoading;
  const isError = insuranceQuery.isError || membersQuery.isError;

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
          <p className="font-display text-base">We couldn't load your family insurance.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Your records are safe — this is just a loading problem.
          </p>
          <button
            type="button"
            onClick={() => {
              insuranceQuery.refetch();
              membersQuery.refetch();
            }}
            className="mt-4 rounded-lg border border-border px-4 py-2 text-sm hover:border-border-strong hover:bg-accent/40 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            Try again
          </button>
        </div>
      )}

      {insuranceQuery.data && membersQuery.data && !isLoading && !isError && (
        <FamilyInsuranceContent data={insuranceQuery.data} members={membersQuery.data.members} />
      )}
    </div>
  );
}

function FamilyInsuranceContent({
  data,
  members,
}: {
  data: { policies: HealthPolicy[]; recommendation: InsuranceRecommendation | null };
  members: FamilyMemberSummary[];
}) {
  const [showAddForm, setShowAddForm] = useState(false);

  return (
    <div className="space-y-6">
      {data.recommendation && <RecommendationCard recommendation={data.recommendation} />}

      <div className="surface-card p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
            Policies on file
          </p>
          <button
            type="button"
            onClick={() => setShowAddForm((v) => !v)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-cyan hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            {showAddForm ? "Cancel" : "Add a policy"}
          </button>
        </div>

        {showAddForm && <AddPolicyForm members={members} onDone={() => setShowAddForm(false)} />}

        {data.policies.length === 0 && !showAddForm ? (
          <p className="text-sm text-muted-foreground">No health policies recorded yet.</p>
        ) : (
          <div className="space-y-3 mt-3">
            {data.policies.map((policy) => (
              <PolicyRow key={policy.id} policy={policy} members={members} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RecommendationCard({ recommendation }: { recommendation: InsuranceRecommendation }) {
  return (
    <div role="status" className="surface-card p-5 border border-cyan/30 bg-cyan/5 space-y-3">
      <div className="flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-cyan shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-2">
          <p className="text-sm font-medium">{recommendation.why}</p>
          <p className="text-xs text-muted-foreground">{recommendation.why_now}</p>
          <div className="flex flex-wrap gap-3 text-xs">
            <span className="rounded-full bg-cyan/10 px-2.5 py-1">
              Your floater: up to {formatINR(recommendation.floater_deduction_limit)}
            </span>
            <span className="rounded-full bg-cyan/10 px-2.5 py-1">
              Standalone parent policy: up to {formatINR(recommendation.parent_deduction_limit)}
            </span>
          </div>
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
              {recommendation.what_information_was_used.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          {recommendation.what_information_is_missing.length > 0 && (
            <div>
              <p className="uppercase tracking-wide text-[10px] text-muted-foreground/80">
                We don't yet know
              </p>
              <ul className="list-disc list-inside">
                {recommendation.what_information_is_missing.map((item) => (
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

function PolicyRow({ policy, members }: { policy: HealthPolicy; members: FamilyMemberSummary[] }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(
    new Set(policy.covered_members.map((m) => m.id)),
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
    if (selected.size === 0) {
      setError("A policy must cover at least one family member.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updatePolicyCoverage(policy.id, Array.from(selected));
      await queryClient.invalidateQueries({ queryKey: ["family-insurance"] });
      setEditing(false);
    } catch {
      setError("We couldn't save this change.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{POLICY_TYPE_LABEL[policy.policy_type]}</p>
          <p className="text-xs text-muted-foreground">
            {formatINR(policy.sum_insured)} cover · {formatINR(policy.annual_premium)}/yr
            {policy.insurer ? ` · ${policy.insurer}` : ""}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Covers:{" "}
            {policy.covered_members
              .map((m) => m.name ?? relationshipLabel(m.relationship_type))
              .join(", ")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (!editing) {
              setSelected(new Set(policy.covered_members.map((m) => m.id)));
              setError(null);
            }
            setEditing((v) => !v);
          }}
          className="flex items-center gap-1.5 text-xs text-cyan hover:underline shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded"
        >
          <UsersIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {editing ? "Cancel" : "Edit coverage"}
        </button>
      </div>

      {editing && (
        <div className="mt-4 space-y-3">
          <fieldset>
            <legend className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Who does this policy cover?
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

type NewPolicyForm = {
  policy_type: PolicyType;
  sum_insured: string;
  annual_premium: string;
  insurer: string;
};

const EMPTY_POLICY_FORM: NewPolicyForm = {
  policy_type: "family_floater",
  sum_insured: "500000",
  annual_premium: "12000",
  insurer: "",
};

function AddPolicyForm({
  members,
  onDone,
}: {
  members: FamilyMemberSummary[];
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<NewPolicyForm>(EMPTY_POLICY_FORM);
  const [selected, setSelected] = useState<Set<string>>(new Set());
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selected.size === 0) {
      setError("Select at least one family member this policy covers.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.createInsurancePolicy({
        policy_type: form.policy_type,
        sum_insured: Number(form.sum_insured),
        annual_premium: Number(form.annual_premium),
        insurer: form.insurer || undefined,
        household_member_ids: Array.from(selected),
      });
      await queryClient.invalidateQueries({ queryKey: ["family-insurance"] });
      onDone();
    } catch {
      setError("We couldn't save this policy. Nothing else was changed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-border p-4 space-y-3 mb-4">
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Policy type</span>
        <select
          value={form.policy_type}
          onChange={(e) => setForm((f) => ({ ...f, policy_type: e.target.value as PolicyType }))}
          className="field-input w-full"
        >
          {(Object.keys(POLICY_TYPE_LABEL) as PolicyType[]).map((type) => (
            <option key={type} value={type}>
              {POLICY_TYPE_LABEL[type]}
            </option>
          ))}
        </select>
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Sum insured (₹)</span>
          <input
            type="number"
            min="1"
            required
            value={form.sum_insured}
            onChange={(e) => setForm((f) => ({ ...f, sum_insured: e.target.value }))}
            className="field-input w-full"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-muted-foreground">Annual premium (₹)</span>
          <input
            type="number"
            min="0"
            required
            value={form.annual_premium}
            onChange={(e) => setForm((f) => ({ ...f, annual_premium: e.target.value }))}
            className="field-input w-full"
          />
        </label>
      </div>

      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Insurer (optional)</span>
        <input
          value={form.insurer}
          onChange={(e) => setForm((f) => ({ ...f, insurer: e.target.value }))}
          placeholder="e.g. Star Health"
          className="field-input w-full"
        />
      </label>

      <fieldset>
        <legend className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Who does this policy cover?
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

      {error && (
        <p role="alert" className="text-xs text-red-400">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={saving}
        className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-1.5 text-xs font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {saving ? "Saving…" : "Save policy"}
      </button>
    </form>
  );
}
