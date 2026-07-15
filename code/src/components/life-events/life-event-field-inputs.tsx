import { Plus, X } from "lucide-react";
import type { EntityKind, LifeEventField } from "@/lib/life-events";

export type EntityOptionList = { value: string; label: string }[];
export type EntityOptionsMap = Record<EntityKind, EntityOptionList>;

// The values a life-event form collects, keyed by field name. Every value is
// kept as its raw string/boolean form (matching every plain `<input>` in
// this codebase's other forms, e.g. app.goals.tsx's `NewGoalForm`) — numeric
// and date coercion happens once, at submit time, in `buildInputsPayload`.
export type LifeEventFormValues = Record<
  string,
  string | string[] | boolean | GoalContributionRow[]
>;

export type GoalContributionRow = { goal_id: string; new_monthly_contribution: string };

function FieldShell({
  label,
  required,
  helpText,
  children,
}: {
  label: string;
  required?: boolean;
  helpText?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs text-muted-foreground">
        {label}
        {required && <span className="text-red-400"> *</span>}
      </span>
      {children}
      {helpText && <span className="block text-[11px] text-muted-foreground/70">{helpText}</span>}
    </label>
  );
}

function EntitySelect({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  options: EntityOptionList;
  placeholder: string;
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="field-input">
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function GoalContributionsInput({
  rows,
  goals,
  onChange,
}: {
  rows: GoalContributionRow[];
  goals: EntityOptionList;
  onChange: (rows: GoalContributionRow[]) => void;
}) {
  function updateRow(index: number, patch: Partial<GoalContributionRow>) {
    onChange(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }
  function removeRow(index: number) {
    onChange(rows.filter((_, i) => i !== index));
  }
  return (
    <div className="space-y-2">
      {rows.map((row, i) => (
        <div key={i} className="flex items-center gap-2">
          <select
            value={row.goal_id}
            onChange={(e) => updateRow(i, { goal_id: e.target.value })}
            className="field-input flex-1"
          >
            <option value="">Select a goal…</option>
            {goals.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            placeholder="New monthly $"
            value={row.new_monthly_contribution}
            onChange={(e) => updateRow(i, { new_monthly_contribution: e.target.value })}
            className="field-input w-36"
          />
          <button
            type="button"
            onClick={() => removeRow(i)}
            aria-label="Remove goal contribution"
            className="p-2 text-muted-foreground hover:text-foreground shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...rows, { goal_id: "", new_monthly_contribution: "" }])}
        className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
      >
        <Plus className="h-3.5 w-3.5" /> Add goal
      </button>
    </div>
  );
}

export function LifeEventFieldInput({
  field,
  value,
  onChange,
  entityOptions,
}: {
  field: LifeEventField;
  value: LifeEventFormValues[string] | undefined;
  onChange: (value: LifeEventFormValues[string]) => void;
  entityOptions: EntityOptionsMap;
}) {
  switch (field.kind) {
    case "text": {
      // Datalist suggestions (AutomationAudit.md Phase 5) — offered, never
      // enforced: the browser's native autocomplete list, not a restriction
      // on what can be typed and submitted.
      const listId = field.suggestions ? `${field.name}-suggestions` : undefined;
      return (
        <FieldShell label={field.label} required={field.required} helpText={field.helpText}>
          <input
            type="text"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            list={listId}
            className="field-input"
          />
          {field.suggestions && (
            <datalist id={listId}>
              {field.suggestions.map((s) => (
                <option key={s} value={s} />
              ))}
            </datalist>
          )}
        </FieldShell>
      );
    }
    case "number":
      return (
        <FieldShell label={field.label} required={field.required} helpText={field.helpText}>
          <input
            type="number"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            required={field.required}
            min={field.min}
            step={field.step ?? "any"}
            className="field-input"
          />
        </FieldShell>
      );
    case "date":
      return (
        <FieldShell label={field.label} required={field.required} helpText={field.helpText}>
          <input
            type="date"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            required={field.required}
            className="field-input"
          />
        </FieldShell>
      );
    case "boolean":
      return (
        <label className="flex items-center gap-2 text-sm pt-6">
          <input
            type="checkbox"
            checked={(value as boolean) ?? field.defaultValue ?? false}
            onChange={(e) => onChange(e.target.checked)}
            className="h-4 w-4 rounded border-border"
          />
          {field.label}
          {field.helpText && (
            <span className="text-[11px] text-muted-foreground/70">({field.helpText})</span>
          )}
        </label>
      );
    case "select":
      return (
        <FieldShell label={field.label} required={field.required} helpText={field.helpText}>
          <select
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            required={field.required}
            className="field-input"
          >
            {!field.required && <option value="">—</option>}
            {field.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </FieldShell>
      );
    case "entity":
      return (
        <FieldShell label={field.label} required={field.required} helpText={field.helpText}>
          <EntitySelect
            value={(value as string) ?? ""}
            onChange={onChange}
            options={entityOptions[field.entity]}
            placeholder="Select…"
          />
        </FieldShell>
      );
    case "multi-entity": {
      const selected = (value as string[]) ?? [];
      const options = entityOptions[field.entity];
      return (
        <FieldShell label={field.label} helpText={field.helpText}>
          <div className="flex flex-wrap gap-2">
            {options.length === 0 && (
              <span className="text-xs text-muted-foreground">Nothing available.</span>
            )}
            {options.map((o) => {
              const checked = selected.includes(o.value);
              return (
                <label
                  key={o.value}
                  className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs cursor-pointer transition-colors ${
                    checked ? "border-primary bg-primary/10" : "border-border bg-surface"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) =>
                      onChange(
                        e.target.checked
                          ? [...selected, o.value]
                          : selected.filter((v) => v !== o.value),
                      )
                    }
                    className="h-3.5 w-3.5"
                  />
                  {o.label}
                </label>
              );
            })}
          </div>
        </FieldShell>
      );
    }
    case "goal-contributions":
      return (
        <FieldShell label={field.label} helpText={field.helpText}>
          <GoalContributionsInput
            rows={(value as GoalContributionRow[]) ?? []}
            goals={entityOptions.goal}
            onChange={onChange}
          />
        </FieldShell>
      );
  }
}
