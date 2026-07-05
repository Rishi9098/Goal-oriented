/**
 * API service layer.
 *
 * When VITE_API_BASE_URL is set the client talks to the real FastAPI backend.
 * Without it every call falls back to mock fixtures so the UI remains
 * fully functional during local frontend-only development.
 */

import type { Goal } from "./mock-data";
import { goals as goalsFixture } from "./mock-data";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

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
  return out;
}

// ── Token management ──────────────────────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem("ns_access_token");
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem("ns_access_token", access);
  localStorage.setItem("ns_refresh_token", refresh);
}

export function clearTokens(): void {
  localStorage.removeItem("ns_access_token");
  localStorage.removeItem("ns_refresh_token");
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

let _refreshPromise: Promise<void> | null = null;

async function _doRefresh(): Promise<void> {
  const rt = localStorage.getItem("ns_refresh_token");
  if (!rt) throw new Error("No refresh token");
  const resp = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!resp.ok) throw new Error("Refresh failed");
  const data = (await resp.json()) as { access_token: string; refresh_token: string };
  setTokens(data.access_token, data.refresh_token);
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
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (resp.status === 401 && !_retry && BASE_URL) {
    if (!_refreshPromise) {
      _refreshPromise = _doRefresh().finally(() => { _refreshPromise = null; });
    }
    try {
      await _refreshPromise;
      return apiFetch<T>(path, options, true);
    } catch {
      clearTokens();
      window.location.href = "/auth/sign-in";
      throw new Error("Session expired. Please sign in again.");
    }
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(parseError(body, resp.status));
  }
  if (resp.status === 204) return undefined as unknown as T;
  return resp.json() as Promise<T>;
}

// ── Mock fallback helpers ─────────────────────────────────────────────────────

const delay = <T,>(value: T, ms = 350): Promise<T> =>
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
      ? apiFetch<{ access_token: string; refresh_token: string }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        })
      : delay({ access_token: "mock-token", refresh_token: "mock-refresh" }),

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
      : delay({ id: "mock-id", email: "demo@northstar.app", full_name: patch.full_name ?? "Demo User" }),

  forgotPassword: (email: string) =>
    BASE_URL
      ? apiFetch<{ message: string; reset_token?: string }>("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        })
      : delay({ message: "If that email exists, a reset link has been sent.", reset_token: "mock-reset-token" }),

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
    BASE_URL
      ? apiFetch<void>("/auth/me", { method: "DELETE" })
      : delay(undefined),
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
    BASE_URL
      ? apiFetch<void>(`/goals/${id}`, { method: "DELETE" })
      : delay(undefined),

  // ── Income ─────────────────────────────────────────────────────────────────
  getIncome: (): Promise<IncomeSource[]> =>
    BASE_URL ? apiFetch<IncomeSource[]>("/income") : delay<IncomeSource[]>([]),

  createIncome: (data: {
    source_type: string;
    description?: string;
    annual_amount: number;
  }): Promise<IncomeSource> =>
    BASE_URL
      ? apiFetch<IncomeSource>("/income", { method: "POST", body: JSON.stringify(data) })
      : delay<IncomeSource>({
          id: `i_${Date.now()}`,
          source_type: data.source_type,
          description: data.description ?? null,
          annual_amount: data.annual_amount,
          is_active: true,
        }),

  deleteIncome: (id: string): Promise<void> =>
    BASE_URL ? apiFetch<void>(`/income/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Expenses ───────────────────────────────────────────────────────────────
  getExpenses: (): Promise<Expense[]> =>
    BASE_URL ? apiFetch<Expense[]>("/expenses") : delay<Expense[]>([]),

  createExpense: (data: {
    category: string;
    description?: string;
    monthly_amount: number;
  }): Promise<Expense> =>
    BASE_URL
      ? apiFetch<Expense>("/expenses", { method: "POST", body: JSON.stringify(data) })
      : delay<Expense>({
          id: `e_${Date.now()}`,
          category: data.category,
          description: data.description ?? null,
          monthly_amount: data.monthly_amount,
          is_active: true,
        }),

  deleteExpense: (id: string): Promise<void> =>
    BASE_URL ? apiFetch<void>(`/expenses/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Assets ─────────────────────────────────────────────────────────────────
  getAssets: (): Promise<Asset[]> =>
    BASE_URL ? apiFetch<Asset[]>("/assets") : delay<Asset[]>([]),

  createAsset: (data: {
    asset_type: string;
    institution?: string;
    description?: string;
    current_value: number;
  }): Promise<Asset> =>
    BASE_URL
      ? apiFetch<Asset>("/assets", { method: "POST", body: JSON.stringify(data) })
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
      ? apiFetch<Asset>(`/assets/${id}`, { method: "PATCH", body: JSON.stringify(patch) })
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
    BASE_URL ? apiFetch<void>(`/assets/${id}`, { method: "DELETE" }) : delay(undefined),

  // ── Liabilities ────────────────────────────────────────────────────────────
  getLiabilities: (): Promise<Liability[]> =>
    BASE_URL ? apiFetch<Liability[]>("/liabilities") : delay<Liability[]>([]),

  createLiability: (data: {
    liability_type: string;
    institution?: string;
    description?: string;
    balance: number;
    interest_rate?: number;
    monthly_payment?: number;
  }): Promise<Liability> =>
    BASE_URL
      ? apiFetch<Liability>("/liabilities", { method: "POST", body: JSON.stringify(data) })
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
      ? apiFetch<Liability>(`/liabilities/${id}`, { method: "PATCH", body: JSON.stringify(patch) })
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
    BASE_URL ? apiFetch<void>(`/liabilities/${id}`, { method: "DELETE" }) : delay(undefined),

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
          percentiles: { p10: 1_980_000, p25: 2_300_000, p50: 2_640_000, p75: 3_020_000, p90: 3_410_000 },
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
};
