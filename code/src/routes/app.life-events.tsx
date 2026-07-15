import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CalendarClock, Loader2, Plus, RotateCcw, Undo2 } from "lucide-react";
import { api } from "@/lib/api";
import type { LifeEventRecord, UndoConflict } from "@/lib/api";
import {
  findLifeEventType,
  LIFE_EVENT_TYPES,
  summarizeAffectedAreas,
  undoConflictSentence,
} from "@/lib/life-events";
import { RecordLifeEventDialog } from "@/components/life-events/RecordLifeEventDialog";

export const Route = createFileRoute("/app/life-events")({
  head: () => ({ meta: [{ title: "Life Events — Northstar" }] }),
  staticData: { shellTitle: "Life Events" },
  component: LifeEventsPage,
});

const PAGE_SIZE = 20;

type UndoState =
  | { status: "idle" }
  | { status: "working" }
  | { status: "blocked"; conflicts: UndoConflict[] }
  | { status: "error"; message: string };

function eventLabel(eventType: string): string {
  return findLifeEventType(eventType)?.label ?? eventType;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function StatusPill({ event }: { event: LifeEventRecord }) {
  return event.status === "applied" ? (
    <span className="px-2 py-0.5 rounded-full bg-success/15 text-success text-xs shrink-0">
      Recorded
    </span>
  ) : (
    <span className="px-2 py-0.5 rounded-full bg-muted text-muted-foreground text-xs shrink-0">
      Reversed
    </span>
  );
}

function LifeEventRow({
  event,
  onUndone,
}: {
  event: LifeEventRecord;
  onUndone: (updated: LifeEventRecord) => void;
}) {
  const [undoState, setUndoState] = useState<UndoState>({ status: "idle" });

  async function performUndo(force: boolean) {
    setUndoState({ status: "working" });
    try {
      const result = await api.undoLifeEvent(event.id, force);
      if (result.blocked) {
        setUndoState({ status: "blocked", conflicts: result.conflicts });
        return;
      }
      setUndoState({ status: "idle" });
      onUndone({ ...event, status: "undone", undone_at: new Date().toISOString() });
    } catch (err) {
      setUndoState({
        status: "error",
        message: err instanceof Error ? err.message : "Undo failed.",
      });
    }
  }

  return (
    <div className="px-6 py-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{eventLabel(event.event_type)}</p>
            <StatusPill event={event} />
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {formatDate(event.occurred_on)} · Updated{" "}
            {summarizeAffectedAreas(event.effects.map((e) => e.entity_table))}
            {event.notes && ` · ${event.notes}`}
          </p>
        </div>
        {event.status === "applied" && (
          <button
            type="button"
            onClick={() => performUndo(false)}
            disabled={undoState.status === "working"}
            className="inline-flex items-center gap-1.5 shrink-0 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs hover:border-border-strong hover:bg-accent/50 transition-colors disabled:opacity-50"
          >
            {undoState.status === "working" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Undo2 className="h-3.5 w-3.5" />
            )}
            Undo
          </button>
        )}
      </div>

      {undoState.status === "blocked" && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-xs space-y-2">
          <p className="flex items-center gap-1.5 text-warning">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            This can't be undone cleanly — some of what it changed has since changed again:
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
            {undoState.conflicts.map((c) => (
              <li key={c.effect_id}>{undoConflictSentence(c.entity_table, c.reason)}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => performUndo(true)}
            className="inline-flex items-center gap-1.5 text-warning hover:underline"
          >
            <RotateCcw className="h-3 w-3" /> Undo anyway, discarding those later changes too
          </button>
        </div>
      )}
      {undoState.status === "error" && <p className="text-xs text-red-400">{undoState.message}</p>}
    </div>
  );
}

function LifeEventsPage() {
  const [events, setEvents] = useState<LifeEventRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  async function loadPage(offset: number, append: boolean) {
    if (append) setLoading(true);
    setLoadError(null);
    try {
      const result = await api.getLifeEvents({
        event_type: typeFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setEvents((prev) => (append ? [...prev, ...result.items] : result.items));
      setTotal(result.total);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load life events.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    loadPage(0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refetch only when the type filter itself changes
  }, [typeFilter]);

  function handleRecorded(event: LifeEventRecord) {
    setEvents((prev) => [event, ...prev]);
    setTotal((t) => t + 1);
    setDialogOpen(false);
  }

  function handleUndone(updated: LifeEventRecord) {
    setEvents((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 w-full md:w-72">
            <CalendarClock className="h-4 w-4 text-muted-foreground shrink-0" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-transparent outline-none text-sm flex-1"
            >
              <option value="">All event types</option>
              {LIFE_EVENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => setDialogOpen(true)}
            className="md:ml-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-primary to-cyan text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
          >
            <Plus className="h-4 w-4" /> Record life event
          </button>
        </div>

        <div className="surface-card overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center gap-2">
            <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
              History
            </p>
            {total > 0 && (
              <span className="text-xs text-muted-foreground">
                ({events.length} of {total})
              </span>
            )}
          </div>

          {loadError && (
            <div className="px-6 py-6 flex items-center gap-2 text-sm text-red-400 bg-red-500/5">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {loadError}
            </div>
          )}

          {!loadError && loading && events.length === 0 && (
            <div className="divide-y divide-border">
              {[1, 2, 3].map((i) => (
                <div key={i} className="px-6 py-4 h-16 animate-pulse bg-surface/40" />
              ))}
            </div>
          )}

          {!loadError && !loading && events.length === 0 && (
            <div className="px-6 py-10 text-center text-sm text-muted-foreground">
              No life events recorded yet. Use "Record life event" to get started.
            </div>
          )}

          <AnimatePresence initial={false}>
            <div className="divide-y divide-border">
              {events.map((event) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <LifeEventRow event={event} onUndone={handleUndone} />
                </motion.div>
              ))}
            </div>
          </AnimatePresence>

          {!loadError && events.length < total && (
            <div className="px-6 py-4 border-t border-border">
              <button
                type="button"
                onClick={() => loadPage(events.length, true)}
                disabled={loading}
                className="text-sm text-primary hover:underline disabled:opacity-50"
              >
                {loading ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {dialogOpen && (
          <RecordLifeEventDialog onClose={() => setDialogOpen(false)} onRecorded={handleRecorded} />
        )}
      </AnimatePresence>
    </>
  );
}
