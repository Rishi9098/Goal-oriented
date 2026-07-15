# Threat Model

**Status:** Canonical · **Last verified against code:** 2026-07-06, cross-checked 2026-07-13
**Supersedes:** `RiskRegister.md` (archived — consolidates every risk flagged across the project's early planning phases into one register).
**Scope:** regulatory/compliance, security/privacy, data-correctness, and business/strategic risk — deliberately broader than `docs/09_Security/SecurityArchitecture.md`'s implementation-level security controls.

---

## 1. Regulatory / Compliance Risks

| Risk | Severity | Mitigation |
|---|---|---|
| The AI Advisor may constitute "investment advice" under SEBI's Research Analyst/Investment Adviser framework — not researched | **High** | Must be resolved before any advice-adjacent AI milestone begins; likely requires legal counsel review, not just product design. Restated and reconfirmed as still-open in `docs/07_AI/AIArchitecture.md` §9's "Regulatory positioning, flagged as unresolved." |
| Account Aggregator (AA) framework regulatory requirements — not researched | **High** | A dedicated research phase required before Account Aggregation is scheduled into any milestone. |
| NRI DTAA and NRO-TDS specifics unverified | Medium-High | Do not ship any NRI-specific tax guidance until closed — the single highest compliance-risk unverified item found in the project's persona research. |
| Presumptive taxation scheme eligibility (freelancers/business owners) unverified | Medium | Do not build persona-specific tax guidance for these personas until researched. |
| NPS's 20% lump-sum withdrawal tax treatment is genuinely provisional (a December 2025 regulatory rule change) | Medium | Any recommendation touching this must carry an explicit "provisional" confidence flag. |
| Senior-citizen basic exemption slab inconsistently sourced | Low-Medium | Needs primary-source confirmation before stating a specific number to users. |
| Recommending HUF/legal structures carries advisory-adjacent liability | Medium | Frame as "consider consulting a CA," never as a directive. |

## 2. Security / Privacy Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Account aggregation, if built, implies handling third-party financial credentials/consent tokens — categorically higher-risk than the current manual-entry model | **High** | A full security architecture review is required before this is scheduled — not yet started. |
| Household permission model (who sees whose data within a family) is a real design surface | Medium | Explicit test coverage required whenever shared-household-login access is built — not assumed correct by default. Directly relevant to `docs/02_Architecture/RecommendationEngine.md` §2's `household_members.role` dead column (a forward-looking placeholder for exactly this). |
| AI conversation memory (proposed) is new PII-adjacent data at rest that doesn't exist in the current schema | Low-Medium | Standard data-at-rest protections apply once built — flagged because it's genuinely new data, not because a specific gap exists yet. See `docs/07_AI/AIArchitecture.md` §8. |
| Nominee data (name, relationship, sometimes DOB) is new, modest-sensitivity PII | Low | Standard protections sufficient — the relevant rule already minimizes required fields. |

## 3. Data-Correctness Risks (this project's own central theme)

| Risk | Severity | Mitigation |
|---|---|---|
| Any hardcoded tax section/rate/scheme-status ships wrong the moment the underlying rule changes (proven to happen quarterly for rates, and within one fiscal year for an entire Act renumbering) | **High if violated** | The entire versioned-policy-data schema (`docs/05_Database/DatabaseSchema.md`) exists specifically to prevent this. The remaining risk is organizational — a future engineer bypassing the schema with a hardcoded fix under deadline pressure — not architectural. Directly the subject of Coding Standards Rule 2 and Rule 4. |
| Initial data-seeding could itself introduce an error at the source | Medium-High | The highest data-review rigor should apply specifically to any future seed-data change. |
| A scheme recommended after it closes to new subscribers (the PMVVY pattern) | Medium | Already mitigated — the `status` lifecycle field + hard-gate short-circuit is verified, tested, and documented in `docs/02_Architecture/RecommendationEngine.md` §5. |
| `tax_sections`' one real consumer doesn't filter by `effective_from`/`effective_to` | Low today, real if a second row is ever seeded | See DB-003, `docs/05_Database/DatabaseSchema.md` §4. |

## 4. Business / Strategic Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Unknown actual user-base composition — persona work is theoretical until validated against real usage | **High** | Explicitly blocks prioritizing any decumulation/retirement-drawdown feature and should inform re-checking every "users benefited" estimate elsewhere in this documentation, all of which are reasoned estimates, not measured data. |
| Household/family features assume a meaningful fraction of users are married/have dependents — unvalidated | Medium | Flagged as an open question this documentation cannot answer on its own. |
| Enterprise/Advisor version tracks are entirely unresearched | Low (not yet committed to) | Needs dedicated research phases, not sized or scheduled. |

## 5. Engineering / Technical Debt Risks (cross-reference)

The single largest, longest-standing risk in this category — **no frontend automated test coverage at all** — is tracked in full in `docs/03_Engineering/TechnicalDebt.md` rather than duplicated here; every new frontend feature adds more untested surface unless addressed in parallel.

---

## Related Documents
`docs/09_Security/SecurityArchitecture.md` (implementation-level controls) · `docs/03_Engineering/TechnicalDebt.md` · `docs/07_AI/AIArchitecture.md` §9 (AI-specific safety/regulatory posture) · `docs/02_Architecture/RecommendationEngine.md` (the versioned-data discipline that mitigates the data-correctness risks above)


## Related Tests
None — this document's risks are largely unresearched/unvalidated by design (regulatory questions, user-base composition) rather than code-testable claims.

---

*Archived original: `docs/13_Archive/ArchivedReports/RiskRegister.md`.*
