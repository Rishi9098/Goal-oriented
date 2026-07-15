# User Personas

**Status:** Canonical · **Last verified against code:** 2026-07-06
**Supersedes:** `UserPersonasReport.md`, `FIRST_TIME_USER_REVIEW.md` (both archived).

---

## The 11 Personas

1. **Student** — earliest-stage, minimal income, planning horizon is aspirational rather than concrete.
2. **Fresh Graduate** (0–3 years experience) — first real income, first real goals, high sensitivity to "how do I even start" friction.
3. **Salaried Employee** (mid-career, established) — the core, most-supported persona today; the majority of Goals/Dashboard/Family functionality is built with this persona as the primary target.
4. **Freelancer / Gig Worker** — irregular income makes fixed monthly-contribution goal modeling a real fit problem; presumptive-taxation guidance is unverified research (see `docs/09_Security/ThreatModel.md` §1).
5. **Business Owner** — HUF/business-entity modeling is schema-ready (`huf_entities`, zero consumers today) but not feature-built.
6. **Married Couple** (no children yet, or DINK) — the Family module's spouse-member flow is built for this persona specifically.
7. **Family** (with children) — the single most fully-supported Family-domain persona: child dependents, SSY eligibility, education goals with custom inflation all target this persona directly.
8. **Retiree** (recently retired, still drawing down) — a real, documented gap: no decumulation/withdrawal-phase modeling exists anywhere in the Monte Carlo engine (`docs/02_Architecture/CalculationEngine.md` §5).
9. **Senior Citizen** (75+) — SCSS eligibility modeling exists for the base case; the real scheme's additional 55+/50+ special routes are deliberately unseeded (`docs/02_Architecture/RecommendationEngine.md` §5).
10. **HNI (High Net Worth Individual)** — largely unaddressed; no dedicated portfolio-concentration or complex-holdings modeling exists.
11. **NRI (Non-Resident Indian)** — DTAA/NRO-TDS specifics are explicitly unresearched; do not ship NRI-specific tax guidance until closed (`docs/09_Security/ThreatModel.md` §1, the single highest compliance-risk unverified item).

## Cross-Persona Patterns

Every persona's data ultimately flows through the same household model (`docs/02_Architecture/RecommendationEngine.md` §2) regardless of family structure — a single Student and an 11-person joint family both get exactly one `Household`, differing only in member count. This uniformity is why the household-as-aggregator architectural decision (ADR-002) scales across all 11 personas without per-persona schema branching.

## First-Time User Experience

The onboarding wizard (12 steps) is deliberately kept to a handful of questions per step rather than a full census — a design choice validated directly against first-time-user walkthroughs. The most recent completion mission's Phase 3 added a one-sentence Plan Health explanation to onboarding's closing screen specifically to reduce first-view anxiety around a previously unexplained number (`docs/06_Frontend/FrontendArchitecture.md` §7).

## The One Unresolved, High-Severity Business Risk Across All Personas

**Unknown actual user-base composition** — persona work above is a reasoned model, not validated against who Northstar's real users actually are (life stage, income bracket, family status). This explicitly blocks prioritizing any decumulation feature (Persona 8) and should inform re-checking every "users benefited" assumption anywhere else in this documentation (`docs/09_Security/ThreatModel.md` §4).

---

## Related Documents
`docs/01_Product/Vision.md` · `docs/01_Product/UserJourneys.md` · `docs/02_Architecture/RecommendationEngine.md` (the Family module these personas drive) · `docs/09_Security/ThreatModel.md` (persona-linked compliance risks)


## Related Tests
None — personas are a design model, not a tested artifact; the one open validation question (real user-base composition) is tracked in `09_Security/ThreatModel.md` §4, not a test.

---

*Archived originals: `docs/13_Archive/ArchivedReports/UserPersonasReport.md`, `FIRST_TIME_USER_REVIEW.md`.*
