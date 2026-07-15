// Shared, presentation-only helpers for rendering certified Family API data.
// No business logic lives here — relationship_type is an enum the backend
// already assigns; this only maps it to a display label. Used by both
// app.profile.tsx and app.family.tsx to avoid two independent copies drifting
// apart the way the pre-Stabilization-Sprint household summary once did.

const RELATIONSHIP_LABELS: Record<string, string> = {
  self: "You",
  spouse: "Spouse",
  child: "Child",
  parent: "Parent",
  other: "Other",
};

export function relationshipLabel(relationshipType: string): string {
  return RELATIONSHIP_LABELS[relationshipType] ?? relationshipType;
}

const RELATIONSHIP_ICON: Record<string, string> = {
  self: "👤",
  spouse: "💍",
  child: "🧒",
  parent: "🧓",
  other: "👤",
};

export function relationshipIcon(relationshipType: string): string {
  return RELATIONSHIP_ICON[relationshipType] ?? "👤";
}
