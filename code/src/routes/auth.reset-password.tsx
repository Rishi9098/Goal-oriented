import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { ArrowLeft, CheckCircle2, Eye, EyeOff, Loader2, Lock } from "lucide-react";
import { auth } from "@/lib/api";

const searchSchema = z.object({ token: z.string().optional() });

export const Route = createFileRoute("/auth/reset-password")({
  head: () => ({ meta: [{ title: "Set new password — Northstar" }] }),
  validateSearch: searchSchema,
  component: ResetPassword,
});

type State = "idle" | "loading" | "done" | "error";

function ResetPassword() {
  const { token: tokenFromUrl } = Route.useSearch();
  const navigate = useNavigate();
  const [token, setToken] = useState(tokenFromUrl ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [state, setState] = useState<State>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mismatch = confirm.length > 0 && password !== confirm;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mismatch || password.length < 8) return;
    setState("loading");
    setErrorMsg(null);
    try {
      await auth.resetPassword(token, password);
      setState("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Reset failed. The token may have expired.");
      setState("error");
    }
  };

  if (state === "done") {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 hero-bg">
        <div className="w-full max-w-sm text-center space-y-4">
          <CheckCircle2 className="h-12 w-12 text-success mx-auto" />
          <h1 className="font-display text-2xl tracking-tight">Password updated</h1>
          <p className="text-sm text-muted-foreground">
            Your password has been changed. You can now sign in with the new password.
          </p>
          <button
            onClick={() => navigate({ to: "/auth/sign-in" })}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition"
          >
            Go to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 hero-bg">
      <div className="w-full max-w-sm">
        <Link
          to="/auth/sign-in"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>

        <h1 className="font-display text-3xl tracking-tight">Set new password</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Choose a strong password of at least 8 characters.
        </p>

        {state === "error" && errorMsg && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
          {!tokenFromUrl && (
            <label className="block">
              <span className="text-xs text-muted-foreground">Reset token</span>
              <input
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste reset token here"
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary font-mono"
              />
            </label>
          )}

          <label className="block">
            <span className="text-xs text-muted-foreground">New password</span>
            <div className="mt-1 flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5 focus-within:border-primary transition-colors">
              <Lock className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                type={showPw ? "text" : "password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 characters"
                autoComplete="new-password"
                className="bg-transparent outline-none text-sm flex-1"
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="text-muted-foreground hover:text-foreground transition"
                tabIndex={-1}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          <label className="block">
            <span className="text-xs text-muted-foreground">Confirm password</span>
            <div className={`mt-1 flex items-center gap-2 rounded-lg border bg-surface px-3 py-2.5 focus-within:border-primary transition-colors ${mismatch ? "border-destructive" : "border-border"}`}>
              <Lock className="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                type={showPw ? "text" : "password"}
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat password"
                autoComplete="new-password"
                className="bg-transparent outline-none text-sm flex-1"
              />
            </div>
            {mismatch && (
              <p className="mt-1 text-xs text-destructive">Passwords don't match</p>
            )}
          </label>

          <button
            type="submit"
            disabled={state === "loading" || mismatch || !password || !token}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {state === "loading" ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Updating…</>
            ) : (
              "Update password"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
