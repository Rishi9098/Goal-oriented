/**
 * Life Event Engine — frontend field configuration.
 *
 * A single, config-driven description of every registered event type's
 * `inputs` shape (backend/app/services/*_handler.py — one config entry per
 * handler, field names matching each handler's own `inputs["..."]`/
 * `inputs.get("...")` calls exactly). This is data only, not UI: the form
 * renderer (`components/life-events/`) walks this structure generically so
 * adding an 18th... 19th event type never requires new form-building code,
 * only a new config entry here.
 *
 * Every optional field is submitted only when the user actually filled it
 * in (see `buildInputsPayload` in the record dialog) — this mirrors each
 * handler's own "explicit opt-in, never assumed" rule (e.g. Salary Raise's
 * `goal_id` + `new_monthly_contribution`, taken only if both are present),
 * so the frontend never needs to hard-validate optional field pairs itself:
 * submitting only one half of a pair is a documented, harmless no-op on the
 * backend, not a frontend validation concern.
 */

import {
  INCOME_TYPES,
  LIQUID_ASSET_TYPES,
  INVESTMENT_TYPES,
  LIABILITY_TYPES,
} from "@/lib/financial-labels";

// Datalist suggestions (AutomationAudit.md Phase 5) for the free-text
// fields below — the same canonical values Financials/onboarding already
// use, reused rather than duplicated. Assets can be either liquid or
// investment type, so both lists are offered together for any asset_type
// field, regardless of which sub-list onboarding itself splits them into.
const INCOME_TYPE_SUGGESTIONS = INCOME_TYPES.map((t) => t.label);
const ASSET_TYPE_SUGGESTIONS = [...LIQUID_ASSET_TYPES, ...INVESTMENT_TYPES].map((t) => t.label);
const LIABILITY_TYPE_SUGGESTIONS = LIABILITY_TYPES.map((t) => t.label);

export type EntityKind = "income" | "expense" | "asset" | "liability" | "goal" | "member";

export type LifeEventField =
  | {
      kind: "text";
      name: string;
      label: string;
      required?: boolean;
      placeholder?: string;
      helpText?: string;
      // Native <datalist> suggestions (AutomationAudit.md Phase 5) — offered,
      // never enforced: typing any other value is always still allowed and
      // submitted as-is.
      suggestions?: string[];
    }
  | {
      kind: "number";
      name: string;
      label: string;
      required?: boolean;
      placeholder?: string;
      min?: number;
      step?: number;
      helpText?: string;
    }
  | { kind: "date"; name: string; label: string; required?: boolean; helpText?: string }
  | { kind: "boolean"; name: string; label: string; defaultValue?: boolean; helpText?: string }
  | {
      kind: "select";
      name: string;
      label: string;
      required?: boolean;
      options: { value: string; label: string }[];
      helpText?: string;
    }
  | {
      kind: "entity";
      name: string;
      label: string;
      required?: boolean;
      entity: EntityKind;
      helpText?: string;
    }
  | { kind: "multi-entity"; name: string; label: string; entity: EntityKind; helpText?: string }
  // Retirement's only field with no equivalent elsewhere in the catalog: a
  // repeatable {goal_id, new_monthly_contribution} list
  // (`retirement_handler.py`'s `goal_contributions`). Modeled as its own
  // field kind rather than a generic "array of fields" system — YAGNI, this
  // shape appears exactly once across all 18 events.
  | { kind: "goal-contributions"; name: "goal_contributions"; label: string; helpText?: string };

export type LifeEventFieldGroup = {
  title: string;
  description?: string;
  fields: LifeEventField[];
};

export type LifeEventTypeConfig = {
  value: string;
  label: string;
  categoryLabel: string;
  description: string;
  requiredFields: LifeEventField[];
  optionalGroups: LifeEventFieldGroup[];
  // BehavioralDesignAudit.md Phase 7 — shown as a distinct confirmation
  // view after a successful record, only for unambiguously joyful
  // milestones (never guessed at for an event whose emotional weight
  // could go either way for a given person).
  celebration?: { title: string; body: string };
  // A short, honest, non-alarmist acknowledgment shown at the top of the
  // form for the catalog's hardest moments — never advice, never a forced
  // next step, just acknowledgment and a factual boundary on what
  // recording this actually does.
  supportiveNote?: string;
};

const ASSET_TYPE_FIELD = (name: string, label: string, defaultHelp: string): LifeEventField => ({
  kind: "text",
  name,
  label,
  placeholder: "e.g. Savings, Checking, Real estate, Stocks",
  helpText: defaultHelp,
  suggestions: ASSET_TYPE_SUGGESTIONS,
});

// A distinct helper from ASSET_TYPE_FIELD (MicrocopyAudit.md Phase 4) — an
// income-type field showing asset examples ("Savings, Checking...") was a
// real, live mismatch on Job Change's "New income type" and Inheritance's
// "Income type" fields.
const INCOME_TYPE_FIELD = (name: string, label: string, defaultHelp: string): LifeEventField => ({
  kind: "text",
  name,
  label,
  placeholder: "e.g. Salary, Freelance, Rental, Dividends",
  helpText: defaultHelp,
  suggestions: INCOME_TYPE_SUGGESTIONS,
});

const GENDER_FIELD: LifeEventField = {
  kind: "select",
  name: "gender",
  label: "Gender",
  options: [
    { value: "", label: "Prefer not to say" },
    { value: "male", label: "Male" },
    { value: "female", label: "Female" },
    { value: "other", label: "Other" },
  ],
};

const RISK_PROFILE_FIELD: LifeEventField = {
  kind: "select",
  name: "risk_profile",
  label: "Risk profile",
  options: [
    { value: "conservative", label: "Conservative" },
    { value: "balanced", label: "Balanced" },
    { value: "aggressive", label: "Aggressive" },
  ],
};

const EMPLOYMENT_STATUS_OPTIONS = [
  { value: "employed", label: "Employed" },
  { value: "self_employed", label: "Self-employed" },
  { value: "unemployed", label: "Unemployed" },
  { value: "retired", label: "Retired" },
];

export const LIFE_EVENT_TYPES: LifeEventTypeConfig[] = [
  // ── Income & Career ──────────────────────────────────────────────────
  {
    value: "salary_raise",
    label: "Salary Raise",
    categoryLabel: "Income & Career",
    description: "Update an existing income source's annual amount.",
    requiredFields: [
      {
        kind: "entity",
        name: "income_source_id",
        label: "Income source",
        required: true,
        entity: "income",
      },
      {
        kind: "number",
        name: "new_annual_amount",
        label: "New annual amount ($)",
        required: true,
        min: 0,
      },
    ],
    optionalGroups: [
      {
        title: "Also increase a goal's contribution",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          { kind: "entity", name: "goal_id", label: "Goal", entity: "goal" },
          {
            kind: "number",
            name: "new_monthly_contribution",
            label: "New monthly contribution ($)",
            min: 0,
          },
        ],
      },
    ],
  },
  {
    value: "job_change",
    label: "Job Change",
    categoryLabel: "Income & Career",
    description: "Retires the old income source and creates a new one under the new employer.",
    requiredFields: [
      {
        kind: "entity",
        name: "old_income_source_id",
        label: "Current income source",
        required: true,
        entity: "income",
      },
      { kind: "text", name: "new_employer", label: "New employer", required: true },
      { kind: "text", name: "new_occupation", label: "New occupation", required: true },
      {
        kind: "number",
        name: "new_annual_amount",
        label: "New annual amount ($)",
        required: true,
        min: 0,
      },
    ],
    optionalGroups: [
      {
        title: "New income source details",
        fields: [
          INCOME_TYPE_FIELD(
            "new_source_type",
            "Income type",
            'Defaults to "salary" if left blank.',
          ),
          { kind: "text", name: "description", label: "Description" },
        ],
      },
    ],
  },
  {
    value: "bonus",
    label: "Bonus",
    categoryLabel: "Income & Career",
    description: "A one-time cash windfall, added as a liquid asset.",
    requiredFields: [
      { kind: "number", name: "amount", label: "Bonus amount ($)", required: true, min: 0 },
    ],
    optionalGroups: [
      {
        title: "Where it's held",
        fields: [
          ASSET_TYPE_FIELD("asset_type", "Asset type", 'Defaults to "savings" if left blank.'),
          { kind: "text", name: "institution", label: "Institution" },
          { kind: "text", name: "description", label: "Description" },
        ],
      },
    ],
  },
  {
    value: "retirement",
    label: "Retirement",
    categoryLabel: "Income & Career",
    description: "Sets employment status to retired and winds down salary income.",
    celebration: {
      title: "🎉 Congratulations on your retirement!",
      body: "Your plan now reflects this new chapter.",
    },
    requiredFields: [],
    optionalGroups: [
      {
        title: "Salary income sources to deactivate",
        description: "Select every salary income source this retirement replaces.",
        fields: [
          {
            kind: "multi-entity",
            name: "income_source_ids",
            label: "Income sources",
            entity: "income",
          },
        ],
      },
      {
        title: "Pension income",
        fields: [
          { kind: "number", name: "pension_amount", label: "Annual pension amount ($)", min: 0 },
          { kind: "text", name: "pension_description", label: "Description" },
        ],
      },
      {
        title: "Retirement planning assumptions",
        fields: [
          { kind: "number", name: "retirement_age", label: "Retirement age", min: 0 },
          {
            kind: "number",
            name: "social_security_monthly",
            label: "Social security ($/mo)",
            min: 0,
          },
        ],
      },
      {
        title: "Update goal contributions",
        description: "Add a row per retirement goal whose monthly contribution should change.",
        fields: [
          { kind: "goal-contributions", name: "goal_contributions", label: "Goal contributions" },
        ],
      },
    ],
  },
  // ── Housing ───────────────────────────────────────────────────────────
  {
    value: "house_purchase",
    label: "House Purchase",
    categoryLabel: "Housing",
    description: "Creates the home asset and its mortgage liability.",
    celebration: {
      title: "🎉 Congratulations on your new home!",
      body: "Your home and mortgage are now part of your plan.",
    },
    requiredFields: [
      {
        kind: "number",
        name: "property_value",
        label: "Property value ($)",
        required: true,
        min: 0,
      },
      {
        kind: "number",
        name: "mortgage_balance",
        label: "Mortgage balance ($)",
        required: true,
        min: 0,
      },
    ],
    optionalGroups: [
      {
        title: "Home details",
        fields: [
          { kind: "text", name: "institution", label: "Institution" },
          { kind: "text", name: "description", label: "Description" },
        ],
      },
      {
        title: "Mortgage terms",
        fields: [
          {
            kind: "number",
            name: "mortgage_interest_rate",
            label: "Interest rate (%)",
            min: 0,
            step: 0.01,
          },
          {
            kind: "number",
            name: "mortgage_monthly_payment",
            label: "Monthly payment ($)",
            min: 0,
          },
          { kind: "text", name: "mortgage_institution", label: "Lender" },
          { kind: "text", name: "mortgage_description", label: "Description" },
        ],
      },
      {
        title: "Down payment from an existing asset",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          {
            kind: "entity",
            name: "down_payment_asset_id",
            label: "Funding asset",
            entity: "asset",
          },
          { kind: "number", name: "down_payment_amount", label: "Down payment amount ($)", min: 0 },
        ],
      },
      {
        title: "Bump a linked goal's progress",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          { kind: "entity", name: "goal_id", label: "Goal", entity: "goal" },
          {
            kind: "number",
            name: "new_goal_current_amount",
            label: "New goal progress ($)",
            min: 0,
          },
        ],
      },
    ],
  },
  {
    value: "home_sale",
    label: "Home Sale",
    categoryLabel: "Housing",
    description: "Retires the home asset and directs net proceeds to a liquid asset.",
    requiredFields: [
      {
        kind: "entity",
        name: "home_asset_id",
        label: "Home asset",
        required: true,
        entity: "asset",
      },
      { kind: "number", name: "net_proceeds", label: "Net proceeds ($)", required: true, min: 0 },
    ],
    optionalGroups: [
      {
        title: "Pay off the mortgage",
        fields: [
          {
            kind: "entity",
            name: "mortgage_liability_id",
            label: "Mortgage liability",
            entity: "liability",
          },
          {
            kind: "boolean",
            name: "payoff_mortgage",
            label: "Pay off this mortgage with the sale",
            defaultValue: true,
            helpText: "Defaults to yes whenever a mortgage liability is selected.",
          },
        ],
      },
      {
        title: "Proceeds destination",
        description:
          "Pick an existing asset to add the proceeds to, or leave blank to create a new one.",
        fields: [
          {
            kind: "entity",
            name: "proceeds_asset_id",
            label: "Add to existing asset",
            entity: "asset",
          },
          ASSET_TYPE_FIELD(
            "proceeds_asset_type",
            "New asset type (if not adding to an existing one)",
            'Defaults to "savings".',
          ),
          { kind: "text", name: "proceeds_description", label: "New asset description" },
        ],
      },
    ],
  },
  {
    value: "new_loan",
    label: "New Loan",
    categoryLabel: "Housing",
    description: "Creates a liability, optionally linked to a purchased asset.",
    requiredFields: [
      {
        kind: "text",
        name: "liability_type",
        label: "Loan type",
        required: true,
        placeholder: "e.g. Car loan, Personal loan, Mortgage",
        suggestions: LIABILITY_TYPE_SUGGESTIONS,
      },
      { kind: "number", name: "balance", label: "Balance ($)", required: true, min: 0 },
      {
        kind: "number",
        name: "monthly_payment",
        label: "Monthly payment ($)",
        required: true,
        min: 0,
      },
    ],
    optionalGroups: [
      {
        title: "Loan terms",
        fields: [
          { kind: "number", name: "interest_rate", label: "Interest rate (%)", min: 0, step: 0.01 },
          { kind: "text", name: "institution", label: "Lender" },
          { kind: "text", name: "description", label: "Description" },
        ],
      },
      {
        title: "What this loan funded",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          ASSET_TYPE_FIELD("asset_type", "Asset type", "e.g. vehicle"),
          { kind: "number", name: "asset_value", label: "Asset value ($)", min: 0 },
          { kind: "text", name: "asset_institution", label: "Institution" },
          { kind: "text", name: "asset_description", label: "Description" },
        ],
      },
    ],
  },
  // ── Family ────────────────────────────────────────────────────────────
  {
    value: "marriage",
    label: "Marriage",
    categoryLabel: "Family",
    description: "Adds a spouse to your household.",
    celebration: {
      title: "🎉 Congratulations!",
      body: "Your household now reflects your marriage.",
    },
    requiredFields: [
      { kind: "text", name: "name", label: "Spouse's name", required: true },
      { kind: "date", name: "date_of_birth", label: "Date of birth", required: true },
    ],
    optionalGroups: [
      {
        title: "More details",
        fields: [GENDER_FIELD, { kind: "text", name: "relationship_detail", label: "Notes" }],
      },
    ],
  },
  {
    value: "birth_of_child",
    label: "Birth of Child",
    categoryLabel: "Family",
    description: "Adds a child to your household, with an optional college fund goal.",
    celebration: {
      title: "🎉 Congratulations on your new addition!",
      body: "Welcome to the family — your household has been updated.",
    },
    requiredFields: [
      { kind: "text", name: "name", label: "Child's name", required: true },
      { kind: "date", name: "date_of_birth", label: "Date of birth", required: true },
    ],
    optionalGroups: [
      { title: "More details", fields: [GENDER_FIELD] },
      {
        title: "Start a college fund",
        description:
          "Both amount and target date are needed together — filling only one is a no-op.",
        fields: [
          { kind: "number", name: "goal_target_amount", label: "Target amount ($)", min: 0 },
          { kind: "date", name: "goal_target_date", label: "Target date" },
          { kind: "text", name: "goal_name", label: "Goal name" },
          { kind: "number", name: "goal_current_amount", label: "Starting amount ($)", min: 0 },
          {
            kind: "number",
            name: "goal_monthly_contribution",
            label: "Monthly contribution ($)",
            min: 0,
          },
          RISK_PROFILE_FIELD,
        ],
      },
    ],
  },
  {
    value: "adoption",
    label: "Adoption",
    categoryLabel: "Family",
    description: "Identical to Birth of Child in every respect — only the history label differs.",
    celebration: {
      title: "🎉 Congratulations on your new addition!",
      body: "Welcome to the family — your household has been updated.",
    },
    requiredFields: [
      { kind: "text", name: "name", label: "Child's name", required: true },
      { kind: "date", name: "date_of_birth", label: "Date of birth", required: true },
    ],
    optionalGroups: [
      { title: "More details", fields: [GENDER_FIELD] },
      {
        title: "Start a college fund",
        description:
          "Both amount and target date are needed together — filling only one is a no-op.",
        fields: [
          { kind: "number", name: "goal_target_amount", label: "Target amount ($)", min: 0 },
          { kind: "date", name: "goal_target_date", label: "Target date" },
          { kind: "text", name: "goal_name", label: "Goal name" },
          { kind: "number", name: "goal_current_amount", label: "Starting amount ($)", min: 0 },
          {
            kind: "number",
            name: "goal_monthly_contribution",
            label: "Monthly contribution ($)",
            min: 0,
          },
          RISK_PROFILE_FIELD,
        ],
      },
    ],
  },
  {
    value: "dependent_parent",
    label: "Caring for a Parent",
    categoryLabel: "Family",
    description: "Adds a parent who depends on you to your household.",
    requiredFields: [
      { kind: "text", name: "name", label: "Parent's name", required: true },
      {
        kind: "select",
        name: "relationship_detail",
        label: "Relationship",
        required: true,
        options: [
          { value: "mother", label: "Mother" },
          { value: "father", label: "Father" },
        ],
      },
      {
        kind: "select",
        name: "has_own_insurance",
        label: "Has their own health insurance?",
        required: true,
        options: [
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
          { value: "not_sure", label: "Not sure" },
        ],
      },
    ],
    optionalGroups: [
      {
        title: "More details",
        fields: [{ kind: "date", name: "date_of_birth", label: "Date of birth" }, GENDER_FIELD],
      },
    ],
  },
  {
    value: "divorce",
    label: "Divorce",
    categoryLabel: "Family",
    description: "Removes a spouse from your household.",
    supportiveNote:
      "We know this is a difficult time. This only updates your financial records — nothing else — and you can take as long as you need.",
    requiredFields: [
      { kind: "entity", name: "member_id", label: "Spouse", required: true, entity: "member" },
    ],
    optionalGroups: [],
  },
  // ── Major Purchases & Windfalls ──────────────────────────────────────
  {
    value: "inheritance",
    label: "Inheritance",
    categoryLabel: "Major Purchases & Windfalls",
    description: "Creates an asset for the inherited amount.",
    requiredFields: [
      { kind: "number", name: "amount", label: "Amount ($)", required: true, min: 0 },
    ],
    optionalGroups: [
      {
        title: "Asset details",
        fields: [
          ASSET_TYPE_FIELD("asset_type", "Asset type", 'Defaults to "savings".'),
          { kind: "text", name: "institution", label: "Institution" },
          { kind: "text", name: "description", label: "Description" },
        ],
      },
      {
        title: "Ongoing income (e.g. an inherited rental property)",
        fields: [
          { kind: "number", name: "income_amount", label: "Annual income amount ($)", min: 0 },
          INCOME_TYPE_FIELD("income_source_type", "Income type", 'Defaults to "rental".'),
          { kind: "text", name: "income_description", label: "Description" },
        ],
      },
    ],
  },
  {
    value: "major_medical_event",
    label: "Medical Emergency",
    categoryLabel: "Major Purchases & Windfalls",
    description: "Records an ongoing healthcare expense, with optional funding.",
    supportiveNote:
      "Dealing with unexpected medical costs is stressful. This just helps your plan reflect what's happening — nothing more.",
    requiredFields: [
      {
        kind: "number",
        name: "monthly_amount",
        label: "Monthly healthcare expense ($)",
        required: true,
        min: 0,
      },
    ],
    optionalGroups: [
      {
        title: "Existing expense to increase",
        description: "Leave blank to create a new healthcare expense instead.",
        fields: [
          { kind: "entity", name: "expense_id", label: "Existing expense", entity: "expense" },
          { kind: "text", name: "description", label: "New expense description" },
        ],
      },
      {
        title: "Pay part of it from savings",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          { kind: "entity", name: "lump_sum_asset_id", label: "Funding asset", entity: "asset" },
          { kind: "number", name: "lump_sum_amount", label: "Lump sum amount ($)", min: 0 },
        ],
      },
      {
        title: "Finance the rest with a loan",
        fields: [
          { kind: "number", name: "loan_balance", label: "Loan balance ($)", min: 0 },
          {
            kind: "number",
            name: "loan_interest_rate",
            label: "Interest rate (%)",
            min: 0,
            step: 0.01,
          },
          { kind: "number", name: "loan_monthly_payment", label: "Monthly payment ($)", min: 0 },
          { kind: "text", name: "loan_description", label: "Description" },
        ],
      },
    ],
  },
  {
    value: "business_start",
    label: "Business Start",
    categoryLabel: "Major Purchases & Windfalls",
    description: "Sets employment status to self-employed, with optional funding.",
    requiredFields: [],
    optionalGroups: [
      {
        title: "Startup cost from savings",
        description: "Both fields are needed together — filling only one is a no-op.",
        fields: [
          { kind: "entity", name: "funding_asset_id", label: "Funding asset", entity: "asset" },
          { kind: "number", name: "funding_amount", label: "Amount ($)", min: 0 },
        ],
      },
      {
        title: "Ongoing business expense",
        fields: [
          { kind: "number", name: "ongoing_expense_amount", label: "Monthly amount ($)", min: 0 },
          { kind: "text", name: "expense_description", label: "Description" },
        ],
      },
      {
        title: "Startup loan",
        fields: [
          { kind: "number", name: "loan_balance", label: "Loan balance ($)", min: 0 },
          {
            kind: "number",
            name: "loan_interest_rate",
            label: "Interest rate (%)",
            min: 0,
            step: 0.01,
          },
          { kind: "number", name: "loan_monthly_payment", label: "Monthly payment ($)", min: 0 },
          { kind: "text", name: "loan_description", label: "Description" },
        ],
      },
    ],
  },
  {
    value: "business_sale",
    label: "Business Sale",
    categoryLabel: "Major Purchases & Windfalls",
    description: "Directs sale proceeds to an asset, with optional debt payoff and payout income.",
    requiredFields: [
      { kind: "number", name: "net_proceeds", label: "Net proceeds ($)", required: true, min: 0 },
    ],
    optionalGroups: [
      {
        title: "Proceeds destination",
        description:
          "Pick an existing asset to add the proceeds to, or leave blank to create a new one.",
        fields: [
          {
            kind: "entity",
            name: "proceeds_asset_id",
            label: "Add to existing asset",
            entity: "asset",
          },
          ASSET_TYPE_FIELD(
            "proceeds_asset_type",
            "New asset type (if not adding to an existing one)",
            'Defaults to "savings".',
          ),
          { kind: "text", name: "proceeds_description", label: "New asset description" },
        ],
      },
      {
        title: "Pay off a business liability",
        fields: [
          {
            kind: "entity",
            name: "business_liability_id",
            label: "Liability",
            entity: "liability",
          },
        ],
      },
      {
        title: "Ongoing installment payout",
        fields: [
          { kind: "number", name: "income_amount", label: "Annual amount ($)", min: 0 },
          { kind: "text", name: "income_description", label: "Description" },
        ],
      },
      {
        title: "Update employment status",
        fields: [
          {
            kind: "select",
            name: "new_employment_status",
            label: "New status",
            options: EMPLOYMENT_STATUS_OPTIONS,
          },
        ],
      },
    ],
  },
  // ── Debt ──────────────────────────────────────────────────────────────
  {
    value: "loan_payoff",
    label: "Loan Payoff",
    categoryLabel: "Debt",
    description: "Closes out a liability in full.",
    celebration: {
      title: "🎉 Debt paid off!",
      body: "One less thing to worry about — nice work.",
    },
    requiredFields: [
      {
        kind: "entity",
        name: "liability_id",
        label: "Liability",
        required: true,
        entity: "liability",
      },
    ],
    optionalGroups: [],
  },
  // ── Planning ──────────────────────────────────────────────────────────
  {
    value: "education_planning",
    label: "Education Planning",
    categoryLabel: "Planning",
    description: "Creates a new education-category goal.",
    requiredFields: [
      { kind: "text", name: "name", label: "Goal name", required: true },
      { kind: "number", name: "target_amount", label: "Target amount ($)", required: true, min: 0 },
      { kind: "date", name: "target_date", label: "Target date", required: true },
    ],
    optionalGroups: [
      {
        title: "More details",
        fields: [
          { kind: "number", name: "current_amount", label: "Starting amount ($)", min: 0 },
          {
            kind: "number",
            name: "monthly_contribution",
            label: "Monthly contribution ($)",
            min: 0,
          },
          RISK_PROFILE_FIELD,
        ],
      },
    ],
  },
];

export function findLifeEventType(value: string): LifeEventTypeConfig | undefined {
  return LIFE_EVENT_TYPES.find((t) => t.value === value);
}

export function groupLifeEventTypesByCategory(): {
  category: string;
  types: LifeEventTypeConfig[];
}[] {
  const order: string[] = [];
  const byCategory = new Map<string, LifeEventTypeConfig[]>();
  for (const type of LIFE_EVENT_TYPES) {
    if (!byCategory.has(type.categoryLabel)) {
      byCategory.set(type.categoryLabel, []);
      order.push(type.categoryLabel);
    }
    byCategory.get(type.categoryLabel)!.push(type);
  }
  return order.map((category) => ({ category, types: byCategory.get(category)! }));
}

// ── Human labels for the generic undo engine's raw backend vocabulary ──────
// MicrocopyAudit.md Phase 4: `entity_table` (a literal Postgres table name —
// backend/app/services/life_event_service.py's `_ENTITY_MODELS` registry)
// and a handful of fixed conflict-reason sentences were being shown to
// users verbatim (e.g. "income_sources: Row has changed since this event
// was recorded"). Both are finite, known sets — mapped here, not guessed.

const ENTITY_TABLE_LABELS: Record<string, string> = {
  income_sources: "your income",
  expenses: "your expenses",
  assets: "your assets",
  liabilities: "your debts",
  goals: "your goals",
  household_members: "your family",
  dependents: "your family",
  user_profiles: "your profile",
  financial_assumptions: "your planning assumptions",
};

export function entityTableLabel(table: string): string {
  return ENTITY_TABLE_LABELS[table] ?? "your plan";
}

// "your income, your assets" -> "your income and your assets" -> "your
// income, your assets, and your goals" — never a raw, comma-joined list of
// table names.
export function summarizeAffectedAreas(tables: string[]): string {
  const unique = Array.from(new Set(tables.map(entityTableLabel)));
  if (unique.length === 0) return "your plan";
  if (unique.length === 1) return unique[0];
  if (unique.length === 2) return `${unique[0]} and ${unique[1]}`;
  return `${unique.slice(0, -1).join(", ")}, and ${unique[unique.length - 1]}`;
}

// Exactly the three reasons life_event_service.py's undo_life_event ever
// returns (verified directly against the backend source, not guessed) —
// mapped to a predicate that reads naturally after entityTableLabel() as
// the subject ("your income has changed since you recorded this").
const UNDO_CONFLICT_REASON_PREDICATES: Record<string, string> = {
  "Row has changed since this event was recorded": "has changed since you recorded this",
  "Row no longer exists": "no longer exists — it may have been removed since",
  "Unrecognized entity table — cannot verify it is safe to undo":
    "can't be safely checked, so we won't undo it automatically",
};

export function undoConflictSentence(entityTable: string, reason: string): string {
  const subject = entityTableLabel(entityTable);
  const predicate = UNDO_CONFLICT_REASON_PREDICATES[reason];
  // Graceful fallback for a future reason this list doesn't know about yet
  // — still readable, never a raw, untranslated backend string alone.
  if (!predicate) return `${subject}: ${reason}`;
  return `${subject.charAt(0).toUpperCase() + subject.slice(1)} ${predicate}`;
}
