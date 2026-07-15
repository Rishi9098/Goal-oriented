# Architecture Decision Records

**Status:** Canonical · **Last verified against code:** 2026-07-10, cross-checked 2026-07-13
**Supersedes:** `ArchitectureDecisionRecordBible.md` (archived), `ArchitectureDecisionRecord.md` (the original standalone ADR-001 document — its content is fully preserved below, its stale "Proposed" status field corrected here per the note in ADR-001 itself).
**Rule, honored throughout this document:** every ADR decision below is preserved verbatim from its source — no decision has been reworded, softened, or reversed. Where a decision's real-world consequence was later found to be more nuanced than originally stated, that nuance is added as a note, never as a silent edit to the original record.

---

## Decision Catalog

### ADR-001: Goal Probability Recalculation Trigger

- **Status:** Accepted & Implemented. *(Note: the original standalone `ArchitectureDecisionRecord.md` document's own status field still read "Proposed — awaiting approval" at archival time — never updated after implementation shipped. `CHANGELOG.md`'s "Fixed (Stabilization Sprint — PCA-3...)" entry and the project's own state log both confirm the fix shipped. Treated here as verified fact; the stale field is a documentation-process gap, not a live ambiguity.)*
- **Context:** `planning_service.get_dashboard()` called `refresh_goal_probabilities()` on every view, re-running an unseeded 2,000-path simulation and persisting the result every time — a Product Consistency Audit found a goal showing 3.8% and 5% on two different screens in one session.
- **Decision:** Recalculate goal probability only when plan inputs change (the Calculation Context fields: `current_amount`, `monthly_contribution`, `target_date`, `risk_profile`, `target_amount`). Dashboard/Reports become pure reads.
- **Alternatives considered:** an explicit "regenerate" button (rejected — worse UX for no benefit); async recalculation with versioning (rejected for that sprint — no background-job infrastructure exists); keeping current behavior (rejected — it's the bug).
- **Consequences:** *Positive* — probability stable across screens, cheaper reads, full auditability of what triggered a value. *Negative, accepted* — no time-decay signal without an explicit edit (judged minor, since the prior "signal" was dominated by RNG noise anyway).
- **Related files:** `planning_service.py`, `routers/goals.py`, `routers/dashboard.py`, `routers/reports.py`, `monte_carlo.py`.
- **Related tests:** `test_repeated_dashboard_reads_never_change_goal_probability`, `TestCalculateGoalProbability`.

### ADR-002: Household as Aggregator, Never Owner

- **Status:** Accepted & Implemented (Milestone 1).
- **Context:** the Family module needed to group existing per-user data (goals, assets) into a household view without disturbing the existing single-owner data model.
- **Decision:** `households`/`household_members` reference existing tables via joins; no `household_id` column was ever added to `goals`, `assets`, `income_sources`, or any pre-existing table.
- **Alternatives considered:** adding a `household_id` FK directly to `goals`/`assets` — implicitly rejected; never appears as a considered path in any design document.
- **Consequences:** *Positive* — zero changes to any pre-existing ownership/security check; the entire Family module is additive. *Negative* — genuinely joint (shared-contribution) goals are structurally unsupported, a real, later-discovered limitation of this same decision.
- **Related files:** `models/household.py`, `family_service.py`.
- **Related tests:** `test_household_policy_models.py`.

### ADR-003: Nullable Sibling Column for HUF Ownership

- **Status:** Accepted & Implemented (Foundation Reconciliation).
- **Context:** `HUFEntity` existed (Milestone 1) but could hold none of its own income/assets — a HIGH-severity finding.
- **Decision:** Add a nullable `huf_entity_id` FK (`ON DELETE SET NULL`) to `income_sources`/`expenses`/`assets`/`liabilities`.
- **Alternatives considered:** parallel HUF-scoped tables (rejected — unnecessary duplication); a polymorphic `Owner` supertype (rejected — premature generalization, would break `user_id`'s stable FK target for a third owner type not concretely planned).
- **Consequences:** *Positive* — additive, zero breaking change, HUF entities can now hold real financial data. *Negative* — none identified; `ON DELETE SET NULL`'s correctness required manual verification against real Postgres since SQLite's test backend doesn't enforce it by default.
- **Related files:** `models/financials.py`, migration `006_foundation_reconciliation`.
- **Related tests:** `test_foundation_reconciliation.py::test_deleting_huf_entity_nulls_ownership_not_cascades`.

### ADR-004: Deprecate-in-Place Rather Than Remove

- **Status:** Accepted & Implemented (Foundation Reconciliation; extended by Engineering Constitution Rule 11 during the Stabilization Sprint).
- **Context:** `user_profiles.dependents`/`marital_status` and `financial_assumptions.tax_rate` were superseded by the new household model and the versioned tax-slab engine, respectively, but real user data might already reference them.
- **Decision:** Mark fields deprecated in code comments, naming the authoritative replacement, without a schema change. Later, after a real incident found this alone insufficient (a frontend consumer kept reading the deprecated field), **Rule 11 (Deprecation Completion)** was added, requiring every consumer — frontend and backend — to be found and migrated before a deprecation is considered complete.
- **Alternatives considered:** immediate removal — implicitly rejected as too risky without first confirming zero consumers; this gap is precisely what caused the incident below.
- **Consequences:** *Positive* — no breaking schema change; a documented migration plan exists. *Negative* — a code-comment deprecation alone does not prevent a live bug if a consumer is missed; this negative consequence directly produced Rule 11.
- **Related files:** `models/profile.py`, `models/assumptions.py`, `app.profile.tsx`.

### ADR-005: Recommendations Computed Live, Never Persisted

- **Status:** Accepted & Implemented (Milestone 2, Family Insurance/Recommendations tasks).
- **Context:** the `recommendations` table existed (Milestone 1) as the designed output store for a future Recommendation Engine, but building Insurance and Scheme recommendations against it would recreate ADR-001's exact staleness risk in a new domain.
- **Decision:** Compute every recommendation fresh on every read; the `recommendations`/`recommendation_citations` tables remain unused.
- **Alternatives considered:** persist to `recommendations` as originally designed — implicitly rejected, evidenced by explicit citation of ADR-001 as the reason not to.
- **Consequences:** *Positive* — zero risk of a stale recommendation; zero invalidation logic needed. *Negative* — the `recommendations` table's original design (ranking/conflict-resolution via `company_policies`) was never fully realized, since the shipped feature took a different architectural path.
- **Related files:** `family_insurance_service.py`, `family_recommendations_service.py`.
- **Related tests:** `test_nothing_is_persisted`, `test_calculation_lifecycle_untouched`.
- **Independently reconfirmed** by this same architectural answer being arrived at four separate times — Insurance, Schemes, Recommendations, and later Notifications (ADR-006) — without code reuse between the decisions, evidence this is the correct answer for the domain, not one engineer's habit.

### ADR-006: Notification Markers Store State, Never Content

- **Status:** Accepted & Implemented (Global Shell Phase 3).
- **Context:** the Notification Center needed to track per-user read/dismissed state without inventing a fourth instance of the "persist a computed fact" anti-pattern.
- **Decision:** `notification_markers` stores only `read_at`/`dismissed_at`, keyed by a deterministic `uuid5` hash of a source-specific natural key; every notification's actual title/body is read live, every request.
- **Alternatives considered:** a conventional `notifications` table storing generated content — implicitly rejected.
- **Consequences:** *Positive* — a fourth domain independently arrives at the identical live-computation pattern with zero incidents. *Negative* — no cleanup job exists for markers whose underlying fact has permanently disappeared (an accepted, minor, unbounded-growth cost, same shape as `password_reset_tokens`).
- **Related files:** `notification_service.py`, `models/notification.py`.
- **Related tests:** `test_get_notifications_never_creates_a_marker_row`.

### ADR-007: Single `activeOverlay` State for Global Shell Overlays

- **Status:** Accepted & Implemented (Milestone 2.6.1).
- **Context:** the Global Shell Certification found the Profile Menu and Command Palette could be simultaneously open — traced to 4 independently-built overlay states across 4 separate development phases, coincidentally agreeing or disagreeing based on which Radix primitive happened to auto-close on which trigger.
- **Decision:** Consolidate into one `activeOverlay: "palette"|"notifications"|"profile"|"more"|null` state, owned by `AppShell`, structurally guaranteeing mutual exclusion.
- **Alternatives considered:** a Context provider or event-bus mechanism — implicitly rejected in favor of the simpler, already-proven controlled-component pattern the Palette already used.
- **Consequences:** *Positive* — mutual exclusion becomes a type-level guarantee, not an emergent property; live-verified across every pairwise overlay combination at desktop and mobile widths. *Negative* — none identified.
- **Related files:** `app-shell.tsx`, `notification-center.tsx`.

### ADR-008: Goal Tagging as Descriptive, Never Ownership

- **Status:** Accepted & Implemented (Milestone 2).
- **Context:** the Family module needed to associate goals with the household members they affect, without building genuine joint-ownership infrastructure ahead of a proven need.
- **Decision:** `goal_household_members` is purely descriptive; `goals.user_id` is never read or written by any tagging operation.
- **Alternatives considered:** a genuine co-ownership model — explicitly named as future work, deliberately not built now.
- **Consequences:** *Positive* — zero risk to the existing single-owner security model; the UI is required to disclose the limitation rather than imply a capability that doesn't exist. *Negative* — per-person contribution tracking remains unsupported, a real product gap for households wanting to jointly fund a goal.
- **Related files:** `models/goal_household_member.py`, `family_service.set_goal_household_tags`.
- **Related tests:** `test_tagging_never_changes_goal_owner`, `test_duplicate_tag_rejected_by_unique_constraint`.

### ADR-009: `VARCHAR` Over `ENUM` for New Policy-Engine Fixed-Vocabulary Fields

- **Status:** Accepted & Implemented (Milestone 1).
- **Context:** `goals.category`/`risk_profile` set a precedent of native Postgres `ENUM` for fixed-vocabulary fields; the new Policy Engine domain needed several similar fields.
- **Decision:** Use plain `VARCHAR` for every new fixed-vocabulary field in the Policy/Family domain, diverging from the `ENUM` precedent.
- **Alternatives considered:** matching the existing `ENUM` convention — implicitly rejected in favor of extensibility.
- **Consequences:** *Positive* — a new scheme category or relationship type never requires an `ALTER TYPE` migration. *Negative* — a real, flagged inconsistency against the pre-existing convention, and `scheme_eligibility_rules.value`'s own string-typed, un-discriminated value column is a direct, compounding consequence of this same preference.
- **Related files:** `models/policy.py`, `models/household.py`.

### ADR-010: AppShell Persistent Mount

- **Status:** Accepted & Implemented (Global Shell Phase 0).
- **Context:** each of 13 leaf routes independently rendered its own `<AppShell>`, causing a full remount — and a fresh `auth.me()`/`getDashboard()` fetch — on every navigation.
- **Decision:** Mount `AppShell` once, at the `/app` layout route; leaf routes render only inside its `<Outlet/>`.
- **Alternatives considered:** none named explicitly as rejected — a straightforward fix once the remount cost was measured, not a multi-option evaluation.
- **Consequences:** *Positive* — measured, quantified improvement (14→2 `auth.me()` calls, 12→0 dashboard calls across 6 navigations); the explicit stated prerequisite for the Profile Menu, Command Palette, and Notification Center work that followed. *Negative* — none identified.
- **Related files:** `app.tsx`, `app-shell.tsx`.

### ADR-011: Deferred Schema Domains at Milestone 1

- **Status:** Accepted & Implemented (Milestone 1 Decision Log).
- **Context:** early database design had planned `AI_CONVERSATIONS`/`AI_MESSAGES`, `notifications`, and an HNI/NRI asset-source-detail extension table — none were built in Milestone 1.
- **Decision:** Defer all three; build only what Milestone 1's own scope explicitly named.
- **Alternatives considered:** building all designed tables immediately "since the design already exists" — implicitly rejected: "building them now would be exactly the kind of 'add abstractions before they're needed' the implementation principles warn against."
- **Consequences:** *Positive* — Milestone 1 stayed scoped and shipped cleanly. *Negative* — none identified; the eventual Notification Center build used a *different*, simpler `notification_markers` shape than originally designed, proving the deferral correct (the early-built version would have been wasted).
- **Related volumes:** the AI Copilot document still confirms `AI_CONVERSATIONS`/`AI_MESSAGES` don't exist as of its own compilation.

### ADR-012: HUF Entities Included Ahead of Their Own Milestone

- **Status:** Accepted & Implemented (Milestone 1).
- **Context:** Milestone 1's brief named "Family entities" and "Nominee entities" but not HUF specifically; HUF's actual need was a Milestone 2 "Inheritance" requirement.
- **Decision:** Include the already-designed, already-verified HUF schema in Milestone 1 anyway.
- **Alternatives considered:** waiting for Milestone 2 to build HUF schema from scratch — implicitly rejected, since the design already existed and was verified, making early inclusion strictly cheaper than a later schema patch.
- **Consequences:** *Positive* — avoided a later, second schema-change pass. *Negative* — this is the direct origin of ADR-003's own triggering finding (HUF couldn't hold its own data) — including the entity ahead of its full design review meant the ownership-attribution gap wasn't caught until a dedicated later audit ran.
- **Related files:** `models/estate.py`.

### ADR-013: Rule-Based Fallback as a First-Class AI Requirement, Not a Degraded Mode

- **Status:** Accepted & Implemented (pre-Milestone-2 Backend Foundation).
- **Context:** an AI Copilot feature was wanted, but the product needed to remain fully functional in any environment without an OpenAI API key.
- **Decision:** `_fallback_response()` is not an error-path afterthought — it is a designed, tested, always-available second implementation of the same endpoint's contract, selected by the presence/absence of `settings.openai_api_key`.
- **Alternatives considered:** requiring an API key for the Copilot to function at all — implicitly rejected; `CLAUDE.md`'s explicit "the app works without an API key" rule and the fallback's presence from the feature's earliest recorded history both confirm this.
- **Consequences:** *Positive* — zero hard external dependency for a core advertised feature; graceful degradation on any OpenAI outage or misconfiguration is free. *Negative* — the fallback's own limitations (it never cites the actual stored probability number) mean the environment most evaluators will actually see (no API key configured) is a materially less capable experience than the GPT-4o path — a real, still-open gap.
- **Related files:** `copilot.py`.
- **Related tests:** `test_openai_error_falls_back_instead_of_500`, `TestCopilotOpenAIPath`.

---

## Mistakes That Became Design Decisions

*(Preserved in full — this is the most valuable narrative content in this entire documentation system, per the mission's own "never lose engineering findings" rule.)*

### The flagship story: an incident → ADR-001 → the Calculation Lifecycle

**Original problem:** `refresh_goal_probabilities()`, called on every Dashboard/Reports view, silently re-ran an unseeded Monte Carlo simulation and persisted the new, random result every time. A goal's stored `probability`/`on_track` depended on which screen was last opened, not on any user action.

**How it was found:** not by code review, but by a live, first-time-user walkthrough that noticed the same goal showing two different numbers on two different pages in one session.

**How it was investigated before any fix:** a full, dedicated, code-cited investigation report, explicitly scoped as "investigation only... no code changed," tracing the exact execution path and every alternative before a single line changed.

**The solution:** ADR-001 — recalculate only on goal create/update; reads become pure.

**The permanent lesson:** "one calculation, one source" — re-derived independently three more times afterward (Insurance recommendations, Family recommendations, Notifications) without needing a second incident to teach the lesson again. This is the single most valuable "mistake" in this codebase's history, because the fix generalized far beyond its original bug.

### A deprecated field kept being read → Rule 11 (Deprecation Completion)

**Original problem:** `user_profiles.dependents`/`marital_status` were marked deprecated with a code comment naming their replacement — but the Profile page's frontend kept reading (and writing) them for a full extra day, showing a household summary that visibly contradicted what the user had actually entered during onboarding.

**The uncomfortable detail worth preserving:** an earlier audit had *already named this exact bug class as a real risk*, one day before it was found actually manifesting — "this is not a hypothetical risk: it is the exact same bug class already found and fixed in this codebase." The forward-looking audit correctly identified the risk; it did not, on its own, prevent the bug, because a documented risk and a completed migration are not the same thing.

**The solution:** point the Profile page at the real, certified `GET /family` endpoint instead; remove the dependency on the deprecated fields entirely — not just stop writing to them, stop reading them too.

**The permanent lesson:** Rule 11, added directly citing this incident — "a deprecation is only complete once every consumer has been found and migrated, not just the one the original change happened to touch." A code comment naming a replacement is necessary but not sufficient.

### The Global Shell overlay bug → ADR-007

**Original problem:** four header overlays, each built in a separate development phase, each managing its own open/closed state independently. Two Radix primitives happened to auto-close on an outside interaction; one didn't — producing a real, reproduced bug (both simultaneously visible) that no single phase's own review could have caught, since each phase only tested its own overlay in isolation.

**How it was found:** a dedicated, cross-phase integration review run specifically because four independently-shipped phases had never been tested *together*.

**The solution:** ADR-007 — one shared `activeOverlay` state, structurally guaranteeing mutual exclusion.

**The permanent lesson:** "relying on multiple independent third-party components' *coincidentally agreeing* default behaviors is not the same guarantee as one shared, structurally-enforced state." The frontend-domain sibling of the ADR-001 lesson — different subsystem, same underlying insight: an emergent property of independently-built parts is not a designed guarantee, no matter how long it happens to hold.

### A milestone-sequencing lesson, not an architecture lesson

**Original problem:** onboarding's Family step told users they could "add full details anytime from Family" — a destination that did not yet exist in the shipped navigation, because that copy shipped ahead of the actual Family Home screen, per the approved "one feature at a time" sequencing.

**The lesson, distinct in kind from the other three:** this was not a code defect — the copy was correct per the approved design, just temporarily dead in the shipped product during the gap between two adjacent tasks. **The durable lesson for future milestone planning:** a UI promise referencing a not-yet-shipped destination is a real, user-visible defect for exactly as long as the gap between the promising feature and the promised feature remains open — worth minimizing that gap deliberately, not just tolerating it as an implementation-order artifact.

---

## Future Decisions (owed, not yet made)

| Future work | Decision owed | Recommended direction |
|---|---|---|
| Portfolio Engine | Where allocation/concentration analysis lives relative to `planning_service.get_dashboard()` | A new, separate `portfolio_service.py`, never an expansion of `planning_service.py` itself |
| Tax Optimizer | Resolve which tax-rate source wins *before* building | Deprecate `financial_assumptions.tax_rate` fully (Rule 11 process) and build against the already-existing, versioned `tax_regimes`/`tax_slabs` |
| Estate Planning | How much succession-law reasoning the system will attempt | Keep `EstateDocument` strictly status-only (already enforced by a permanent test); do not let this module infer legal outcomes without real legal-domain review |
| HUF tax computation | Whether HUF gets its own tax computation now that ADR-003 resolved ownership | Build as its own service, reusing the nullable `huf_entity_id` attribution already in place |
| Local Qwen (AI) | Serving tier, provider abstraction shape | `LLM_PROVIDER = local\|openai\|none`, generalizing the existing API-key presence check |
| RAG (AI) | Vector store choice | pgvector on the existing PostgreSQL instance, not a new managed vector database |
| AI Agents | Whether to adopt an agent framework | No — a hand-rolled bounded loop, keeping the grounding validator's seat in the control flow un-obscured |
| Mobile App | Whether the backend needs to change at all | No backend change — `lib/api.ts` already fully separates the contract from the UI |
| Enterprise (RBAC, multi-tenant) | Where role/permission logic attaches | Extend `family_service.resolve_owned_household`'s already-forward-looking comment rather than inventing a new authorization layer |
| Enterprise (scale beyond one process) | Rate limiter backing store | Redis-backed, exactly as the rate limiter's own docstring already prescribes |
| Any new assumptions-driven calculation | Whether `financial_assumptions.expected_return_*`/`retirement_age`/`social_security_monthly` finally get wired in, or are removed/relabeled | Decide explicitly, one way or the other — this is the single most-repeated open finding across this entire documentation system and should not remain undecided indefinitely |

---

## Related Documents
`docs/02_Architecture/SystemArchitecture.md`, `CalculationEngine.md`, `RecommendationEngine.md`, `LifeEventEngine.md`, `FrontendArchitecture.md`, `AIArchitecture.md`, `DatabaseArchitecture.md` — every one of these cites the ADR numbers defined here. `docs/03_Engineering/EngineeringHandbook.md` (the Engineering Constitution rules ADR-004/ADR-011 reference).

## Related ADRs
This document is the ADR catalog itself.


## Related Tests
Each ADR's own "Related tests" field (preserved verbatim in each entry above) names the specific test proving that decision holds — e.g. ADR-001's `test_repeated_dashboard_reads_never_change_goal_probability`.

## Related Validation Reports
The 4 incident narratives in this document's own "Mistakes That Became Design Decisions" section are themselves validation reports in miniature — each traces a real, found problem to its root cause and its permanent fix.

## Related Implementation Reports
N/A — ADRs document decisions, not implementations; see the architecture document for each decision's domain for its own implementation history.

## Related Future Work
11 "Future Decisions owed" — see this document's own closing table.

---

*Archived originals: `docs/13_Archive/ArchivedReports/ArchitectureDecisionRecordBible.md`, `ArchitectureDecisionRecord.md`.*
