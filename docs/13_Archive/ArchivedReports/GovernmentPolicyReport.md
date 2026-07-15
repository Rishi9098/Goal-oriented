# Government Policy Report — Indian Financial Planning Schemes

**Date:** 2026-07-06
**Method:** Every figure below was verified via live web search against current (2026) sources — not recalled from training data. Rates that change quarterly (SCSS, SSY, PPF) are marked with the specific quarter verified. Sources are cited per scheme.
**Scope of this pass:** The 9 highest-impact schemes for a retail financial planner (retirement, child, senior-citizen, and general long-term savings categories) plus the core tax framework. This is **not exhaustive** — the brief's full list (PMJJBY, PMSBY, Ayushman Bharat, PMAY, Mudra loans, and others) is not covered in this pass; flagged for a follow-up if you want the full catalog before building the policy engine's initial schema.

---

## ⚠️ Single Most Important Finding: The Tax Law Itself Is Being Replaced

**The Income-tax Act, 1961 is being replaced by the Income-tax Act, 2025, effective 1 April 2026 (Tax Year 2026-27).** Every section number a financial planner has memorized is changing — Section 80C becomes **Section 123**, and the Act introduces a single "Tax Year" concept replacing the Financial Year/Assessment Year distinction. The deduction amounts and eligible instruments are unchanged; only the citations move. Returns filed in July 2026 for income earned in FY 2025-26 still use the old Section 80C numbering; only Tax Year 2026-27 onward uses Section 123.

**Architectural implication (this is the whole reason "never hardcode policies" is in your brief):** any policy engine for this product must store section/citation references as **versioned, effective-dated data**, not as string literals anywhere in code, database seed data, or user-facing copy. A hardcoded `"Section 80C"` string anywhere in this codebase becomes wrong the day this product's users start filing for Tax Year 2026-27. This single fact should be treated as the design constraint that validates the "configurable policy engine, not hardcoded" requirement in your brief — it isn't a hypothetical future-proofing concern, it is happening in the exact fiscal year Northstar would need to be correct for.

*Source: [Income Tax Act 2025 vs 1961 — Complete Section Mapping Guide](https://taxonation.com/show-detail-article/279744/income-tax-act-2025-vs-1961-the-complete-section-mapping-guide), [Section 123 of Income Tax Act 2025 — ClearTax](https://cleartax.in/s/section-123-income-tax-act-2025), [Income Tax Act 2025: Key Changes — ClearTax](https://cleartax.in/s/income-tax-act-2025)*

---

## Tax Framework (applies across every scheme below)

### Income Tax Slabs — Tax Year 2026-27

Budget 2026 made **no change** to slabs from FY 2025-26.

| New Tax Regime (default) | Rate |
|---|---|
| ₹0 – ₹4 lakh | Nil |
| ₹4 – ₹8 lakh | 5% |
| ₹8 – ₹12 lakh | 10% |
| ₹12 – ₹16 lakh | 15% |
| ₹16 – ₹20 lakh | 20% |
| ₹20 – ₹24 lakh | 25% |
| Above ₹24 lakh | 30% |

Section 87A rebate makes taxable income up to ₹12 lakh effectively tax-free under the new regime (₹60,000 rebate). **Old regime** basic exemption is ₹2.5 lakh, with different slabs, but permits deductions (80C/123, 80D, HRA, home-loan interest) that the new regime mostly disallows. The new regime is the default; taxpayers must actively opt into the old regime to use deduction-based planning — **this is a first-order decision every user of this product needs help making, and it depends entirely on how many deductions they actually have (i.e., depends on the scheme data below).**

*Source: [Income Tax Slabs for FY 2026-27 — Axis Max Life](https://www.axismaxlife.com/blog/tax-savings/income-tax-slab-2026-27), [Budget 2026-27 — HDFC Bank](https://www.hdfc.bank.in/blogs/union-budget/budget-2026-27-income-tax-act-2026-tax-slabs-stt)*

### Key Deductions (old regime only)

| Section (1961 Act) | Section (2025 Act, from Tax Year 2026-27) | Limit | What qualifies |
|---|---|---|---|
| 80C | 123 | ₹1,50,000 combined | PPF, EPF (employee share), ELSS, NSC, SSY, SCSS principal, life insurance premium, home-loan principal, tuition fees |
| 80CCD(1B) | (mapping not yet independently verified — treat as pending) | ₹50,000, over and above 80C/123's ₹1.5L | Additional voluntary NPS contribution |
| 80D | (mapping not yet independently verified) | ₹25,000 (self/spouse/children); ₹50,000 if the assessee is 60+ | Health insurance premiums |

Combined own-NPS-contribution ceiling: up to ₹2,00,000 (₹1.5L under 80C/123 + ₹50K under 80CCD(1B)).

*Source: [Income Tax Deductions List FY 2026-27 — Kotak Life](https://www.kotaklife.com/insurance-guide/savingstax/income-tax-deductions-list), [BusinessToday — Section 80C becomes Section 123](https://www.businesstoday.in/personal-finance/tax/story/income-tax-act-2025-section-80c-becomes-section-123-from-april-1-2026-heres-what-taxpayers-must-know-522120-2026-03-24)*

### Capital Gains (equity & equity mutual funds) — unchanged by Budget 2026

- **LTCG** (holding > 12 months): 12.5%, with the first ₹1.25 lakh/year exempt.
- **STCG** (holding ≤ 12 months): 20% (raised from 15% by Budget 2024; unchanged since).

*Source: [ClearTax LTCG](https://cleartax.in/s/long-term-capital-gains-ltcg-tax), [Mutual Fund Taxation India 2026](https://www.onepercentclub.io/blog/mutual-fund-taxation-india/)*

---

## Scheme Profiles

### 1. Public Provident Fund (PPF)

| Field | Value |
|---|---|
| Governing authority | Ministry of Finance / RBI (operated via post offices and authorized banks) |
| Purpose | Long-term, risk-free general savings with full tax exemption |
| Eligibility | Any resident individual; one account per person (a guardian may open one for a minor) |
| Age requirement | None (minors via guardian) |
| Income requirement | None |
| Investment limit | ₹500 min – ₹1,50,000 max per year |
| Lock-in | 15 years; partial withdrawal allowed after 5 years; loan against balance after 1 year (up to 25%) |
| Returns | **7.1% p.a.**, verified for Q1 FY 2026-27, compounded annually, unchanged since Jan 2023 |
| Risk | None (sovereign-backed) |
| Tax treatment | **EEE** — contribution deductible under 80C/123 (old regime only), interest tax-free, maturity tax-free |
| Withdrawal rules | Full withdrawal only at 15-year maturity (extendable in 5-year blocks); premature closure allowed only for specific medical/education reasons after 5 years, with a rate penalty |
| Documents | KYC (PAN, address proof), account-opening form |
| Advantages | Zero risk, full tax exemption, disciplined long horizon, loan facility |
| Limitations | Long lock-in, contribution cap too low to be a sole retirement vehicle for higher earners, no liquidity before 5 years |
| Ideal user | Any risk-averse saver wanting a guaranteed, tax-free component of their portfolio, especially in the old tax regime |
| Planning scenarios | Emergency-fund overflow, child's future education (paired with SSY if a girl child), a "safe floor" allocation within a retirement plan |
| API availability | None public; rate changes announced quarterly by Ministry of Finance press release |
| Update frequency | Interest rate: quarterly. Contribution limits/tax rules: annual budget cycle (rare mid-year change) |

*Source: [ClearTax PPF](https://cleartax.in/s/ppf), [Bajaj Finserv PPF Interest Rate 2026–27](https://www.bajajfinserv.in/investments/ppf-interest-rates)*

---

### 2. Employees' Provident Fund (EPF)

| Field | Value |
|---|---|
| Governing authority | EPFO (Employees' Provident Fund Organisation), under Ministry of Labour |
| Purpose | Mandatory retirement savings for salaried employees |
| Eligibility | Employees of establishments with 20+ employees (some smaller establishments covered too) |
| Age requirement | Working-age employment |
| Income requirement | Mandatory below a wage ceiling; voluntary above it in many cases |
| Investment limit | 12% of (Basic + DA) from employee, 12% from employer — of the employer's 12%, 8.33% routes to EPS (pension) and 3.67% to EPF |
| Lock-in | Until retirement/resignation with a 2-month gap, though full withdrawal has conditions |
| Returns | **8.25% p.a. for FY 2025-26**, unchanged for a third consecutive year; FY 2026-27 rate not yet announced as of this research (declared near fiscal year-end) |
| Risk | None (sovereign-managed) |
| Tax treatment | EEE if the employee completes 5 years of continuous service; otherwise the employer's contribution + interest becomes taxable on early withdrawal |
| Withdrawal rules | Full withdrawal on retirement/2-month unemployment gap; partial withdrawal permitted for home purchase, medical treatment, marriage, education under specific EPFO rules |
| Documents | UAN (Universal Account Number), linked Aadhaar, bank account |
| Advantages | Employer-matched, disciplined, tax-free if held 5+ years |
| Limitations | Illiquid, rate not user-controllable, job-hopping before 5 years triggers tax |
| Ideal user | Every salaried employee — this is largely automatic, not opt-in |
| Planning scenarios | Retirement corpus base layer; a "switched jobs mid-year" scenario needs to check the 5-year continuity rule before assuming tax-free status |
| API availability | EPFO member portal has login-gated balance access; no public developer API found in this research pass |
| Update frequency | Interest rate: annual (declared by EPFO's Central Board of Trustees near FY end) |

*Source: [ClearTax EPF Interest Rate](https://cleartax.in/s/epf-interest-rate), [Bajaj Finserv EPF Interest Rate](https://www.bajajfinserv.in/investments/epf-interest-rate)*

---

### 3. National Pension System (NPS)

| Field | Value |
|---|---|
| Governing authority | PFRDA (Pension Fund Regulatory and Development Authority) |
| Purpose | Voluntary, market-linked retirement corpus with the largest tax-deduction ceiling of any scheme |
| Eligibility | Any Indian citizen (resident or NRI), 18–70 for new Tier I accounts |
| Age requirement | 18–70 to join; corpus payout structured around age 60 |
| Income requirement | None to join; self-employed vs. salaried changes the deduction formula |
| Investment limit | No upper cap on contribution; deduction caps apply (see below) |
| Lock-in | Tier I: until age 60 (partial withdrawal exceptions exist). Tier II: no lock-in, but must stay 3 years to claim 80C/123 |
| Returns | Market-linked (equity/debt/govt-securities mix chosen by subscriber or auto-allocated); not a fixed rate |
| Risk | Low–moderate–high depending on the subscriber's chosen equity/debt/G-sec split |
| Tax treatment | Employee's own contribution: up to 10% of (Basic+DA) under 80CCD(1), within the overall ₹1.5L 80C/123 ceiling. **Additional ₹50,000 under 80CCD(1B)**, over and above the ₹1.5L. Employer's contribution: up to 10% of salary (14% under the new tax regime) deductible under 80CCD(2), **available even under the new regime** — the one NPS benefit that survives regime choice. |
| Withdrawal rules | **Changed December 2025 (PFRDA):** non-government subscribers can now withdraw **up to 80% as lump sum** at exit, with a minimum 20% annuitization only required for corpus above ₹12 lakh (more flexible than the historical 60/40 split). Of the amount withdrawn, only 60% of total accumulated wealth is unconditionally tax-exempt under Section 10(12A); the newly-permitted extra 20% lump sum is **not automatically tax-free** and may be taxed at slab rate absent a future clarifying amendment. Partial withdrawal of up to 25% of *own* contributions (not employer's) allowed after 3 years, for specified purposes (critical illness, child's education/marriage). |
| Documents | PAN, Aadhaar, bank account, PRAN (Permanent Retirement Account Number) issuance |
| Advantages | Highest combined tax-deduction ceiling of any single instrument (up to ₹2L own + employer 80CCD(2) uncapped by the 1.5L ceiling), employer contribution survives new-regime, market-linked upside |
| Limitations | Illiquid until 60, complex withdrawal taxation (the December 2025 rule change makes the "extra 20%" tax treatment a genuine open question your calculation engine must model conservatively until further clarified), returns not guaranteed |
| Ideal user | Salaried employees in the old regime maximizing deductions, or new-regime employees whose employer offers 80CCD(2) contributions, or anyone wanting a low-cost market-linked retirement vehicle |
| Planning scenarios | "How much of my retirement contribution should go to NPS vs. EPF vs. PPF" is the single most common real planning question this scheme touches — depends on regime choice, employer NPS matching availability, and risk appetite |
| API availability | PFRDA/NSDL (now Protean) have subscriber-facing portals; no public developer API found in this pass |
| Update frequency | Withdrawal/exit rules: changed materially as recently as December 2025 — this scheme's rules move faster than PPF/SSY's. Tax treatment of the new 20% lump-sum tranche should be treated as **provisional** until confirmed by a Finance Ministry circular. |

*Source: [ClearTax NPS](https://cleartax.in/s/nps-national-pension-scheme), [NPS Withdrawal Rules 2026 — Protean](https://www.proteantech.in/articles/lump-sum-revolution-with-nps/), [New NPS withdrawal rules taxation — 1Finance](https://1finance.co.in/blog/new-nps-withdrawal-rules-taxation/)*

---

### 4. Sukanya Samriddhi Yojana (SSY)

| Field | Value |
|---|---|
| Governing authority | Ministry of Finance, via post offices/banks |
| Purpose | Dedicated long-term savings for a girl child's education/marriage |
| Eligibility | Resident parent/legal guardian of a girl child under 10; max 2 accounts per family (3rd allowed only for twins/triplets in specific cases) |
| Age requirement | Girl child must be under 10 at account opening |
| Income requirement | None |
| Investment limit | ₹250 min – ₹1,50,000 max per year |
| Lock-in | Deposits for 15 years from opening; account matures 21 years from opening (or on the girl's marriage after 18, whichever earlier) |
| Returns | **8.2% p.a., verified for Q1 FY 2026-27**, compounded annually |
| Risk | None (sovereign-backed) |
| Tax treatment | **EEE** — same structure as PPF |
| Withdrawal rules | Up to 50% withdrawable once the girl turns 18 (for higher education); full maturity at 21 years or marriage after 18 |
| Documents | Girl's birth certificate, guardian KYC |
| Advantages | Highest fixed-return EEE instrument among government schemes surveyed, purpose-built discipline |
| Limitations | Not available for a boy child, per-family account cap, very long horizon |
| Ideal user | Parents/guardians of a girl child under 10 planning for her education or marriage |
| Planning scenarios | Should be the default first suggestion in this product's "education goal" flow whenever the user has a daughter under 10 — a concrete, high-confidence recommendation-engine rule |
| API availability | None found |
| Update frequency | Interest rate: quarterly |

*Source: [ClearTax SSY](https://cleartax.in/s/sukanya-samriddhi-yojana), [BankBazaar SSY](https://www.bankbazaar.com/saving-schemes/sukanya-samriddhi-account-interest-rate.html)*

---

### 5. Senior Citizens' Savings Scheme (SCSS)

| Field | Value |
|---|---|
| Governing authority | Ministry of Finance, via post offices/banks |
| Purpose | Regular quarterly income for senior citizens with capital safety |
| Eligibility | Individuals 60+; or 55+ if retired under superannuation/VRS (within 1 month of receiving retirement funds); retired defense personnel 50+ |
| Age requirement | 60 (or the early-retiree exceptions above) |
| Income requirement | None |
| Investment limit | ₹1,000 min – ₹30,00,000 max |
| Lock-in | 5 years, extendable once by 3 years |
| Returns | **8.2% p.a., verified for Jul–Sep 2026 quarter**, paid out quarterly (Apr 1 / Jul 1 / Oct 1 / Jan 1) — this is one of the highest guaranteed rates of any scheme surveyed |
| Risk | None (sovereign-backed) |
| Tax treatment | Principal deductible under 80C/123 (old regime); **interest is fully taxable at slab rate** — not EEE, unlike PPF/SSY |
| Withdrawal rules | Premature closure allowed with a rate penalty after 1 year |
| Documents | Age proof, KYC, (retirement proof if using the early-eligibility route) |
| Advantages | Highest safe quarterly-income rate surveyed, simple, government-backed |
| Limitations | Interest fully taxable (a common user misconception this product should correct), ₹30L cap may be insufficient for a large retirement corpus |
| Ideal user | Retirees needing predictable quarterly cash flow; a core "retirement income phase" (as opposed to "accumulation phase") recommendation |
| Planning scenarios | Should be surfaced automatically once a user's age crosses 60 and their goal shifts from accumulation to income — with an explicit tax-treatment warning, since users often confuse it with PPF's tax-free status |
| API availability | None found |
| Update frequency | Interest rate: quarterly |

*Source: [ClearTax SCSS](https://cleartax.in/s/senior-citizen-savings-scheme), [Upstox — SCSS Jul-Sep 2026](https://upstox.com/news/personal-finance/investing/senior-citizen-savings-scheme-scss-interest-rate-july-september-2026/article-196140/)*

---

### 6. National Savings Certificate (NSC)

| Field | Value |
|---|---|
| Governing authority | Ministry of Finance, via post offices |
| Purpose | Fixed-tenure, tax-deductible general savings |
| Investment limit | No stated maximum found in this pass; commonly cited as no upper cap |
| Lock-in | 5 years |
| Returns | **7.7% p.a.** |
| Tax treatment | Principal deductible under 80C/123; interest is taxable but is deemed reinvested each year (and itself qualifies for 80C/123 in that year) except in the final year, when it's paid out and fully taxable |
| Ideal user | Old-regime taxpayers wanting a fixed-tenure alternative to PPF with a shorter lock-in |
| Update frequency | Interest rate: quarterly |

*Source: [ClearTax NSC](https://cleartax.in/s/nsc-national-savings-certificate)*

---

### 7. Kisan Vikas Patra (KVP)

| Field | Value |
|---|---|
| Governing authority | Ministry of Finance, via post offices |
| Purpose | Simple capital-doubling savings certificate |
| Investment limit | ₹1,000 min, no stated maximum |
| Returns | **7.5% p.a.**, doubles invested capital in 115 months |
| Tax treatment | **No 80C/123 deduction** — interest is fully taxable; this is a key differentiator from NSC/PPF that users commonly confuse |
| Ideal user | Someone wanting a simple, non-tax-linked doubling instrument — generally a weaker choice than PPF/NSC for anyone with 80C/123 headroom remaining |
| Update frequency | Interest rate: quarterly |

*Source: [ClearTax KVP](https://cleartax.in/s/kisan-vikas-patra)*

---

### 8. Atal Pension Yojana (APY)

| Field | Value |
|---|---|
| Governing authority | PFRDA |
| Purpose | Guaranteed minimum pension for the unorganized-sector/lower-income working population |
| Eligibility | Indian citizens 18–40 with a savings bank/post-office account linked to Aadhaar and mobile |
| Age requirement | 18–40 to join |
| Income requirement | **Income taxpayers have been ineligible since October 2022** — if a subscriber is later found to be a taxpayer, the account is closed and only accumulated savings returned, no bonus |
| Investment limit | Contribution scales by age-at-joining and chosen pension tier; e.g., ₹42/month at 18 for a ₹1,000 pension, up to ₹1,454/month at 40 for a ₹5,000 pension |
| Returns | Guaranteed monthly pension of ₹1,000–₹5,000 after age 60 (government guarantees the shortfall if fund returns are insufficient) |
| Risk | None to the subscriber (government-guaranteed minimum) |
| Withdrawal rules | Pension begins at 60; premature exit only in death/terminal-illness cases |
| Advantages | Truly guaranteed minimum pension, extremely low entry cost |
| Limitations | Income-taxpayer exclusion means this is **irrelevant to most users of a product like Northstar** unless explicitly targeting gig/unorganized-sector personas |
| Ideal user | Non-taxpaying gig workers, small traders, unorganized-sector workers — a persona this product likely does not currently target |
| Planning scenarios | The policy engine should gate this scheme's eligibility check on the user's tax-filing status, not just age — this is the one scheme surveyed where "are you a taxpayer" is a hard disqualifier rather than just a tax-treatment nuance |
| Update frequency | Scheme extended by Union Cabinet through FY2030-31 (approved 21 January 2026) — a rare multi-year policy commitment, lower change-frequency risk than most schemes here |

*Source: [ClearTax APY](https://cleartax.in/s/atal-pension-yojna), [jansuraksha.gov.in APY scheme details PDF](https://jansuraksha.gov.in/Files/APY/ENGLISH/APY.pdf)*

---

### 9. Pradhan Mantri Vaya Vandana Yojana (PMVVY) — CLOSED, historical context only

**Closed to new subscriptions since 31 March 2023.** Any source suggesting new PMVVY enrollment in 2026 is wrong — this must **not** be offered as a live recommendation option in the product. Existing policyholders continue at a locked-in 7.4% p.a. for their original 10-year term, administered by LIC. For new senior citizens seeking an equivalent product today, the market has shifted to **SCSS + LIC Saral Pension Plan (annuity) + NPS Tier I** as the replacement combination.

**Product implication:** the policy engine needs an explicit `status: active | closed_to_new | sunset` field per scheme, not just a boolean, and the recommendation logic must hard-block "closed_to_new" schemes from ever being suggested to a new user regardless of how well they'd otherwise fit the eligibility criteria — this is exactly the kind of stale-data bug a hardcoded scheme list would eventually produce.

*Source: [Right to Information Wiki — PMVVY 2026 guide](https://righttoinformation.wiki/apply-pmvvy-pradhan-mantri-vaya-vandana-yojana-2026), [BankBazaar PMVVY](https://www.bankbazaar.com/saving-schemes/pradhan-mantri-vaya-vandana-yojana.html)*

---

## Cross-Scheme Comparison

| Scheme | Rate (verified) | Tax treatment | Lock-in | Best for |
|---|---|---|---|---|
| PPF | 7.1% | EEE | 15y | Universal safe long-term |
| EPF | 8.25% (FY25-26) | EEE if 5y+ service | Until retirement | Salaried, automatic |
| NPS (own contribution) | Market-linked | EEE-ish, capped, complex exit tax | Till 60 | Max tax deduction + market upside |
| SSY | 8.2% (Q1 FY26-27) | EEE | 21y | Girl child's future |
| SCSS | 8.2% (Q3 FY26-27) | Principal deductible, interest taxable | 5y | Retiree income |
| NSC | 7.7% | Principal deductible, interest taxable (reinvest quirk) | 5y | Shorter-tenure 80C/123 alternative |
| KVP | 7.5% | **No deduction**, interest taxable | ~115mo | Simple doubling, no tax angle |
| APY | Guaranteed pension | N/A (guarantee, not a return rate) | Till 60 | Non-taxpayer, unorganized sector |
| PMVVY | 7.4% (legacy only) | — | Closed | Historical reference only |

---

## Policy Engine Design Implications

1. **Every numeric field above (rate, limit, ceiling) must be stored as a versioned, effective-dated record** (`scheme_id`, `field`, `value`, `effective_from`, `effective_to`, `source_citation`), not a static config constant — PPF/SSY/SCSS rates already change quarterly, proven by this research.
2. **Every section-number citation must be similarly versioned**, given the 1961→2025 Act transition happening in the exact year this product would need to be correct.
3. **Scheme status needs a lifecycle field** (`active` / `closed_to_new` / `sunset`), proven necessary by PMVVY.
4. **Eligibility rules need to support hard disqualifiers beyond age/income**, proven necessary by APY's taxpayer exclusion.
5. **Tax-treatment fields need a "provisional/confirmed" flag**, proven necessary by NPS's December 2025 withdrawal-rule change where the new 20% lump-sum tranche's taxation isn't yet fully settled.
6. **Regime-dependence is a first-class field**, not an afterthought — NPS's 80CCD(2) is the only benefit here that survives the new tax regime; every other 80C/123 deduction requires the old regime.

---

## What's Not Covered in This Pass

Per the sequencing agreed, this report covers the highest-impact retirement/child/senior/general-savings schemes plus the tax framework. Not yet researched: PMJJBY/PMSBY (insurance), Ayushman Bharat, PMAY (housing), Mudra loans, ELSS-specific fund-level rules, employer-provided benefits (gratuity, leave encashment) in tax detail, and NRI-specific scheme variations. Flagging for a follow-up phase rather than guessing at these.
