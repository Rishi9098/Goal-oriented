# Risk Register

**Date:** 2026-07-06
**Method:** Consolidates every risk flagged across Phases 0-6 into one register, so none of them get lost across nine separate report files. Each entry traces to the specific report/phase that surfaced it.

---

## Regulatory / Compliance Risks

| Risk | Source | Severity | Mitigation |
|---|---|---|---|
| AI Advisor may constitute "investment advice" under SEBI's Research Analyst/Investment Adviser framework — not researched this engagement | `AIArchitectureReport.md`, `FeatureGapAnalysisReport.md` #10 | **High** | Must be resolved before V3's explainable-AI-advisor milestone begins; may require legal review, not just product design |
| Account Aggregator (AA) framework regulatory requirements — not researched | `FeatureGapAnalysisReport.md` #2 | **High** | Dedicated research phase required before Account Aggregation is scheduled into any milestone |
| NRI DTAA and NRO-TDS specifics unverified | `UserPersonasReport.md` persona 11 | **Medium-High** | Do not ship any NRI-specific tax guidance until this is closed — flagged as the single highest compliance-risk unverified item in Phase 4 |
| Presumptive taxation scheme eligibility (freelancers/business owners) unverified | `UserPersonasReport.md` personas 4-5 | Medium | Do not build persona-specific tax guidance for these personas until researched |
| NPS's new 20% lump-sum withdrawal tranche tax treatment is genuinely provisional (December 2025 PFRDA rule change, tax treatment not yet fully clarified) | `GovernmentPolicyReport.md` | Medium | Any recommendation touching this must carry the "provisional" confidence flag (`PolicyEngineReport.md`/`AIArchitectureReport.md`'s confidence-scoring design already accounts for this) |
| Senior-citizen-specific old-regime basic exemption slab inconsistently sourced | `UserPersonasReport.md` persona 9 | Low-Medium | Needs primary-source confirmation before stating a specific number to users |
| Recommending HUF/legal structures carries advisory-adjacent liability | `FeatureGapAnalysisReport.md` #4 | Medium | Frame as "consider consulting a CA," never as a directive |

## Security / Privacy Risks

| Risk | Source | Severity | Mitigation |
|---|---|---|---|
| Account aggregation (if built) implies handling third-party financial credentials/consent tokens — categorically higher-risk than current manual-entry model | `FeatureGapAnalysisReport.md` #2 | **High** | Full security architecture review required before this is scheduled |
| Household permission model (who sees whose data within a family) is a real design surface, not an afterthought | `FeatureGapAnalysisReport.md` #3, `PrioritizedBacklog.md` Milestone 4 | Medium | Explicit test coverage required in Milestone 4, not assumed correct by default |
| AI conversation memory (`AI_MESSAGES`) is new PII-adjacent data at rest that doesn't exist in the current schema | `AIArchitectureReport.md` | Low-Medium | Standard data-at-rest protections apply; flagged because it's genuinely new data, not because a specific gap was found |
| Nominee data (name, relationship, sometimes DOB) is new, modest-sensitivity PII | `FeatureGapAnalysisReport.md` #5 | Low | Standard protections sufficient given SEBI's own rule already minimizes required fields (no mandatory PAN/Aadhaar for nominees) |

## Data-Correctness Risks (this engagement's own central theme, made explicit)

| Risk | Source | Severity | Mitigation |
|---|---|---|---|
| Any hardcoded tax section/rate/scheme-status ships wrong the moment the underlying rule changes (proven to happen quarterly for rates, and this exact fiscal year for the entire Act) | Every phase, most acutely `GovernmentPolicyReport.md` and `PrivateProductReport.md` | **High if violated** | The entire Phase 5 versioned-policy-data schema exists specifically to prevent this — the risk is organizational (a future engineer bypassing the schema with a quick hardcoded fix under deadline pressure), not architectural |
| Milestone 2's initial data-seeding could itself introduce an error at the source | `PrioritizedBacklog.md` Milestone 2 | **Medium-High** | Highest data-review rigor of the whole roadmap should apply specifically to this milestone |
| Stale scheme recommended after it closes to new subscribers (the PMVVY/SGB pattern, verified twice in this engagement — Phase 1 and Phase 6) | `GovernmentPolicyReport.md`, `PrivateProductReport.md` | Medium | `status` lifecycle field + hard-gate company policy already designed (Phase 5/`PolicyEngineReport.md`) |

## Business / Strategic Risks

| Risk | Source | Severity | Mitigation |
|---|---|---|---|
| **Unknown actual user-base composition** — this entire engagement's persona work is theoretical until validated against who Northstar's real users actually are (life stage, income bracket, family status) | `ProductRoadmapReport.md` V4 note, `FeatureGapAnalysisReport.md` #8 | **High** | Explicitly blocks prioritizing Decumulation (V4) and should inform re-checking every other "users benefited" estimate in `FeatureGapAnalysisReport.md`, all of which are reasoned estimates, not measured data |
| Household/family features assume a meaningful fraction of users are married/have dependents — unvalidated against actual usage | `FeatureGapAnalysisReport.md` #3 | Medium | Flagged as an open question the report itself cannot answer |
| Building Explainable AI Advisor before the underlying Tax/Goal-Prioritization engines exist would have nothing real to narrate | `AIArchitectureReport.md`, `ProductRoadmapReport.md` | Low (already mitigated by roadmap sequencing) | V3 sequencing already places this correctly after V2's engines |
| Enterprise/Advisor version tracks are entirely unresearched | `ProductRoadmapReport.md` | Low (not yet committed to) | Explicitly flagged as needing dedicated research phases, not sized or scheduled |

## Engineering / Technical Debt Risks (carried forward from the prior session's work, still relevant)

| Risk | Source | Severity | Mitigation |
|---|---|---|---|
| No frontend automated test coverage at all | `TechnicalDebt.md` (prior session) | **High** | Still unresolved as of this engagement; every new V2 milestone in `PrioritizedBacklog.md` adds more untested frontend surface unless this is addressed in parallel |
| In-memory rate limiter can't scale horizontally without Redis | `AUDIT.md` (prior session) | Medium | Unchanged; becomes more relevant if this roadmap succeeds and traffic grows |
| No per-user cost cap on the OpenAI Copilot endpoint | `AUDIT.md`, `TechnicalDebt.md` | Medium | Becomes materially more relevant once the Explainable AI Advisor (V3) increases Copilot usage/sophistication — should be revisited before V3, not after |

---

## Highest-Priority Items on This Register

1. **Unknown user-base composition** — because it silently undermines the confidence of every "users benefited" estimate in the entire Feature Gap Analysis, this is arguably the single most important open item from this whole engagement to resolve before committing engineering time to V2.
2. **SEBI investment-advice classification** — a hard blocker for V3's centerpiece feature, and worth starting the legal/regulatory research now given how long such reviews typically take, rather than waiting until V2 is complete.
3. **The no-per-user-cost-cap gap on Copilot**, carried forward from before this engagement — becomes a live financial-exposure risk the moment usage increases, and this entire roadmap is designed to increase usage.
