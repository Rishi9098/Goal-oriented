import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, Mail } from "lucide-react";
import { auth } from "@/lib/api";

export const Route = createFileRoute("/auth/forgot-password")({
  head: () => ({ meta: [{ title: "Reset password — Northstar" }] }),
  component: ForgotPassword,
});

type State = "idle" | "loading" | "sent" | "error";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<State>("idle");
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setState("loading");
    setErrorMsg(null);
    try {
      const data = await auth.forgotPassword(email);
      setResetToken(data.reset_token ?? null);
      setState("sent");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong.");
      setState("error");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 hero-bg">
      <div className="w-full max-w-sm">
        <Link
          to="/auth/sign-in"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>

        <h1 className="font-display text-3xl tracking-tight">Forgot password</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Enter your email and we'll send a reset link.
        </p>

        {state === "sent" ? (
          <div className="mt-6 space-y-4">
            <div className="rounded-lg border border-success/30 bg-success/10 px-4 py-4 text-sm text-success">
              Check your inbox — a reset link is on its way.
            </div>

            {resetToken && (
              <div className="rounded-lg border border-border bg-surface p-4 text-xs space-y-2">
                <p className="text-muted-foreground font-medium uppercase tracking-widest">
                  Dev mode — reset token
                </p>
                <p className="font-mono break-all text-foreground">{resetToken}</p>
                <Link
                  to="/auth/reset-password"
                  search={{ token: resetToken }}
                  className="inline-flex items-center gap-1 text-cyan hover:underline mt-1"
                >
                  Use this token <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            )}

            <button
              onClick={() => {
                setState("idle");
                setEmail("");
                setResetToken(null);
              }}
              className="text-sm text-muted-foreground hover:text-foreground transition"
            >
              Send to a different email
            </button>
          </div>
        ) : (
          <>
            {state === "error" && errorMsg && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {errorMsg}
              </div>
            )}

            <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
              <label className="block">
                <span className="text-xs text-muted-foreground">Email address</span>
                <div className="mt-1 flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5 focus-within:border-primary transition-colors">
                  <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@domain.com"
                    autoComplete="email"
                    className="bg-transparent outline-none text-sm flex-1"
                  />
                </div>
              </label>

              <button
                type="submit"
                disabled={state === "loading"}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {state === "loading" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Sending…
                  </>
                ) : (
                  <>
                    Send reset link <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
