import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Check, Loader2, Pencil, X } from "lucide-react";
import { auth } from "@/lib/api";
import { api } from "@/lib/api";
import type { FamilyMemberSummary } from "@/lib/api";
import { relationshipLabel } from "@/lib/family";

export const Route = createFileRoute("/app/profile")({
  head: () => ({ meta: [{ title: "Profile — Northstar" }] }),
  staticData: { shellTitle: "Profile" },
  component: Profile,
});

type FormState = {
  fullName: string;
  email: string;
};

type Status = "idle" | "saving" | "saved" | "error";

function initials(name: string) {
  return name
    .trim()
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function Profile() {
  const [form, setForm] = useState<FormState>({
    fullName: "",
    email: "",
  });
  const [saved, setSaved] = useState<FormState | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [loading, setLoading] = useState(true);
  const [familyMembers, setFamilyMembers] = useState<FamilyMemberSummary[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // PCA-2: household data now comes from the certified Family service
    // (api.getFamilyHome), never from user_profiles.marital_status/dependents.
    // api.getProfile() is no longer called here — nothing on this screen
    // reads from it anymore once those two fields are removed.
    Promise.all([auth.me(), api.getFamilyHome()]).then(([user, familyHome]) => {
      const initial: FormState = {
        fullName: user.full_name ?? "",
        email: user.email,
      };
      setForm(initial);
      setSaved(initial);
      setFamilyMembers(familyHome.members);
      setLoading(false);
    });
  }, []);

  const isDirty =
    saved !== null && (form.fullName !== saved.fullName || form.email !== saved.email);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (status === "saved") setStatus("idle");
  };

  const handleReset = () => {
    if (saved) setForm(saved);
    setStatus("idle");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty) return;
    setStatus("saving");
    try {
      await auth.updateMe({ full_name: form.fullName });
      setSaved(form);
      setStatus("saved");
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  const avatarText = initials(form.fullName) || "?";

  return (
    <div className="max-w-2xl space-y-6">
      {/* Avatar header */}
      <div className="surface-card p-6 flex items-center gap-4">
        <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center text-2xl font-medium text-primary-foreground shrink-0 select-none">
          {avatarText}
        </div>
        <div>
          <p className="font-display text-xl">{form.fullName || "Your Name"}</p>
          <p className="text-sm text-muted-foreground">{form.email}</p>
        </div>
      </div>

      {/* Editable form */}
      <form onSubmit={handleSubmit} noValidate>
        <div className="surface-card p-6 space-y-5">
          <div className="flex items-center justify-between mb-1">
            <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
              Personal details
            </p>
            {status === "saved" && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <Check className="h-3.5 w-3.5" /> Saved
              </span>
            )}
            {status === "error" && <span className="text-xs text-red-400">Failed to save</span>}
          </div>

          <Field label="Full name">
            <input
              name="fullName"
              value={form.fullName}
              onChange={handleChange}
              placeholder="Alex Reyes"
              className="field-input"
              required
              minLength={2}
            />
          </Field>

          <Field label="Email address">
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              className="field-input"
              required
            />
          </Field>

          <Field label="Household">
            <div className="rounded-lg border border-border bg-surface px-3 py-2.5 space-y-1.5">
              {familyMembers.map((member) => (
                <div key={member.id} className="flex items-center justify-between text-sm">
                  <span>{member.name ?? relationshipLabel(member.relationship_type)}</span>
                  <span className="text-xs text-muted-foreground">
                    {relationshipLabel(member.relationship_type)}
                    {!member.name && member.relationship_type !== "self" && " · not yet added"}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">
              This reflects the family details you&apos;ve shared and can&apos;t be edited here yet.
            </p>
          </Field>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            {isDirty && (
              <button
                type="button"
                onClick={handleReset}
                className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:border-border-strong hover:text-foreground transition"
              >
                <X className="h-3.5 w-3.5" />
                Discard
              </button>
            )}
            <button
              type="submit"
              disabled={!isDirty || status === "saving"}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {status === "saving" ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Pencil className="h-3.5 w-3.5" />
                  Save changes
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}
