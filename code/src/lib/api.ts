/**
 * API service layer.
 *
 * When VITE_API_BASE_URL is set the client talks to the real FastAPI backend.
 * Without it every call falls back to mock fixtures so the UI remains
 * fully functional during local frontend-only development.
 */

import type { Goal } from "./mock-data";
import { goals as goalsFixture } from "./mock-data";

const ENV_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (import.meta.env.PROD && !ENV_URL) {
  console.error("CRITICAL: VITE_API_BASE_URL is missing in production!");
}

const SHOULD_USE_MOCK = !ENV_URL && import.meta.env.DEV;
const BASE_URL = SHOULD_USE_MOCK 
  ? undefined 
  : (ENV_URL ? (ENV_URL.endsWith('/api/v1') ? ENV_URL : `${ENV_URL}/api/v1`) : '/api/v1');

// ── Backend ↔ frontend shape mapping ─────────────────────────────────────────
// The backend returns snake_case; the frontend Goal type uses camelCase.

type RawGoal = {
  id: string;
  name: string;
  category: Goal["category"];
  target_amount: number;
  current_amount: number;
  target_date: string;
  monthly_contribution: number;
  on_track: boolean;
  probability: number;
  risk_profile: Goal["riskProfile"];
  custom_inflation_rate: number | null;
};

function toGoal(r: RawGoal): Goal {
  return {
    id: r.id,
    name: r.name,
    category: r.category,
    targetAmount: r.target_amount,
    currentAmount: r.current_amount,
    targetDate: r.target_date,
    monthlyContribution: r.monthly_contribution,
    onTrack: r.on_track,
    probability: r.probability,
    riskProfile: r.risk_profile,
    customInflationRate: r.custom_inflation_rate,
  };
}

function toGoalPatch(patch: Partial<Goal>): Partial<RawGoal> {
  const out: Partial<RawGoal> = {};
  if (patch.name !== undefined) out.name = patch.name;
  if (patch.category !== undefined) out.category = patch.category;
  if (patch.targetAmount !== undefined) out.target_amount = patch.targetAmount;
  if (patch.currentAmount !== undefined) out.current_amount = patch.currentAmount;
  if (patch.targetDate !== undefined) out.target_date = patch.targetDate;
  if (patch.monthlyContribution !== undefined) out.monthly_contribution = patch.monthlyContribution;
  if (patch.riskProfile !== undefined) out.risk_profile = patch.riskProfile;
  if (patch.customInflationRate !== undefined)
    out.custom_inflation_rate = patch.customInflationRate;
  return out;
}

// ── Token management ──────────────────────────────────────────────────────────
//
// The refresh token lives only in a backend-set httpOnly cookie (never
// readable by JS, so an XSS payload can't exfiltrate it) — see AUDIT.md #4.
// The access token is short-lived and low-value enough to keep in
// localStorage for the simple "is there a session" checks in route guards.

function getToken(): string | null {
  return localStorage.getItem("ns_access_token");
}

export function setAccessToken(access: string): void {
  localStorage.setItem("ns_access_token", access);
}

export function clearAccessToken(): void {
  localStorage.removeItem("ns_access_token");
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|; )ns_csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

let _refreshPromise: Promise<void> | null = null;

async function _doRefresh(): Promise<void> {
  const csrf = getCsrfToken();
  if (!csrf) throw new Error("No refresh session");
  const resp = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
  });
  if (!resp.ok) throw new Error("Refresh failed");
  const data = (await resp.json()) as { access_token: string };
  setAccessToken(data.access_token);
}

function parseError(body: unknown, httpStatus: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0)
    return (detail[0] as { msg?: string }).msg ?? `HTTP ${httpStatus}`;
  return `HTTP ${httpStatus}`;
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  _retry = false,
  extraOkStatuses: number[] = [],
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (resp.status === 401 && !_retry && BASE_URL) {
    if (!_refreshPromise) {
      _refreshPromise = _doRefresh().finally(() => {
        _refreshPromise = null;
      });
    }
    try {
      await _refreshPromise;
      return apiFetch<T>(path, options, true, extraOkStatuses);
    } catch {
      clearAccessToken();
      window.location.href = "/auth/sign-in";
      throw new Error("Session expired. Please sign in again.");
    }
  }

  // `undo_life_event`'s 409 is a normal, well-shaped response body (a
  // blocked-with-conflicts result — LifeEventEngineArchitecture.md §7),
  // not an error to surface as a thrown exception like every other
  // non-2xx status here. `extraOkStatuses` lets one call site (undoLifeEvent)
  // opt into treating it as a successful response without changing the
  // default throw-on-!ok behavior every other caller of apiFetch relies on.
  if (!resp.ok && !extraOkStatuses.includes(resp.status)) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(parseError(body, resp.status));
  }
  if (resp.status === 204) return undefined as unknown as T;
  return resp.json() as Promise<T>;
}

// ── Mock fallback helpers ─────────────────────────────────────────────────────

const delay = <T>(value: T, ms = 350): Promise<T> =>
  new Promise((r) => setTimeout(() => r(value), ms));

// ── Domain types ──────────────────────────────────────────────────────────────

export type DashboardSuggestion = {
  id: string;
  title: string;
  impact: string;
  severity: "warning" | "info" | "success";
};

export type UserProfile = {
  id: string;
  user_id: string;
  date_of_birth: string | null;
  gender: string | null;
  marital_status: string | null;
  dependents: number;
  country: string | null;
  state_province: string | null;
  employment_status: string | null;
  employer: string | null;
  occupation: string | null;
  onboarding_complete: boolean;
  current_step: number;
};

// ── Family (Milestone 2 Task 4) ──────────────────────────────────────────────

export type OnboardingSeedRequest = {
  has_spouse: boolean;
  has_children: boolean;
  children_count?: number;
  has_dependent_parents: boolean;
};

export type FamilyMemberSummary = {
  id: string;
  relationship_type: string;
  name: string | null;
  is_complete: boolean;
};

export type FamilyHome = {
  household: { id: string; name: string };
  members: FamilyMemberSummary[];
};

export type RelationshipType = "spouse" | "child" | "parent" | "other";
export type Gender = "female" | "male" | "other";
export type InsuranceStatus = "yes" | "no" | "not_sure";

// Request body shared by POST /family/members and PUT /family/members/{id}
// — mirrors backend/app/schemas/family.py's FamilyMemberFieldsBase exactly,
// not the illustrative JSON in Milestone2ImplementationContract.md (which
// omits is_tax_dependent and uses a dependent_type field that doesn't exist
// in the real schema).
export type FamilyMemberFields = {
  name: string;
  date_of_birth?: string | null;
  gender?: Gender | null;
  is_tax_dependent?: boolean;
  relationship_detail?: string | null;
  has_own_insurance?: InsuranceStatus | null;
};

export type EligibleScheme = { code: string; reason: string };

export type FamilyMemberDetail = FamilyMemberFields & {
  id: string;
  household_id: string;
  relationship_type: string;
  // Milestone 2 Task 7: reuses the backend's family_service.is_complete()
  // via the API response — never re-derived from raw fields on the
  // frontend, which would risk a second, drifting completeness definition.
  is_complete: boolean;
  eligible_schemes: EligibleScheme[];
};

export type FamilyMemberFullDetail = {
  member: FamilyMemberDetail;
  tagged_goals: { id: string; name: string }[];
  coverage: { health_policy_id: string; policy_type: string }[];
};

// Milestone 2 Task 8 — a household member a goal is tagged with. Distinct
// from FamilyMemberSummary: only the fields the tagging UI needs.
export type TaggedMember = {
  id: string;
  name: string | null;
  relationship_type: string;
};

export type FamilyGoalSummary = {
  id: string;
  name: string;
  category: string;
  target_amount: number;
  current_amount: number;
  target_date: string;
  probability: number;
  on_track: boolean;
  tagged_members: TaggedMember[];
};

// Milestone 2 Task 10 — Family Insurance
export type PolicyType = "family_floater" | "individual" | "senior_citizen_standalone";

export type HealthPolicy = {
  id: string;
  policy_type: PolicyType;
  sum_insured: number;
  annual_premium: number;
  insurer: string | null;
  is_active: boolean;
  covered_members: TaggedMember[];
};

// A calculation-lite fact application (RecommendationIntegrityReview_
// Task10.md) — never a Milestone 5 Recommendation Engine output, and
// always fully explained: why/why_now/what_used/what_missing are never
// empty when a recommendation exists at all.
export type InsuranceRecommendation = {
  recommendation_type: "standalone_parent_policy";
  subjects: string[];
  why: string;
  why_now: string;
  what_information_was_used: string[];
  what_information_is_missing: string[];
  floater_deduction_limit: number;
  parent_deduction_limit: number;
  confidence_score: number;
};

export type FamilyInsurance = {
  policies: HealthPolicy[];
  recommendation: InsuranceRecommendation | null;
};

// Milestone 2 Task 11 — aggregation over the insurance (Task 10) and
// scheme-eligibility (Task 3) engines. Every recommendation, regardless of
// source, always carries all five fields (RecommendationIntegrityReview_
// Task11.md) — never partially populated.
export type RecommendationSource = "insurance" | "schemes" | "financial_health";

export type FamilyRecommendation = {
  source: RecommendationSource;
  recommendation_type: string;
  subjects: string[];
  reference_code: string;
  why: string;
  why_now: string;
  what_information_was_used: string[];
  what_information_is_missing: string[];
  confidence_score: number;
};

export type RecommendationConflict = {
  subject: string;
  reference_code: string;
  sources: RecommendationSource[];
  note: string;
};

export type FamilyRecommendationsResult = {
  recommendations: FamilyRecommendation[];
  conflicts: RecommendationConflict[];
};

// Phase 3 (Notification Center). Title/body always come from the backend's
// live read of the existing recommendation/goal/audit-log data — never
// persisted content (ArchitectureReview_Phase3.md). This client never
// invents or recomputes any of it.
//
// Must mirror backend/app/schemas/notification.py's NotificationSource
// exactly — "life_event" and "divorce_review" existed there and were
// already being sent by notification_service.py's
// _collect_life_event_facts/_collect_divorce_review_facts, but were never
// added here (LifeEventIntegrationReview.md Phase 2 §2).
export type NotificationSource =
  | "insurance"
  | "schemes"
  | "family_member_added"
  | "goal_at_risk"
  | "goal_completed"
  | "life_event"
  | "divorce_review";

export type NotificationItem = {
  id: string;
  source: NotificationSource;
  title: string;
  body: string;
  action_path: string;
  state: "unread" | "read";
  created_at: string;
};

export type NotificationListResult = {
  items: NotificationItem[];
  unread_count: number;
};

// Milestone 2 Task 12 — read-only composition over existing services. Every
// card is nullable: a section that failed to compute server-side arrives as
// null and renders as "unavailable", never as a zero that could be mistaken
// for a real figure (IntegrationIntegrityReview_Task12.md).
export type FamilyDashboard = {
  dependents: {
    total_members: number;
    children: number;
    parents: number;
    spouse: number;
    others: number;
  } | null;
  education: {
    goal_id: string;
    goal_name: string;
    target_date: string;
    target_amount: number;
    tagged_member_names: string[];
  } | null;
  coverage: { covered_members: number; total_members: number } | null;
  parents: { uncovered_parent_names: string[] } | null;
  retirement: {
    goal_id: string;
    goal_name: string;
    probability: number;
    on_track: boolean;
  } | null;
  emergency: { liquid_assets: number; monthly_expenses: number } | null;
  recommendations: FamilyRecommendation[];
  conflicts: RecommendationConflict[];
  recommendations_unavailable: boolean;
};

// Milestone 2.1-P1 — a direct passthrough of scheme_eligibility_service's
// three buckets (Task 3, certified). No new eligibility logic on either
// side of this type.
export type SchemeEligibilityItem = {
  scheme_code: string;
  scheme_name: string;
  member_name: string | null;
  reason: string;
};

export type FamilySchemes = {
  eligible: SchemeEligibilityItem[];
  potentially_eligible: SchemeEligibilityItem[];
  not_eligible: SchemeEligibilityItem[];
};

export type IncomeSource = {
  id: string;
  source_type: string;
  description: string | null;
  annual_amount: number;
  is_active: boolean;
};

export type Expense = {
  id: string;
  category: string;
  description: string | null;
  monthly_amount: number;
  is_active: boolean;
};

export type Asset = {
  id: string;
  asset_type: string;
  institution: string | null;
  description: string | null;
  current_value: number;
  is_active: boolean;
};

export type Liability = {
  id: string;
  liability_type: string;
  institution: string | null;
  description: string | null;
  balance: number;
  interest_rate: number | null;
  monthly_payment: number | null;
  is_active: boolean;
};

export type FinancialAssumptions = {
  id: string;
  inflation_rate: number;
  expected_return_conservative: number;
  expected_return_balanced: number;
  expected_return_aggressive: number;
  tax_rate: number;
  retirement_age: number;
  social_security_monthly: number;
};

// ── Dashboard / simulation types ──────────────────────────────────────────────

export type DashboardData = {
  net_worth: number;
  net_worth_delta_pct: number;
  liquid_assets: number;
  invested: number;
  liabilities: number;
  monthly_income: number;
  monthly_expenses: number;
  monthly_savings_rate: number;
  projected_retirement: number;
  plan_health_score: number;
  alerts: number;
  goal_count: number;
  goals_on_track: number;
  suggestions: DashboardSuggestion[];
};

export type SimulationResult = {
  id: string;
  success_rate: number;
  percentiles: { p10: number; p25: number; p50: number; p75: number; p90: number };
  distribution: Record<string, number>;
};

export type OptimizationResult = {
  goal_id: string;
  current_probability: number;
  suggestions: Array<{
    description: string;
    monthly_contribution_delta: number;
    risk_profile_change: string | null;
    projected_probability: number;
    impact_summary: string;
  }>;
};

export type GoalReportItem = {
  id: string;
  name: string;
  category: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  probability: number;
  on_track: boolean;
  target_date: string;
};

export type ReportSummary = {
  generated_at: string;
  plan_health_score: number;
  net_worth: number;
  liquid_assets: number;
  invested: number;
  liabilities: number;
  monthly_income: number;
  monthly_expenses: number;
  monthly_savings_rate: number;
  goal_count: number;
  goals_on_track: number;
  goals: GoalReportItem[];
};

// ── Life Event Engine ──────────────────────────────────────────────────────
// Wraps the existing, already-tested `POST/GET /life-events*` endpoints
// (LifeEventAPI_ImplementationReport.md, LifeEventEngine_BackendHardeningReport.md)
// exactly as-is — no client-side reinterpretation of any handler's inputs.

export type LifeEventEffect = {
  entity_table: string;
  entity_id: string;
  change_type: "create" | "update" | "soft_delete" | "reactivate";
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
};

export type LifeEventRecord = {
  id: string;
  event_type: string;
  occurred_on: string;
  recorded_at: string;
  inputs: Record<string, unknown>;
  status: "applied" | "undone";
  undone_at: string | null;
  notes: string | null;
  effects: LifeEventEffect[];
  audit_action: string;
};

export type LifeEventListResult = {
  items: LifeEventRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type LifeEventCreateResult = {
  life_event: LifeEventRecord;
  audit_reference: string;
};

export type LifeEventPreviewResult = {
  event_type: string;
  effects: LifeEventEffect[];
  affected_entities: string[];
  validation_errors: string[];
};

export type UndoConflict = {
  effect_id: string;
  entity_table: string;
  entity_id: string;
  reason: string;
};

export type UndoResult = {
  success: boolean;
  blocked: boolean;
  conflicts: UndoConflict[];
};

// ── Mock fixtures ─────────────────────────────────────────────────────────────

const MOCK_SUGGESTIONS: DashboardSuggestion[] = [
  {
    id: "s1",
    title: "Increase education fund contribution by $180/mo",
    impact: "Raises education fund success rate from 54% to 71%.",
    severity: "warning",
  },
  {
    id: "s2",
    title: "Rebalance to 60/40 ahead of Q1",
    impact: "Reduces drawdown risk by ~6% on a 12-month horizon.",
    severity: "info",
  },
  {
    id: "s3",
    title: "Move $12k of idle cash to T-bills",
    impact: "Captures ~$520/yr at current yields with zero added risk.",
    severity: "success",
  },
];

const MOCK_PROFILE: UserProfile = {
  id: "mock-profile",
  user_id: "mock-user",
  date_of_birth: null,
  gender: null,
  marital_status: null,
  dependents: 0,
  country: null,
  state_province: null,
  employment_status: null,
  employer: null,
  occupation: null,
  onboarding_complete: false,
  current_step: 0,
};

// Infers a plausible relationship_type from the mock id prefix (matching
// mockFamilyHomeFrom's own "mock-spouse"/"mock-child-N" convention below) so
// the mock path exercises the same form-per-type branching production does.
function mockFamilyMemberFrom(id: string, data: FamilyMemberFields): FamilyMemberDetail {
  const relationship_type = id.includes("spouse")
    ? "spouse"
    : id.includes("child")
      ? "child"
      : id.includes("parent")
        ? "parent"
        : "other";
  const eligible_schemes: EligibleScheme[] =
    relationship_type === "child" && data.gender === "female"
      ? [{ code: "SSY", reason: "Daughter under 10 (mock)" }]
      : [];
  // Mirrors family_service.is_complete()'s exact rule set, for mock-mode
  // fixtures only — the real completeness authority remains the backend.
  const is_complete =
    !!data.name &&
    (relationship_type === "spouse" || relationship_type === "child"
      ? !!data.date_of_birth
      : relationship_type === "parent"
        ? !!data.relationship_detail && !!data.has_own_insurance
        : !!data.relationship_detail);
  return {
    id,
    household_id: "mock-household",
    relationship_type,
    name: data.name,
    date_of_birth: data.date_of_birth ?? null,
    gender: data.gender ?? null,
    is_tax_dependent: data.is_tax_dependent ?? false,
    relationship_detail: data.relationship_detail ?? null,
    has_own_insurance: data.has_own_insurance ?? null,
    is_complete,
    eligible_schemes,
  };
}

// Default mock for GET /family (no request body to derive from, unlike the
// onboarding-seed mock below) — mirrors the real backend's lazy-provision
// fallback: a self-only household is the correct default absent real data.
const MOCK_FAMILY_HOME: FamilyHome = {
  household: { id: "mock-household", name: "My Household" },
  members: [{ id: "mock-self", relationship_type: "self", name: "Demo User", is_complete: true }],
};

// Mirrors the real backend's onboarding-seed behavior (self + one row per
// "yes" answer) so the mock path exercises the same shape the frontend will
// see in production — never a hollow stand-in.
function mockFamilyHomeFrom(request: OnboardingSeedRequest): FamilyHome {
  const members: FamilyMemberSummary[] = [
    { id: "mock-self", relationship_type: "self", name: "You", is_complete: true },
  ];
  if (request.has_spouse) {
    members.push({
      id: "mock-spouse",
      relationship_type: "spouse",
      name: null,
      is_complete: false,
    });
  }
  if (request.has_children) {
    const count = request.children_count ?? 1;
    for (let i = 0; i < count; i++) {
      members.push({
        id: `mock-child-${i}`,
        relationship_type: "child",
        name: null,
        is_complete: false,
      });
    }
  }
  if (request.has_dependent_parents) {
    members.push({
      id: "mock-parent",
      relationship_type: "parent",
      name: null,
      is_complete: false,
    });
  }
  return { household: { id: "mock-household", name: "My Household" }, members };
}

const MOCK_ASSUMPTIONS: FinancialAssumptions = {
  id: "mock-assumptions",
  inflation_rate: 0.03,
  expected_return_conservative: 0.05,
  expected_return_balanced: 0.07,
  expected_return_aggressive: 0.09,
  tax_rate: 0.22,
  retirement_age: 65,
  social_security_monthly: 0,
};

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  login: (email: string, password: string) =>
    BASE_URL
      ? apiFetch<{ access_token: string }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        })
      : delay({ access_token: "mock-token" }),

  logout: () =>
    BASE_URL
      ? apiFetch<void>("/auth/logout", { method: "POST" }).catch(() => undefined)
      : delay(undefined),

  register: (email: string, password: string, fullName?: string) =>
    BASE_URL
      ? apiFetch<{ id: string; email: string }>("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, full_name: fullName }),
        })
      : delay({ id: "mock-id", email }),

  me: () =>
    BASE_URL
      ? apiFetch<{ id: string; email: string; full_name: string | null }>("/auth/me")
      : delay({ id: "mock-id", email: "demo@northstar.app", full_name: "Demo User" }),

  updateMe: (patch: { full_name?: string; password?: string }) =>
    BASE_URL
      ? apiFetch<{ id: string; email: string; full_name: string | null }>("/auth/me", {
          method: "PUT",
          body: JSON.stringify(patch),
        })
      : delay({
          id: "mock-id",
          email: "demo@northstar.app",
          full_name: patch.full_name ?? "Demo User",
        }),

  forgotPassword: (email: string) =>
    BASE_URL
      ? apiFetch<{ message: string; reset_token?: string }>("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        })
      : delay({
          message: "If that email exists, a reset link has been sent.",
          reset_token: "mock-reset-token",
        }),

  resetPassword: (token: string, newPassword: string) =>
    BASE_URL
      ? apiFetch<void>("/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({ token, new_password: newPassword }),
        })
      : delay(undefined),

  changePassword: (currentPassword: string, newPassword: string) =>
    BASE_URL
      ? apiFetch<void>("/auth/change-password", {
          method: "POST",
          body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
        })
      : delay(undefined),

  deleteAccount: () =>
    BASE_URL ? apiFetch<void>("/auth/me", { method: "DELETE" }) : delay(undefined),
};

// ── API surface ───────────────────────────────────────────────────────────────

export const api = {
  // ── Dashboard ─────────────────────────────────────────────────────────────
  getDashboard: (): Promise<DashboardData> =>
    BASE_URL
      ? apiFetch<DashboardData>("/dashboard")
      : delay<DashboardData>({
          net_worth: 902_300,
          net_worth_delta_pct: 4.8,
          liquid_assets: 184_500,
          invested: 657_800,
          liabilities: 124_000,
          monthly_income: 10_000,
          monthly_expenses: 6_900,
          monthly_savings_rate: 31,
          projected_retirement: 3_180_000,
          plan_health_score: 82,
          alerts: 2,
          goal_count: 5,
          goals_on_track: 4,
          suggestions: MOCK_SUGGESTIONS,
        }),

  // ── Profile ────────────────────────────────────────────────────────────────
  getProfile: (): Promise<UserProfile | null> =>
    BASE_URL
      ? apiFetch<UserProfile>("/profile").catch(() => null)
      : delay<UserProfile | null>(null),

  upsertProfile: (data: Partial<Omit<UserProfile, "id" | "user_id">>): Promise<UserProfile> =>
    BASE_URL
      ? apiFetch<UserProfile>("/profile", { method: "PUT", body: JSON.stringify(data) })
      : delay<UserProfile>({ ...MOCK_PROFILE, ...data }),

  // ── Family ───────────────────────────────────────────────────────────────
  // PCA-2 (Stabilization Sprint): the certified read source for household
  // data — replaces app.profile.tsx's prior use of the deprecated
  // user_profiles.marital_status/dependents fields. Wraps the existing,
  // already-tested GET /api/v1/family endpoint (Milestone 2 Task 2); no new
  // backend API was introduced for this fix.
  getFamilyHome: (): Promise<FamilyHome> =>
    BASE_URL ? apiFetch<FamilyHome>("/family") : delay<FamilyHome>(MOCK_FAMILY_HOME),

  seedFamilyOnboarding: (data: OnboardingSeedRequest): Promise<FamilyHome> =>
    BASE_URL
      ? apiFetch<FamilyHome>("/family/onboarding-seed", {
          method: "POST",
          body: JSON.stringify(data),
        })
      : delay<FamilyHome>(mockFamilyHomeFrom(data)),

  // Milestone 2 Task 6: wraps the existing, already-tested
  // POST/PUT/GET /api/v1/family/members[/{id}] endpoints (Task 2) — no new
  // backend API. Server-side validation, audit logging, and SSY-eligibility
  // evaluation (Task 3) already happen inline in these endpoints; this
  // client only calls them, never reimplements any of that.
  createFamilyMember: (
    data: { relationship_type: RelationshipType } & FamilyMemberFields,
  ): Promise<FamilyMemberDetail> =>
    BASE_URL
      ? apiFetch<FamilyMemberDetail>("/family/members", {
          method: "POST",
          body: JSON.stringify(data),
        })
      : delay<FamilyMemberDetail>(mockFamilyMemberFrom(`mock-${data.relationship_type}`, data)),

  updateFamilyMember: (memberId: string, data: FamilyMemberFields): Promise<FamilyMemberDetail> =>
    BASE_URL
      ? apiFetch<FamilyMemberDetail>(`/family/members/${memberId}`, {
          method: "PUT",
          body: JSON.stringify(data),
        })
      : delay<FamilyMemberDetail>(mockFamilyMemberFrom(memberId, data)),

  getFamilyMember: (memberId: string): Promise<FamilyMemberFullDetail> =>
    BASE_URL
      ? apiFetch<FamilyMemberFullDetail>(`/family/members/${memberId}`)
      : delay<FamilyMemberFullDetail>({
          member: mockFamilyMemberFrom(memberId, { name: "" }),
          tagged_goals: [],
          coverage: [],
        }),

  // Milestone 2 Task 7: soft-delete only (backend sets is_active=false and
  // writes a family_member_removed audit row) — wraps the existing,
  // certified DELETE /api/v1/family/members/{id} endpoint. No new backend
  // API.
  deleteFamilyMember: (memberId: string): Promise<void> =>
    BASE_URL
      ? apiFetch<void>(`/family/members/${memberId}`, { method: "DELETE" })
      : delay<void>(undefined),

  // Milestone 2 Task 8 — wraps the existing goals list (routers/goals.py's
  // own filter/ordering, reused server-side) plus the goal_household_members
  // tag join. No goal calculation is touched by this read.
  getFamilyGoals: (): Promise<FamilyGoalSummary[]> =>
    BASE_URL
      ? apiFetch<FamilyGoalSummary[]>("/family/goals")
      : delay<FamilyGoalSummary[]>(
          goalsFixture.map((g) => ({
            id: g.id,
            name: g.name,
            category: g.category,
            target_amount: g.targetAmount,
            current_amount: g.currentAmount,
            target_date: g.targetDate,
            probability: g.probability,
            on_track: g.onTrack,
            tagged_members: [],
          })),
        ),

  // Replaces a goal's full "who this affects" tag set in one call — wraps
  // the existing, certified PUT /api/v1/goals/{id}/family-tags endpoint.
  // Never touches goal ownership or its Monte Carlo probability.
  setGoalFamilyTags: (
    goalId: string,
    householdMemberIds: string[],
  ): Promise<{ goal_id: string; tagged_members: TaggedMember[] }> =>
    BASE_URL
      ? apiFetch<{ goal_id: string; tagged_members: TaggedMember[] }>(
          `/goals/${goalId}/family-tags`,
          {
            method: "PUT",
            body: JSON.stringify({ household_member_ids: householdMemberIds }),
          },
        )
      : delay({
          goal_id: goalId,
          tagged_members: householdMemberIds.map((id) => ({
            id,
            name: MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.name ?? "Family member",
            relationship_type:
              MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.relationship_type ?? "other",
          })),
        }),

  // Milestone 2 Task 10 — Family Insurance. Read-only; the recommendation
  // is computed fresh on every call, never persisted (see backend's
  // RecommendationIntegrityReview_Task10.md #4).
  getFamilyInsurance: (): Promise<FamilyInsurance> =>
    BASE_URL
      ? apiFetch<FamilyInsurance>("/family/insurance")
      : delay<FamilyInsurance>({ policies: [], recommendation: null }),

  createInsurancePolicy: (data: {
    policy_type: PolicyType;
    sum_insured: number;
    annual_premium: number;
    insurer?: string;
    household_member_ids: string[];
  }): Promise<HealthPolicy> =>
    BASE_URL
      ? apiFetch<HealthPolicy>("/family/insurance/policies", {
          method: "POST",
          body: JSON.stringify(data),
        })
      : delay<HealthPolicy>({
          id: `hp_${Date.now()}`,
          policy_type: data.policy_type,
          sum_insured: data.sum_insured,
          annual_premium: data.annual_premium,
          insurer: data.insurer ?? null,
          is_active: true,
          covered_members: data.household_member_ids.map((id) => ({
            id,
            name: MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.name ?? "Family member",
            relationship_type:
              MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.relationship_type ?? "other",
          })),
        }),

  updatePolicyCoverage: (policyId: string, householdMemberIds: string[]): Promise<HealthPolicy> =>
    BASE_URL
      ? apiFetch<HealthPolicy>(`/family/insurance/policies/${policyId}/coverage`, {
          method: "PUT",
          body: JSON.stringify({ household_member_ids: householdMemberIds }),
        })
      : delay<HealthPolicy>({
          id: policyId,
          policy_type: "family_floater",
          sum_insured: 500_000,
          annual_premium: 12_000,
          insurer: null,
          is_active: true,
          covered_members: householdMemberIds.map((id) => ({
            id,
            name: MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.name ?? "Family member",
            relationship_type:
              MOCK_FAMILY_HOME.members.find((m) => m.id === id)?.relationship_type ?? "other",
          })),
        }),

  // Milestone 2 Task 11 — Family Recommendations. Read-only aggregation
  // over the insurance and scheme-eligibility engines; nothing persisted.
  getFamilyRecommendations: (): Promise<FamilyRecommendationsResult> =>
    BASE_URL
      ? apiFetch<FamilyRecommendationsResult>("/family/recommendations")
      : delay<FamilyRecommendationsResult>({ recommendations: [], conflicts: [] }),

  // Phase 3 — Notification Center. Read-only: computes every source fresh
  // server-side and never mutates state (ArchitectureReview_Phase3.md).
  getNotifications: (): Promise<NotificationListResult> =>
    BASE_URL
      ? apiFetch<NotificationListResult>("/notifications")
      : delay<NotificationListResult>({ items: [], unread_count: 0 }),

  markNotificationRead: (source: NotificationSource, id: string): Promise<void> =>
    BASE_URL
      ? apiFetch<void>(`/notifications/${source}/${id}/read`, { method: "POST" })
      : delay(undefined),

  dismissNotification: (source: NotificationSource, id: string): Promise<void> =>
    BASE_URL
      ? apiFetch<void>(`/notifications/${source}/${id}/dismiss`, { method: "POST" })
      : delay(undefined),

  // Milestone 2 Task 12 — Family Dashboard. Read-only composition; the
  // mock mirrors the empty-household shape (just "you", nothing else yet).
  getFamilyDashboard: (): Promise<FamilyDashboard> =>
    BASE_URL
      ? apiFetch<FamilyDashboard>("/family/dashboard")
      : delay<FamilyDashboard>({
          dependents: {
            total_members: MOCK_FAMILY_HOME.members.length,
            children: MOCK_FAMILY_HOME.members.filter((m) => m.relationship_type === "child")
              .length,
            parents: MOCK_FAMILY_HOME.members.filter((m) => m.relationship_type === "parent")
              .length,
            spouse: MOCK_FAMILY_HOME.members.filter((m) => m.relationship_type === "spouse").length,
            others: MOCK_FAMILY_HOME.members.filter((m) => m.relationship_type === "other").length,
          },
          education: null,
          coverage: { covered_members: 0, total_members: MOCK_FAMILY_HOME.members.length },
          parents: { uncovered_parent_names: [] },
          retirement: null,
          emergency: { liquid_assets: 0, monthly_expenses: 0 },
          recommendations: [],
          conflicts: [],
          recommendations_unavailable: false,
        }),

  // Milestone 2.1-P1 — Family Government Schemes. Read-only; a direct
  // passthrough of the certified eligibility engine, nothing persisted.
  getFamilySchemes: (): Promise<FamilySchemes> =>
    BASE_URL
      ? apiFetch<FamilySchemes>("/family/schemes")
      : delay<FamilySchemes>({ eligible: [], potentially_eligible: [], not_eligible: [] }),

  // ── Goals ──────────────────────────────────────────────────────────────────
  getGoals: (): Promise<Goal[]> =>
    BASE_URL
      ? apiFetch<RawGoal[]>("/goals").then((raws) => raws.map(toGoal))
      : delay<Goal[]>(goalsFixture),

  createGoal: (g: Omit<Goal, "id" | "onTrack" | "probability">): Promise<Goal> =>
    BASE_URL
      ? apiFetch<RawGoal>("/goals", {
          method: "POST",
          body: JSON.stringify({
            name: g.name,
            category: g.category,
            target_amount: g.targetAmount,
            current_amount: g.currentAmount,
            target_date: g.targetDate,
            monthly_contribution: g.monthlyContribution,
            risk_profile: g.riskProfile,
          }),
        }).then(toGoal)
      : delay<Goal>({ ...g, id: `g_${Date.now()}`, onTrack: true, probability: 70 }),

  updateGoal: (id: string, patch: Partial<Goal>): Promise<Goal> =>
    BASE_URL
      ? apiFetch<RawGoal>(`/goals/${id}`, {
          method: "PATCH",
          body: JSON.stringify(toGoalPatch(patch)),
        }).then(toGoal)
      : delay<Goal>({ ...(goalsFixture.find((g) => g.id === id) as Goal), ...patch, id }),

  deleteGoal: (id: string): Promise<void> =>
    BASE_URL ? apiFetch<void>(`/goals/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Income ─────────────────────────────────────────────────────────────────
  getIncome: (): Promise<IncomeSource[]> =>
    BASE_URL ? apiFetch<IncomeSource[]>("/financials/income") : delay<IncomeSource[]>([]),

  createIncome: (data: {
    source_type: string;
    description?: string;
    annual_amount: number;
  }): Promise<IncomeSource> =>
    BASE_URL
      ? apiFetch<IncomeSource>("/financials/income", { method: "POST", body: JSON.stringify(data) })
      : delay<IncomeSource>({
          id: `i_${Date.now()}`,
          source_type: data.source_type,
          description: data.description ?? null,
          annual_amount: data.annual_amount,
          is_active: true,
        }),

  updateIncome: (
    id: string,
    patch: { description?: string; annual_amount?: number },
  ): Promise<IncomeSource> =>
    BASE_URL
      ? apiFetch<IncomeSource>(`/financials/income/${id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        })
      : delay<IncomeSource>({
          id,
          source_type: "salary",
          description: null,
          annual_amount: 0,
          is_active: true,
          ...patch,
        }),

  deleteIncome: (id: string): Promise<void> =>
    BASE_URL ? apiFetch<void>(`/financials/income/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Expenses ───────────────────────────────────────────────────────────────
  getExpenses: (): Promise<Expense[]> =>
    BASE_URL ? apiFetch<Expense[]>("/financials/expenses") : delay<Expense[]>([]),

  createExpense: (data: {
    category: string;
    description?: string;
    monthly_amount: number;
  }): Promise<Expense> =>
    BASE_URL
      ? apiFetch<Expense>("/financials/expenses", { method: "POST", body: JSON.stringify(data) })
      : delay<Expense>({
          id: `e_${Date.now()}`,
          category: data.category,
          description: data.description ?? null,
          monthly_amount: data.monthly_amount,
          is_active: true,
        }),

  updateExpense: (
    id: string,
    patch: { description?: string; monthly_amount?: number },
  ): Promise<Expense> =>
    BASE_URL
      ? apiFetch<Expense>(`/financials/expenses/${id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        })
      : delay<Expense>({
          id,
          category: "housing",
          description: null,
          monthly_amount: 0,
          is_active: true,
          ...patch,
        }),

  deleteExpense: (id: string): Promise<void> =>
    BASE_URL
      ? apiFetch<void>(`/financials/expenses/${id}`, { method: "DELETE" })
      : delay(undefined),

  // ── Assets ─────────────────────────────────────────────────────────────────
  getAssets: (): Promise<Asset[]> =>
    BASE_URL ? apiFetch<Asset[]>("/financials/assets") : delay<Asset[]>([]),

  createAsset: (data: {
    asset_type: string;
    institution?: string;
    description?: string;
    current_value: number;
  }): Promise<Asset> =>
    BASE_URL
      ? apiFetch<Asset>("/financials/assets", { method: "POST", body: JSON.stringify(data) })
      : delay<Asset>({
          id: `a_${Date.now()}`,
          asset_type: data.asset_type,
          institution: data.institution ?? null,
          description: data.description ?? null,
          current_value: data.current_value,
          is_active: true,
        }),

  updateAsset: (
    id: string,
    patch: { current_value?: number; institution?: string; description?: string },
  ): Promise<Asset> =>
    BASE_URL
      ? apiFetch<Asset>(`/financials/assets/${id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        })
      : delay<Asset>({
          id,
          asset_type: "checking",
          institution: null,
          description: null,
          current_value: 0,
          is_active: true,
          ...patch,
        }),

  deleteAsset: (id: string): Promise<void> =>
    BASE_URL ? apiFetch<void>(`/financials/assets/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Liabilities ────────────────────────────────────────────────────────────
  getLiabilities: (): Promise<Liability[]> =>
    BASE_URL ? apiFetch<Liability[]>("/financials/liabilities") : delay<Liability[]>([]),

  createLiability: (data: {
    liability_type: string;
    institution?: string;
    description?: string;
    balance: number;
    interest_rate?: number;
    monthly_payment?: number;
  }): Promise<Liability> =>
    BASE_URL
      ? apiFetch<Liability>("/financials/liabilities", {
          method: "POST",
          body: JSON.stringify(data),
        })
      : delay<Liability>({
          id: `l_${Date.now()}`,
          liability_type: data.liability_type,
          institution: data.institution ?? null,
          description: data.description ?? null,
          balance: data.balance,
          interest_rate: data.interest_rate ?? null,
          monthly_payment: data.monthly_payment ?? null,
          is_active: true,
        }),

  updateLiability: (
    id: string,
    patch: {
      balance?: number;
      interest_rate?: number;
      monthly_payment?: number;
      institution?: string;
      description?: string;
    },
  ): Promise<Liability> =>
    BASE_URL
      ? apiFetch<Liability>(`/financials/liabilities/${id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        })
      : delay<Liability>({
          id,
          liability_type: "other",
          institution: null,
          description: null,
          balance: 0,
          interest_rate: null,
          monthly_payment: null,
          is_active: true,
          ...patch,
        }),

  deleteLiability: (id: string): Promise<void> =>
    BASE_URL
      ? apiFetch<void>(`/financials/liabilities/${id}`, { method: "DELETE" })
      : delay(undefined),

  // ── Assumptions ────────────────────────────────────────────────────────────
  getAssumptions: (): Promise<FinancialAssumptions> =>
    BASE_URL
      ? apiFetch<FinancialAssumptions>("/assumptions")
      : delay<FinancialAssumptions>(MOCK_ASSUMPTIONS),

  upsertAssumptions: (
    data: Partial<Omit<FinancialAssumptions, "id">>,
  ): Promise<FinancialAssumptions> =>
    BASE_URL
      ? apiFetch<FinancialAssumptions>("/assumptions", {
          method: "PUT",
          body: JSON.stringify(data),
        })
      : delay<FinancialAssumptions>({ ...MOCK_ASSUMPTIONS, ...data }),

  // ── Simulation ─────────────────────────────────────────────────────────────
  simulate: (input: {
    goalId?: string;
    initialAmount: number;
    monthlyContribution: number;
    yearsToGoal: number;
    riskProfile: string;
    numSimulations?: number;
  }): Promise<SimulationResult> =>
    BASE_URL
      ? apiFetch<SimulationResult>("/simulate", {
          method: "POST",
          body: JSON.stringify({
            goal_id: input.goalId,
            initial_amount: input.initialAmount,
            monthly_contribution: input.monthlyContribution,
            years_to_goal: input.yearsToGoal,
            risk_profile: input.riskProfile,
            num_simulations: input.numSimulations ?? 10000,
          }),
        })
      : delay<SimulationResult>({
          id: "mock-sim",
          success_rate: 81,
          percentiles: {
            p10: 1_980_000,
            p25: 2_300_000,
            p50: 2_640_000,
            p75: 3_020_000,
            p90: 3_410_000,
          },
          distribution: {},
        }),

  optimize: (input: {
    goalId: string;
    targetProbability?: number;
    maxMonthlyIncrease?: number;
    allowRiskAdjustment?: boolean;
  }): Promise<OptimizationResult> =>
    BASE_URL
      ? apiFetch<OptimizationResult>("/simulate/optimize", {
          method: "POST",
          body: JSON.stringify({
            goal_id: input.goalId,
            target_probability: input.targetProbability ?? 80,
            max_monthly_increase: input.maxMonthlyIncrease ?? 500,
            allow_risk_adjustment: input.allowRiskAdjustment ?? true,
          }),
        })
      : delay<OptimizationResult>({
          goal_id: input.goalId,
          current_probability: 54,
          suggestions: [
            {
              description: "Increase monthly contribution by $180",
              monthly_contribution_delta: 180,
              risk_profile_change: null,
              projected_probability: 71,
              impact_summary: "Raises success probability from 54% to 71%.",
            },
          ],
        }),

  // ── AI Copilot ─────────────────────────────────────────────────────────────
  chat: (
    message: string,
    conversationId?: string,
  ): Promise<{ reply: string; conversation_id: string }> =>
    BASE_URL
      ? apiFetch<{ reply: string; conversation_id: string }>("/copilot", {
          method: "POST",
          body: JSON.stringify({ message, conversation_id: conversationId }),
        })
      : delay({
          reply:
            "I've analyzed your current plan. To improve goal success rates, consider increasing your monthly contributions or extending your timeline. Would you like me to run specific scenarios?",
          conversation_id: "mock-conv",
        }),

  // ── Reports ────────────────────────────────────────────────────────────────
  getReportSummary: (): Promise<ReportSummary> =>
    BASE_URL
      ? apiFetch<ReportSummary>("/reports/summary")
      : delay<ReportSummary>({
          generated_at: new Date().toISOString(),
          plan_health_score: 74,
          net_worth: 245_000,
          liquid_assets: 45_000,
          invested: 200_000,
          liabilities: 0,
          monthly_income: 10_000,
          monthly_expenses: 6_900,
          monthly_savings_rate: 31,
          goal_count: 3,
          goals_on_track: 2,
          goals: [
            {
              id: "g1",
              name: "Retirement",
              category: "retirement",
              target_amount: 2_000_000,
              current_amount: 200_000,
              monthly_contribution: 2_000,
              probability: 74,
              on_track: true,
              target_date: "2055-01-01",
            },
            {
              id: "g2",
              name: "Home Purchase",
              category: "home",
              target_amount: 100_000,
              current_amount: 25_000,
              monthly_contribution: 1_500,
              probability: 88,
              on_track: true,
              target_date: "2027-06-01",
            },
            {
              id: "g3",
              name: "Education Fund",
              category: "education",
              target_amount: 80_000,
              current_amount: 10_000,
              monthly_contribution: 500,
              probability: 62,
              on_track: false,
              target_date: "2032-09-01",
            },
          ],
        }),

  // ── Life Event Engine ────────────────────────────────────────────────────
  getLifeEvents: (params?: {
    event_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<LifeEventListResult> => {
    if (!BASE_URL) {
      return delay<LifeEventListResult>({
        items: [],
        total: 0,
        limit: params?.limit ?? 20,
        offset: params?.offset ?? 0,
      });
    }
    const query = new URLSearchParams();
    if (params?.event_type) query.set("event_type", params.event_type);
    if (params?.start_date) query.set("start_date", params.start_date);
    if (params?.end_date) query.set("end_date", params.end_date);
    query.set("limit", String(params?.limit ?? 20));
    query.set("offset", String(params?.offset ?? 0));
    return apiFetch<LifeEventListResult>(`/life-events?${query.toString()}`);
  },

  getLifeEvent: (id: string): Promise<LifeEventRecord> =>
    apiFetch<LifeEventRecord>(`/life-events/${id}`),

  previewLifeEvent: (
    eventType: string,
    inputs: Record<string, unknown>,
  ): Promise<LifeEventPreviewResult> =>
    BASE_URL
      ? apiFetch<LifeEventPreviewResult>("/life-events/preview", {
          method: "POST",
          body: JSON.stringify({ event_type: eventType, inputs }),
        })
      : delay<LifeEventPreviewResult>({
          event_type: eventType,
          effects: [],
          affected_entities: [],
          validation_errors: [],
        }),

  recordLifeEvent: (data: {
    event_type: string;
    occurred_on: string;
    inputs: Record<string, unknown>;
    notes?: string;
    idempotency_key?: string;
  }): Promise<LifeEventCreateResult> =>
    BASE_URL
      ? apiFetch<LifeEventCreateResult>("/life-events", {
          method: "POST",
          body: JSON.stringify(data),
        })
      : delay<LifeEventCreateResult>({
          life_event: {
            id: `le_${Date.now()}`,
            event_type: data.event_type,
            occurred_on: data.occurred_on,
            recorded_at: new Date().toISOString(),
            inputs: data.inputs,
            status: "applied",
            undone_at: null,
            notes: data.notes ?? null,
            effects: [],
            audit_action: "life_event_recorded",
          },
          audit_reference: `audit_${Date.now()}`,
        }),

  undoLifeEvent: (id: string, force = false): Promise<UndoResult> =>
    BASE_URL
      ? apiFetch<UndoResult>(
          `/life-events/${id}/undo`,
          { method: "POST", body: JSON.stringify({ force }) },
          false,
          [409],
        )
      : delay<UndoResult>({ success: true, blocked: false, conflicts: [] }),
};
