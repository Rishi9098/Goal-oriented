type Slice = { label: string; value: number; color: string };

type Props = {
  liquid: number;
  invested: number;
  liabilities: number;
  netWorth: number;
};

const fmtDollar = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

function buildGradient(slices: Slice[], total: number): string {
  let cursor = 0;
  const parts: string[] = [];
  for (const s of slices) {
    const pct = (s.value / total) * 100;
    parts.push(`${s.color} ${cursor.toFixed(1)}% ${(cursor + pct).toFixed(1)}%`);
    cursor += pct;
  }
  return `conic-gradient(${parts.join(", ")})`;
}

export function NetWorthBreakdown({ liquid, invested, liabilities, netWorth }: Props) {
  const totalAssets = liquid + invested + Math.max(0, netWorth + liabilities - liquid - invested);
  const other = Math.max(0, totalAssets - liquid - invested);

  const slices: Slice[] = [
    { label: "Cash & savings", value: liquid, color: "#38bdf8" },
    { label: "Investments", value: invested, color: "#818cf8" },
    ...(other > 0 ? [{ label: "Other assets", value: other, color: "#34d399" }] : []),
    ...(liabilities > 0
      ? [{ label: "Liabilities", value: liabilities, color: "#f87171" }]
      : []),
  ].filter((s) => s.value > 0);

  const totalDisplay = slices.reduce((s, x) => s + x.value, 0);

  if (totalDisplay === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center gap-2 text-center">
        <p className="text-sm text-muted-foreground">
          Add assets to see your breakdown
        </p>
      </div>
    );
  }

  const gradient = buildGradient(slices, totalDisplay);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-6">
        <div className="relative shrink-0">
          <div
            className="h-32 w-32 rounded-full"
            style={{ background: gradient }}
          />
          <div className="absolute inset-0 m-auto h-20 w-20 rounded-full bg-[oklch(0.20_0.04_262)]" />
        </div>

        <div className="flex min-w-0 flex-col gap-2">
          {slices.map((s) => {
            const pct = ((s.value / totalDisplay) * 100).toFixed(1);
            return (
              <div key={s.label} className="flex items-start gap-2">
                <span
                  className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: s.color }}
                />
                <div className="min-w-0">
                  <p className="truncate text-xs text-muted-foreground">{s.label}</p>
                  <p className="text-sm font-medium text-foreground">
                    {fmtDollar(s.value)}{" "}
                    <span className="text-xs font-normal text-muted-foreground">
                      {pct}%
                    </span>
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-lg border border-border/50 bg-surface/40 px-4 py-2.5">
        <p className="text-xs text-muted-foreground">Net worth</p>
        <p className="font-display text-lg font-semibold text-foreground">
          {fmtDollar(netWorth)}
        </p>
      </div>
    </div>
  );
}
