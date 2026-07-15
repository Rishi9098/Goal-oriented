import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, Eye, Loader2, Sparkles, HeartHandshake } from "lucide-react";
import { useDialogA11y } from "@/hooks/use-dialog-a11y";
import { api } from "@/lib/api";
import type { LifeEventRecord } from "@/lib/api";
import {
  groupLifeEventTypesByCategory,
  summarizeAffectedAreas,
  type LifeEventTypeConfig,
} from "@/lib/life-events";
import {
  allFields,
  buildEntityOptions,
  buildInputsPayload,
  missingRequiredFields,
} from "@/lib/life-events-form";
import {
  LifeEventFieldInput,
  type EntityOptionsMap,
  type LifeEventFormValues,
} from "@/components/life-events/life-event-field-inputs";

const EMPTY_ENTITY_OPTIONS: EntityOptionsMap = {
  income: [],
  expense: [],
  asset: [],
  liability: [],
  goal: [],
  member: [],
};

type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "loaded";
      affectedEntities: string[];
      effectCount: number;
      validationErrors: string[];
    };

function todayIso(): string {
  return new Date().toISOString().split("T")[0];
}

export function RecordLifeEventDialog({
  onClose,
  onRecorded,
}: {
  onClose: () => void;
  onRecorded: (event: LifeEventRecord) => void;
}) {
  const [selectedType, setSelectedType] = useState<LifeEventTypeConfig | null>(null);
  const [entityOptions, setEntityOptions] = useState<EntityOptionsMap>(EMPTY_ENTITY_OPTIONS);
  const [occurredOn, setOccurredOn] = useState(todayIso());
  const [notes, setNotes] = useState("");
  const [values, setValues] = useState<LifeEventFormValues>({});
  const [preview, setPreview] = useState<PreviewState>({ status: "idle" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // BehavioralDesignAudit.md Phase 7 — a distinct, honest confirmation for
  // unambiguously joyful milestones only (selectedType.celebration is unset
  // for every other event, so this never fires for them). Manual "Done"
  // dismissal only — no forced timer.
  const [celebrating, setCelebrating] = useState<{
    event: LifeEventRecord;
    celebration: { title: string; body: string };
  } | null>(null);

  useEffect(() => {
    Promise.all([
      api.getIncome(),
      api.getExpenses(),
      api.getAssets(),
      api.getLiabilities(),
      api.getGoals(),
      api.getFamilyHome(),
    ]).then(([income, expenses, assets, liabilities, goals, family]) => {
      setEntityOptions(
        buildEntityOptions({
          income,
          expenses,
          assets,
          liabilities,
          goals,
          members: family.members,
        }),
      );
    });
  }, []);

  // Auto-select the single option (AutomationAudit.md Phase 5) — only ever
  // when a field's entity list has exactly one item and nothing is chosen
  // yet; the field stays a fully live, editable select/checkbox, never
  // locked or hidden. Re-runs if entityOptions arrives after a type is
  // already selected (e.g. a slow network), so nothing is missed.
  useEffect(() => {
    if (!selectedType) return;
    setValues((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const field of allFields(selectedType)) {
        if (field.kind === "entity") {
          const options = entityOptions[field.entity];
          if (options.length === 1 && !next[field.name]) {
            next[field.name] = options[0].value;
            changed = true;
          }
        } else if (field.kind === "multi-entity") {
          const options = entityOptions[field.entity];
          const current = next[field.name] as string[] | undefined;
          if (options.length === 1 && (!current || current.length === 0)) {
            next[field.name] = [options[0].value];
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
  }, [selectedType, entityOptions]);

  function selectType(type: LifeEventTypeConfig) {
    setSelectedType(type);
    setValues({});
    setPreview({ status: "idle" });
    setError(null);
  }

  function updateField(name: string, value: LifeEventFormValues[string]) {
    setValues((prev) => ({ ...prev, [name]: value }));
    setPreview({ status: "idle" });
  }

  async function handlePreview() {
    if (!selectedType) return;
    setPreview({ status: "loading" });
    try {
      const result = await api.previewLifeEvent(
        selectedType.value,
        buildInputsPayload(selectedType, values),
      );
      setPreview({
        status: "loaded",
        affectedEntities: result.affected_entities,
        effectCount: result.effects.length,
        validationErrors: result.validation_errors,
      });
    } catch (err) {
      setPreview({
        status: "error",
        message: err instanceof Error ? err.message : "Preview failed.",
      });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedType) return;
    const missing = missingRequiredFields(selectedType, values);
    if (missing.length > 0) {
      setError(`Please fill in: ${missing.join(", ")}.`);
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const result = await api.recordLifeEvent({
        event_type: selectedType.value,
        occurred_on: occurredOn,
        inputs: buildInputsPayload(selectedType, values),
        notes: notes.trim() || undefined,
      });
      if (selectedType.celebration) {
        setCelebrating({ event: result.life_event, celebration: selectedType.celebration });
      } else {
        onRecorded(result.life_event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record this life event.");
    } finally {
      setSaving(false);
    }
  }

  const categories = groupLifeEventTypesByCategory();

  function finishCelebration() {
    if (!celebrating) return;
    onRecorded(celebrating.event);
  }

  // AccessibilityAudit.md Phase 8 — this dialog is hand-rolled (framer-motion,
  // not Radix), so it doesn't get Escape-to-close, a focus trap, or focus
  // return for free the way the shell's Radix overlays do. This hook adds
  // exactly that, matching the behavior already certified elsewhere in the app.
  const dialogRef = useDialogA11y(celebrating ? finishCelebration : onClose);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-background/70 backdrop-blur grid place-items-center p-4"
      onClick={celebrating ? undefined : onClose}
    >
      <motion.div
        ref={dialogRef}
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 20, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="life-event-dialog-heading"
        tabIndex={-1}
        className="w-full max-w-2xl surface-card p-6 max-h-[90vh] overflow-y-auto outline-none"
      >
        {celebrating ? (
          <div className="text-center py-6">
            <div className="mx-auto h-14 w-14 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center shadow-glow mb-5">
              <Sparkles className="h-6 w-6 text-primary-foreground" />
            </div>
            <h2 id="life-event-dialog-heading" className="font-display text-2xl tracking-tight">
              {celebrating.celebration.title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
              {celebrating.celebration.body}
            </p>
            <button
              type="button"
              onClick={finishCelebration}
              className="mt-8 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-6 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
            >
              Done
            </button>
          </div>
        ) : !selectedType ? (
          <>
            <h2 id="life-event-dialog-heading" className="font-display text-xl tracking-tight">
              Record a life event
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Pick what happened — we'll update your financial plan accordingly.
            </p>
            <div className="mt-5 space-y-5">
              {categories.map(({ category, types }) => (
                <div key={category}>
                  <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">
                    {category}
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {types.map((type) => (
                      <button
                        key={type.value}
                        type="button"
                        onClick={() => selectType(type)}
                        className="text-left rounded-lg border border-border bg-surface p-3 hover:border-border-strong hover:bg-accent/50 transition-colors"
                      >
                        <p className="text-sm font-medium">{type.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                          {type.description}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end pt-5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent"
              >
                Cancel
              </button>
            </div>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => setSelectedType(null)}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-3"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Choose a different event
            </button>
            <h2 id="life-event-dialog-heading" className="font-display text-xl tracking-tight">
              {selectedType.label}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">{selectedType.description}</p>

            {selectedType.supportiveNote && (
              <div className="mt-4 rounded-lg border border-border bg-surface/60 px-4 py-3 text-sm flex gap-2.5">
                <HeartHandshake className="h-4 w-4 text-cyan shrink-0 mt-0.5" aria-hidden="true" />
                <p className="text-muted-foreground">{selectedType.supportiveNote}</p>
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <form className="mt-5 space-y-5" onSubmit={handleSubmit}>
              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-1.5">
                  <span className="text-xs text-muted-foreground">Date it happened</span>
                  <input
                    type="date"
                    value={occurredOn}
                    onChange={(e) => setOccurredOn(e.target.value)}
                    required
                    className="field-input"
                  />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs text-muted-foreground">Notes (optional)</span>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any context worth remembering"
                    className="field-input"
                  />
                </label>
              </div>

              {selectedType.requiredFields.length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  {selectedType.requiredFields.map((field) => (
                    <LifeEventFieldInput
                      key={field.name}
                      field={field}
                      value={values[field.name]}
                      onChange={(v) => updateField(field.name, v)}
                      entityOptions={entityOptions}
                    />
                  ))}
                </div>
              )}

              {selectedType.optionalGroups.map((group) => (
                <fieldset
                  key={group.title}
                  className="rounded-lg border border-border p-4 space-y-3"
                >
                  <legend className="px-1 text-xs font-medium text-muted-foreground">
                    {group.title} <span className="text-muted-foreground/60">(optional)</span>
                  </legend>
                  {group.description && (
                    <p className="text-[11px] text-muted-foreground/70 -mt-1">
                      {group.description}
                    </p>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    {group.fields.map((field) => (
                      <div
                        key={field.name}
                        className={
                          field.kind === "multi-entity" || field.kind === "goal-contributions"
                            ? "col-span-2"
                            : ""
                        }
                      >
                        <LifeEventFieldInput
                          field={field}
                          value={values[field.name]}
                          onChange={(v) => updateField(field.name, v)}
                          entityOptions={entityOptions}
                        />
                      </div>
                    ))}
                  </div>
                </fieldset>
              ))}

              {preview.status === "loaded" && (
                <div className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
                  {preview.validationErrors.length > 0 ? (
                    <p className="text-red-400">{preview.validationErrors.join(" ")}</p>
                  ) : preview.effectCount === 0 ? (
                    <p>Nothing to update yet — fill in the fields above to see what will change.</p>
                  ) : (
                    <p>This will update {summarizeAffectedAreas(preview.affectedEntities)}.</p>
                  )}
                </div>
              )}
              {preview.status === "error" && (
                <p className="text-sm text-red-400">{preview.message}</p>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={preview.status === "loading"}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm hover:bg-accent disabled:opacity-50"
                >
                  {preview.status === "loading" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                  Preview effects
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-cyan text-sm font-medium text-primary-foreground shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Recording…
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" /> Record event
                    </>
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}
