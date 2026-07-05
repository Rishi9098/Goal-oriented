import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Bell, Check, Eye, EyeOff, KeyRound, Loader2, Link2, Trash2 } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { auth, clearAccessToken } from "@/lib/api";

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — Northstar" }] }),
  component: Settings,
});

type PwStatus = "idle" | "saving" | "saved" | "error";

function Settings() {
  return (
    <AppShell title="Settings">
      <div className="max-w-2xl space-y-5">
        <ChangePasswordSection />
        <ComingSoonCard
          icon={Bell}
          title="Notifications"
          description="Weekly digest and plan drift alerts — coming in a future release."
        />
        <ComingSoonCard
          icon={Link2}
          title="Linked accounts"
          description="Institution connections via Plaid — coming in a future release."
        />
        <DeleteAccountSection />
      </div>
    </AppShell>
  );
}

function ChangePasswordSection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [status, setStatus] = useState<PwStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const mismatch = next.length > 0 && confirm.length > 0 && next !== confirm;
  const canSubmit =
    current.length >= 8 && next.length >= 8 && next === confirm && status !== "saving";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setStatus("saving");
    setErrorMsg("");
    try {
      await auth.changePassword(current, next);
      setStatus("saved");
      setCurrent("");
      setNext("");
      setConfirm("");
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update password");
      setStatus("error");
    }
  };

  return (
    <section className="surface-card p-6 space-y-5">
      <div className="flex items-center gap-2.5">
        <KeyRound className="h-4 w-4 text-muted-foreground" />
        <p className="font-display text-sm uppercase tracking-widest text-muted-foreground">
          Security
        </p>
        {status === "saved" && (
          <span className="ml-auto flex items-center gap-1 text-xs text-emerald-400">
            <Check className="h-3.5 w-3.5" /> Password updated
          </span>
        )}
        {status === "error" && (
          <span className="ml-auto text-xs text-red-400">{errorMsg}</span>
        )}
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <PasswordField
          label="Current password"
          value={current}
          onChange={setCurrent}
          show={showCurrent}
          onToggleShow={() => setShowCurrent((v) => !v)}
          autoComplete="current-password"
        />
        <PasswordField
          label="New password"
          value={next}
          onChange={setNext}
          show={showNext}
          onToggleShow={() => setShowNext((v) => !v)}
          autoComplete="new-password"
          hint="Minimum 8 characters"
        />
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Confirm new password
          </label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            className={`field-input ${mismatch ? "border-red-500/60" : ""}`}
            placeholder="Repeat new password"
          />
          {mismatch && (
            <p className="text-xs text-red-400">Passwords do not match</p>
          )}
        </div>

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={!canSubmit}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {status === "saving" ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
              </>
            ) : (
              "Update password"
            )}
          </button>
        </div>
      </form>
    </section>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  show,
  onToggleShow,
  autoComplete,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggleShow: () => void;
  autoComplete: string;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          className="field-input pr-10"
          placeholder="••••••••"
        />
        <button
          type="button"
          onClick={onToggleShow}
          tabIndex={-1}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
          aria-label={show ? "Hide password" : "Show password"}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function ComingSoonCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="surface-card p-5 flex items-start gap-4 opacity-60">
      <div className="mt-0.5 rounded-md bg-surface-elevated p-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div>
        <p className="font-medium text-sm">{title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      <span className="ml-auto shrink-0 text-xs text-muted-foreground/60 border border-border px-2 py-0.5 rounded-full">
        Coming soon
      </span>
    </div>
  );
}

function DeleteAccountSection() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<"idle" | "confirm" | "deleting">("idle");
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");

  const handleDelete = async () => {
    if (typed !== "DELETE") return;
    setPhase("deleting");
    setError("");
    try {
      await auth.deleteAccount();
      await auth.logout();
      clearAccessToken();
      await navigate({ to: "/auth/sign-in" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete account");
      setPhase("confirm");
    }
  };

  return (
    <section className="surface-card p-6 space-y-4 border-red-500/20">
      <div className="flex items-center gap-2.5">
        <Trash2 className="h-4 w-4 text-red-400" />
        <p className="font-display text-sm uppercase tracking-widest text-red-400/80">
          Danger zone
        </p>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium text-sm">Delete account</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Permanently deactivates your account. Your data will not be recoverable.
          </p>
        </div>
        {phase === "idle" && (
          <button
            onClick={() => setPhase("confirm")}
            className="shrink-0 rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:border-red-500/60 transition"
          >
            Delete account
          </button>
        )}
      </div>

      {phase !== "idle" && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 space-y-3">
          <p className="text-sm text-red-300">
            Type <strong className="font-mono">DELETE</strong> to confirm account deletion.
          </p>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="DELETE"
            className="field-input font-mono border-red-500/40 focus:border-red-500"
            autoFocus
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => {
                setPhase("idle");
                setTyped("");
                setError("");
              }}
              disabled={phase === "deleting"}
              className="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition disabled:opacity-40"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={typed !== "DELETE" || phase === "deleting"}
              className="flex items-center gap-1.5 rounded-lg bg-red-500/20 border border-red-500/40 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {phase === "deleting" ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Deleting…
                </>
              ) : (
                "Confirm deletion"
              )}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
