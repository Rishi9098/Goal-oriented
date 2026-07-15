import { createFileRoute, Outlet } from "@tanstack/react-router";

// Thin layout only — matches the existing app.tsx/app.index.tsx split.
// The real Family Home content lives in app.family.index.tsx; this file's
// only job is to let /app/family/add and /app/family/members/$id render as
// sibling routes under the same path prefix, not get swallowed by a
// non-Outlet parent component.
export const Route = createFileRoute("/app/family")({
  component: () => <Outlet />,
});
