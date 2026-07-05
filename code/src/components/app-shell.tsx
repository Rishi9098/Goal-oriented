import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { type ReactNode, useState, useEffect } from "react";
import {
  LayoutDashboard,
  Target,
  Sparkles,
  BarChart3,
  Settings as SettingsIcon,
  User,
  Bell,
  Search,
  LogOut,
} from "lucide-react";
import { auth, api, clearTokens } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/app/goals", label: "Goals", icon: Target },
  { to: "/app/copilot", label: "AI Copilot", icon: Sparkles },
  { to: "/app/reports", label: "Reports", icon: BarChart3 },
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: SettingsIcon },
];

export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [initials, setInitials] = useState("··");
  const [planHealth, setPlanHealth] = useState<number | null>(null);

  useEffect(() => {
    auth.me().then((user) => {
      const name = (user.full_name ?? user.email ?? "").trim();
      const parts = name.split(/\s+/);
      setInitials(
        parts.length >= 2
          ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
          : name.slice(0, 2).toUpperCase() || "?",
      );
    }).catch(() => setInitials("?"));

    api.getDashboard().then((d) => setPlanHealth(d.plan_health_score)).catch(() => {});
  }, []);

  function handleSignOut() {
    clearTokens();
    navigate({ to: "/auth/sign-in", replace: true });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        {/* Sidebar */}
        <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-border bg-surface/40 backdrop-blur sticky top-0 h-screen">
          <div className="px-6 py-6">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-cyan shadow-glow" />
              <span className="font-display text-lg font-semibold tracking-tight">Northstar</span>
            </Link>
          </div>
          <nav className="px-3 flex-1 space-y-1">
            {nav.map((item) => {
              const Icon = item.icon;
              const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-accent text-foreground shadow-[inset_0_0_0_1px_var(--color-border-strong)]"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          {planHealth !== null && (
            <div className="m-3 surface-card p-4">
              <p className="text-xs text-muted-foreground">Plan health</p>
              <p className="mt-1 font-display text-2xl">
                {planHealth}
                <span className="text-sm text-muted-foreground">/100</span>
              </p>
              <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-cyan transition-all duration-700"
                  style={{ width: `${planHealth}%` }}
                />
              </div>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="mx-3 mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors w-[calc(100%-1.5rem)]"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </aside>

        {/* Main */}
        <div className="flex-1 min-w-0">
          <header className="sticky top-0 z-20 border-b border-border bg-background/70 backdrop-blur-xl">
            <div className="flex h-16 items-center gap-3 px-4 md:px-8">
              <h1 className="font-display text-lg font-medium tracking-tight">{title}</h1>
              <div className="ml-auto flex items-center gap-2">
                <div className="hidden md:flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted-foreground w-72">
                  <Search className="h-4 w-4" />
                  <span>Search goals, holdings, reports…</span>
                  <kbd className="ml-auto font-mono text-[10px] text-muted-foreground/70">⌘K</kbd>
                </div>
                <button className="relative rounded-lg border border-border bg-surface p-2 hover:bg-accent transition">
                  <Bell className="h-4 w-4" />
                  <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-cyan" />
                </button>
                <div className="h-9 w-9 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center font-medium text-primary-foreground text-sm">
                  {initials}
                </div>
              </div>
            </div>
          </header>
          <main className="px-4 md:px-8 py-6 md:py-10 pb-24 lg:pb-10">{children}</main>
        </div>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 border-t border-border bg-background/90 backdrop-blur-xl">
        <div className="grid grid-cols-5 h-16">
          {nav.slice(0, 4).concat(nav[5]).map((item) => {
            const Icon = item.icon;
            const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 text-[10px] transition-colors",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                <Icon className={cn("h-5 w-5", active && "text-cyan")} />
                <span>{item.label.split(" ")[0]}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
