import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Target,
  Users,
  Sparkles,
  BarChart3,
  Settings as SettingsIcon,
  User,
  Landmark,
  ShieldCheck,
  Plus,
  UserPlus,
  Clock,
  History,
  Wallet,
} from "lucide-react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command";
import { DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { auth, api } from "@/lib/api";

// Every navigable page named in this phase's Search Scope Review, whether
// or not it also appears in the sidebar's own `nav` array (app-shell.tsx) —
// Schemes, Insurance, and Recommendations are reached today only via
// in-page links, not the sidebar, so they're listed here explicitly rather
// than derived from `nav`.
//
// Financials and Life Events were added to the sidebar after this list was
// last written and had silently fallen out of sync (NavigationReview.md
// Phase 1) — both are real, current, primary-nav pages and belong here for
// the same reason every other entry does.
const PAGES = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/life-events", label: "Life Events", icon: History },
  { to: "/app/goals", label: "Goals", icon: Target },
  { to: "/app/family", label: "Family", icon: Users },
  { to: "/app/financials", label: "Financials", icon: Wallet },
  { to: "/app/reports", label: "Reports", icon: BarChart3 },
  { to: "/app/copilot", label: "AI Copilot", icon: Sparkles },
  { to: "/app/profile", label: "Profile", icon: User },
  { to: "/app/settings", label: "Settings", icon: SettingsIcon },
  { to: "/app/family/schemes", label: "Government Schemes", icon: Landmark },
  { to: "/app/family/insurance", label: "Family Insurance", icon: ShieldCheck },
  { to: "/app/family/recommendations", label: "Recommendations", icon: Sparkles },
] as const;

// Both actions reuse an already-existing, already-working destination.
// "Create Goal" relies on app.goals.tsx's `?new=true` search param (added
// in this same phase) to open the page's existing "New goal" modal on
// load — the modal and form themselves are untouched, pre-existing code.
const QUICK_ACTIONS = [
  { to: "/app/goals", search: { new: true }, label: "Create Goal", icon: Plus },
  {
    to: "/app/family/add",
    search: { type: "other" as const },
    label: "Add Family Member",
    icon: UserPlus,
  },
];

const RECENT_SEARCHES_KEY_PREFIX = "ns_recent_searches_";
const MAX_RECENT = 5;

function loadRecent(userId: string | undefined): string[] {
  if (!userId || typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCHES_KEY_PREFIX + userId);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function saveRecent(userId: string | undefined, query: string): void {
  if (!userId || !query.trim() || typeof window === "undefined") return;
  const key = RECENT_SEARCHES_KEY_PREFIX + userId;
  const existing = loadRecent(userId).filter((q) => q !== query);
  const next = [query, ...existing].slice(0, MAX_RECENT);
  window.localStorage.setItem(key, JSON.stringify(next));
}

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

export function GlobalPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState("");
  const [everOpened, setEverOpened] = useState(false);
  const [recent, setRecent] = useState<string[]>([]);

  // Reads the same ["currentUser"] cache AppShell already populates —
  // costs nothing extra (React Query dedupes by key), and gives this
  // component the user id it needs to scope recent-search storage.
  const { data: currentUser } = useQuery({
    queryKey: ["currentUser"],
    queryFn: () => auth.me(),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (open) {
      setEverOpened(true);
      setRecent(loadRecent(currentUser?.id));
    } else {
      setInputValue("");
    }
  }, [open, currentUser?.id]);

  // Lazy: these never fetch until the palette has been opened at least
  // once (ArchitectureReview_Phase2.md §3/§9). Query keys intentionally
  // match existing usages elsewhere so the cache is shared, not duplicated.
  const { data: goals, isLoading: goalsLoading } = useQuery({
    queryKey: ["goals"],
    queryFn: () => api.getGoals(),
    enabled: everOpened,
  });
  const { data: familyHome, isLoading: familyLoading } = useQuery({
    queryKey: ["family-home"],
    queryFn: () => api.getFamilyHome(),
    enabled: everOpened,
  });
  const { data: schemes, isLoading: schemesLoading } = useQuery({
    queryKey: ["family-schemes"],
    queryFn: () => api.getFamilySchemes(),
    enabled: everOpened,
  });
  const { data: insurance, isLoading: insuranceLoading } = useQuery({
    queryKey: ["family-insurance"],
    queryFn: () => api.getFamilyInsurance(),
    enabled: everOpened,
  });

  function go(opts: {
    to: string;
    search?: Record<string, unknown>;
    params?: Record<string, unknown>;
  }) {
    if (inputValue.trim()) saveRecent(currentUser?.id, inputValue.trim());
    onOpenChange(false);
    void navigate(opts as never);
  }

  const schemeItems = [
    ...(schemes?.eligible ?? []),
    ...(schemes?.potentially_eligible ?? []),
    ...(schemes?.not_eligible ?? []),
  ];

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <DialogTitle className="sr-only">Command palette</DialogTitle>
      <DialogDescription className="sr-only">
        Search goals, family members, government schemes, and insurance policies, or jump to any
        page.
      </DialogDescription>
      <CommandInput
        placeholder="Search goals, family, schemes, insurance…"
        value={inputValue}
        onValueChange={setInputValue}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {!inputValue && recent.length > 0 && (
          <>
            <CommandGroup heading="Recent">
              {recent.map((q) => (
                <CommandItem key={q} value={q} onSelect={() => setInputValue(q)}>
                  <Clock className="h-4 w-4" />
                  {q}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        <CommandGroup heading="Pages">
          {PAGES.map((page) => {
            const Icon = page.icon;
            return (
              <CommandItem key={page.to} value={page.label} onSelect={() => go({ to: page.to })}>
                <Icon className="h-4 w-4" />
                {page.label}
              </CommandItem>
            );
          })}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Quick Actions">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <CommandItem
                key={action.label}
                value={action.label}
                onSelect={() => go({ to: action.to, search: action.search })}
              >
                <Icon className="h-4 w-4" />
                {action.label}
              </CommandItem>
            );
          })}
        </CommandGroup>

        {!!inputValue && (goalsLoading || (goals && goals.length > 0)) && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Goals">
              {goalsLoading ? (
                <CommandItem disabled value="__loading_goals">
                  Loading goals…
                </CommandItem>
              ) : (
                goals?.map((goal) => (
                  <CommandItem
                    key={goal.id}
                    value={`${goal.name} ${goal.category}`}
                    onSelect={() => go({ to: "/app/goals" })}
                  >
                    <Target className="h-4 w-4" />
                    <span className="flex-1 truncate">{goal.name}</span>
                    <span className="text-xs text-muted-foreground">view in Goals</span>
                  </CommandItem>
                ))
              )}
            </CommandGroup>
          </>
        )}

        {!!inputValue && (familyLoading || (familyHome && familyHome.members.length > 0)) && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Family Members">
              {familyLoading ? (
                <CommandItem disabled value="__loading_family">
                  Loading family members…
                </CommandItem>
              ) : (
                familyHome?.members
                  .filter((m) => m.relationship_type !== "self")
                  .map((member) => (
                    <CommandItem
                      key={member.id}
                      value={`${member.name ?? member.relationship_type} ${member.relationship_type}`}
                      onSelect={() =>
                        go({ to: "/app/family/members/$id", params: { id: member.id } })
                      }
                    >
                      <Users className="h-4 w-4" />
                      <span className="flex-1 truncate">
                        {member.name ?? `Unnamed ${member.relationship_type}`}
                      </span>
                      <span className="text-xs text-muted-foreground capitalize">
                        {member.relationship_type}
                      </span>
                    </CommandItem>
                  ))
              )}
            </CommandGroup>
          </>
        )}

        {!!inputValue && (schemesLoading || schemeItems.length > 0) && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Government Schemes">
              {schemesLoading ? (
                <CommandItem disabled value="__loading_schemes">
                  Loading schemes…
                </CommandItem>
              ) : (
                schemeItems.map((item, i) => (
                  <CommandItem
                    key={`${item.scheme_code}-${i}`}
                    value={`${item.scheme_name} ${item.member_name ?? ""}`}
                    onSelect={() => go({ to: "/app/family/schemes" })}
                  >
                    <Landmark className="h-4 w-4" />
                    <span className="flex-1 truncate">{item.scheme_name}</span>
                    <span className="text-xs text-muted-foreground">view in Schemes</span>
                  </CommandItem>
                ))
              )}
            </CommandGroup>
          </>
        )}

        {!!inputValue && (insuranceLoading || (insurance && insurance.policies.length > 0)) && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Family Insurance">
              {insuranceLoading ? (
                <CommandItem disabled value="__loading_insurance">
                  Loading insurance…
                </CommandItem>
              ) : (
                insurance?.policies.map((policy) => (
                  <CommandItem
                    key={policy.id}
                    value={`${policy.policy_type} ${policy.insurer ?? ""}`}
                    onSelect={() => go({ to: "/app/family/insurance" })}
                  >
                    <ShieldCheck className="h-4 w-4" />
                    <span className="flex-1 truncate capitalize">
                      {policy.policy_type.replace(/_/g, " ")}
                      {policy.insurer ? ` — ${policy.insurer}` : ""}
                    </span>
                    <span className="text-xs text-muted-foreground">view in Insurance</span>
                  </CommandItem>
                ))
              )}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
