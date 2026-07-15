# Product Consistency Roadmap

**Date:** 2026-07-06
**Last updated:** 2026-07-07 — all three Stabilization Sprint Critical findings (PCA-1, PCA-2, PCA-3) resolved (see `PROJECT_STATE.md`).
**Source:** `ProductConsistencyAudit.md` — 16 issues, grouped here by severity for prioritization.

---

## Critical (Stabilization Sprint — all three resolved; feature development remains frozen pending user approval to resume)

These three issues actively contradict what the user was just told, or undermine the specific numbers the product asks users to trust. Each is a concrete example of the exact failure mode this project's own `docs/ENGINEERING_CONSTITUTION.md` and Foundation Reconciliation decision log warned about: two representations of one fact disagreeing.

| ID | Title | Why it's Critical | Owning Milestone | Status |
|---|---|---|---|---|
| PCA-1 | Onboarding promises a "Family" destination that does not exist | A specific, twice-repeated promise made during the most personal part of onboarding, with no way to fulfill it today | Resolved via copy fix (not Task 5 — building the screen would be new-feature work, out of scope for a stabilization sprint) | ✅ Resolved 2026-07-07 |
| PCA-2 | Profile's "Household" field contradicts the family data just entered | The product visibly disagrees with itself about the user's own family, on two screens in the same session | Resolved via a read-only display sourced from the certified `GET /api/v1/family` endpoint — no new backend API | ✅ Resolved 2026-07-07 |
| PCA-3 | Goal success probability changes depending on which screen was visited last | The core number this product exists to produce is not stable — a structural violation of "one calculation, one source" | Resolved via ADR-001 — Monte Carlo execution centralized behind goal create/update only; Dashboard/Reports are now pure reads | ✅ Resolved 2026-07-07 |

**Recommendation:** PCA-1's actual fix (a copy change) turned out smaller in scope than this roadmap originally anticipated ("resolves naturally as Milestone 2 continues") — the stabilization sprint's stricter "no new features" constraint meant the fix had to be decoupled from Task 5 entirely, which is a better outcome (resolved now, not gated on a future feature ship). PCA-2's investigation similarly found the real problem was larger than originally filed (a write-side bug in addition to the read-side one) — resolved by removing dependency on the deprecated fields entirely rather than patching the read path alone. PCA-3's investigation and approved ADR (`ArchitectureDecisionRecord.md`) resolved the finding via a broader rule than initially recommended ("read operations must never perform or persist financial calculations") while explicitly deferring the architecturally-strongest long-term option (async recalculation with versioning) to a future Calculation Engine milestone, since it would require background-job infrastructure this codebase does not have — correctly out of scope for a stabilization fix.

**All three Critical findings are now resolved.** Per the sprint's own closing instruction, feature development (Milestone 2 Task 5 onward) remains frozen until the user reviews this and explicitly approves resuming it.

---

## High (fix within the current localization/tax-planning pass)

These three issues are all instances of the same underlying gap: the frontend was built generically and has not caught up to how India-specific this product's backend already is.

| ID | Title | Owning Milestone |
|---|---|---|
| PCA-4 | U.S.-only financial account types (401(k), IRA) shown to every user | Milestone 4 (or a dedicated localization effort — no current milestone owns onboarding-copy localization explicitly) |
| PCA-5 | Currency symbol never follows the selected country | Milestone 4 (or a dedicated localization effort) |
| PCA-6 | Onboarding's flat "Tax Rate" field bypasses the certified tax-slab engine | Milestone 4 (Tax Planning) |

**Recommendation:** These three should be scoped together, not separately — they're all symptoms of the same "onboarding predates the India-specific backend" root cause, and a single localization/tax-planning pass within Milestone 4 could address all three at once rather than three uncoordinated patches.

---

## Medium (fix opportunistically, or bundle with the milestone that already owns the surface)

| ID | Title | Owning Milestone |
|---|---|---|
| PCA-7 | Zero government-scheme information visible anywhere in the product | Milestone 2, Task 11 (already scheduled) |
| PCA-8 | AI Copilot's fallback answer never cites the actual number | Milestone 6 (AI Advisor) |
| PCA-9 | "Linked accounts via Plaid" advertises an India-incompatible vendor | Unassigned — needs a product decision first |
| PCA-10 | Plan health score shown with no explanation anywhere | Milestone 5 or 6 |
| PCA-11 | Net Worth Projection card's headline number contradicts its own chart | Not milestone-gated — standalone bug investigation |
| PCA-12 | Plan health duplicated across three surfaces, can disagree | Milestone 4 (tied to PCA-3's fix) |
| PCA-16 | Financial jargon used throughout with no glossary or inline explanation | Milestone 6 (AI Advisor/explainability) |

**Recommendation:** PCA-7 and PCA-12 already ride along with scheduled work (Task 11 and PCA-3's fix, respectively) — no independent action needed beyond what's already planned. PCA-11 is the one item here worth pulling forward immediately regardless of milestone sequencing, since "looks broken" is a worse first impression than any Medium-severity jargon or explanation gap. PCA-9 is blocked on a product decision (is account aggregation even planned for India, and with what vendor?) before it can be assigned anywhere.

---

## Low (opportunistic copy/design polish, no milestone dependency)

| ID | Title |
|---|---|
| PCA-13 | Delete-account copy is internally contradictory |
| PCA-14 | Two competing, unlabeled primary CTAs on the landing page |
| PCA-15 | Children-count placeholder looks like a real value, causes an avoidable form error |

**Recommendation:** Bundle these three into a single small "copy polish" pass whenever convenient — none are blocking, none require a design or architecture decision, and fixing them together is more efficient than three separate one-line PRs.

---

## Cross-Cutting Observation

Six of the sixteen issues (PCA-2, PCA-3, PCA-6, PCA-9, PCA-10, PCA-12) trace back to the same underlying pattern this project has already named and fixed once before, in the Foundation Reconciliation: **a UI surface built against an older data model, still running, after the data model it depends on was superseded.** The Foundation Reconciliation fixed this at the schema level (deprecating `user_profiles.dependents`/`marital_status`, `financial_assumptions.tax_rate`) but this audit shows the *frontend* consumers of those now-deprecated fields were never revisited. Recommend treating "does any shipped UI still read a field marked deprecated in a prior reconciliation" as a standing check for every future milestone's Design Review step, not a one-time cleanup.

---

## Suggested Sequencing

1. **Immediately, independent of Milestone 2:** PCA-11 (looks-broken bug), PCA-3/PCA-12 (probability instability) — both are trust-critical and neither depends on unshipped Family features.
2. **Alongside Milestone 2 Task 5:** PCA-1 resolves on its own; schedule PCA-2 as a direct follow-up.
3. **As a bundled localization pass within Milestone 4:** PCA-4, PCA-5, PCA-6.
4. **Riding along with already-scheduled work:** PCA-7 (Task 11), PCA-8 and PCA-16 (Milestone 6).
5. **Whenever convenient:** PCA-13, PCA-14, PCA-15.
6. **Needs a decision before it can be scheduled at all:** PCA-9.
