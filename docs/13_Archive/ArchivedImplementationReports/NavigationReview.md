# Navigation Review — Phase 1 (Navigation & Information Architecture)

**Date:** 2026-07-12
**Scope:** Every navigation surface in the authenticated app — desktop sidebar, mobile bottom nav, and the Command Palette (⌘K) — evaluated against one question: *does Life Events appear where a user would expect a first-class workflow to live?*

**Method:** Direct inspection of the current, live code (`app-shell.tsx`, `global-palette.tsx`, every route file), cross-checked against every existing document that already made a navigation decision, so this review extends rather than re-litigates prior work.

---

## 1. Documents read and how this review relates to them

| Document | What it already established | How this review uses it |
|---|---|---|
| `NavigationAudit.md` (2026-07-08) | Route inventory, auth guard, 404/error handling, keyboard gaps — all still correct today. Its claim that ⌘K is "dead, no keyboard shortcut registered" is **stale**: the shortcut is registered and wired in the current code (verified directly in `app-shell.tsx`). | This review does not re-audit routing/guards/404 handling — that ground is already covered and unchanged. It corrects the one stale claim inline rather than silently ignoring it. |
| `GlobalShellArchitecture.md` | Recommended promoting `AppShell` to the `/app` layout route (a "Phase 0" prerequisite) instead of remounting it per leaf route. | **Already implemented** — confirmed directly in `app.tsx` (comment: "Phase 0 — Persistent AppShell Foundation"). Not re-touched here. |
| `FrontendArchitectureUserExperienceBible.md` | Documents the nav as "7-item primary nav... Dashboard/Goals/Family/AI Copilot/Reports/Profile/Settings" and mobile as "4 primary + 3 overflow." | **Stale** — the live nav already has 9 desktop items (Financials and Life Events were added in a later session than this Bible volume was written) and mobile overflow already has 5 items, not 3. This review documents the *current* state and will note the Bible needs a refresh (tracked as an outstanding risk, not fixed here — out of scope for a navigation-only phase). |
| `FamilyPlanningDesign.md` Part 2 | Litigated a specific, documented conflict between its own prose ("Family second") and its own diagram ("Goals before Family") — resolved in code in favor of the diagram, with a comment recording the decision. Also fixed the "5 mobile slots" constraint (4 primary + More). | This review's changes preserve that resolution exactly — Goals stays immediately before Family, and the 5-slot mobile constraint is preserved (membership changes, slot count does not). |
| `ProductDesignAuthorityReview.md` (this session) | Sections 8/9 already identified: Life Events sits mid-list on desktop between two low-engagement modules, is absent from the mobile primary nav (exactly backwards for an "I need to log this right now" feature), is absent from the Command Palette, and AI Copilot outranks both Financials and Life Events in nav position despite having zero integration with either. | This is the primary mandate for this phase's changes — the findings are adopted, not repeated wholesale. |
| ADR-001 / ADR-005 (`ArchitectureDecisionRecordBible.md`) | Goal probability is never recalculated on read; recommendations are never persisted, always computed live. | **Not implicated.** This phase touches zero calculation or recommendation logic — it reorders existing links and adds two entries to a client-side array. Compliance is by construction, not by special handling. |

---

## 2. Current state (verified directly against live code)

**Desktop sidebar** (`app-shell.tsx`, `nav` array), in order:
Dashboard → Goals → Family → **AI Copilot** → **Financials** → **Life Events** → Reports → Profile → Settings.

**Mobile bottom nav** (5 slots total): 4 primary — Dashboard, Goals, Family, **AI Copilot** — plus "More," which contains Reports, Profile, Settings, Financials, **Life Events**.

**Command Palette** (`global-palette.tsx`, `PAGES` array): Dashboard, Goals, Family, AI Copilot, Reports, Profile, Settings, Government Schemes, Family Insurance, Recommendations. **Financials and Life Events are both absent** — pressing ⌘K and typing "life" or "financials" returns nothing, even though both are real, current, primary-nav pages.

## 3. The problem, stated precisely

Life Events is the Life Event Engine's entire product-facing surface — the one workflow purpose-built for "something just happened in my life, let me record it." Today it is:

1. **Sixth of nine items on desktop** — sandwiched between Financials and Reports, the two most utilitarian, least emotionally engaged modules in the product.
2. **Absent from the mobile primary nav entirely**, relegated to a secondary "More" sheet — backwards for a feature whose entire value proposition is capturing a real-world event in the moment, which is disproportionately a mobile use case.
3. **Unreachable by the Command Palette** — a user who has learned to reach for ⌘K (the product's own power-user shortcut) cannot find Life Events through it at all.

Meanwhile **AI Copilot** — a screen with, by direct inspection of its own code, zero awareness of Life Events, Goals changes, or Recommendations (a stateless, generic chat interface) — occupies the fourth position on desktop and one of only four primary mobile slots. Nav position is a promise about importance; right now the promise is backwards.

## 4. Decision

Two changes, both additive/reordering only — no new routes, no new components, no backend change, no calculation touched:

**A. Desktop reorder:** Dashboard → **Life Events** → Goals → Family → Financials → Reports → **AI Copilot** → Profile → Settings.
- Life Events moves to position 2 — directly after the overview, before anything else, satisfying "Life Events must become a first-class workflow."
- Goals immediately precedes Family, preserving `FamilyPlanningDesign.md`'s already-litigated resolution untouched.
- AI Copilot moves to position 7 (below Reports), reflecting its current, verified lack of integration with the rest of the product — not a demotion of the feature's *future* importance, but an honest reflection of *today's* level of integration. Phase 2 of this mission (Life Event ↔ Product Integration) is expected to change this calculus; nav position can be revisited then.

**B. Mobile primary swap:** Dashboard, Goals, Family, **Life Events** replace Dashboard, Goals, Family, **AI Copilot** as the four primary slots. AI Copilot moves into "More" alongside Reports/Profile/Settings/Financials. Slot count is unchanged (still 4 primary + "More" = 5), so no layout/grid change is required — only array membership changes.

**C. Command Palette fix:** add **Life Events** and **Financials** to `PAGES` in `global-palette.tsx`, matching every other real, current page. This is a direct bug fix (the palette's own stated purpose is "every navigable page," and it was silently missing two) discovered in the course of this review, not a new feature.

## 5. Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| Also reorder Family relative to Goals | Out of scope — that specific ordering was already deliberately litigated and resolved in `FamilyPlanningDesign.md`/code comments; revisiting it belongs to a dedicated Family IA review, not this phase. |
| Expand mobile primary nav to 6 slots to fit Life Events without removing anything | Would violate the documented, intentional "5 mobile slots" constraint (`FamilyPlanningDesign.md` Part 2, restated in the current code comment) for no corresponding benefit — a straight swap achieves the same goal with zero layout risk. |
| Remove AI Copilot from primary nav entirely (desktop and mobile) | Too aggressive for a navigation-only phase — Copilot remains one tap away in both contexts; removing it outright is a product decision beyond "reorder for information architecture," and premature before Phase 2 determines whether it becomes genuinely integrated. |
| Leave Command Palette untouched (defer to a future "Search" phase) | The gap was discovered directly in the course of this review and is a one-line, zero-risk, same-file fix directly relevant to "does Life Events appear where a user would expect it" — deferring a fix already in hand would be inconsistent with the mission's own "improve everything already built" instruction. |

## 6. What this phase explicitly does not do

- Does not touch the Dashboard, Reports, Recommendations, Family, or AI Copilot *content* — that is Phase 2 (Life Event Product Integration).
- Does not touch Plan Health, microcopy, automation, consistency, accessibility, or performance — each has its own later phase.
- Does not add breadcrumbs, fix the landing page's dead links, or address the keyboard-focus gaps `NavigationAudit.md` already found on Goals/`app.family.add.tsx` — those are pre-existing, already-documented, unrelated findings, not part of this mission's Phase 1 mandate (Life Events IA specifically).
- Does not refresh `FrontendArchitectureUserExperienceBible.md`'s stale nav-count prose — flagged as an outstanding risk (Section 7 of the implementation report) for a documentation-maintenance pass, not silently rewritten as a side effect of a navigation phase.
