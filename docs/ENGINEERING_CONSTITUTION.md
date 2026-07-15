# Engineering Constitution

**Purpose:** The durable, non-negotiable engineering rules for Northstar — distinct from `PRODUCT_PRINCIPLES.md` (what we build) and `UX_PRINCIPLES.md` (how it should feel). This document exists so every future feature, whether built by a human or an AI agent, inherits the same architectural discipline this codebase has already proven works, rather than each contributor re-deriving it from scratch.

---

## 1. Routers are thin. Always.

A router validates input, calls exactly one service function, and returns a schema. No business logic, no calculation, no branching on domain rules inside a router body — ever. This has held without exception since the project's first commit and is the single most load-bearing rule in this codebase.

## 2. Never hardcode a fact that can change without a code deploy.

Government scheme rates, tax slabs, section numbers — anything a regulator or market can change independent of this codebase's release cycle — is versioned, effective-dated data (`scheme_rates`, `tax_slabs`, `tax_sections`), never a constant. This rule was not theoretical: every research phase of this project independently surfaced a real example of exactly this kind of fact changing within the last 12-18 months. Treat any new hardcoded financial constant as a defect, not a shortcut.

## 3. Migrations are additive by default.

Prefer a new nullable column or a new table over altering an existing column's meaning or nullability. Every migration in this project's history through the Foundation Reconciliation has been additive-only, verified via an upgrade → downgrade → upgrade cycle against a real database, not just reviewed by eye. A migration that isn't reversible, or that changes existing data's meaning, requires an explicit decision log entry (see Rule 8), not a quiet merge.

## 4. Never invent a financial policy, rate, or rule.

If a specific number (a scheme's interest rate, a deduction ceiling, a tax slab boundary) hasn't been verified against a live, current, authoritative source, it does not go in a seed script, a test fixture, or a comment stated as fact. State the gap explicitly instead. This project's seed data deliberately leaves gaps (the old tax regime's full slab table, certain Section mappings) rather than filling them with a plausible-sounding guess.

## 5. `mypy --strict` and Ruff are the gate, not a suggestion.

Every backend change lands with `ruff check app/` and `mypy --strict app/` both clean. This is not aspirational — it has been true at the end of every session in this project's history, verified by actually running both tools, not assumed from a prior pass.

## 6. Tests prove behavior; they do not get adjusted to match a bug.

If a test fails after a change, the change is wrong until proven otherwise — never loosen an assertion to make a red test green without first establishing the assertion itself was incorrect. Where a test genuinely cannot validate something in this environment (e.g., SQLite's test backend not enforcing a Postgres-specific `ON DELETE SET NULL` without a pragma), that limitation is documented in the test itself and the real behavior is verified directly against the target database — never silently skipped.

## 7. Minimal diff. No premature abstraction.

Three similar lines beat a shared helper built for a fourth case that doesn't exist yet. A polymorphic ownership abstraction was explicitly considered and rejected in favor of a simple nullable sibling column specifically because only two owner types exist today — build for the requirements in front of you, not the ones you can imagine.

## 8. Every non-obvious decision gets a decision log entry.

Problem, options considered, chosen solution, reasoning, trade-offs, future implications — in `PROJECT_STATE.md` or a dedicated report, not just in a commit message. A future contributor (human or AI) should never have to re-derive *why* a nullable column was chosen over a new table, or why a legacy field was deprecated instead of removed.

## 9. Verify against real infrastructure, not just unit tests.

A migration's rollback path is tested by actually running `alembic downgrade` against a real database, not inferred from reading the `downgrade()` function. A CHECK constraint's rejection behavior is tested by actually inserting a violating row and catching the real exception. Where the unit-test environment can't validate something, say so and verify it another way — don't report success on an assumption.

## 10. The AI Advisor computes nothing; it narrates what was already computed.

Any LLM-backed feature receives a fully-computed, fully-cited result from a deterministic service and rephrases it in plain language — it never originates a financial number, a policy citation, or a confidence score itself. This is the single most important rule for anything in the AI Advisor milestone and follows directly from Rule 4: an LLM stating a tax figure from its own training is exactly the kind of unverified financial fact Rule 4 forbids, regardless of how confident the phrasing sounds.

## 11. Deprecation Completion

A field, API, or model is not considered fully deprecated until:

- No production UI reads it.
- No backend service depends on it.
- No tests rely on it except migration/regression tests explicitly checking the deprecated path still behaves safely.
- Documentation identifies its replacement.
- A removal plan exists.

This rule exists because of a real, verified incident: the Foundation Reconciliation (2026-07-06) marked `user_profiles.marital_status`/`dependents` and `financial_assumptions.tax_rate` deprecated at the schema level — but the frontend was never audited for consumers, and `code/src/routes/app.profile.tsx` kept reading *and writing* the deprecated profile fields for another full day, surfacing a visibly wrong "Household" summary to real users (`ProductConsistencyAudit.md` PCA-2) until a dedicated stabilization sprint caught it. Marking something deprecated in the schema or in a code comment is necessary but not sufficient — deprecation is only complete once every consumer has been found and migrated, not just the one the original change happened to touch. When deprecating a field going forward, grep the entire codebase (frontend and backend) for every reader before considering the deprecation done, and record the removal plan in the same decision log entry that announces the deprecation (Rule 8) — not as a follow-up someone might get to.
