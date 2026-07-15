# FORMAL DESIGN REVIEW — Milestone 1 (Financial Profile Management)

**Reviewer role:** Principal Engineer, adversarial design review
**Reviewed:** `Milestone1ImplementationSpecification.md`, cross-checked against `ImplementationRoadmap.md`, `PreLaunchProductAudit.md`, and current source (not just the spec's own claims about current source).
**Posture:** The specification is assumed wrong until each claim is independently re-verified. Every finding below is backed by a source citation obtained during this review, not by re-reading the spec's own assertions.

Three of the findings below directly contradict specific, explicit claims the specification makes about "no decision needed" or "matches existing convention." Those are flagged as such — they are not new problems the spec failed to anticipate, they are cases where the spec's own stated resolution is factually wrong.

---

## ISSUES

### DR-01 — Nav placement decision contradicts an explicit, documented, cited design rule
**Severity:** HIGH — blocking
**Description:** Spec §0.3 decides to insert a new "Financials" nav item "immediately after `/app/goals` and before `/app/family`." `code/src/components/app-shell.tsx`'s own `nav` array carries a comment directly above it: *"Order matches `FamilyPlanningDesign.md`'s concrete nav diagram (Family directly after Goals, before AI Copilot)."* Inserting Financials between Goals and Family pushes Family to third position, breaking the specific rule the file itself documents and cites.
**Why it matters:** This isn't a style nitpick — the codebase has an explicit convention of citing and preserving documented nav-ordering rationale, and PLA-007/Volume 6 already flagged Family's first-class nav placement as a deliberate product decision (`PRODUCT_PRINCIPLES.md` #5: "Family is a first-class navigation item... precisely because it's a defensible product position"). Silently reordering it as a side effect of an unrelated feature is exactly the kind of undocumented architectural drift the Engineering Constitution's Rule 8 ("every non-obvious decision gets a decision log entry") exists to prevent — and this spec makes the decision without even noticing the conflict existed.
**Suggested correction:** Revise §0.3. Two defensible options: (a) place Financials *before* Goals (Dashboard → Financials → Goals → Family → ...), on the rationale that financial facts are logically prerequisite to goal planning, not a peer of it; or (b) place it *after* Family/Copilot, alongside Reports (both are "look at your data" surfaces, distinct from the "act on your plan" surfaces Goals/Family represent). Either is defensible; "between Goals and Family" is the one option that's already ruled out by the codebase's own documentation. Whichever is chosen, add a comment matching the existing file's citation convention.
**Spec must change before implementation:** Yes.

### DR-02 — Testing Strategy assumes infrastructure that does not exist in this repository
**Severity:** HIGH — blocking
**Description:** Spec §1.10 and §3.18 call for "one Playwright end-to-end journey per this project's web-testing convention" and component-level tests for the new React components. `code/package.json`'s `devDependencies` contain no testing library at all — no Playwright, Vitest, Jest, React Testing Library, or Cypress — and no `playwright.config.*`, `*.test.*`, `*.spec.*`, or `e2e/` directory exists anywhere under `code/`. There is no frontend test runner in this project today.
**Why it matters:** The phrase "per this project's web-testing convention" asserts a convention that does not exist in this codebase — it describes the *reviewer's own general web-testing defaults*, not anything verified against this repository. An engineer following this spec literally would either silently fail to produce the required tests, or would have to scope, choose, install, and configure an entire frontend testing stack as an unplanned prerequisite — a real piece of infrastructure work with its own risk and LOC cost that appears nowhere in `ImplementationRoadmap.md`'s Milestone 1 estimate (~900-1300 frontend LOC, no mention of new tooling).
**Suggested correction:** Either (a) explicitly scope "introduce a frontend test runner" as a named, estimated prerequisite task inside Milestone 1 — pick one (Vitest + React Testing Library is the lower-friction pairing given this is already a Vite project) and say so, or (b) descope frontend automated testing for Milestone 1 to backend integration tests only (which do have a real, working pytest setup) plus a manual QA checklist, and defer frontend test infra to its own tracked item. Do not leave the spec asserting a convention that isn't there.
**Spec must change before implementation:** Yes.

### DR-03 — Mobile bottom-nav placement is entirely unaddressed
**Severity:** HIGH — blocking
**Description:** `app-shell.tsx` hardcodes two arrays, `MOBILE_PRIMARY` (4 routes: Dashboard, Goals, Family, Copilot) and `MOBILE_MORE` (3 routes: Reports, Profile, Settings), with a comment: *"Mobile bottom nav can only fit 5 slots... Dashboard, Goals, Family, Copilot stay primary; Reports/Profile/Settings move behind 'More.'"* The spec's §0.3 only discusses the desktop `nav` array and never mentions either mobile array.
**Why it matters:** This is not a cosmetic omission — without an explicit decision, an engineer must either (a) silently leave Financials out of both mobile arrays, making the entire feature this milestone builds unreachable from the mobile bottom nav (the primary nav surface on the smallest breakpoint this project explicitly tests, per its own web-testing rules covering 320/768/1024/1440), or (b) guess, inconsistently with whatever the desktop decision (DR-01) turns out to be. Given the audit's own Part 9 finding that this product needs users to actually maintain their financial data over years, shipping the fix to that problem in a way that's unreachable on mobile is a real, user-facing regression risk, not a hypothetical.
**Suggested correction:** Resolve alongside DR-01. If Financials is judged important enough for a primary desktop nav slot (which §0.3's own rationale argues), the honest question is which existing `MOBILE_PRIMARY` item it displaces, or whether the 5-slot budget needs to become 5 primary + Financials as a 5th non-"More" primary item (the comment says "can only fit 5 slots" but only 4 are currently listed as primary — there may already be one free slot; verify before assuming a displacement is needed).
**Spec must change before implementation:** Yes.

### DR-04 — Proposed `extra="forbid"` change introduces a new, inconsistent API convention and touches already-shipped endpoints for a problem the frontend already prevents
**Severity:** MEDIUM-HIGH
**Description:** Spec §0.7/§2.A.7 proposes adding `model_config = {"extra": "forbid"}` to the two new Update schemas, and further proposes retroactively applying it to the already-shipped `AssetUpdate`/`LiabilityUpdate` "if not already set." Verified: **no** existing schema in this codebase sets `extra="forbid"` — not `GoalUpdate`, not any of the `financials.py` schemas, not `assumptions.py`. The default Pydantic v2 behavior (silently ignore unrecognized fields) is the codebase-wide, unbroken convention today. Separately verified: no frontend call site anywhere spreads a full entity object into a patch payload (`grep` for `...income`/`...expense`/`...asset`/`...liability` in `api.ts`/`onboarding.tsx` returns nothing) — every existing `update*` function's TypeScript signature already accepts only the intended patch fields, meaning the problem this proposal defends against (a stray `source_type` reaching the API) is already prevented at the type layer.
**Why it matters:** This is a novel validation behavior introduced in exactly two schemas while every sibling schema in the same file, and every other Update schema in the project, remains permissive — a real, self-inflicted API inconsistency (the review brief's item 4 directly). Worse, the "retroactively apply to Asset/Liability" half of the proposal means Milestone 1 — whose entire premise per the Roadmap is "additive, low-risk, does not touch already-shipped endpoints" — would in fact modify two already-shipped, already-tested endpoints' validation behavior for a defensive measure the type system already provides. That directly contradicts the Roadmap's own risk rating for this milestone ("Low... additive endpoints/schemas... well-understood CRUD pattern").
**Suggested correction:** Drop the `extra="forbid"` proposal entirely for Milestone 1. If field-immutability enforcement is wanted at the API layer (not just the UI layer, per §0.7), that's a separate, deliberate, project-wide API-consistency decision that should be made once, for every Update schema in the codebase, not introduced piecemeal in this milestone.
**Spec must change before implementation:** Yes.

### DR-05 — Generic form-component design is asserted, not actually specified
**Severity:** MEDIUM
**Description:** Spec §1.1 mandates a single, entity-parameterized `AddRowForm`/`EditRowForm`/`FinancialRow` set of components "via a field-config parameter," but no field-config schema is ever defined — not which fields are editable per entity (§0.7's immutability rule), not which fields need the ×100/÷100 percentage conversion (interest_rate does, balance doesn't), not field types (text/number/select), not per-entity option lists.
**Why it matters:** This directly undercuts the document's own stated bar: *"detailed enough that an engineer unfamiliar with the project can implement Milestone 1 without making architectural decisions."* Designing a config-driven form abstraction that correctly handles four entities with meaningfully different field shapes (Income has 3 fields; Liability has 6, one of which needs percentage conversion and one of which is nullable-with-different-empty-state-semantics per §2.D's acceptance criteria) is itself a non-trivial interface design task, not a mechanical detail — left unspecified, it's exactly the kind of decision the document claims to have already made.
**Suggested correction:** Either add a concrete field-config type definition (conceptual, not code — e.g., "each entity config is a list of `{ key, label, kind: 'text'|'select'|'currency'|'percentage', editable: boolean, options?, required? }` records") to Part 1, or explicitly narrow scope: build four separate, non-generic components for Milestone 1 (more LOC, zero interface-design risk) and note the shared-abstraction refactor as a deliberate, separately-scoped follow-up once four real implementations exist to generalize from — which is actually more consistent with Engineering Constitution Rule 7 ("a shared helper built for a fourth case that doesn't exist yet" — here, arguably, the fourth case exists but the *config interface* still doesn't, and inventing it now is speculative in exactly the way Rule 7 warns against).
**Spec must change before implementation:** Yes — at minimum, the field-config schema must be added.

### DR-06 — Assumptions get-or-create race condition is understated as a "verify during implementation" hedge rather than a required fix
**Severity:** MEDIUM
**Description:** `backend/app/models/assumptions.py` confirms `user_id` is `unique=True` at the DB level. `backend/app/routers/assumptions.py`'s `get_assumptions` does an unguarded select-then-insert: if no row exists, it inserts one with defaults — with no `try/except IntegrityError` and no `ON CONFLICT` handling. Two concurrent `GET /assumptions` calls for the same never-before-seen user (e.g., two browser tabs opened to Settings simultaneously right after signup) can both pass the `scalar_one_or_none() is None` check before either commits; the second `INSERT` raises an uncaught unique-constraint violation, surfacing as an unhandled 500.
**Why it matters:** This is a pre-existing latent bug, not introduced by Milestone 1 — but Milestone 1 is precisely the change that turns "Assumptions" from a onboarding-only, single-request code path into a Settings-card that loads every time a user opens Settings, materially increasing the odds of the specific concurrent-tab pattern that triggers it. The spec's own §3.9 downgrades this to "verify the uniqueness constraint exists at the DB level during implementation... if it does not, that is a pre-existing gap outside Milestone 1's scope to fix, but flag it if found" — this framing is backwards: the constraint *does* exist (verified above), which is exactly what makes the race a live, reachable bug, not a hypothetical one the spec can defer.
**Suggested correction:** Wrap `get_assumptions`'s insert path in a `try/except IntegrityError: await db.rollback(); <re-select>` (or switch to a Postgres `INSERT ... ON CONFLICT (user_id) DO NOTHING` + re-select), scoped as part of Milestone 1 since M1 is what increases this endpoint's real-world concurrent-call frequency.
**Spec must change before implementation:** Yes.

### DR-07 — Percentage conversion has an unaddressed floating-point round-trip risk
**Severity:** MEDIUM
**Description:** Spec §0.9 correctly identifies the ×100 (display) / ÷100 (submit) conversion requirement but does not address IEEE-754 floating-point round-trip error — e.g., in JavaScript, `3.5 / 100 === 0.034999999999999996`, not `0.035`. Sent to a Pydantic `float` field this is silently accepted (no rounding occurs anywhere in the pipeline described), and the *next* time that value is loaded and multiplied back by 100 for display, the user may see `3.4999999999999996` instead of `3.5`.
**Why it matters:** This is a visible, confusing bug in a form whose entire purpose is numerical precision for financial projections — the audit's Part 9 (CFP perspective) explicitly holds this product to a "would a real advisor trust this" bar, and an input field that silently drifts a user's own entered value is exactly the kind of small trust-eroding bug the audit's PLA-011 was about.
**Suggested correction:** Round to a fixed, sensible precision (e.g., 4 decimal places on the stored fraction, matching the finest granularity any of these fields realistically need — a tax rate specified to 0.01% is already absurd precision) at the point of conversion, both directions, not just on submit.
**Spec must change before implementation:** Yes — one line, low effort, real user-facing bug if skipped.

### DR-08 — Delete confirmation is unchanged from the Goals pattern despite materially different stakes and no restore path
**Severity:** MEDIUM
**Description:** §1.1/§1.4 reuse `GoalSimPanel`'s exact two-step "Are you sure?" / "Yes, delete" / "Cancel" pattern verbatim for Income/Expense/Asset/Liability rows. Unlike a goal (which is one of potentially several similar planning targets a user iterates on), a Liability row here can represent a $310,000 mortgage record with payment history context; deleting it is soft (recoverable in the database) but **there is no restore UI in Milestone 1** (that's explicitly Milestone 5, per the Roadmap) — from the user's perspective, this delete is indistinguishable from permanent.
**Why it matters:** `UX_PRINCIPLES.md` #10 sets the bar explicitly for "emotionally-loaded data... error copy should reflect that, every time" — the same reasoning extends to destructive-feeling actions, not just error copy. A bare "Are you sure?" undersells the stakes for financial records in a way it doesn't for a goal.
**Suggested correction:** At minimum, strengthen the confirm copy for these four entities specifically (e.g., "Delete this mortgage record? You can't undo this from the app yet.") rather than copying Goals' generic copy verbatim. Consider (non-blocking, product decision) whether Milestone 5's restore capability should be pulled forward to ship alongside Milestone 1 for just these four entities, given they're new construction anyway.
**Spec must change before implementation:** Recommended, not strictly blocking.

### DR-09 — Bundling full `financials_service.py` extraction with the two new endpoints increases regression blast radius beyond what the milestone needs
**Severity:** MEDIUM
**Description:** §1.1/§2.A.10 direct the implementing engineer to extract *all* CRUD logic for all four entities (14 existing endpoints plus the 2 new ones) out of `financials.py` into a new service file in the same milestone.
**Why it matters:** This turns a scoped "add 2 endpoints" change into a full-file refactor of every already-shipped, already-tested financials endpoint. `backend/tests/test_financials.py` does have real coverage (confirmed: 25 tests across `TestIncome`/`TestExpenses`/`TestAssets`/`TestLiabilities`/`TestAssumptions`), which mitigates but does not eliminate the risk — a mistake in the extraction (e.g., reordering `flush()`/`refresh()`/`commit()`, or a copy-paste error moving eight near-identical CRUD blocks) could regress working endpoints in a milestone the Roadmap explicitly rates "Low risk," which is only true if the diff stays as small as the roadmap assumed.
**Suggested correction:** Either (a) proceed with full extraction and treat the existing 25-test suite as the explicit regression gate — every one of those tests must still pass unmodified, not just "conceptually still be true" — or (b) narrow the extraction to only the new Income/Expense update logic, leaving the other 12 endpoints' inline logic untouched for now and tracking the full extraction as a separate, lower-stakes cleanup item. Either is acceptable; the spec should state which, rather than implying the larger refactor is free.
**Spec must change before implementation:** Recommended.

### DR-10 — Reduced-motion claim is based on a convention that does not exist in this codebase
**Severity:** MEDIUM
**Description:** §1.9 states new animations must "respect `prefers-reduced-motion`... confirm the project's existing reduced-motion handling convention during implementation and match it; do not invent a second convention." A repository-wide search for `prefers-reduced-motion`/`useReducedMotion` in `code/src/` returns **zero results**. `GoalSimPanel.tsx`'s own `motion`/`AnimatePresence` usage — which this spec explicitly cites as the pattern to reuse — does not itself handle reduced motion.
**Why it matters:** The spec's own audit blind-spot register (`EngineeringKnowledgeIndex.md`, cited in `PreLaunchProductAudit.md`'s Part 10 scorecard) already flags accessibility as unscored and unaudited. This spec section implies a convention exists to inherit, when in fact Milestone 1 would be the *first* place in the codebase to actually implement this if built as literally described — a materially larger task than "match the existing pattern," and one this spec's complexity/LOC estimates don't account for.
**Suggested correction:** State plainly that no existing convention exists. Either explicitly scope a minimal reduced-motion guard for the new components only (accepting that it's ahead of the rest of the app, not "matching" it), or explicitly defer this requirement to Milestone 6 (Accessibility) and drop the "respect prefers-reduced-motion" bullet from Milestone 1's baseline for now, rather than asserting a false premise.
**Spec must change before implementation:** Recommended.

### DR-11 — Wireframes are desktop-only despite a stated 320px testing requirement
**Severity:** MEDIUM
**Description:** §1.3 and §3.4's ASCII wireframes both show a dense, multi-column row layout (type / description / amount / edit icon / delete icon for the list rows; a two-column grid for the Assumptions form) with no corresponding mobile/narrow-viewport layout described, despite §1.10 committing to 320/768/1024/1440 screenshot coverage.
**Why it matters:** A row with 3-5 inline fields plus two icon buttons does not fit at 320-375px without either horizontal scroll (bad — this org's own performance/testing rules call out "verify no overflow" at these breakpoints) or an entirely different stacked-card layout for narrow screens, which is a real design decision, not a CSS tweak, and isn't described anywhere in this document.
**Suggested correction:** Add an explicit mobile wireframe (stacked label/value pairs per row instead of inline columns, matching how the existing Goals cards on `/app/goals` likely already collapse — verify and reuse that pattern rather than inventing a new one) to §1.3 and §3.4.
**Spec must change before implementation:** Recommended.

### DR-12 — Minor factual error: spec claims `test_assumptions.py` is absent; assumption tests already exist under a different file
**Severity:** LOW
**Description:** §3.18 states: *"new `backend/tests/test_assumptions.py` if one does not already exist (confirmed absent from the current test directory listing)."* Verified: there is no file named `test_assumptions.py`, but `backend/tests/test_financials.py` already contains a full `TestAssumptions` class (`test_get_assumptions_creates_defaults`, `test_get_assumptions_idempotent`, `test_update_assumptions`, `test_assumptions_requires_auth`) with real, working coverage of the exact get-or-create and partial-update behavior this milestone touches.
**Why it matters:** Following the spec literally would create a redundant, competing test file for functionality already covered, rather than extending the existing, correctly-scoped test class — minor wasted effort, not a design flaw, but worth correcting since it's stated as a verified fact ("confirmed absent") that turns out to be false — a filename-only grep, not a content check.
**Suggested correction:** Extend `TestAssumptions` in `test_financials.py` (add the DR-06 race-condition regression test and any new field-level boundary cases there) rather than creating a new file.
**Spec must change before implementation:** Yes, but trivial (one sentence fix).

### DR-13 — No pagination on the four list endpoints
**Severity:** LOW — non-blocking
**Description:** `GET /financials/{income,expenses,assets,liabilities}` return unbounded lists; the spec neither adds pagination nor explicitly notes the decision not to.
**Why it matters:** For the realistic cardinality of a personal finance app (a handful to a few dozen rows per user, even over decades), this is genuinely low-risk — flagging it mainly because "missing pagination" is an explicit, named review-standard item, and the spec should say "considered and intentionally deferred," not stay silent.
**Suggested correction:** Add one sentence to Part 0 noting pagination was considered and deferred as out-of-scope given expected cardinality (YAGNI, per Engineering Constitution Rule 7), so a future reviewer doesn't have to re-derive the same conclusion.
**Spec must change before implementation:** No.

### DR-14 — Liability `interest_rate` frontend bound not stated
**Severity:** LOW — non-blocking
**Description:** §2.D notes the percentage-conversion requirement for `interest_rate` but never states the frontend input's `max` attribute (should be `100`, matching the backend's `le=1` after ×100 conversion — distinct from Assumptions' return-rate fields, which cap at 50).
**Why it matters:** Minor completeness gap; an implementing engineer would likely infer the correct bound from the backend schema anyway, but the document's own stated bar ("without making architectural decisions") means this small inference shouldn't be required either.
**Suggested correction:** Add `max="100"` explicitly to §2.D's validation rules.
**Spec must change before implementation:** No.

---

## OVERALL DESIGN REVIEW SCORE: 6.5 / 10

The specification's backend analysis is strong and independently re-verified as accurate: the API contracts, validation bounds, soft-delete correction, `updated_at` correction, and the ADR-001-consistent "no calculation trigger" determination all held up under adversarial re-checking with no errors found. The percentage-conversion trap (DR-07's root cause was correctly identified in the spec itself, just not fully closed) and the immutable-type-field precedent are genuinely good catches that most specs at this level of detail would miss. What pulls the score down is not sloppiness but overreach: three sections assert "no decision needed, matches existing convention" in cases where the convention either doesn't exist (frontend testing, reduced-motion) or points the opposite direction (nav ordering, extra-field validation) — and those are exactly the kind of confident-but-wrong claims that are most dangerous in a document whose entire purpose is to let someone implement without re-deriving architecture.

## IMPLEMENTATION READINESS: **Go with Changes**

Not a No-Go: the core CRUD design, database analysis, and calculation-boundary reasoning are sound, and none of the findings above invalidate Part 2's per-entity API contracts, which are the bulk of the document and the hardest part to get right. Not a clean Go: DR-01 through DR-06 are concrete, evidence-backed corrections that change what gets built (nav position, mobile reachability, test approach, one new schema decision, one bug fix, one component-design gap) and should be resolved in the spec, not discovered mid-implementation.

## BLOCKING ISSUES (must be resolved in the spec before implementation starts)
- DR-01 — Nav placement contradicts documented design rule
- DR-02 — Testing strategy assumes non-existent infrastructure
- DR-03 — Mobile nav placement unaddressed
- DR-04 — `extra="forbid"` proposal creates API inconsistency, touches shipped endpoints unnecessarily
- DR-05 — Generic form component's config schema is unspecified
- DR-06 — Assumptions race condition needs a real fix, not a hedge
- DR-07 — Percentage round-trip precision needs explicit rounding
- DR-12 — Factual correction: extend existing `TestAssumptions`, don't create a duplicate file

## NON-BLOCKING IMPROVEMENTS (recommended, can be addressed during implementation)
- DR-08 — Strengthen delete-confirmation copy for financial entities
- DR-09 — Decide and state the scope of the service-layer extraction explicitly
- DR-10 — Be honest that no reduced-motion convention exists yet; scope accordingly
- DR-11 — Add a mobile wireframe
- DR-13 — Note the pagination deferral explicitly
- DR-14 — State the `interest_rate` frontend bound explicitly
