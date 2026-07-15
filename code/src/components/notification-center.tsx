import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, X, Loader2, AlertCircle } from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { api, type NotificationItem } from "@/lib/api";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 120_000;

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

type RowProps = {
  item: NotificationItem;
  onOpen: (item: NotificationItem) => void;
  onDismiss: (item: NotificationItem) => void;
};

function NotificationRow({ item, onOpen, onDismiss }: RowProps) {
  return (
    <div
      className={cn(
        "group relative flex gap-3 rounded-lg px-3 py-2.5 text-left transition hover:bg-accent",
        item.state === "unread" && "bg-surface",
      )}
    >
      <button
        type="button"
        onClick={() => onOpen(item)}
        className="flex-1 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
      >
        <div className="flex items-center gap-2">
          {item.state === "unread" && (
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" aria-hidden="true" />
          )}
          <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
        </div>
        <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{item.body}</p>
      </button>
      <button
        type="button"
        onClick={() => onDismiss(item)}
        aria-label={`Dismiss: ${item.title}`}
        className="shrink-0 self-start rounded p-1 text-muted-foreground opacity-0 transition hover:bg-border/50 hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

// M2.6.1: open state is now controlled by AppShell's single shared
// activeOverlay variable (see ArchitectureReview_M2.6.1.md) instead of a
// local useState, so the palette and profile menu can correctly close this
// popover, and vice versa. Everything else (queries, mutations, rendering)
// is unchanged.
export function NotificationCenter({ open, onOpenChange }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.getNotifications(),
    refetchInterval: POLL_INTERVAL_MS,
    staleTime: 30_000,
  });

  const readMutation = useMutation({
    mutationFn: (item: NotificationItem) => api.markNotificationRead(item.source, item.id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const dismissMutation = useMutation({
    mutationFn: (item: NotificationItem) => api.dismissNotification(item.source, item.id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  function handleOpen(item: NotificationItem) {
    if (item.state === "unread") readMutation.mutate(item);
    onOpenChange(false);
    void navigate({ to: item.action_path });
  }

  function handleDismiss(item: NotificationItem) {
    dismissMutation.mutate(item);
  }

  const items = data?.items ?? [];
  const unreadCount = data?.unread_count ?? 0;
  const todayItems = items.filter((i) => isToday(i.created_at));
  const earlierItems = items.filter((i) => !isToday(i.created_at));

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : "Notifications"}
          className="relative rounded-lg border border-border bg-surface p-2 hover:bg-accent transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span
              className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-cyan px-1 text-[10px] font-medium text-background"
              aria-hidden="true"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <p className="text-sm font-medium text-foreground">Notifications</p>
          {unreadCount > 0 && <p className="text-xs text-muted-foreground">{unreadCount} unread</p>}
        </div>

        <div className="max-h-96 overflow-y-auto p-1.5">
          {isLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading…
            </div>
          )}

          {isError && !isLoading && (
            <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-5 w-5" />
              Couldn't load notifications. Try again shortly.
            </div>
          )}

          {!isLoading && !isError && items.length === 0 && (
            <div className="flex flex-col items-center gap-1 py-8 text-center">
              <p className="text-sm font-medium text-foreground">You're all caught up</p>
              <p className="text-xs text-muted-foreground">
                New goal, insurance, scheme, and life event updates will show up here.
              </p>
            </div>
          )}

          {!isLoading && !isError && todayItems.length > 0 && (
            <div className="mb-1">
              <p className="px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Today
              </p>
              {todayItems.map((item) => (
                <NotificationRow
                  key={item.id}
                  item={item}
                  onOpen={handleOpen}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          )}

          {!isLoading && !isError && earlierItems.length > 0 && (
            <div>
              <p className="px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Earlier
              </p>
              {earlierItems.map((item) => (
                <NotificationRow
                  key={item.id}
                  item={item}
                  onOpen={handleOpen}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
