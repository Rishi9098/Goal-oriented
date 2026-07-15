# Private Financial Product Research Report

**Date:** 2026-07-06
**Method:** Live-verified, same standard as Phase 1. This phase surfaced **four major 2025-2026 changes** that a hardcoded product-tax-treatment table would have gotten wrong if written any earlier — direct further evidence for the policy-engine design in Phase 5.

---

## ⚠️ Four Major Findings This Phase

1. **GST on individual life/health insurance premiums dropped to 0% effective 22 September 2025** (from 18%) — group policies are explicitly excluded and remain at 18%. This is a huge, recent, high-impact change: any premium-comparison or insurance-cost calculation in this product must know the payment date relative to 22 Sep 2025, not just apply a flat rate.
2. **Sovereign Gold Bonds (SGB) have been discontinued for new issuance since February 2024** — existing bonds remain valid, and Budget 2026 further restricted the maturity capital-gains exemption to **original subscribers who hold to the full 8-year term** (a secondary buyer no longer gets the same exemption). Another PMVVY-shaped trap: must never be recommended as a "buy new" option.
3. **Debt mutual funds bought on/after 1 April 2023 get zero LTCG benefit and zero indexation** — every gain, regardless of holding period, is taxed at the investor's slab rate under Section 50AA. Units bought *before* 1 April 2023 are grandfathered into the old 12.5%-LTCG-no-indexation treatment. **This means a single debt-fund holding's tax treatment depends on its purchase date, not just its category** — a materially more granular data requirement than equity funds, where the tax rule is holding-period-based only.
4. **ULIPs with annual premiums above ₹2.5 lakh (for policies issued after 1 Feb 2021) lose their Section 10(10D) exemption** and are taxed as capital gains instead (12.5% LTCG / 20% STCG) — but the death benefit remains fully tax-exempt regardless of premium size. ULIPs issued on/before 1 Feb 2021 keep full exemption regardless of premium.

---

## Product Profiles

### Savings Accounts, Fixed Deposits (FD), Recurring Deposits (RD)

**How they work:** Bank-held, principal-guaranteed instruments; FD locks a lump sum for a fixed tenure at a fixed rate, RD builds a corpus via fixed monthly deposits.
**Taxation:** Interest is fully taxable at slab rate (not preferential capital-gains treatment) — TDS applies above ₹40,000/year interest (₹50,000 for senior citizens) per bank, per Section 194A (not independently re-verified this pass, standard convention, flagged as such).
**Recommendation logic:** Core emergency-fund and short-horizon-goal vehicle for every persona; not a genuine wealth-building instrument once inflation and tax are accounted for — the "guaranteed 7% FD" narrative commonly overstates real (inflation- and tax-adjusted) returns, and Northstar's calculation engine should show the *real* return, not just the nominal rate, per Phase 5's inflation-adjustment calculation.

### Mutual Funds (Equity, Debt, Hybrid)

**Equity-oriented funds:** LTCG 12.5% above ₹1.25L/year exemption (>12 months), STCG 20% (≤12 months) — verified in Phase 1, unchanged.
**Debt funds:** See Finding #3 above — purchase-date-dependent tax treatment is a genuinely more complex data requirement than most users (or most competing apps, per the Competitor Analysis) model correctly.
**Hybrid funds:** Tax treatment follows the fund's actual equity allocation (≥65% equity-oriented gets equity treatment; below that, debt treatment) — not independently re-verified this pass, flagged for confirmation before being stated as a hard threshold in-product.
**Recommendation logic:** The purchase-date dependency for debt funds (Finding #3) means Northstar's `assets` schema needs a `purchase_date` per holding (not just a category), which the current schema's generic `Asset` model (Project Discovery) doesn't explicitly capture as a tax-relevant field today.

### Index Funds / ETFs

Same tax treatment as the equity mutual funds they track (LTCG/STCG per Phase 1's equity rules). Primary differentiator versus active equity funds is cost (expense ratio) and tracking-error, not tax treatment — a comparison Northstar could support once fund-level expense-ratio data is available (currently, the schema has no per-holding expense-ratio field).

### Stocks (Direct Equity)

Same LTCG/STCG treatment as equity mutual funds. Requires a demat account — this is where the new SEBI nomination rule (Phase 3) applies directly: every new single-holder demat account needs a nominee or opt-out from September 2026.

### Bonds (Corporate, Government, SGB)

Corporate bond interest is taxed at slab rate; capital gains on sale follow the general debt-instrument rules (see debt mutual fund treatment above as the closest analogy, though direct bonds have their own specific rules not independently re-verified here). **SGB is a closed product for new buyers (Finding #2)** — Northstar must apply the same `status: closed_to_new` lifecycle field designed in Phase 5's `schemes` table to any private product catalog, not just government schemes; the PMVVY lesson generalizes.

### Gold (Physical, Digital, SGB, Gold ETF)

Physical/digital gold: capital gains taxed per standard asset rules, no special exemption. **SGB specifically: original-subscriber-only exemption at 8-year maturity (Finding #2)** — a materially better tax outcome than physical gold *if and only if* held by the original subscriber to full term; a secondary-market SGB buyer (the only way to acquire SGB exposure today, per Finding #2) does not get this benefit, which is a subtle, easily-mis-sold distinction Northstar's product copy must get right.

### REITs / InvITs

**Verified this phase:** dividend taxation depends on whether the underlying SPV opted into the concessional corporate tax regime (Section 115BAA) — taxable at slab rate if it opted in, exempt if not, meaning **two REITs can have different dividend tax treatment for the same investor**, a genuinely fund-specific fact Northstar cannot infer from the "REIT" category alone. Capital gains: LTCG 12.5% (>12 months), STCG 20%. **A transition nuance verified this phase:** the ₹1.25L LTCG exemption did not apply to REIT units for FY 2025-26 specifically, only from FY 2026-27 onward (a Section 115UA amendment) — exactly the kind of effective-dated rule the Phase 5 policy engine schema is built to hold correctly.

### Health Insurance & Term Insurance

**GST removal (Finding #1) is the single biggest recent cost change in this category** — a premium quote from before 22 Sep 2025 and one from after are not comparable without adjusting for the 18-point GST removal. Tax deduction: 80D/123, ₹25,000 (₹50,000 if 60+), doubled if a separate parents' policy exists (Phase 3). Family-floater-vs-standalone-parent-policy tradeoff already covered in Phase 3.

### ULIPs (Unit Linked Insurance Plans)

Bundled insurance + market-linked investment. **Tax treatment bifurcates sharply at the ₹2.5L annual premium threshold for post-Feb-2021 policies (Finding #4).** Northstar's product guidance should be explicit that a ULIP is not automatically "tax-free like PPF" — many users conflate insurance-wrapped products with the EEE government schemes from Phase 1, and this is a real, verified distinction, not a nuance.

### Credit Cards, Personal Loans, Education Loans, Business Loans, Mortgages

Not independently re-verified for 2026-specific regulatory changes in this pass (RBI's credit-card/lending guidelines change periodically but weren't the focus of this research cycle) — these are primarily **liability-side** products already representable in the existing `liabilities` schema (balance, interest rate, monthly payment), and the EMI calculation (Phase 5, Calculation #4) already covers their core math. Education loans carry a specific tax benefit (Section 80E-equivalent, interest deduction with no upper limit for a specified number of years) not independently verified this pass — flagged for a follow-up if the education-planning persona work is prioritized.

### Employer Retirement Plans & Employee Benefits (Gratuity, Leave Encashment, ESOPs)

Not independently researched this pass beyond EPF (already covered in Phase 1). Gratuity, leave encashment, and ESOP taxation each have their own specific rules not verified here — flagged as a genuine gap, since ESOP taxation in particular (perquisite tax at exercise, capital gains at sale) is a real planning need for the salaried/tech-employee persona segment and was not covered.

---

## Cross-Product Pattern: The Policy Engine's Case Gets Stronger

Every single product category researched this phase — insurance GST, SGB, debt funds, REITs, ULIPs — had at least one **effective-dated rule change in the last 12-18 months** that a static, hardcoded tax-treatment table would have shipped incorrectly. Combined with Phase 1's Income Tax Act transition, this confirms the Phase 5 database design's versioned/effective-dated schema isn't over-engineering for a hypothetical — it is the minimum structure needed to be correct across the *products* layer too, not just the *government schemes* layer.

---

## What's Not Covered / Flagged for Follow-Up

Credit card/lending-specific RBI guidelines, ESOP/gratuity/leave-encashment taxation, education-loan interest deduction specifics, hybrid-fund equity-allocation threshold confirmation, and corporate-bond-specific tax mechanics beyond the general debt-instrument analogy used above.
