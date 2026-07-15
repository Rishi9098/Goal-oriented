# User Personas Report

**Date:** 2026-07-06
**Method:** Each persona is grounded in the verified facts from `GovernmentPolicyReport.md` (schemes, tax) and `FamilyHUFPlanningReport.md` (family/HUF/insurance/estate), plus two additional targeted verifications this phase (NRI investment restrictions, HNI product minimums — sources cited inline). Where a detail wasn't independently verified in this pass, it's explicitly flagged rather than stated as fact — several personas below (business owners' presumptive taxation, senior-citizen-specific old-regime exemption slabs, NRI DTAA/TDS specifics) have real open questions flagged for a follow-up research pass rather than guessed at.

---

## 1. Student

| Field | Detail |
|---|---|
| Income | None or small allowance/part-time income; not tax-filing in most cases |
| Goals | Build an emergency fund from scratch; establish a savings *habit*, not yet a specific corpus target |
| Risk tolerance | Should be high given a 40+ year horizon, but behaviorally this persona has never experienced a loss — expect low actual risk tolerance until educated |
| Tax concerns | Effectively none |
| Government scheme eligibility | APY (18-40) is technically eligible, but low-value here since the persona isn't yet a taxpayer and won't be for years — not a priority recommendation |
| Investment behaviour | Very small ticket sizes (₹500-2,000/month), high sensitivity to seeing *any* visible progress |
| Dashboard requirements | Radically simplified — net worth may be near-zero or negative (student loans); progress-toward-habit framing matters more than absolute numbers |
| AI assistance requirements | Educational, first-principles explanations (matches your brief's "explain every concept from first principles" instruction) — this persona is where that instruction matters most literally |

## 2. Fresh Graduate (first job, 0-3 years experience)

| Field | Detail |
|---|---|
| Income | First salary, typically ₹4-12 lakh/year bracket |
| Goals | Emergency fund (first real one), starting retirement savings, a near-term consumer goal (vehicle, further education) |
| Risk tolerance | High (long horizon), but first real decision point: **old vs. new tax regime** — this persona has minimal deductions yet (no home loan, maybe no dependents), so the new regime is very likely optimal, but "very likely" needs to be a calculated comparison, not a default assumption |
| Tax concerns | Regime choice is the single highest-leverage decision; EPF starts automatically the moment they're employed |
| Government scheme eligibility | EPF (mandatory via employer), NPS (voluntary, note employer 80CCD(2) match only if the specific employer offers it), PPF (voluntary) |
| Investment behaviour | First SIPs, often influenced by peers/social media more than a plan — a real behavioral risk this persona's AI assistant should actively counter with grounded, personalized numbers |
| Dashboard requirements | Cash-flow view (this is often the first time this persona has tracked income vs. expenses at all), simple goal-probability framing |
| AI assistance requirements | Regime-choice calculator grounded in *their actual numbers*, not generic advice; plain-language EPF/NPS explainer |

## 3. Salaried Employee (mid-career, established)

| Field | Detail |
|---|---|
| Income | ₹12-30+ lakh/year, single or dual income household |
| Goals | Home purchase, child's education (if applicable), retirement, often multiple concurrent goals competing for the same monthly surplus |
| Risk tolerance | Moderate — real competing near-term (home down payment) and long-term (retirement) goals require genuine risk-profile differentiation *per goal*, which Northstar's existing per-goal risk_profile field already supports architecturally |
| Tax concerns | Old-vs-new regime recalculated annually as deductions (home loan interest, 80C/123 usage, health insurance) accumulate — unlike the fresh graduate, this persona's answer may genuinely be "old regime," and the app must re-evaluate this every year, not assume the graduate-era answer still holds |
| Government scheme eligibility | Full EPF, voluntary PPF/NPS, SSY if a daughter exists, SCSS not yet relevant |
| Investment behaviour | Mix of SIPs, EPF (automatic), possibly direct equity — most likely to have multiple accounts across multiple platforms that a manual-entry-only tool (Northstar's current model) makes tedious to keep current |
| Dashboard requirements | Full net worth, multi-goal view, cash-flow trend over time (not just current month, per the Monarch Money forward-projection gap noted in the Competitor Analysis) |
| AI assistance requirements | Annual regime re-evaluation prompts, goal-prioritization guidance when surplus is insufficient for all active goals simultaneously |

## 4. Freelancer / Gig Worker

| Field | Detail |
|---|---|
| Income | Irregular, often lumpy; no employer-side EPF at all |
| Goals | Emergency fund is disproportionately critical here (income volatility, no employer safety net) — should likely be gated ahead of other goals in any recommendation ordering |
| Risk tolerance | Should generally be more conservative on the *core* emergency layer than an equivalent-income salaried persona, even if the goal-specific risk profile for long-term goals is unchanged |
| Tax concerns | Quarterly advance tax obligations (not deeply verified this pass — flagged for follow-up on exact presumptive-taxation-scheme applicability for freelance/professional income); no employer EPF means the *entire* retirement tax-deduction burden falls on self-contribution (NPS 80CCD(1B), PPF) |
| Government scheme eligibility | No EPF; PPF and self-contribution NPS are this persona's primary tax-advantaged retirement vehicles; APY excluded once income-taxpaying (likely for most freelancers earning enough to matter) |
| Investment behaviour | Often under-saves for retirement specifically because there's no automatic EPF deduction forcing the habit — this is a real behavioral gap a recommendation engine should actively flag, not assume away |
| Dashboard requirements | Income volatility visualization (income smoothing / rolling average), not a single "monthly income" number the way a salaried dashboard can assume |
| AI assistance requirements | Cash-flow smoothing guidance, proactive retirement-gap alerts given the missing-EPF structural disadvantage |

## 5. Business Owner

| Field | Detail |
|---|---|
| Income | Business income, often more volatile and harder to separate from personal finances than salaried income |
| Goals | Business reinvestment vs. personal wealth-building tradeoff, succession planning if family-run |
| Risk tolerance | Already concentrated in one illiquid asset (the business itself) — personal-portfolio risk tolerance for *other* investments should generally skew more conservative to diversify away from that concentration, not naively "high because young" |
| Tax concerns | Presumptive taxation scheme eligibility for smaller businesses/professionals not independently verified this pass — flagged as an open research item; **HUF is most legitimately relevant to this persona specifically**, per Phase 3's finding that HUF needs a real income/asset source to fund it |
| Government scheme eligibility | No EPF (unless the owner also formally employs themselves through the business in a structure that provides it); PPF/NPS self-contribution as with freelancers |
| Investment behaviour | Often under-diversified (over-indexed to the business), may have complex asset structures (business + personal + possibly HUF) |
| Dashboard requirements | Needs to separate business and personal net worth clearly rather than commingle them — a structural schema requirement, not just a UI filter |
| AI assistance requirements | HUF eligibility assessment (per Phase 3's gating criteria), diversification-away-from-business-concentration guidance |

## 6. Married Couple (no children yet, or DINK)

| Field | Detail |
|---|---|
| Income | Dual income, combined household planning |
| Goals | Joint goals (home, travel, eventual family planning) alongside each spouse's individual retirement track |
| Risk tolerance | Needs to be modeled *per spouse* even for joint goals, since India has **no joint tax filing** (each spouse files an individual return) — this is a real, structurally important fact: "household net worth" is a useful aggregate view, but every tax calculation underneath it must remain per-individual |
| Tax concerns | Each spouse independently chooses regime and independently manages their own 80C/123 ceiling — a joint goal funded by both spouses' contributions still needs per-spouse tax attribution to compute correctly |
| Government scheme eligibility | Each spouse independently eligible for EPF/PPF/NPS on their own PAN; a family-floater health policy is a genuinely joint decision (per Phase 3) |
| Investment behaviour | Often has account sprawl across two people's separate pre-marriage accounts that never gets consolidated into a single planning view |
| Dashboard requirements | **A household aggregate view built from two per-individual sub-ledgers**, not a merged single ledger — this is the core "family/household" schema requirement Phase 3 and the Project Discovery Report both flagged as entirely absent from Northstar today |
| AI assistance requirements | Joint-goal contribution splitting guidance that still respects each spouse's individual tax position |

## 7. Family (with children)

| Field | Detail |
|---|---|
| Income | Single or dual income, now with dependents |
| Goals | Education (SSY if a daughter under 10 exists — a concrete, high-confidence automatic recommendation per Phase 1/3), larger emergency fund, family health insurance, life insurance adequacy (term cover sized to replace the earning parent's contribution to family goals — a real calculation the current Northstar has no equivalent of) |
| Risk tolerance | Generally more conservative on the core safety-net layer (health insurance, emergency fund, term cover) than a childless equivalent-income household, while long-horizon goals (retirement, education 15+ years out) can still run higher-risk allocations |
| Tax concerns | Same per-spouse filing structure as married couples, plus now genuinely benefits from HUF consideration if there's a business/ancestral-property source, per Phase 3 |
| Government scheme eligibility | SSY (daughter under 10), all prior schemes continue; family-floater vs. separate-parent-policy decision from Phase 3 becomes actionable the moment dependent parents are also recorded |
| Investment behaviour | Typically the highest number of concurrent goals of any persona (multiple children, multiple horizons) — this is where Northstar's existing goal-prioritization/optimizer logic is most directly valuable, if extended to rank across competing goals rather than optimize one at a time |
| Dashboard requirements | Full household view (per persona 6) plus per-child goal tracking, plus the estate/nomination basics from Phase 3 (a will, at minimum) once there are dependents whose inheritance matters |
| AI assistance requirements | Automatic SSY surfacing for daughters under 10, term-insurance-adequacy calculation, will/nomination nudge once dependents are recorded |

## 8. Retiree (recently retired, still drawing down)

| Field | Detail |
|---|---|
| Income | Pension/annuity/withdrawal income, not salary — the entire "monthly income" concept changes character |
| Goals | Shift from *accumulation* to *sustainable withdrawal* — a fundamentally different calculation than anything in Northstar's current Monte Carlo engine, which is built around "will I reach a target," not "will my corpus last through an unknown lifespan while I withdraw from it" |
| Risk tolerance | Lower for the near-term income-generating portion of the portfolio; some allocation can still run higher-risk if the horizon (spouse's life expectancy, legacy goals) genuinely extends further |
| Tax concerns | NPS exit taxation is directly relevant and, per Phase 1, genuinely unsettled for the newly-permitted extra 20% lump-sum tranche — this persona is exactly who needs the "provisional, not confirmed" tax-treatment flag from the Government Policy Report surfaced prominently, not glossed over |
| Government scheme eligibility | SCSS (60+, ₹30L cap, 8.2% verified, but interest fully taxable — a common misconception this persona in particular needs corrected, since PPF/SSY habits from earlier life stages are EEE and SCSS is not); legacy PMVVY policyholders (pre-March 2023) continue at their locked-in rate |
| Investment behaviour | Shifting from SIP/accumulation mode to withdrawal/income mode — a mode Northstar's UI has no concept of today (everything is framed as "contribution" and "target") |
| Dashboard requirements | Withdrawal-sustainability view (a genuinely new calculation type — see Phase 5), income-source breakdown (SCSS/NPS/pension/annuity), not a contribution-tracking view |
| AI assistance requirements | NPS withdrawal-tax guidance with explicit uncertainty flagged, SCSS-vs-PPF tax-treatment correction, sustainable-withdrawal-rate calculation |

## 9. Senior Citizen (75+, or simply "elderly" as distinct from "recently retired")

| Field | Detail |
|---|---|
| Income | Often lower and more fixed than the "recently retired" persona; may be more dependent on family/children |
| Goals | Capital preservation and predictable income are now the dominant goals, essentially exclusively |
| Risk tolerance | Should default low; any equity exposure at this stage is a deliberate, explicit choice, not a default |
| Tax concerns | Higher 80D health-insurance deduction ceiling (₹50,000, verified in Phase 1) applies; **a specific higher basic-exemption slab for senior/super-senior citizens under the old tax regime was referenced in some sources during this research but not independently re-verified with a primary source in this pass — flagged as needing confirmation before stating a specific number to users** |
| Government scheme eligibility | SCSS is the primary vehicle; family-floater-vs-standalone-parent-policy decision (Phase 3) is *about* this persona from the adult child's planning perspective as much as the senior's own |
| Investment behaviour | Minimal new investment activity typically; mostly managing existing corpus and income streams |
| Dashboard requirements | Extremely simple, large-text, income-focused — likely not this persona's own primary interaction mode in practice (an adult child managing on their behalf is at least as common a real usage pattern, which has its own access/permissions implications for a family-view feature) |
| AI assistance requirements | Simple, jargon-free income and tax-treatment explanations |

## 10. HNI (High Net Worth Individual)

| Field | Detail |
|---|---|
| Income | Typically classified at **₹5 crore+ in investable financial assets** (verified this phase) |
| Goals | Wealth preservation, tax-efficient structuring, legacy/estate planning, often multi-generational |
| Risk tolerance | Individually variable, but typically has room for genuinely alternative/illiquid allocations that lower-net-worth personas shouldn't be steered toward |
| Tax concerns | HUF and trust structuring both become genuinely relevant at this asset scale (Phase 3's HUF-eligibility gating criteria are most likely to be *met* by this persona), estate planning is not optional |
| Government scheme eligibility | Government schemes become largely irrelevant at this scale relative to their contribution ceilings (₹1.5-2L NPS ceiling is immaterial against a ₹5Cr+ portfolio) — this persona's needs are almost entirely in the *private product* domain, not the government-scheme domain |
| Investment behaviour | **PMS (Portfolio Management Services): ₹50 lakh minimum. AIF (Alternative Investment Funds) Category II/III: ₹1 crore minimum.** Typical allocation observed: 40-50% equity, 20-30% debt, 10-20% alternatives, 5-10% gold/commodities (verified this phase) |
| Dashboard requirements | Multi-asset-class consolidated view spanning PMS/AIF/direct equity/real estate/gold — a materially more complex aggregation problem than any other persona, and one Northstar's current schema (bank-account-style assets/liabilities) doesn't model at all |
| AI assistance requirements | Sophisticated scenario modeling, HUF/trust structuring guidance, estate-planning coordination — this persona is the least well served by a rule-based fallback Copilot and the most likely to expect genuinely reasoned, defensible advice with real stakes |

## 11. NRI (Non-Resident Indian)

| Field | Detail |
|---|---|
| Income | Foreign-earned, with specific rules governing how it can be invested back into India |
| Goals | Often maintaining Indian family obligations (supporting parents, property) alongside foreign-jurisdiction retirement planning — a genuinely dual-country planning problem |
| Risk tolerance | Individually variable, no NRI-specific pattern found |
| Tax concerns | Complex — DTAA (Double Taxation Avoidance Agreement) treatment and NRO-account TDS specifics were **not independently verified in this pass** and should not be stated as fact in-product without further research; this is one of the highest-compliance-risk personas to get wrong |
| Government scheme eligibility (verified this phase) | **Cannot open a new PPF account** — an existing pre-NRI-status PPF can continue but cannot be extended in 5-year blocks the way a resident's can, and maturity proceeds can only go to an NRO account, repatriable up to **USD 1 million/year**. **Cannot open SSY** (confirmed in Phase 1). **NPS is available** — requires 18-70 age, an active NRE or NRO account, and standard KYC/PAN; NRE-account contributions are freely repatriable, NRO-account contributions capped at the same USD 1M/year repatriation limit. |
| Investment behaviour | Must operate through NRE (foreign-earned, freely repatriable) or NRO (India-earned, e.g. rental income, repatriation-capped) accounts — a fundamentally different account architecture than every other persona here, none of which distinguish repatriable vs. non-repatriable capital at all |
| Dashboard requirements | Needs an NRE/NRO capital-source distinction as a first-class schema concept, not just an account label — repatriation limits are a genuine constraint on what "liquid" means for this persona that no other persona faces |
| AI assistance requirements | Extremely cautious, well-sourced guidance given the unverified DTAA/TDS gap above — this persona is the strongest argument in the whole engagement for the AI Advisor's "confidence score" and "required assumptions" fields (per your original brief) rather than confident-sounding but unverified tax advice |

---

## Cross-Persona Patterns Worth Carrying Into Phase 5 (Database Design)

1. **Household/family is a real, recurring requirement** across personas 6, 7, 9, and partially 10 — not a niche feature.
2. **Per-individual tax attribution must survive inside any household aggregate** — India's no-joint-filing structure makes this a hard constraint, not a nice-to-have.
3. **Withdrawal/decumulation (personas 8, 9) is architecturally absent from Northstar today** — the entire calculation engine is accumulation-oriented (Monte Carlo toward a target), and retirees need the inverse problem (sustainable withdrawal from an existing corpus).
4. **NRI capital has a repatriability dimension no other persona's money has** — a schema-level distinction (NRE vs. NRO sourced), not just a label.
5. **HNI asset classes (PMS, AIF) don't fit the current `assets` table's implicit "bank-account-like" shape** — they need their own richer representation (lock-in, redemption terms, manager, category).

---

## What's Not Covered / Flagged for Follow-Up

- Presumptive taxation scheme eligibility for freelancers/small business owners (persona 4, 5) — not verified this pass.
- Senior-citizen-specific basic exemption slab under the old regime (persona 9) — referenced inconsistently across sources, needs a primary-source confirmation before being stated to users.
- NRI DTAA and NRO-TDS specifics (persona 11) — flagged as the single highest compliance-risk open item across all 11 personas.
