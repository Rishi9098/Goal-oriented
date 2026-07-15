# Operations Runbook

**Status:** Canonical · **Last verified against code:** 2026-07-14
**Supersedes:** `ProjectOwnersHandbook.md` §7 (Debugging Guide) and §14 (Maintenance Checklist) — archived in full; the Debugging Guide's symptom-first entries are preserved in `docs/03_Engineering/EngineeringHandbook.md` §4 rather than duplicated here, since debugging is a day-to-day engineering activity, not an operations cadence.

---

## 1. Maintenance Cadence

### Weekly
- [ ] Run the full backend test suite — confirm ≥80% coverage and still passing at the ~97%+ level last measured, not just above the hard floor.
- [ ] Run `tsc --noEmit` and `eslint` on the frontend locally too — CI already runs both (`.github/workflows/ci.yml`'s `frontend` job) on every push/PR, but a local run catches issues before they reach a PR.
- [ ] Skim recently merged PRs for any new hardcoded value that should have been a versioned database row.

### Monthly
- [ ] Grep the frontend for the on-track threshold (`"70"`) and any other backend literal, category list, etc. — confirm no new place has silently re-derived a value that should reference one source.
- [ ] Review `seed_policy_data.py`'s citations for freshness — small-savings scheme rates are the specific, named quarterly-cadence risk.
- [ ] Check for any new zero-consumer table or component introduced since last review — either it's deliberate pre-built runway (document it as such) or it's genuinely dead and should be flagged.

### Quarterly
- [ ] **Re-verify every scheme-rate/tax-section row against its real government source** — the single highest-value recurring task in this entire codebase, because a stale government figure is the one class of bug that silently violates Coding Standards Rule 4 without ever throwing an exception.
- [ ] Review `docs/03_Engineering/TechnicalDebt.md` — close at least the smallest, cheapest items each quarter so debt doesn't compound indefinitely.
- [ ] Re-read `docs/03_Engineering/CodingStandards.md` in full — confirm the last quarter's changes didn't drift from any rule without a documented, deliberate decision.
- [ ] If an annual tax-slab change window is approaching, schedule the update explicitly rather than discovering it's stale reactively.

### Before Release
See `docs/11_Release/ReleaseGuide.md` §2 for the full checklist.

### Before Production (first deploy, or any major infrastructure change)
- [ ] Re-read `docs/02_Architecture/SystemArchitecture.md` §10 (Known Risks) in full — several (the in-memory rate limiter, no CD/deployment automation, single-process assumptions) are specifically about production readiness and must be consciously accepted or fixed before real users depend on this.
- [ ] Confirm `JWT_SECRET_KEY`/`OPENAI_API_KEY` are real, environment-provided secrets, never placeholder values.
- [ ] Confirm the rate limiter's `trusted_proxy_ips` matches your actual deployment topology.
- [ ] Decide, deliberately, whether you're accepting the in-memory rate limiter's single-process limitation or replacing it with Redis before scaling past one process.

## 2. Incident Response Pointers

For symptom-first debugging ("a goal's probability changed unexpectedly," "a recommendation disappeared," "the Dashboard looks inconsistent," "a notification is missing," "the AI Copilot's reply seems disconnected"), see `docs/03_Engineering/EngineeringHandbook.md` §4 — each entry names the exact file/function to open, in order, and distinguishes expected behavior from a real regression.

## 3. Health Check

`GET /health` — no auth, excluded from rate limiting, checks liveness + DB connectivity. **Known gap:** its `except Exception` doesn't page a human on DB failure — deferred pending an alerting-backend decision (Datadog/PagerDuty/etc.); the JSON body itself is already orchestrator-readable today.

---

## Related Documents
`docs/03_Engineering/EngineeringHandbook.md` (debugging guide) · `docs/11_Release/ReleaseGuide.md` · `docs/11_Release/DeploymentGuide.md` · `docs/03_Engineering/TechnicalDebt.md`


## Related Tests
The CI pipeline itself (`.github/workflows/ci.yml`) is the automated backbone this runbook's weekly checklist assumes is already running.

---

*Archived original: `docs/13_Archive/ArchivedReports/ProjectOwnersHandbook.md` §7, §14.*
