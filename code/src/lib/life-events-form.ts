import type { Asset, Expense, FamilyMemberSummary, IncomeSource, Liability } from "@/lib/api";
import type { Goal } from "@/lib/mock-data";
import type { LifeEventField, LifeEventTypeConfig } from "@/lib/life-events";
import type {
  EntityOptionsMap,
  GoalContributionRow,
  LifeEventFormValues,
} from "@/components/life-events/life-event-field-inputs";

export function buildEntityOptions(data: {
  income: IncomeSource[];
  expenses: Expense[];
  assets: Asset[];
  liabilities: Liability[];
  goals: Goal[];
  members: FamilyMemberSummary[];
}): EntityOptionsMap {
  return {
    income: data.income
      .filter((i) => i.is_active)
      .map((i) => ({
        value: i.id,
        label: `${i.source_type}${i.description ? ` — ${i.description}` : ""} ($${i.annual_amount.toLocaleString()}/yr)`,
      })),
    expense: data.expenses
      .filter((e) => e.is_active)
      .map((e) => ({
        value: e.id,
        label: `${e.category}${e.description ? ` — ${e.description}` : ""} ($${e.monthly_amount.toLocaleString()}/mo)`,
      })),
    asset: data.assets
      .filter((a) => a.is_active)
      .map((a) => ({
        value: a.id,
        label: `${a.asset_type}${a.description ? ` — ${a.description}` : ""} ($${a.current_value.toLocaleString()})`,
      })),
    liability: data.liabilities
      .filter((l) => l.is_active)
      .map((l) => ({
        value: l.id,
        label: `${l.liability_type}${l.description ? ` — ${l.description}` : ""} ($${l.balance.toLocaleString()})`,
      })),
    goal: data.goals.map((g) => ({ value: g.id, label: `${g.name} (${g.category})` })),
    member: data.members.map((m) => ({
      value: m.id,
      label: `${m.name ?? "Unnamed"} (${m.relationship_type})`,
    })),
  };
}

// Exported for reuse by RecordLifeEventDialog's auto-select-single-option
// automation (AutomationAudit.md Phase 5) — one field-flattening
// implementation, not a second copy.
export function allFields(config: LifeEventTypeConfig): LifeEventField[] {
  return [config.requiredFields, ...config.optionalGroups.map((g) => g.fields)].flat();
}

// Every optional field is included only when the user actually filled it in
// — see life-events.ts's own module docstring for why this is sufficient
// to satisfy every handler's "explicit opt-in, both-or-neither" pairs
// without the frontend needing to separately validate each pair.
export function buildInputsPayload(
  config: LifeEventTypeConfig,
  values: LifeEventFormValues,
): Record<string, unknown> {
  const inputs: Record<string, unknown> = {};
  for (const field of allFields(config)) {
    const raw = values[field.name];
    switch (field.kind) {
      case "text":
      case "date":
      case "select": {
        if (typeof raw === "string" && raw.trim() !== "") inputs[field.name] = raw;
        break;
      }
      case "number": {
        if (typeof raw === "string" && raw.trim() !== "") inputs[field.name] = Number(raw);
        break;
      }
      case "boolean": {
        if (typeof raw === "boolean") inputs[field.name] = raw;
        break;
      }
      case "entity": {
        if (typeof raw === "string" && raw !== "") inputs[field.name] = raw;
        break;
      }
      case "multi-entity": {
        if (Array.isArray(raw) && raw.length > 0) inputs[field.name] = raw;
        break;
      }
      case "goal-contributions": {
        const rows = (raw as GoalContributionRow[] | undefined) ?? [];
        const complete = rows.filter((r) => r.goal_id && r.new_monthly_contribution.trim() !== "");
        if (complete.length > 0) {
          inputs[field.name] = complete.map((r) => ({
            goal_id: r.goal_id,
            new_monthly_contribution: Number(r.new_monthly_contribution),
          }));
        }
        break;
      }
    }
  }
  return inputs;
}

export function missingRequiredFields(
  config: LifeEventTypeConfig,
  values: LifeEventFormValues,
): string[] {
  return config.requiredFields
    .filter((field) => {
      const raw = values[field.name];
      if (field.kind === "boolean") return false;
      if (Array.isArray(raw)) return raw.length === 0;
      return typeof raw !== "string" || raw.trim() === "";
    })
    .map((field) => field.label);
}
