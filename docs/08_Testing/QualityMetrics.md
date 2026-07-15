# Quality Metrics

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Supersedes:** `FeatureCompletenessMatrix.md` (07-08, archived — several of its "missing" findings are corrected below against current code, not silently inherited), `PreLaunchProductAudit.md`, `ProductConsistencyAudit.md`, `ProductDriftReview.md`, `FutureCompatibilityAuditReport.md`/`_v2.md`/`_Light.md`, `InteractiveProductAudit.md`, `BrokenInteractionReport.md`, `DeadClickReport.md`, `FoundationReconciliationReport.md`, `UXConsistencyReview.md`, plus the 10 Audit/Report pairs from the most recent completion mission.

---

## 1. Current Backend Metrics (live, re-verified this session)

- **673 tests passing**, 0 failing.
- **97.89% coverage** (required minimum: 80%).
- `ruff check app/` and `mypy --strict app/` both clean, 87 source files.

## 2. Feature Completeness — Corrected Against Current Code

The source matrix (07-08) named **Global search**, **Notification center**, and **Profile avatar menu** as "Never implemented." **This is now stale** — all three were built in the Global Shell initiative (Phases 0–3) that followed shortly after that matrix was compiled, and are confirmed live and complete in this session's own direct interaction with the running app (Command Palette, `notification-center.tsx`, `AppShell`'s profile dropdown).

**Still genuinely open, re-confirmed:**

| Feature | Status | Detail |
|---|---|---|
| Update email | ❌ Broken | UI exists, but the parameter is never sent to the backend and no schema field exists to receive it — a partially-implemented, abandoned change. |
| Dashboard goal-card click-through | ❌ Missing | Clicking a goal card on the Dashboard does nothing — never implemented. |
| Reports PDF export | ⚠ Partial | Uses `window.print()`, not a real export — functional as a workaround, not a true "export" feature. |
| AI Copilot mode disclosure | ❌ Missing | The UI never discloses whether a reply came from GPT-4o or the deterministic fallback — a real, still-open honesty gap given `docs/07_AI/AIArchitecture.md`'s own finding that the fallback path is materially less capable. |
| Landing page legal pages (Privacy/Terms/Disclosures) | ❌ Missing | Linked from the footer, no destination page exists. |
| Landing page live demo | ⚠ Partial | Redirects to sign-in — no actual demo mode exists. |
| Landing page account-linking claim | ❌ Contradicted | Marketing copy claims a live capability Settings' own UI honestly labels "Coming soon" — the clearest instance of FE-001. |
| `components/ui/*` shadcn scaffold | ❌ Mostly unused | ~50 files of dialog/dropdown/tabs/select/table primitives, imported by only a handful of app screens — dead scaffold, a hygiene finding, not a defect. |
| Personal tax calculation | ❌ Not started | Versioned tax *data* exists; no computation engine — documented, correctly-deferred future work (`docs/07_AI/AIArchitecture.md` §7's `calculate_tax` gap). |

**Correctly, honestly disabled (not gaps):** Settings' "Linked accounts" and "Notifications preferences" both correctly display a "Coming soon" label rather than a broken or misleading control — the right pattern, contrasted directly against the Landing page's own violation of it above.

## 3. Product Consistency & Drift

Across the project's history, dedicated Product Consistency Audits (PCA-1 through PCA-8+) and Drift Reviews ran at multiple points specifically to catch exactly this class of "documentation/marketing says X, code does Y" gap — PCA-2 (the deprecated-field incident, `docs/03_Engineering/ArchitectureDecisionRecords.md` ADR-004) and PCA-3 (the ADR-001 incident) are the two most consequential examples in this project's entire history. The Future Compatibility Audits (original, `_v2`, and the later `_Light` re-run) tracked the same class of risk specifically for forward-compatibility as new milestones landed.

## 4. Most Recent Completion Mission — Summary

The 10-phase Product Experience Completion mission (Navigation, Life Event Integration, Plan Health UX, Microcopy, Automation, Cross-Module Consistency, Behavioral Design, Accessibility, Performance UX, Final Review) is the most recent and most current quality pass over this product. Its own final scorecard: Overall 9/10, Engineering 9/10, UX 9/10, Financial Planning Integrity 9/10, Accessibility 8/10, Behavioral Design 9/10, Consistency 9/10 — **GO WITH MINOR CHANGES**. Full detail: `docs/13_Archive/ArchivedReports/NorthstarFinalProductReview.md` and `Northstar_ProductCompletionReport.md`.

---

## Related Documents
`docs/08_Testing/ValidationStrategy.md` (the chronological checkpoint record these metrics summarize) · `docs/08_Testing/TestingStrategy.md` · `docs/03_Engineering/TechnicalDebt.md` (every item above also appears there, categorized)


## Related Tests
The live 673-test backend run this document's own §1 cites, plus every mission phase's own validation record in `08_Testing/ValidationStrategy.md`.

---

*Archived originals: `docs/13_Archive/ArchivedReports/FeatureCompletenessMatrix.md`, `PreLaunchProductAudit.md`, `ProductConsistencyAudit.md`, `ProductDriftReview.md`, `FutureCompatibilityAuditReport.md`, `FutureCompatibilityAuditReport_v2.md`, `FutureCompatibilityAudit_Light.md`, `InteractiveProductAudit.md`, `BrokenInteractionReport.md`, `DeadClickReport.md`, `FoundationReconciliationReport.md`, `UXConsistencyReview.md`, plus the 10 most-recent-mission audit/report pairs.*
