import { createFileRoute, Outlet, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

export const Route = createFileRoute("/app")({
  beforeLoad: () => {
    // Client-side navigation guard — localStorage only available in browser
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("ns_access_token");
    if (!token) {
      throw redirect({ to: "/auth/sign-in" });
    }
  },
  component: AppLayout,
});

function AppLayout() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Re-check on every mount, including after SSR hydration
    const token = localStorage.getItem("ns_access_token");
    if (!token) {
      navigate({ to: "/auth/sign-in", replace: true });
    } else {
      setReady(true);
    }
  }, [navigate]);

  if (!ready) return null;
  // AppShell mounts once here (Phase 0 — Persistent AppShell Foundation) and
  // stays mounted while <Outlet/> swaps leaf content between navigations —
  // see ArchitectureReview_Phase0.md. Previously each leaf route rendered
  // its own <AppShell>, causing a full remount (and a fresh auth.me()/
  // getDashboard() fetch) on every navigation — measured in
  // PerformanceBaseline_Phase0.md.
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
