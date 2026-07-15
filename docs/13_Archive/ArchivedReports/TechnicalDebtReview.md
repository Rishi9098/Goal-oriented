# Technical Debt Review — Post-Stabilization-Sprint

**Date:** 2026-07-07
**Scope:** Catalog technical debt closed by the Stabilization Sprint, debt newly surfaced (not created) by its investigations, and debt already known and still open — so the ledger is accurate before Milestone 2 resumes. Investigation only.

---

## Debt Closed by This Sprint

| Item | How it was closed |
|---|---|
| Onboarding promised a "Family" destination that didn't exist (PCA-1) | Copy corrected to make no destination claim. |
| Two parallel, disconnected representations of household data (Profile's deprecated-field mapping vs. the real household model) (PCA-2) | Deprecated-field dependency removed entirely (read and write); Profile now sources from the certified model. |
| Two parallel implementations of "compute a goal's probability" (`refresh_goal_probabilities` and `_refresh_probability`) (PCA-3) | Collapsed into one centralized function, `calculate_goal_probability`. |
| Read endpoints silently mutating financial data with no audit trail (PCA-3) | Removed entirely; Dashboard/Reports are now pure reads. |
| `quick_probability`/`quick_probability_async` had no seeding support, unlike the full engine (PCA-3) | Added `seed` parameter, wired to the same `settings.monte_carlo_seed` the full engine already used. |
| No formal rule requiring a full-codebase sweep before considering a deprecation "done" | `docs/ENGINEERING_CONSTITUTION.md` Rule 11 added, closing exactly the gap PCA-2 exposed. |

## Debt Newly Surfaced (Not Created) by This Sprint's Investigations

These are pre-existing issues the sprint's deep tracing happened to uncover while resolving PCA-1/2/3. None were introduced by the sprint's own changes; each is flagged here so it isn't lost.

| Item | Found during | Severity | Status |
|---|---|---|---|
| Profile's Risk Profile field is fully editable and shows a "Saved" confirmation, but is never actually sent to any API in `handleSubmit` | PCA-2 investigation (`DataSourceMigrationReport.md` Finding 5) | Real, user-visible correctness bug (a setting silently doesn't save) | **Open — explicitly not fixed**, correctly out of PCA-2's scope. Not yet triaged into the `ProductConsistencyAudit.md`/Roadmap system. **Recommend:** file as a new audit finding or a standalone bug ticket before it's forgotten — it currently exists nowhere except this note and the PCA-2 PR report. |
| `update_goal()` (`routers/goals.py`) triggers a full Monte Carlo recompute on **any** PATCH, not just on changes to Calculation Context fields | PCA-3 investigation, re-confirmed during this resumption review (`FutureCompatibilityAudit_Light.md`, Task 9 finding) | Efficiency debt today (harmless but wasteful); becomes a **direct correctness/intent mismatch** the moment Task 9 adds `custom_inflation_rate` to `GoalUpdate`, since the Contract explicitly says that field should *not* trigger a Monte Carlo re-run this milestone | **Open.** Pre-existed this sprint (the old `_refresh_probability` had the identical unconditional-call behavior) — not a regression PCA-3 introduced, but PCA-3's centralization is precisely what makes this easy to fix correctly when Task 9 is implemented. **Recommend:** resolve as part of Task 9's own Design Review step (already flagged there), not as a separate emergency fix now — it is not itself a Critical finding (no incorrect financial result today, since no field currently exists that should be exempted from recompute). |
| Education-cost inflation multiplier is unverified | Already known — `Milestone2ImplementationContract.md` §9's own text, `CalculationEngineReport.md` #12 | Documented, not invented (correct handling per Rule 4) | **Open, correctly so.** Task 9 must resolve this before shipping a suggested default; not a Stabilization Sprint concern. |

## Debt Already Known, Confirmed Still Accurate

- The 13 remaining Open (non-Critical) `ProductConsistencyAudit.md` findings (PCA-4 through PCA-16) — re-confirmed still open and still accurately described in `ProductDriftReview.md`; none were silently resolved or worsened by this sprint.
- `financial_assumptions.tax_rate` — still deprecated, no removal date, per the documented Foundation Reconciliation decision. Rule 11 (new) gives this a formal completion checklist for whenever it's scheduled, but does not itself require action now.
- Async/versioned Monte Carlo recalculation (ADR-001's Option C) — explicitly and correctly deferred to a future Calculation Engine milestone; re-confirmed this is still the right call, not a workaround avoiding real work.

## Net Debt Change

**Net reduction.** Six items closed (including one structural rule addition that prevents a whole class of future debt), two items surfaced that already existed and are now visible and trackable rather than hidden, one item confirmed correctly still deferred. No new debt was created by any of the three fixes themselves.

## Recommendation

Before or during Task 5's kickoff, file the Risk Profile non-persistence bug as its own tracked item (new `ProductConsistencyAudit.md` entry or equivalent) so it has a permanent record outside this review and the PCA-2 PR report — it is currently only documented in two places that are easy to lose track of once the Stabilization Sprint's own documents stop being actively read.
