import { Link, useMatches, useRouterState, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useState, useEffect, useRef } from "react";
import { ShellTitleOverrideContext } from "@/lib/shell-title";
import { GlobalPalette } from "@/components/global-palette";
import { NotificationCenter } from "@/components/notification-center";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard,
  Target,
  Users,
  Sparkles,
  BarChart3,
  Settings as SettingsIcon,
  User,
  Search,
  LogOut,
  MoreHorizontal,
  Wallet,
  History,
  Info,
} from "lucide-react";
import { auth, api, clearAccessToken } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PlanHealthInfo } from "@/components/PlanHealthInfo";

// Order matches FamilyPlanningDesign.md's concrete nav diagram (Family
// directly after Goals) rather than that same document's prose ("Family
// goes second... before Goals") — the two disagree; the diagram is the
// more specific, actionable artifact. Flagged in this task's Design Review
// rather than silently picking one without a record.
//
// Life Events sits second, directly after the overview (NavigationReview.md
// Phase 1): it's the Life Event Engine's entire product-facing surface —
// "something just happened, let me record it" — and nav position is a
// promise about importance that was previously backwards (mid-list on
// desktop, absent from mobile's primary slots and the Command Palette).
// AI Copilot moves below Reports to honestly reflect today's verified lack
// of integration with Life Events/Goals/Recommendations — not a permanent
// demotion, just not yet earning a top slot until Phase 2 (Life Event
// Product Integration) wires it up.
const nav = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, exact: true },
  // Mobile bottom-nav labels default to the first word of `label`
  // (`item.label.split(" ")[0]`, below) — that default would read as the
  // ambiguous, standalone "Life" for this item, so it gets an explicit
  // `mobileLabel` override; every other item keeps the default behavior.
  { to: "/app/life-events", label: "Life Events", mobileLabel: "Events", icon: History },
  { to: "/app/goals", label: "Goals", icon: Target },
  { to: "/app/family", label: "Family", icon: Users },
  { to: "/app/financials", label: "Financials", icon: Wallet },
  { to: "/app/reports", label: "Reports", icon: BarChart3 },
  { to: "/app/copilot", label: "AI Copilot", icon: Sparkles },
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: SettingsIcon },
];

// Mobile bottom nav can only fit 5 slots (FamilyPlanningDesign.md Part 2 —
// constraint preserved as-is; only which 4 items are primary changes here).
// Life Events replaces AI Copilot as a primary slot (NavigationReview.md
// Phase 1) since logging a real-world event is disproportionately a mobile
// moment, while Copilot today has no integration depending on quick access.
const MOBILE_PRIMARY = ["/app", "/app/life-events", "/app/goals", "/app/family"];
const MOBILE_MORE = [
  "/app/financials",
  "/app/reports",
  "/app/copilot",
  "/app/profile",
  "/app/settings",
];

// Derives the two-letter avatar initials from a display name — same rule
// the shell has always used: first+last word initials, or the first two
// characters of a single-word name.
function computeInitials(name: string): string {
  const trimmed = name.trim();
  const parts = trimmed.split(/\s+/);
  return parts.length >= 2
    ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
    : trimmed.slice(0, 2).toUpperCase() || "?";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  // Phase 0: AppShell is now mounted once by the /app layout route (see
  // app.tsx) instead of once per leaf route, so it can no longer receive
  // the page title as a prop from its own child — each route instead
  // declares it via `staticData.shellTitle` (see router-static-data.d.ts),
  // and the shell reads whichever route is currently deepest-matched.
  const staticTitle = useMatches({
    select: (matches) => matches[matches.length - 1]?.staticData?.shellTitle,
  });
  const [titleOverride, setTitleOverride] = useState<string | null>(null);
  const title = titleOverride ?? staticTitle;
  const navigate = useNavigate();
  // M2.6.1: a single piece of state for every header overlay (palette,
  // notifications, profile menu, mobile "More" sheet) instead of one
  // independent boolean per overlay — structurally guarantees only one can
  // ever be open at a time, rather than relying on each Radix primitive's
  // own default dismiss behavior to coincidentally agree with the others
  // (they didn't: see DependencyValidation_M2.6.1.md #5). See
  // ArchitectureReview_M2.6.1.md for the full reasoning.
  const [activeOverlay, setActiveOverlay] = useState<
    "palette" | "notifications" | "profile" | "more" | null
  >(null);
  const moreRef = useRef<HTMLDivElement>(null);
  const moreActive = MOBILE_MORE.some((to) => pathname.startsWith(to));

  // Phase 2: a single, global ⌘K / Ctrl+K listener, registered once since
  // AppShell itself now mounts once per session (Phase 0) — not once per
  // navigation. Escape-to-close and outside-click are handled by
  // CommandDialog's own underlying Radix Dialog, not hand-built here.
  useEffect(() => {
    function handleShortcut(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setActiveOverlay((v) => (v === "palette" ? null : "palette"));
      }
    }
    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    if (activeOverlay !== "more") return;
    function handleClickOutside(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setActiveOverlay(null);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setActiveOverlay(null);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [activeOverlay]);

  // Phase 0: replaces the previous raw useEffect+promise calls to auth.me()
  // and api.getDashboard() (which re-fired on every AppShell remount) with
  // cached useQuery calls. The ["dashboard"] key intentionally matches the
  // Dashboard route's own query key (app.index.tsx) so the two consumers
  // share one cached request instead of two independent fetches — see
  // ArchitectureReview_Phase0.md §7.
  const { data: currentUser, isError: userError } = useQuery({
    queryKey: ["currentUser"],
    queryFn: () => auth.me(),
    staleTime: 5 * 60_000,
  });
  const { data: dashData } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.getDashboard(),
    staleTime: 60_000,
  });

  // Preserves the exact prior three-state display: "··" while loading,
  // computed initials on success, "?" on error — same as the raw
  // auth.me().then(...).catch(() => setInitials("?")) this replaced.
  const initials = userError
    ? "?"
    : currentUser
      ? computeInitials(currentUser.full_name ?? currentUser.email ?? "")
      : "··";
  const planHealth = dashData?.plan_health_score ?? null;
  const goalCount = dashData?.goal_count ?? 0;

  function handleSignOut() {
    // Best-effort: clear the server-side refresh cookie too, but don't let a
    // network failure block the local sign-out.
    void auth.logout();
    clearAccessToken();
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
            <PlanHealthInfo
              score={planHealth}
              goalCount={goalCount}
              trigger={
                <button
                  type="button"
                  className="m-3 surface-card p-4 text-left w-[calc(100%-1.5rem)] hover:border-border-strong transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    Plan health
                    <Info className="h-3 w-3" aria-hidden="true" />
                  </p>
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
                </button>
              }
            />
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
                <button
                  type="button"
                  onClick={() => setActiveOverlay("palette")}
                  aria-label="Open search"
                  className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted-foreground hover:border-border-strong transition w-9 justify-center md:w-72 md:justify-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <Search className="h-4 w-4 shrink-0" />
                  <span className="hidden md:inline">Search goals, family, schemes…</span>
                  <kbd className="ml-auto hidden md:inline font-mono text-[10px] text-muted-foreground/70">
                    ⌘K
                  </kbd>
                </button>
                <NotificationCenter
                  open={activeOverlay === "notifications"}
                  onOpenChange={(v) => setActiveOverlay(v ? "notifications" : null)}
                />
                <DropdownMenu
                  open={activeOverlay === "profile"}
                  onOpenChange={(v) => setActiveOverlay(v ? "profile" : null)}
                >
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      aria-label="Account menu"
                      className="h-9 w-9 rounded-full bg-gradient-to-br from-primary to-cyan grid place-items-center font-medium text-primary-foreground text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                    >
                      {initials}
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-60">
                    <DropdownMenuLabel className="font-normal">
                      <p className="truncate text-sm font-medium text-foreground">
                        {currentUser?.full_name || "Your account"}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{currentUser?.email}</p>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/app/profile" className="cursor-pointer">
                        <User className="h-4 w-4" />
                        My Profile
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/app/settings" className="cursor-pointer">
                        <SettingsIcon className="h-4 w-4" />
                        Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onSelect={handleSignOut} className="cursor-pointer">
                      <LogOut className="h-4 w-4" />
                      Sign Out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </header>
          <main className="px-4 md:px-8 py-6 md:py-10 pb-24 lg:pb-10">
            <ShellTitleOverrideContext value={setTitleOverride}>
              {children}
            </ShellTitleOverrideContext>
          </main>
        </div>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 border-t border-border bg-background/90 backdrop-blur-xl">
        <div className="grid grid-cols-5 h-16">
          {nav
            .filter((item) => MOBILE_PRIMARY.includes(item.to))
            .map((item) => {
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
                  <span>{item.mobileLabel ?? item.label.split(" ")[0]}</span>
                </Link>
              );
            })}
          <div ref={moreRef} className="relative">
            {activeOverlay === "more" && (
              <div
                role="menu"
                aria-label="More navigation"
                className="absolute bottom-full right-2 mb-2 w-44 rounded-lg border border-border bg-surface shadow-lg overflow-hidden"
              >
                {nav
                  .filter((item) => MOBILE_MORE.includes(item.to))
                  .map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.to}
                        to={item.to}
                        role="menuitem"
                        onClick={() => setActiveOverlay(null)}
                        className="flex items-center gap-2 px-3 py-2.5 text-sm text-foreground hover:bg-accent transition-colors"
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </Link>
                    );
                  })}
              </div>
            )}
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={activeOverlay === "more"}
              aria-label="More navigation"
              onClick={() => setActiveOverlay((v) => (v === "more" ? null : "more"))}
              className={cn(
                "flex h-full w-full flex-col items-center justify-center gap-1 text-[10px] transition-colors",
                moreActive || activeOverlay === "more"
                  ? "text-foreground"
                  : "text-muted-foreground",
              )}
            >
              <MoreHorizontal
                className={cn("h-5 w-5", (moreActive || activeOverlay === "more") && "text-cyan")}
              />
              <span>More</span>
            </button>
          </div>
        </div>
      </nav>

      <GlobalPalette
        open={activeOverlay === "palette"}
        onOpenChange={(v) => setActiveOverlay(v ? "palette" : null)}
      />
    </div>
  );
}
