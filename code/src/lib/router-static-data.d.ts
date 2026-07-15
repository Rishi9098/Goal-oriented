// Module augmentation for TanStack Router's route `staticData` option.
// `shellTitle` is the persistent AppShell header's page-title text — declared
// per-route via `staticData` since AppShell (Phase 0) no longer receives it
// as a prop from a child route (see ArchitectureReview_Phase0.md §4).
import "@tanstack/react-router";

declare module "@tanstack/react-router" {
  interface StaticDataRouteOption {
    shellTitle?: string;
  }
}
