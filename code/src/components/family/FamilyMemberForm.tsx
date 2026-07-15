import { useState } from "react";
import { Loader2 } from "lucide-react";
import type { FamilyMemberFields, Gender, InsuranceStatus, RelationshipType } from "@/lib/api";

type Props = {
  relationshipType: RelationshipType;
  initial?: Partial<FamilyMemberFields>;
  onSubmit: (data: FamilyMemberFields) => Promise<void>;
  submitting: boolean;
  submitError: string | null;
};

const TODAY = new Date().toISOString().slice(0, 10);
const MIN_DOB = (() => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 130);
  return d.toISOString().slice(0, 10);
})();

// Business rules mirror backend/app/services/family_service.py's
// validate_member_fields() exactly — this is client-side UX (fail fast,
// clear message) only; the server remains the real enforcement.
function validate(relationshipType: RelationshipType, fields: FamilyMemberFields): string | null {
  if (!fields.name.trim()) return "Name is required.";
  if (fields.name.length > 255) return "Name must be 255 characters or fewer.";

  if ((relationshipType === "spouse" || relationshipType === "child") && !fields.date_of_birth) {
    return "Date of birth is required.";
  }
  if (fields.date_of_birth) {
    if (fields.date_of_birth > TODAY) return "Date of birth cannot be in the future.";
    if (fields.date_of_birth < MIN_DOB) return "Date of birth cannot be more than 130 years ago.";
  }
  if (relationshipType === "parent") {
    if (fields.relationship_detail !== "mother" && fields.relationship_detail !== "father") {
      return "Please select whether this is your mother or father.";
    }
    if (!fields.has_own_insurance) {
      return "Please answer whether they have their own health insurance.";
    }
  }
  if (relationshipType === "other" && !fields.relationship_detail?.trim()) {
    return "Please tell us their relationship to you.";
  }
  return null;
}

export function FamilyMemberForm({
  relationshipType,
  initial,
  onSubmit,
  submitting,
  submitError,
}: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [dob, setDob] = useState(initial?.date_of_birth ?? "");
  const [gender, setGender] = useState<Gender | "">(initial?.gender ?? "");
  const [relationshipDetail, setRelationshipDetail] = useState(initial?.relationship_detail ?? "");
  const [hasOwnInsurance, setHasOwnInsurance] = useState<InsuranceStatus | "">(
    initial?.has_own_insurance ?? "",
  );
  const [validationError, setValidationError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fields: FamilyMemberFields = {
      name: name.trim(),
      date_of_birth: dob || null,
      gender: relationshipType === "child" && gender ? gender : null,
      relationship_detail: relationshipDetail.trim() || null,
      has_own_insurance: relationshipType === "parent" && hasOwnInsurance ? hasOwnInsurance : null,
    };
    const error = validate(relationshipType, fields);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    await onSubmit(fields);
  }

  const error = validationError ?? submitError;

  return (
    <form onSubmit={handleSubmit} noValidate className="surface-card p-6 space-y-5">
      <Field label="Name">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Their name"
          className="field-input"
          maxLength={255}
        />
      </Field>

      {(relationshipType === "spouse" || relationshipType === "child") && (
        <Field
          label="Date of birth"
          hint={
            relationshipType === "spouse"
              ? "Age affects joint retirement timing and health-insurance premium calculations — nothing else."
              : undefined
          }
        >
          <input
            type="date"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
            max={TODAY}
            className="field-input"
          />
        </Field>
      )}

      {relationshipType === "other" && (
        <Field label="Date of birth (optional)">
          <input
            type="date"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
            max={TODAY}
            className="field-input"
          />
        </Field>
      )}

      {relationshipType === "child" && (
        <Field
          label="Gender (optional)"
          hint="This helps us find scholarships and schemes that might apply — never required."
        >
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value as Gender | "")}
            className="field-input"
          >
            <option value="">Prefer not to say</option>
            <option value="female">Girl</option>
            <option value="male">Boy</option>
            <option value="other">Other</option>
          </select>
        </Field>
      )}

      {relationshipType === "parent" && (
        <>
          <Field label="Relationship">
            <select
              value={relationshipDetail}
              onChange={(e) => setRelationshipDetail(e.target.value)}
              className="field-input"
            >
              <option value="">Select one</option>
              <option value="mother">Mother</option>
              <option value="father">Father</option>
            </select>
          </Field>
          <Field
            label="Do they have their own health insurance?"
            hint="If not, we'll show you whether a separate policy for them saves you money on premiums and taxes — it usually does."
          >
            <select
              value={hasOwnInsurance}
              onChange={(e) => setHasOwnInsurance(e.target.value as InsuranceStatus | "")}
              className="field-input"
            >
              <option value="">Select one</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
              <option value="not_sure">Not sure</option>
            </select>
          </Field>
        </>
      )}

      {relationshipType === "other" && (
        <Field label="Relationship">
          <input
            value={relationshipDetail}
            onChange={(e) => setRelationshipDetail(e.target.value)}
            placeholder="e.g. Sibling, guardian"
            className="field-input"
            maxLength={100}
          />
        </Field>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
        Save & continue
      </button>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
