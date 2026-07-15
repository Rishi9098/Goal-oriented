# Global Shell Technical Debt — Certification

**Date:** 2026-07-08
**Scope:** cosmetic issues, known limitations, and future improvements only. No redesigns recommended, per instruction.

---

## The certification condition (see `GlobalShellCertification.md` Review 1/10)

**Profile Menu doesn't yield to the Command Palette.** Opening the profile dropdown, then invoking ⌘K, leaves both overlays visible simultaneously. Small, targeted fix: have the palette's open-handler explicitly close the profile dropdown (and vice versa) rather than relying on each Radix primitive's own default dismiss behavior. Not a redesign — a few lines coordinating two already-existing pieces of local state.

## Pre-existing, non-shell caching gap

`app.goals.tsx` and `app.profile.tsx` fetch data via raw `useEffect`/`Promise.all` rather than `useQuery`, so they never share the cache keys (`["goals"]`, `["currentUser"]`, `["family-home"]`) the shell's own components (`AppShell`, `GlobalPalette`) already use. Consequence: visiting either page always issues a fresh network call, and neither page benefits from — nor populates — the shared cache the rest of the app relies on. This predates the Global Shell work (Phase 2's `DependencyValidation_Phase2.md` already flagged the Goals-page half of this) and wasn't in scope for any of the four phases to fix. Recommended follow-up, not urgent: migrate both to `useQuery` with the existing keys.

## Known limitations carried forward from individual phases (not re-litigated, just indexed here for completeness)

- **Search (Phase 2):** selecting a specific Goal, Government Scheme, or Insurance Policy result navigates to that entity's list page, not a deep-linked detail view — no such URL-addressable view exists for any of the three today. Family Member results are the one exception (`/app/family/members/$id` already exists).
- **Notifications (Phase 3):** "Insurance" and "Schemes" notification identity is keyed by subject *name*, not member ID, since neither `InsuranceRecommendation` nor `SchemeEligibilityItem` carries an ID — a household member rename would produce a "new" notification for an unchanged underlying fact. All four "standing fact" notification sources (Insurance, Schemes, Goal-at-risk, Goal-completed) dedupe by current-fact identity, not by discrete state-transition events, so a dismissed notification stays dismissed even if the underlying condition transiently resolves and reoccurs.
- **Notifications (Phase 3, deliberately deferred, not a gap):** "Goal probability changed" was never built — it would require new state (a last-notified-probability per goal) that the other four sources don't need, and this phase's instructions explicitly protected the Goal model/dashboard from redesign.
- **Global Shell architecture (this certification):** the originally-reviewed `GlobalShellArchitecture.md` §4 called for one shared `GlobalShellProvider` with an explicit mutual-exclusion rule. What was actually built instead is four independently-stateful overlays that happen to coordinate correctly in most cases via each Radix primitive's own default dismiss behavior — which is *not* the same guarantee as an explicit rule, as the one certification condition demonstrates. If a fifth overlay-type feature is ever added to the header, this is worth revisiting rather than assuming the next Radix primitive will also cooperate by luck.

## Cosmetic-only observations

- The notification dismiss "×" only visually reveals on hover (desktop) — present and tappable on touch throughout, just not visually emphasized until touched. Not a defect, a minor discoverability nicety that could be improved with a persistent, lower-opacity affordance if ever revisited.
- No item in this list requires a redesign of the recommendation engine, the dashboard, or the notification model — every entry here is a small, targeted, well-understood fix or a deliberately-scoped-out feature, consistent with this milestone's own discipline throughout Phases 0-3.
