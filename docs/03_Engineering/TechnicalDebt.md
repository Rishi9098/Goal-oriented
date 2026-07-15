# Technical Debt Register

**Status:** Canonical · **Last verified against code:** 2026-07-14
**Supersedes:** `TechnicalDebt.md` (07-05, archived), `TechnicalDebtReview.md` (07-07, archived), `GlobalShellTechnicalDebt.md` (archived — folded into `docs/06_Frontend/FrontendArchitecture.md` §12–13 directly, referenced here).
**Purpose:** a single, consolidated, by-category list of every known, verified debt item across this entire documentation system — no speculative items, every one sourced to the canonical doc that verified it.

---

## By Category

### Architecture
| Item | Detail |
|---|---|
| Assumptions disconnected from Monte Carlo | `financial_assumptions.expected_return_*`/`tax_rate`/`retirement_age`/`social_security_monthly` stored, user-editable, read by zero calculations — see `docs/02_Architecture/CalculationEngine.md` §8. |
| FE-005 — React Query bypass | 5 frontend pages (not 4, reconciled this pass) bypass the shared cache — see `docs/06_Frontend/FrontendArchitecture.md` §11. |
| `years_to_goal` computed 3 inconsistent ways | Backend day-count, frontend calendar-year subtraction, and a third ms-based calculation — see `docs/02_Architecture/CalculationEngine.md` §3. |
| API-001–API-009 | Logout doesn't revoke the access token; `income`/`expenses` lack `PATCH`; inconsistent 404-vs-lazy-create; no policy-delete endpoint — see `docs/04_API/RESTAPI.md` §5. |
| DB-001–DB-011 | 12 zero-consumer tables; `tax_sections`' reader doesn't filter effective dates; dead `role` column — see `docs/05_Database/DatabaseSchema.md` §4. |

### Calculation
- `ANNUAL_INFLATION = 0.03` in `monte_carlo.py` is declared and never referenced — confirmed dead code.
- The 70% on-track threshold is a single hardcoded literal, unconfigurable, not derived from anything.
- No golden/hand-calculated numeric test exists for Monte Carlo — every test is a property/invariant check (the correct choice for a stochastic engine, not a coverage gap).

### Frontend
- **FE-001 (High)** — Landing/Sign-in pages market SOC 2, AES-256-at-rest, and OAuth account linking as live capabilities; none exist in the verified backend. **Still open** — not touched by any completed mission phase.
- FE-002/003/004 — onboarding and form copy overstate several fields' real calculation effect.
- FE-006 — `react-hook-form`, its Zod resolver, and the shadcn `Sidebar`/`useIsMobile` hook are declared dependencies with zero real consumer.
- FE-011 — `EducationPlanningSection.tsx` fetches tagged members' scheme eligibility in a sequential, un-parallelized N+1 loop.

### Life Event Engine (new since the earlier debt registers)
- No "Death of a Family Member" event exists — a real, named product-completeness gap.
- Untracked household-bootstrap side effect in the effects audit trail (almost certainly correct behavior, not a bug).
- Unbounded list-input loop in Retirement's optional steps (no max-length validation).
- See `docs/02_Architecture/LifeEventEngine.md` §8 for the full remediation history — 3 of the original 6 release-blocking findings from this engine's own NO-GO audit have since been verified fixed (idempotency, row-level undo fingerprint, row locking).

### AI
- AI-001 — conversation history is never sent to the model, even within one session.
- AI-002 — zero access to Family/Insurance/Schemes/Recommendations/Dashboard data.
- AI-003 — the Dashboard's "AI Copilot" card is pure rule-based logic, inconsistently labeled vs. the Family module's own convention.
- AI-004 — `/copilot`, the one endpoint with real external per-call cost, isn't in the rate limiter's tightened-bucket list.

### Performance
- `scheme_eligibility_service` loads the entire schemes/rules catalog unconditionally on every call — fine today, a real scaling risk at catalog growth.
- `family_dashboard_service` is the single most query-heavy endpoint with no dedicated latency test.

### Security
- Rate limiter is in-memory, single-process — will not correctly share limits across multiple workers or horizontal scale.
- No role/permission (RBAC) system anywhere.
- No encryption-at-rest anywhere in the schema, including `huf_entities.huf_pan` (a government tax ID).
- FE-010 — Delete-account copy overstates the actual (soft) deletion guarantee.

### Testing
- No frontend automated test suite exists at all (11,000+ lines of TSX/TS with zero automated coverage — the single longest-standing HIGH-priority item in this register, first flagged 07-05, still open 07-14).
- **Corrected in V2:** every prior report in this project's history (including this register's own V1) claimed no CI/CD pipeline exists. This was never true — `.github/workflows/ci.yml` has existed since the initial commit, running backend lint+typecheck+test and frontend lint+typecheck on every push/PR. What genuinely doesn't exist is a *CD/deployment* step and a frontend Dockerfile — see `docs/11_Release/DeploymentGuide.md`. Downgraded from "no CI/CD pipeline" (High) to "no CD/deployment automation" (Medium) accordingly.
- Backend tests run against SQLite, not real Postgres — a handful of cascade/`SET NULL` guarantees rest on one-time manual verification, not continuous CI.

### Documentation (resolved by this restructuring)
- 254 loose `.md` files at the repository root — the exact discoverability problem this v2 documentation system (`docs/`) was built to resolve. **Resolved by this restructuring effort itself.**

---

## Explicitly Not Debt (reviewed and confirmed correct — listed so it isn't re-flagged by a future pass)

- `get_db`'s broad `except Exception: rollback` — correct session-dependency behavior, not masked error handling.
- `cast()` calls at the `passlib`/`python-jose` type boundary — standard, correct practice for sealing `Any` leakage from untyped third-party libraries.
- The three-migration column build-up on `dependents` (base shape + 2 later extensions) — a real, normal pattern, not debt.
- `EstateDocument` being strictly status-only, never storing document content — a deliberate scope boundary, not an unfinished feature.

---

## Priority Summary

| Priority | Representative items |
|---|---|
| **High** | FE-001 (security marketing overclaim), no frontend test suite |
| **Medium** | FE-005 (React Query bypass, now 5 files), assumptions/Monte Carlo disconnect, API-001/002, DB-001/002, no CD/deployment automation (CI itself exists and is verified working) |
| **Low** | Most FE-0xx and DB-0xx items, dead code, hardcoded thresholds |
| **Info (positive findings, not debt)** | Every FK has an explicit `ON DELETE` clause; `GET /dashboard`/`GET /reports/summary` are continuously test-verified to agree; `/health` correctly excluded from auth/rate-limiting |

**How to use this register in practice:** several items are one-line fixes (add `/copilot` to the sensitive-prefix rate-limit list; add the missing `UNIQUE` constraint to `health_policy_coverage`) that could be knocked out in an afternoon — don't let them accumulate indefinitely just because none is currently on fire.

---

## Related Documents
Every `docs/02_Architecture/*.md`, `docs/04_API/*.md`, and `docs/05_Database/DatabaseSchema.md` document referenced above — this register is an index into their own "Known Risks"/"Findings" sections, not a duplicate source of truth.


## Related Tests
Each debt item above is either a `test_*.py`-confirmed gap (e.g. "no frontend test suite" is confirmed by `find code/src -iname '*.test.*'` returning nothing) or a documentation-only finding (e.g. the now-corrected CI/CD claim).

---

*Archived originals: `docs/13_Archive/ArchivedReports/TechnicalDebt.md`, `TechnicalDebtReview.md`, `GlobalShellTechnicalDebt.md`.*
