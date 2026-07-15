# Migration Guide

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Supersedes:** `DataSourceMigrationReport.md` (archived — the PCA-2 investigation this guide's §2 generalizes into a repeatable process).
**Scope:** two distinct kinds of "migration" this codebase has real, documented experience with — schema migrations (Alembic) and data-source/consumer migrations (moving a frontend or service off a deprecated field onto its replacement).

---

## 1. Writing a Schema Migration (Alembic)

**The one rule, per Coding Standards Rule 3:** additive by default. Prefer a new nullable column or a new table over altering an existing column's meaning or nullability.

**Process:**
1. Write the `upgrade()` function — `CREATE TABLE IF NOT EXISTS` or `ADD COLUMN IF NOT EXISTS` for the common case.
2. Write the exact structural inverse as `downgrade()` — every one of this project's 11 migrations has one, verified by direct reading, not assumed.
3. If the migration adds an index to a potentially large, actively-written table, use `CREATE INDEX CONCURRENTLY` inside `op.get_context().autocommit_block()` — required because PostgreSQL forbids `CONCURRENTLY` index builds inside a transaction block (migration `003`'s own precedent).
4. Test the rollback path by actually running `alembic downgrade` against a real database (Coding Standards Rule 9) — don't infer correctness from reading the function.
5. If the migration represents a non-obvious decision (a new nullable-sibling-column pattern instead of a polymorphic model, a `VARCHAR` instead of an `ENUM`, etc.), add an entry to `docs/03_Engineering/ArchitectureDecisionRecords.md` in the same change — not as a follow-up.

**A real, documented multi-migration pattern to know before assuming any single file tells a table's complete story:** `dependents`' base shape (migration `005`) was extended twice more (`007`, `008`) as two separate implementation efforts discovered missing fields mid-build. This is normal, not debt.

---

## 2. Migrating a Consumer Off a Deprecated Field

This codebase has one real, fully-investigated incident behind this process — preserved here as the template for doing it correctly next time.

**The incident, summarized (full detail in `docs/03_Engineering/ArchitectureDecisionRecords.md`, ADR-004):** `user_profiles.marital_status`/`.dependents` were marked deprecated in a code comment during the Foundation Reconciliation, naming `households`/`household_members`/`dependents` as the replacement. One frontend file (`app.profile.tsx`) was never migrated — and the investigation that eventually found this discovered the problem was **worse than first reported**: not just a stale *read* (a display string computed from the deprecated fields), but a broken *write* path too — saving the Profile form re-derived and overwrote the deprecated fields from a hand-picked dropdown string with no connection to the real household data, meaning a user's "edit" silently updated fields nothing else read, while the actual household data underneath went untouched.

**The generalized process this incident produced (now Coding Standards Rule 11):**
1. **Grep the entire codebase — frontend and backend — for every reader and every writer of the field**, not just the ones the original change happened to touch. The investigation's own finding: checking only the read side would have missed the equally-broken write side.
2. **Identify the authoritative replacement's real API shape** — confirm it has a safe fallback for any account created before the replacement existed (e.g. `GET /family`'s lazy-provisioning of a self-only household for pre-Milestone-2 accounts), so the migration is safe regardless of account age.
3. **Check whether an intermediate mapping layer exists** that assumes the old field's value space — a mapping layer built around a deprecated field's specific vocabulary (e.g. a fixed set of canned "household summary" strings) usually cannot be incrementally extended to the replacement's richer model; it typically needs to be replaced, not patched.
4. **Fix the read and the write together, in one change** — fixing only the display side while leaving a broken write path is a known, real anti-pattern this exact incident demonstrated.
5. **Only after every consumer is confirmed migrated** does Rule 11 consider a deprecation actually complete — update the field's own code comment/documentation to reflect this, and record the removal plan in the same decision log entry.

---

## Related Documents
`docs/05_Database/DatabaseSchema.md` §2 (the 11-migration history) · `docs/03_Engineering/ArchitectureDecisionRecords.md` (ADR-004, Rule 11) · `docs/03_Engineering/CodingStandards.md` (Rules 3, 9, 11)


## Related Tests
Every migration's own `upgrade()`/`downgrade()` pair is its own test, run via `alembic upgrade head` / `alembic downgrade -1` — no separate `test_migrations.py` file exists; correctness is verified by actually running the cycle (Coding Standards Rule 9).

---

*Archived original: `docs/13_Archive/ArchivedReports/DataSourceMigrationReport.md`.*
