import { createContext, use, useLayoutEffect } from "react";

// Phase 0: `staticData.shellTitle` (declared per-route, see
// router-static-data.d.ts) covers every route whose AppShell header title is
// fixed per-route. Exactly one route's title varies at render time instead
// (app.family.add.tsx's title depends on a `?type=` search param, not just
// which route matched) — for that one case, a leaf calls
// `useShellTitle(dynamicTitle)` to override the static value for as long as
// it stays mounted. This is a narrow escape hatch, not a general title API.
// Split into its own file (rather than living in app-shell.tsx) so the
// component file only exports the component — keeps React Fast Refresh happy.
export const ShellTitleOverrideContext = createContext<((title: string | null) => void) | null>(
  null,
);

export function useShellTitle(title: string): void {
  const setOverride = use(ShellTitleOverrideContext);
  useLayoutEffect(() => {
    setOverride?.(title);
    return () => setOverride?.(null);
  }, [setOverride, title]);
}
