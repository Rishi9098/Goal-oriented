// Dummy fixtures for the AI Goal-Based Financial Planning Platform.
// Replace these with real API responses later.

export type Goal = {
  id: string;
  name: string;
  category: "retirement" | "education" | "home" | "travel" | "wealth" | "emergency";
  targetAmount: number;
  currentAmount: number;
  targetDate: string; // ISO
  monthlyContribution: number;
  onTrack: boolean;
  probability: number; // 0-100, Monte Carlo success probability
  riskProfile: "conservative" | "balanced" | "aggressive";
};

export const goals: Goal[] = [
  {
    id: "g_retire",
    name: "Retirement at 60",
    category: "retirement",
    targetAmount: 2_400_000,
    currentAmount: 685_400,
    targetDate: "2049-06-01",
    monthlyContribution: 3200,
    onTrack: true,
    probability: 87,
    riskProfile: "balanced",
  },
  {
    id: "g_home",
    name: "Home down payment",
    category: "home",
    targetAmount: 180_000,
    currentAmount: 96_200,
    targetDate: "2027-09-01",
    monthlyContribution: 1800,
    onTrack: true,
    probability: 78,
    riskProfile: "conservative",
  },
  {
    id: "g_college",
    name: "Education fund",
    category: "education",
    targetAmount: 220_000,
    currentAmount: 41_300,
    targetDate: "2034-08-01",
    monthlyContribution: 650,
    onTrack: false,
    probability: 54,
    riskProfile: "balanced",
  },
  {
    id: "g_japan",
    name: "Sabbatical fund",
    category: "travel",
    targetAmount: 28_000,
    currentAmount: 19_400,
    targetDate: "2026-04-01",
    monthlyContribution: 950,
    onTrack: true,
    probability: 92,
    riskProfile: "conservative",
  },
  {
    id: "g_emer",
    name: "Emergency reserve",
    category: "emergency",
    targetAmount: 60_000,
    currentAmount: 60_000,
    targetDate: "2024-12-01",
    monthlyContribution: 0,
    onTrack: true,
    probability: 100,
    riskProfile: "conservative",
  },
];

export const dashboard = {
  netWorth: 902_300,
  netWorthDelta: 4.8,
  liquidAssets: 184_500,
  invested: 657_800,
  liabilities: 124_000,
  monthlySavingsRate: 31,
  projectedRetirement: 3_180_000,
  alerts: 2,
};

export const netWorthSeries = [
  { month: "Jan", value: 712_000 },
  { month: "Feb", value: 728_400 },
  { month: "Mar", value: 745_200 },
  { month: "Apr", value: 761_100 },
  { month: "May", value: 778_900 },
  { month: "Jun", value: 803_400 },
  { month: "Jul", value: 819_700 },
  { month: "Aug", value: 841_200 },
  { month: "Sep", value: 858_900 },
  { month: "Oct", value: 871_000 },
  { month: "Nov", value: 889_800 },
  { month: "Dec", value: 902_300 },
];

export const allocation = [
  { name: "US Equities", value: 42 },
  { name: "Intl Equities", value: 18 },
  { name: "Bonds", value: 22 },
  { name: "Real Estate", value: 10 },
  { name: "Cash", value: 8 },
];

export const aiSuggestions = [
  {
    id: "s1",
    title: "Increase education fund contribution by $180/mo",
    impact: "Raises education fund success rate from 54% to 71%.",
    severity: "warning" as const,
  },
  {
    id: "s2",
    title: "Rebalance to 60/40 ahead of Q1",
    impact: "Reduces drawdown risk by ~6% on a 12-month horizon.",
    severity: "info" as const,
  },
  {
    id: "s3",
    title: "Move $12k of idle cash to T-bills",
    impact: "Captures ~$520/yr at current yields with zero added risk.",
    severity: "success" as const,
  },
];

export const formatCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

export const formatPercent = (n: number) => `${n.toFixed(0)}%`;
