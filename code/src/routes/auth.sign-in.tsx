import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";
import { auth, setTokens } from "@/lib/api";

export const Route = createFileRoute("/auth/sign-in")({
  head: () => ({ meta: [{ title: "Sign in — Northstar" }] }),
  component: SignIn,
});

function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await auth.login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate({ to: "/app" });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Invalid email or password."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 hero-bg">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 border-r border-border">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-cyan shadow-glow" />
          <span className="font-display text-lg">Northstar</span>
        </Link>
        <div>
          <p className="font-display text-3xl tracking-tight max-w-md">
            "The first tool that made our family's plan feel real — and
            actionable every month."
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            Eliza R. — early customer
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          SOC 2 Type II · AES-256 · read-only linking
        </div>
      </div>

      {/* Right panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h1 className="font-display text-3xl tracking-tight">Welcome back</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to keep your plan on track.
          </p>

          {error && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
            {/* Email */}
            <label className="block">
              <span className="text-xs text-muted-foreground">Email</span>
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

            {/* Password */}
            <label className="block">
              <span className="text-xs text-muted-foreground">Password</span>
              <div className="mt-1 flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5 focus-within:border-primary transition-colors">
                <Lock className="h-4 w-4 text-muted-foreground shrink-0" />
                <input
                  type={showPw ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="bg-transparent outline-none text-sm flex-1"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-glow hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Signing in…
                </>
              ) : (
                <>
                  Sign in <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <div className="text-right">
              <Link
                to="/auth/forgot-password"
                className="text-xs text-muted-foreground hover:text-foreground transition"
              >
                Forgot password?
              </Link>
            </div>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            or
            <div className="h-px flex-1 bg-border" />
          </div>

          <p className="text-sm text-muted-foreground text-center">
            New here?{" "}
            <Link to="/onboarding" className="text-cyan hover:underline">
              Create a free account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
