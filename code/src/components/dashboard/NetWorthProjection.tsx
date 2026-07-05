import { useId } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const YEARS = [0, 5, 10, 15, 20, 25, 30];
const RATES = { conservative: 0.05, balanced: 0.07, aggressive: 0.09 };

const C = {
  conservative: "#64748b",
  balanced: "#818cf8",
  aggressive: "#38bdf8",
} as const;

type Scenario = keyof typeof RATES;

function project(initial: number, monthly: number, years: number, rate: number): number {
  if (years === 0) return Math.round(initial);
  const mr = rate / 12;
  const months = years * 12;
  if (mr === 0) return Math.round(initial + monthly * months);
  return Math.round(
    initial * Math.pow(1 + mr, months) +
      monthly * (Math.pow(1 + mr, months) - 1) / mr,
  );
}

function fmtAxis(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

const fmtDollar = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

type Props = { netWorth: number; monthlySavings: number };

export function NetWorthProjection({ netWorth, monthlySavings }: Props) {
  const uid = useId().replace(/:/g, "");

  const data = YEARS.map((y) => ({
    label: y === 0 ? "Now" : `+${y}y`,
    Conservative: project(netWorth, monthlySavings, y, RATES.conservative),
    Balanced: project(netWorth, monthlySavings, y, RATES.balanced),
    Aggressive: project(netWorth, monthlySavings, y, RATES.aggressive),
  }));

  const at30 = data[data.length - 1];

  return (
    <div className="flex flex-col gap-4">
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${uid}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={C.balanced} stopOpacity={0.22} />
                <stop offset="95%" stopColor={C.balanced} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={fmtAxis}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={56}
            />
            <Tooltip
              formatter={(v: number, name: string) => [fmtDollar(v), name]}
              contentStyle={{
                background: "oklch(0.22 0.04 262)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "12px",
                color: "#e2e8f0",
              }}
              labelStyle={{ color: "#94a3b8", marginBottom: "4px" }}
            />
            <Area
              type="monotone"
              dataKey="Conservative"
              stroke={C.conservative}
              fill="none"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              activeDot={{ r: 3, fill: C.conservative }}
            />
            <Area
              type="monotone"
              dataKey="Balanced"
              stroke={C.balanced}
              fill={`url(#grad-${uid})`}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: C.balanced }}
            />
            <Area
              type="monotone"
              dataKey="Aggressive"
              stroke={C.aggressive}
              fill="none"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 3, fill: C.aggressive }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {(["conservative", "balanced", "aggressive"] as Scenario[]).map((k) => {
          const label = k.charAt(0).toUpperCase() + k.slice(1);
          const val = at30[label as keyof typeof at30] as number;
          return (
            <div
              key={k}
              className="rounded-lg border border-border/60 bg-surface/40 px-3 py-2 text-center"
            >
              <p className="mb-0.5 text-xs" style={{ color: C[k] }}>
                {label}
              </p>
              <p className="font-display text-sm font-semibold text-foreground">
                {fmtAxis(val)}
              </p>
              <p className="text-xs text-muted-foreground">in 30 yrs</p>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-5 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-px w-5 border-t border-dashed"
            style={{ borderColor: C.conservative }}
          />
          5% / yr
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-5 rounded"
            style={{ background: C.balanced }}
          />
          7% / yr
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-5 rounded"
            style={{ background: C.aggressive }}
          />
          9% / yr
        </span>
      </div>
    </div>
  );
}
