# Coding Standards — The Engineering Constitution

**Status:** Canonical · **Last verified against code:** 2026-07-07 (unchanged since — this is durable, rarely-revised doctrine, not a living implementation detail)
**Supersedes:** `docs/ENGINEERING_CONSTITUTION.md` (the pre-existing, actively-maintained source — preserved here verbatim, not rewritten, since it was already correct and current).
**Relationship to `docs/03_Engineering/EngineeringHandbook.md`:** the Handbook's Golden Rules section is a summary-with-consequences of the same 11 rules below; this document is the rules' own canonical, full-text home.

---

## 1. Routers are thin. Always.

A router validates input, calls exactly one service function, and returns a schema. No business logic, no calculation, no branching on domain rules inside a router body — ever. This has held without exception since the project's first commit and is the single most load-bearing rule in this codebase.

## 2. Never hardcode a fact that can change without a code deploy.

Government scheme rates, tax slabs, section numbers — anything a regulator or market can change independent of this codebase's release cycle — is versioned, effective-dated data, never a constant. Treat any new hardcoded financial constant as a defect, not a shortcut.

## 3. Migrations are additive by default.

Prefer a new nullable column or a new table over altering an existing column's meaning or nullability. A migration that isn't reversible, or that changes existing data's meaning, requires an explicit decision log entry (Rule 8), not a quiet merge.

## 4. Never invent a financial policy, rate, or rule.

If a specific number hasn't been verified against a live, current, authoritative source, it does not go in a seed script, a test fixture, or a comment stated as fact. State the gap explicitly instead.

## 5. `mypy --strict` and Ruff are the gate, not a suggestion.

Every backend change lands with both clean — verified by actually running both tools, not assumed from a prior pass.

## 6. Tests prove behavior; they do not get adjusted to match a bug.

If a test fails after a change, the change is wrong until proven otherwise — never loosen an assertion to make a red test green without first establishing the assertion itself was incorrect.

## 7. Minimal diff. No premature abstraction.

Three similar lines beat a shared helper built for a fourth case that doesn't exist yet.

## 8. Every non-obvious decision gets a decision log entry.

Problem, options considered, chosen solution, reasoning, trade-offs, future implications — see `docs/03_Engineering/ArchitectureDecisionRecords.md`.

## 9. Verify against real infrastructure, not just unit tests.

A migration's rollback path is tested by actually running `alembic downgrade` against a real database, not inferred from reading the function. Where the unit-test environment can't validate something, say so and verify it another way.

## 10. The AI Advisor computes nothing; it narrates what was already computed.

Any LLM-backed feature receives a fully-computed, fully-cited result from a deterministic service and rephrases it in plain language — it never originates a financial number, policy citation, or confidence score itself.

## 11. Deprecation Completion

A field, API, or model is not fully deprecated until: no production UI reads it; no backend service depends on it; no tests rely on it except migration/regression tests explicitly checking the deprecated path still behaves safely; documentation identifies its replacement; a removal plan exists.

This rule exists because of a real, verified incident, preserved in full in `docs/03_Engineering/ArchitectureDecisionRecords.md` (ADR-004) — marking something deprecated in a code comment is necessary but not sufficient.

---

## Language-Specific Conventions

**Python (backend):** Python 3.12+, fully type-annotated; `ruff` for linting/formatting (`line-length = 100`); `mypy --strict` must pass; no mutable default arguments, no bare `except`; async-first — every DB call uses `await`.

**TypeScript (frontend):** strict TypeScript, no `any`; PascalCase components, `useCamelCase` hooks; no inline business logic in route files — extract to `lib/`; no comments explaining *what* code does, only *why*.

---

## Related Documents
`docs/03_Engineering/EngineeringHandbook.md` (Golden Rules with consequences) · `docs/03_Engineering/ArchitectureDecisionRecords.md` (the decision log every Rule 8 entry produces) · `docs/03_Engineering/DeveloperGuide.md` (setup, git workflow, PR checklist)

---

*This document mirrors the repo's own `docs/ENGINEERING_CONSTITUTION.md` verbatim — kept in sync as the same source, not a divergent copy.*


## Related Tests
Every rule's enforcement is itself tested indirectly — e.g. Rule 6 (tests prove behavior) is demonstrated by this codebase's own regression-test-per-bug history in `ArchitectureDecisionRecords.md`.
