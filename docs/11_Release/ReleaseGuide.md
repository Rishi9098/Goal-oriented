# Release Guide

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Supersedes:** `ReleaseNotes.md` (archived — the historical "Unreleased" notes from the project's first stabilization pass).
**Note on `CHANGELOG.md`:** remains at the repository root per standard convention — not moved into `docs/`, only referenced from here. It is the project's own living, chronological record; this guide covers *process*, not a duplicate of its content.

---

## 1. What a Release Note Should Capture (established pattern)

The project's own first release-notes pass set the template still worth following: an executive summary distinguishing *what kind* of work this is (bug-fix/quality vs. new feature vs. architectural change), a grouped "what changed" list by category (bug fixes, type-safety fixes, documentation drift corrections), and an explicit, honest production-readiness call with its rationale — not just a checklist of commits.

**Example of the honesty standard to maintain:** the first release pass explicitly stated "production-ready for this workload: yes, at 8/10... contingent on the fixes in this changeset being merged," naming the one non-blocking gap (no frontend automated tests) as a process risk, not a live production risk — a calibrated claim, not a blanket "ready to ship."

## 2. Pre-Release Checklist

- [ ] Full regression run: backend suite + manual/live frontend verification of every screen touched (no frontend automated suite exists, per `docs/08_Testing/TestingStrategy.md`).
- [ ] Confirm every new migration is additive-only with a working `downgrade()` — verified by actually running upgrade→downgrade→upgrade against a real database, not just reviewed by eye.
- [ ] Confirm no new Dashboard/Reports/Notification/Family-Dashboard read path calls a calculation or recommendation-generating function — grep for new imports of `monte_carlo`, `calculate_goal_probability`, or the recommendation services from any router file that should stay read-only.
- [ ] If the AI Copilot's prompt or fallback logic changed: re-run the full Copilot test file, including the OpenAI-path fake-client tests.
- [ ] Update `CHANGELOG.md` with the release's entries, grouped by category.

## 3. Most Recent Release State (as of this documentation system's compilation)

- 673 backend tests passing, 97.89% coverage.
- Zero backend files touched by the most recent Product Experience Completion mission (Phases 1–10) — confirmed by `git status` at the close of every phase.
- Overall product scorecard: 9/10, **GO WITH MINOR CHANGES** — see `docs/08_Testing/QualityMetrics.md` §4.

---

## Related Documents
`CHANGELOG.md` (repository root) · `docs/10_Operations/OperationsRunbook.md` (the Before-Release/Before-Production checklists this guide's §2 summarizes) · `docs/08_Testing/QualityMetrics.md`


## Related Tests
The full regression suite this guide's pre-release checklist requires — see `08_Testing/TestingStrategy.md`.

---

*Archived original: `docs/13_Archive/ArchivedReports/ReleaseNotes.md`.*
