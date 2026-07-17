import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { ArrowRight, ShieldCheck, Sparkles, LineChart, Target, Lock } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Northstar — AI Goal-Based Financial Planning" },
      {
        name: "description",
        content:
          "Plan, simulate, and reach every financial goal with an AI copilot built for serious investors.",
      },
      { property: "og:title", content: "Northstar — AI Goal-Based Financial Planning" },
      {
        property: "og:description",
        content:
          "Plan, simulate, and reach every financial goal with an AI copilot built for serious investors.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen hero-bg text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-30 backdrop-blur-xl bg-background/40 border-b border-border">
        <div className="mx-auto max-w-7xl flex items-center justify-between px-6 h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-cyan shadow-glow" />
            <span className="font-display text-lg font-semibold tracking-tight">Northstar</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#product" className="hover:text-foreground transition">
              Product
            </a>
            <a href="#how" className="hover:text-foreground transition">
              How it works
            </a>
            <a href="#trust" className="hover:text-foreground transition">
              Security
            </a>
            <a href="#pricing" className="hover:text-foreground transition">
              Pricing
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              to="/auth/sign-in"
              className="hidden sm:inline-flex text-sm text-muted-foreground hover:text-foreground px-3 py-2"
            >
              Sign in
            </Link>
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
            >
              Get started <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-40 [mask-image:radial-gradient(70%_60%_at_50%_30%,black,transparent)]" />
        <div className="relative mx-auto max-w-7xl px-6 pt-20 pb-28 md:pt-28 md:pb-36 text-center">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-3 py-1 text-xs text-muted-foreground"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan" />
            New — Monte Carlo simulations powered by GPT planning agents
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="mt-6 font-display text-4xl md:text-6xl lg:text-7xl font-medium tracking-tight max-w-4xl mx-auto"
          >
            The plan behind every <span className="gradient-text">financial goal</span>.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 max-w-2xl mx-auto text-muted-foreground text-lg"
          >
            Northstar models every dollar against every goal — retirement, home, college, sabbatical
            — and tells you exactly what to do this month to stay on track.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-9 flex items-center justify-center gap-3"
          >
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-3 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
            >
              Build your plan <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/app"
              className="inline-flex items-center gap-2 rounded-lg border border-border-strong bg-surface/60 px-5 py-3 text-sm font-medium hover:bg-surface transition"
            >
              View live demo
            </Link>
          </motion.div>

          {/* Hero card */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25 }}
            className="mt-16 mx-auto max-w-5xl surface-card overflow-hidden text-left"
          >
            <div className="grid md:grid-cols-[1.2fr_1fr] gap-0">
              <div className="p-6 md:p-8 border-b md:border-b-0 md:border-r border-border">
                <div className="flex items-baseline justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-muted-foreground">
                      Net worth
                    </p>
                    <p className="mt-1 font-display text-3xl md:text-4xl">$902,300</p>
                  </div>
                  <span className="text-xs rounded-full bg-success/15 text-success px-2 py-0.5">
                    +4.8% YTD
                  </span>
                </div>
                <div className="mt-6 h-40 relative">
                  <svg viewBox="0 0 400 140" className="absolute inset-0 w-full h-full">
                    <defs>
                      <linearGradient id="g" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="oklch(0.66 0.19 255)" stopOpacity="0.5" />
                        <stop offset="100%" stopColor="oklch(0.66 0.19 255)" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path
                      d="M0,110 C40,100 70,95 100,85 C140,72 170,82 200,70 C240,55 270,60 300,45 C340,28 370,30 400,18 L400,140 L0,140 Z"
                      fill="url(#g)"
                    />
                    <path
                      d="M0,110 C40,100 70,95 100,85 C140,72 170,82 200,70 C240,55 270,60 300,45 C340,28 370,30 400,18"
                      fill="none"
                      stroke="oklch(0.82 0.14 200)"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
              </div>
              <div className="p-6 md:p-8 space-y-4">
                {[
                  { name: "Retirement at 60", pct: 87, color: "from-primary to-cyan" },
                  { name: "Brooklyn down payment", pct: 78, color: "from-cyan to-success" },
                  { name: "Maya's college", pct: 54, color: "from-warning to-destructive" },
                ].map((g) => (
                  <div key={g.name}>
                    <div className="flex items-center justify-between text-sm">
                      <span>{g.name}</span>
                      <span className="font-mono text-muted-foreground">{g.pct}%</span>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${g.pct}%` }}
                        transition={{ duration: 1.2, delay: 0.5 }}
                        className={`h-full bg-gradient-to-r ${g.color}`}
                      />
                    </div>
                  </div>
                ))}
                <div className="mt-4 rounded-lg border border-border bg-background/40 p-3 text-xs text-muted-foreground">
                  <span className="text-cyan">Copilot:</span> Increasing Maya's contribution by
                  $180/mo raises her plan to 71%.
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="product" className="mx-auto max-w-7xl px-6 py-24">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-widest text-cyan">Platform</p>
          <h2 className="mt-2 font-display text-3xl md:text-4xl tracking-tight">
            Everything a private wealth desk does — without the desk.
          </h2>
        </div>
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Target,
              title: "Goal-based planning",
              body: "Model every goal with its own horizon, risk, and probability of success. Trade-offs become obvious.",
            },
            {
              icon: LineChart,
              title: "Monte Carlo at any depth",
              body: "Run 10,000 simulations per scenario and see distributions across percentiles in seconds.",
            },
            {
              icon: Sparkles,
              title: "AI copilot",
              body: "A planner that drafts actions, explains trade-offs in plain English, and learns your preferences.",
            },
            {
              icon: ShieldCheck,
              title: "Bank-grade security",
              body: "SOC 2 Type II, AES-256 at rest, OAuth read-only account linking, no credential storage.",
            },
            {
              icon: Lock,
              title: "Private by design",
              body: "Your data is never used to train models. Delete on request, exportable any time.",
            },
            {
              icon: ArrowRight,
              title: "Actionable, not advisory",
              body: "Each recommendation comes with a one-tap action — rebalance, increase, defer, defer.",
            },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="surface-card p-6 hover:border-border-strong transition group"
              >
                <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/30 to-cyan/30 grid place-items-center group-hover:shadow-glow transition">
                  <Icon className="h-5 w-5 text-cyan" />
                </div>
                <h3 className="mt-4 font-display text-lg">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-border bg-surface/30">
        <div className="mx-auto max-w-7xl px-6 py-24">
          <div className="grid md:grid-cols-3 gap-10">
            {[
              { n: "01", t: "Link your accounts", d: "Read-only, OAuth. No credentials stored." },
              {
                n: "02",
                t: "Define your goals",
                d: "Horizon, amount, priority — guided in minutes.",
              },
              { n: "03", t: "Run the plan", d: "Simulate, accept actions, monitor monthly." },
            ].map((s) => (
              <div key={s.n}>
                <p className="font-mono text-xs text-cyan">{s.n}</p>
                <h3 className="mt-2 font-display text-2xl tracking-tight">{s.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="pricing" className="mx-auto max-w-5xl px-6 py-28 text-center">
        <h2 className="font-display text-4xl md:text-5xl tracking-tight">
          Your plan, <span className="gradient-text">re-computed every night</span>.
        </h2>
        <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
          Start free. Upgrade when you're ready to link accounts and run unlimited simulations.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            to="/onboarding"
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-6 py-3 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
          >
            Build your plan <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-gradient-to-br from-primary to-cyan" />
            <span>© {new Date().getFullYear()} Northstar Planning</span>
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground">
              Privacy
            </a>
            <a href="#" className="hover:text-foreground">
              Terms
            </a>
            <a href="#" className="hover:text-foreground">
              Disclosures
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
