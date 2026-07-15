# Market Context — Schemes, Signals & Positioning

Research and synthesis conducted 2026-06-20. Builds on ARCHITECTURE.md
and COMPETITOR_ANALYSIS.md; does not repeat what is already there.

Regulatory note applied throughout: this document catalogs mechanisms
and categories, not named product recommendations. Government schemes
are public policy information. Private sector products are described
by structure and regulator only. No output here constitutes investment
advice.

---

## Table of Contents

1. [Positioning Synthesis](#1-positioning-synthesis)
2. [Government Schemes Catalog](#2-government-schemes-catalog)
3. [Private Sector Schemes Catalog](#3-private-sector-schemes-catalog)
4. [News and Macro Signal Categories](#4-news-and-macro-signal-categories)

---

## 1. Positioning Synthesis

Synthesized from COMPETITOR_ANALYSIS.md §2 (per-competitor gaps) and
§4 (self-critique). No new research in this section.

### 1.1 Competitor gaps, one line each

| Competitor | Core gap | Our specific architectural answer |
|---|---|---|
| **calcwise.finance** | Session-only: plan vanishes on tab close; priority ordering reports infeasibility rather than resolving it | Persistent named simulation runs in PostgreSQL; constrained LP solver surfaces trade-offs (delay X, reduce Y, increase contribution) rather than reporting failure |
| **ET Money / 360 One** | Goals are portfolio labels, not forward simulation; post-acquisition strategic interest is HNI upsell, not the 22-year-old user | Multi-goal simulation is the product; no acquisition agenda; cross-goal optimizer serves the user's constraint, not a sales funnel |
| **Scripbox** | Periodic strategy changes force redemption events that trigger capital gains and break compounding; goal granularity removed in unified-portfolio redesign | We produce a plan, not a managed portfolio; no rebalancing events; per-goal corpus visibility preserved in goal_allocations table |
| **INDmoney** | Goal tracker is dashboard alignment, not forward simulation; financial infrastructure (withdrawal, switches) is where real money fails | No money handling in MVP; purely a planning layer; financial infrastructure risk profile of a web app, not a payment operator |
| **Recipe / Finology** | No Monte Carlo — deterministic return assumption; priority ordering does not solve the constraint problem | 1,000-scenario Monte Carlo is foundational; constrained cross-goal optimizer is the core differentiator over Recipe's ordering |
| **Groww** | Goal planning is an SIP label; GTT execution failures and AI-only support erode trust for the use cases that matter most | Not a brokerage; no order execution; planning output is a calculated projection, not an instruction that executes at a price |
| **ClearTax** | Goal planner funnels to ELSS — one tax-optimized instrument for one goal; no planning depth | No instrument bias; asset-class guidance across equity/debt/gold; multi-goal, multi-horizon |
| **Dhan** | SIP Goal Calculator is a single-goal static formula; the real business is derivatives trading | Not competing on brokerage at all; planning depth where Dhan has none |
| **Nippon India MF** | Goal planner is a retention tool pointing at Nippon's own funds; single-AMC bias by construction | No fund-level recommendation; asset-class only; incentive structure aligned with user, not AMC AUM |
| **freefincal** | Methodologically the most rigorous approach in the Indian market — correct cash-flow model, multi-goal, sequence-of-returns aware — but distributed as Excel with no UX | Our product is freefincal's methodology with a usable interface, persistent scenarios, and an interactive optimizer |

### 1.2 Why us — three sentences for a non-technical reader

Every other financial planning tool in India either recommends specific
funds (which requires regulatory licenses we don't need) or shows you a
single optimistic number and calls it a plan. We run your entire set of
life goals — education, marriage, housing, children, retirement — as one
connected problem, showing you a probability of success across a thousand
market scenarios and exactly what needs to change if you can't fund
everything at once.

Your plan is saved, can be returned to, and can be compared against
alternative versions of your life — including the ones where a goal
doesn't happen, your income pauses for a year, or you decide to delay
buying a house in exchange for a better retirement probability.

---

## 2. Government Schemes Catalog

All figures verified as of June 2026 from government notifications and
SEBI/RBI/Ministry of Finance sources. Rates marked with quarterly review
are subject to change each quarter; verify before presenting to a user.
Present as "government-declared rate as of [quarter]" rather than as a
fact the tool guarantees.

These are relevant to the goal categories in the data model:
`education_self`, `education_child`, `marriage`, `housing`,
`healthcare`, `retirement`, `children`.

Mapping note: most schemes serve multiple goal categories. The primary
mapping below is where the scheme is most commonly used; secondary
mappings are noted.

---

### 2.1 Public Provident Fund (PPF)

| Attribute | Current value (FY 2025-26) |
|---|---|
| Interest rate | 7.1% p.a., compounded annually, calculated monthly |
| Rate review cadence | Quarterly (Ministry of Finance); unchanged Q3 2025-26 |
| Minimum deposit | ₹500 per financial year |
| Maximum deposit | ₹1.5 lakh per financial year |
| Lock-in | 15 years minimum; extendable in 5-year blocks |
| Partial withdrawal | Permitted after 5 years (up to 50% of balance at end of 4th year) |
| Loan facility | After 1 year; up to 25% of previous year-end balance |
| Tax status | EEE — exempt on contribution (under 80C up to ₹1.5L), interest, and maturity |
| Eligibility | Resident individual Indian; minors through guardian; NRIs cannot open new accounts |
| Regulator | Ministry of Finance / post offices and authorised banks |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `retirement` | **Primary** — 15-year horizon aligns with long-term accumulation; EEE status makes post-tax return among the best in fixed-income category |
| `education_child` | **Secondary** — a PPF opened for a child (through parent/guardian) when child is young can mature around higher-education age; useful for domestic degree funding |
| `housing` | **Tertiary** — partial withdrawal permitted after 5 years; can supplement a housing down-payment corpus |
| `marriage` | **Tertiary** — same partial withdrawal logic; niche use case |

**Planning note**: PPF return (7.1%) is comparable to debt mutual fund
post-tax returns for users in the 30%+ tax bracket, because PPF interest
is fully exempt. For a user in the 10-20% tax bracket, the after-tax
return of a debt mutual fund may be comparable or better. The model
should allow users to mark an existing PPF as part of `existing_corpus`
against a relevant goal.

---

### 2.2 National Pension System (NPS)

| Attribute | Current value (2025) |
|---|---|
| Expected returns | 11–20% annualized historically (market-linked; not guaranteed) |
| Return type | Market-linked across Tier I and Tier II accounts |
| Employee contribution deduction | 80CCD(1): up to ₹1.5L within the overall 80C ceiling |
| Additional individual deduction | 80CCD(1B): additional ₹50,000 over and above the 80C limit |
| Employer contribution deduction | 80CCD(2): up to 14% of salary (basic + DA) for both government and private sector employees; effective April 2025 for private sector; available under both old and new tax regimes |
| Self-employed deduction | Up to 20% of gross total income, capped at ₹1.5L under 80CCD(1) |
| Partial withdrawal | Permitted for education, marriage, housing purchase, critical illness (up to 25% of own contributions; after 3 years) |
| At retirement (age 60) | Up to 60% lump sum (tax-free); minimum 20% must be used to purchase annuity (non-govt: up to 80% lump sum since Oct–Dec 2025 reforms) |
| Minimum age to join | 18 |
| Maximum age to join | 70 |
| Account continuation | Until age 75 |
| Regulator | PFRDA (Pension Fund Regulatory and Development Authority) |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `retirement` | **Primary** — the flagship government retirement scheme; 80CCD(2) employer contribution (14%) is effectively free corpus at no cost to the employee; most impactful for salaried users |
| `education_self` | **Secondary** — partial withdrawal permitted for own higher education (subject to conditions); niche |
| `education_child` | **Secondary** — partial withdrawal permitted for child's education |
| `housing` | **Secondary** — partial withdrawal permitted for first-time home purchase |
| `marriage` | **Secondary** — partial withdrawal not permitted for marriage directly; worth flagging |

**Planning note**: The 80CCD(2) 14% employer contribution effectively
increases the user's investable corpus for retirement at zero net cost.
The planner should ask whether the user is receiving employer NPS
contributions and, if so, treat them as a pre-committed contribution
toward the retirement goal's `existing_corpus` (or as a recurring
contribution that reduces the required SIP). This interaction is not
currently captured in the data model's income_segments table.

**Tax regime interaction**: 80CCD(1B) (additional ₹50K) is available
only under the old tax regime. 80CCD(2) (employer contribution) is
available under both regimes. The model's tax treatment differs
depending on which regime the user has opted into — this is a user
input the planner should capture.

---

### 2.3 Sukanya Samriddhi Yojana (SSY)

| Attribute | Current value (FY 2025-26) |
|---|---|
| Interest rate | 8.2% p.a., compounded annually; credited at financial year end |
| Rate review cadence | Quarterly (Ministry of Finance); unchanged Jul–Sep 2025 |
| Minimum deposit | ₹250 per financial year |
| Maximum deposit | ₹1.5 lakh per financial year |
| Deposit duration | 15 years from account opening |
| Maturity | 21 years from account opening |
| Premature closure | Permitted for girl's marriage (after age 18) or girl's death |
| Partial withdrawal | Up to 50% for girl's higher education (after age 18) |
| Tax status | EEE — exempt on contribution (under 80C), interest, and maturity |
| Eligibility | Parents/guardians of girl child below age 10; maximum two accounts per family (one per girl); resident Indians only |
| Regulator | Ministry of Finance / post offices and authorised banks |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `children` | **Primary** — structured specifically for girl child's future financial security; highest government-declared interest rate among small savings schemes |
| `education_child` | **Primary** — partial withdrawal at 50% for girl's higher education is directly aligned; the 21-year maturity horizon matches planning for a child born today to reach university age |
| `marriage` | **Secondary** — premature closure permitted for girl's marriage after age 18 |

**Planning note**: SSY is specifically limited to girl children below 10.
The planner should ask whether the `education_child` or `children` goal
target is a girl child, and only surface SSY as relevant in that case.
Surfacing it for a male child's education goal or a goal with uncertain
child gender at planning time is misleading.

---

### 2.4 PMAY Urban 2.0 — Credit-Linked Subsidy Scheme (CLSS)

| Attribute | Current value |
|---|---|
| Scheme status | Active (2024–2029, 5-year implementation) |
| Target beneficiaries | EWS (income ≤ ₹3L), LIG (₹3–6L), MIG (₹6–9L annual household) |
| Subsidy structure | 4% interest subsidy on first ₹8L of home loan |
| Maximum subsidy | ₹1.80 lakh (NPV ₹1.50 lakh); disbursed in 5 annual instalments |
| Maximum loan amount | ₹25 lakh |
| Maximum property value | ₹35 lakh |
| Applicant eligibility | First-time home loan borrower; no pucca house owned by family anywhere in India; co-ownership by female family member required (except single male applicants) |
| Prior scheme bar | Families that used any government housing scheme in the last 20 years are ineligible |
| Delivery mechanism | Subsidy credited directly to loan account by Primary Lending Institution (PLI), reducing principal |
| Regulator | Ministry of Housing and Urban Affairs; delivered via banks/HFCs (PLIs) |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `housing` | **Primary** — directly reduces the effective cost of first home purchase for qualifying income groups |

**Planning note**: PMAY CLSS is relevant only for users whose household
income falls below ₹9L/year. A user earning ₹50,000/month is at the
top of the MIG threshold. The planner should capture annual household
income (not just the user's take-home) and surface PMAY eligibility as
a contextual note — "if your combined household income is below ₹9L,
your effective home loan cost may be reduced by up to ₹1.8L under
PMAY Urban 2.0" — not as a recommendation to apply.

The property value cap (₹35L) limits relevance for metro housing goals
where today's cost of a 2BHK often exceeds ₹50–80L. The scheme is
most relevant for Tier-2/3 cities.

---

### 2.5 Employees' Provident Fund (EPF)

| Attribute | Current value (FY 2025-26) |
|---|---|
| Interest rate | 8.25% p.a.; calculated monthly, credited annually |
| Rate announcement | Annual (EPFO central board); rate retained at 8.25% for second consecutive year |
| Employee contribution | 12% of basic salary + DA |
| Employer contribution (to PF) | 3.67% of basic salary + DA (balance of 8.33% goes to EPS and EDLI) |
| Total employer contribution | 12% (but only 3.67% reaches the PF account) |
| Taxability of interest | Exempt on contributions up to ₹2.5L/year; taxable above that threshold |
| Withdrawal | Full withdrawal on retirement (age 58) or after 2 months of unemployment; partial withdrawal for education, marriage, housing purchase, medical treatment |
| Regulator | EPFO (Employees' Provident Fund Organisation); Ministry of Labour |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `retirement` | **Primary** — EPF is typically the largest compulsory retirement accumulation vehicle for salaried employees; the planner should treat employer EPF contributions as pre-committed retirement corpus |
| `education_child` | **Secondary** — partial withdrawal permitted for child's education (after 7 years of service, up to 50% of employee's share) |
| `marriage` | **Secondary** — partial withdrawal permitted for own marriage or sibling's marriage (after 7 years) |
| `housing` | **Secondary** — partial withdrawal permitted for housing purchase or construction |

**Planning note**: EPF is mandatory for salaried employees whose basic +
DA is below ₹15,000/month, and optional above that threshold. The
effective EPF accumulation is 3.67% × 2 (employee + employer) of basic
+ DA on the PF side — not 12% × 2. Many users conflate total employer
contribution (12%) with PF contribution (3.67%). The planner should
capture EPF contribution amount separately and model it as a monthly
contribution to `existing_corpus` for the retirement goal.

---

### 2.6 Atal Pension Yojana (APY)

| Attribute | Current value (2025) |
|---|---|
| Pension amounts | ₹1,000 / ₹2,000 / ₹3,000 / ₹4,000 / ₹5,000 per month guaranteed from age 60 |
| Contribution | Age-dependent; example: ₹1,000 pension chosen at age 18 requires ₹42/month; same at age 39 requires ₹264/month |
| Payout | Starts at age 60; guaranteed government-backed |
| Spouse continuation | Spouse receives pension on subscriber's death |
| Nominee corpus | Nominee receives accumulated corpus on death of both subscriber and spouse |
| Eligibility | Indian citizen aged 18–40; bank/post office savings account with Aadhaar for auto-debit |
| Ineligibility | Not available to those covered under statutory provident fund schemes (EPF, Coal Mines PF, Assam Tea PF, etc.) |
| Government co-contribution | Expired March 2020 (available 2015–2020 only); not available for new subscribers |
| Tax deduction | Under Section 80CCD, up to 10% of gross income within the ₹1.5L ceiling; additional ₹50,000 under 80CCD(1B) |
| Regulator | PFRDA |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `retirement` | **Primary** — small guaranteed floor income for retirement; most relevant for gig/informal/self-employed workers without EPF |

**Planning note**: APY's maximum guaranteed pension of ₹5,000/month
(₹60,000/year) is far below the retirement income most users with
middle-class lifestyles need. It is a floor, not a complete retirement
plan. The planner should present APY as a floor contribution that
reduces the market-dependent corpus required, not as a substitute for
equity-linked retirement saving. The EPF ineligibility condition means
most corporate salaried users are not eligible — check EPF status
before surfacing APY.

---

### 2.7 Sovereign Gold Bond (SGB)

| Attribute | Current value |
|---|---|
| Interest rate | 2.5% p.a. paid semi-annually (on face value, i.e., on the gold price at issue) |
| Price | Based on average closing price of 999-purity gold in the preceding week |
| Tenure | 8 years; premature exit permitted at coupon payment dates after 5 years |
| Maximum investment | 4 kg per individual per fiscal year; 20 kg for trusts |
| Minimum investment | 1 gram |
| Capital gains tax | Exempt if held to maturity (8 years); taxable as long-term capital gain if redeemed early (with indexation) |
| Interest taxation | Taxable as per income tax slab |
| Eligibility | Resident individuals, HUFs, trusts, universities, charitable institutions; NRIs and minors not eligible |
| Current status | **Paused** — no new tranches announced for FY 2026-27; last tranches were in FY 2023-24; government has not released an issuance calendar due to high sovereign borrowing cost concerns |
| Existing bonds | Continue to maturity; holders can exit after 5-year lock-in on interest payment dates |
| Regulator | RBI (issuance); SEBI (secondary market trading) |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `marriage` | **Secondary** — gold is culturally linked to marriage costs in India; SGBs offer gold exposure without storage/making-charge burden; 8-year horizon works if goal is 8+ years out |
| `housing` | **Tertiary** — gold as diversification asset; less direct than other instruments |
| `retirement` | **Secondary** — gold as a portfolio diversifier for multi-decade retirement corpus |

**Planning note**: The paused issuance is material. The planner should
not present "invest in SGBs" as an available action without verifying
whether a new tranche has been issued. The catalog should note that
existing SGB holders can model their holding as a gold-equivalent asset
in `existing_corpus`, but new SGB purchases are not currently available.
If issuance resumes, this will be a staleness-category event (see §4).

---

### 2.8 Tax Deduction Sections — 80C, 80D, 80CCD

These are cross-cutting — they affect the effective cost of instruments
across multiple goal categories. Presented as a reference table for
the planner to use when contextualizing the effective return of a
tax-advantaged instrument vs. a taxable one.

| Section | What it covers | Limit (FY 2025-26) | Tax regime |
|---|---|---|---|
| 80C | PPF, ELSS, life insurance premiums, EPF (employee share), SSY, NSC, home loan principal, tuition fees for up to 2 children | ₹1.5 lakh per year (aggregate across all instruments) | Old regime only |
| 80CCC | Contributions to pension plans of life insurance companies | Within the ₹1.5L 80C ceiling | Old regime only |
| 80CCD(1) | NPS / APY contributions by employee or self-employed | Within the ₹1.5L 80C ceiling | Old regime only |
| 80CCD(1B) | Additional NPS / APY contributions | ₹50,000 over and above the ₹1.5L ceiling | Old regime only |
| 80CCD(2) | Employer's NPS contribution | Up to 14% of salary (basic + DA), raised from 10% for private sector from April 2025 | **Both regimes** |
| 80D | Health insurance premiums for self/family | ₹25,000 (self + spouse + children); additional ₹25,000 for parents < 60; ₹50,000 for parents ≥ 60 | Old regime only |
| 80E | Education loan interest | 100% of interest paid, no upper limit; for 8 years from first repayment | **Both regimes** |

**Important**: 80C is only available under the old tax regime. The new
tax regime (with lower slab rates and no most deductions) has been
widely adopted. The planner must ask which tax regime the user is
filing under — this materially changes the after-tax return of PPF,
ELSS, and life insurance premiums. Do not assume old regime.

**80E specifically**: Section 80E covers interest on education loans for
the borrower's own higher education. Full interest deduction with no
cap for 8 years from first repayment. This is significant for an
education_self goal where the user is taking a loan — the actual
out-of-pocket cost of education loan interest is after-tax interest,
not gross interest. Both regimes permit this deduction.

---

### 2.9 Education Loan Interest Subsidy Schemes (Government)

Two distinct government schemes with different eligibility criteria:

#### Central Sector Interest Subsidy Scheme (CSIS) — domestic education

| Attribute | Current details |
|---|---|
| Target | Students from families with annual income ≤ ₹4.5 lakh |
| Eligible courses | Technical or professional courses in India (IBA-approved banks) |
| Subsidy | 100% interest subsidy during moratorium period (course duration + 1 year after completion or 6 months after employment, whichever is earlier) |
| Delivery | Via IBA model education loan; bank credits subsidy from government |
| Administering bank | Designated via IBA; not a single nodal bank |
| Active status | Active; southern states (Kerala, Karnataka, Tamil Nadu) account for majority of claims |

**Goal category mapping**: `education_self`, `education_child`

#### Dr. Ambedkar Central Sector Scheme — overseas education

| Attribute | Current details |
|---|---|
| Target | OBC (Other Backward Classes) and EBC (Economically Backward Classes) students |
| Eligible courses | Masters, M.Phil., PhD programs abroad |
| Subsidy | 100% interest subsidy during moratorium period (course duration + 1 year after completion or 6 months after employment) |
| Maximum loan eligible | ₹20 lakh |
| Gender reservation | 50% of annual outlay reserved for female candidates |
| Nodal bank | Canara Bank |
| Active status | Active |

**Goal category mapping**: `education_self`

**Planning note**: Both schemes are means-tested. A user whose family
income exceeds ₹4.5L/year is ineligible for CSIS. A user from a
general category (non-OBC/EBC) is ineligible for the Dr. Ambedkar
scheme. The planner should surface these only when the user's income
profile and caste category make them plausibly eligible — or with a
clear "check eligibility" prompt rather than presenting them as
universally applicable.

---

## 3. Private Sector Schemes Catalog

**Regulatory flag, read first:** This section covers two separate
regulators. SEBI governs mutual funds and securities. IRDAI (Insurance
Regulatory and Development Authority of India) governs insurance
products. The non-advice rule applies to both: naming a specific
insurer's ULIP or a specific insurer's child plan as a recommendation
has the same problem as naming a specific mutual fund — just under a
different regulator. The disclaimer component in ARCHITECTURE.md §5.1
covers SEBI-regulated products. It needs to also cover IRDAI-regulated
products.

**Updated disclaimer text** (replaces the SEBI-only version in
ARCHITECTURE.md §5.1 and COMPETITOR_ANALYSIS.md §4.9):

> "This is a mathematical projection, not investment or insurance
> advice. Some instruments shown may be regulated by SEBI (mutual funds,
> bonds) or IRDAI (insurance and ULIP products). Consult a SEBI-
> registered Investment Adviser for investment-related decisions, and a
> licensed insurance adviser for insurance-related products."

---

### 3.1 Education Loan Products (Private / NBFC)

**Regulator**: RBI (NBFCs are RBI-regulated for lending)  
**Named product examples** (for catalog only, not recommendations):
Credila Financial Services (formerly HDFC Credila), Avanse Financial
Services, InCred, MPower Financing (for US education)

| Attribute | Typical range (2025) |
|---|---|
| Interest rate — secured (collateral-backed) | 9.75% p.a. onwards (floating, quarterly revision) |
| Interest rate — unsecured (no collateral) | 11.25% p.a. to 16.5% p.a. depending on lender, academic profile, and institution ranking |
| Maximum loan amount — secured | ₹80 lakh and above |
| Maximum loan amount — unsecured | Up to ₹1.25 crore (some lenders) |
| Repayment period | Up to 15 years |
| Rate type | Floating (tied to lender's internal benchmark or repo-linked rate; revised quarterly) |
| Processing time | 7–15 working days (some lenders offer 3-day fast-track for strong profiles) |
| Key eligibility factors | Institution ranking, course type, academic profile, credit history; strong profiles at top institutions attract lower rates |

**Mechanism**: NBFC education loans fill the gap between government bank
loans (which may have caps or documentation barriers) and the total cost
of study. Particularly relevant for overseas education and private
professional programs where government banks may cap at ₹20-40L and
NBFCs cover the remainder.

**Goal category mapping**: `education_self`, `education_child`

**Planning note**: Education loan interest during the moratorium period
is an additional cost on top of the goal's stated amount. The planner
should offer users the ability to model loan-funded education
differently from savings-funded education — the SIP needed is lower
(since the loan covers part of the cost), but the post-graduation
repayment creates a cash-flow constraint during the income_segments
immediately following the education period. This interaction is not
in the current data model.

---

### 3.2 Unit Linked Insurance Plans (ULIPs)

**Regulator**: IRDAI — **not SEBI**. This is the second major regulator.  
**Naming rule**: Do not name specific ULIP products. Catalog by
mechanism only.

| Attribute | Details |
|---|---|
| Structure | Combined life insurance (sum assured) + market-linked investment (equity/debt funds chosen by policyholder) |
| Lock-in | Mandatory 5 years; surrender before 5 years results in fund value credited to discontinued policy fund |
| Premium payment | Regular (monthly/annual) or limited pay; top-ups permitted |
| Fund switching | Permitted between equity/debt funds within the ULIP; typically tax-free under IT Act 2025 |
| Tax on premiums | Section 123 (IT Act 2025): deduction up to ₹1.5L per year on premiums paid |
| Tax on maturity | Section 10(10D): proceeds exempt if annual premium ≤ 10% of sum assured (subject to conditions) |
| GST on premiums | Reduced to 0% on selected ULIP products from September 22, 2025 (was 18%) |
| Sum assured | Minimum 10× annual premium (IRDAI minimum; life cover requirement) |
| IRDAI directive (2024) | IRDAI explicitly told insurers not to sell ULIPs as pure investment products; life insurance component must be prominent |
| Cost structure | Historically high charges; 4G ULIPs (fourth generation) have significantly reduced expense ratios and improved transparency |

**Mechanism as goal instrument**: ULIPs allow equity/debt switching without
capital gains tax, which is a genuine advantage over direct mutual fund
investing for users who want to shift equity/debt allocation over a goal's
timeline (essentially the same glide path the planner models, but inside
a single wrapper). The premium waiver on life event (death/disability)
means the goal corpus continues to be funded even if the contributor dies.

**Genuine advantage vs. mutual fund for goal planning**: The life insurance
component and premium waiver benefit are real differentiators — if a
parent dies 10 years before a child's education goal, a ULIP continues
to be funded (insurer pays premiums), whereas a mutual fund SIP simply
stops. For goals with a high consequence of interruption (child's
education, retirement), this is worth flagging as a mechanism difference,
not a product recommendation.

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `education_child` | **High** — long horizon, premium waiver protects against parental death; maturity aligns with education timeline |
| `retirement` | **Medium** — long horizon works but NPS/mutual funds have lower expense ratios at comparable risk levels |
| `marriage` | **Low** — 5-year lock-in may conflict with goal timing; shorter goals are better served by simpler instruments |

**Planning note for our architecture**: The planner should present ULIPs
as a mechanism category ("combined insurance and market-linked investment,
IRDAI-regulated") with an explicit note that (a) it is an insurance
product, not a securities product, and (b) a licensed insurance adviser
should be consulted before purchase. The disclaimer must cover IRDAI in
addition to SEBI.

---

### 3.3 Child and Education Insurance Plans

**Regulator**: IRDAI — **not SEBI**.  
**Naming rule**: Do not name specific plans. Catalog by mechanism.

These are a sub-category of IRDAI-regulated products. Two main types:

**Endowment-based child plans**: Guaranteed maturity amount paid at a
specified date (e.g., child's 18th birthday). Fixed, non-market-linked
returns. Sum assured on death plus premium waiver means the plan
continues funding even if the parent dies. Low returns compared to
market-linked instruments; predictability is the trade-off.

**ULIP-based child plans**: Same mechanism as §3.2 but specifically
structured with milestone payouts aligned to education costs (e.g., 20%
of sum assured at 16, 20% at 18, 30% at 20, 30% at 22 — matching
school completion, undergraduate entry, and graduation). Market-linked
returns. Premium waiver on parent's death is the critical differentiating
feature.

| Attribute | Details |
|---|---|
| Payout structure | Flexible; installments or lump sum; milestone-aligned payouts for education plans |
| Premium waiver | On death of parent (or total permanent disability): future premiums waived; policy continues; child receives benefits at maturity |
| Sum assured | Up to 10× annual premium (IRDAI cap) |
| Tax (premiums) | Section 123 (IT Act 2025): deduction up to ₹1.5L |
| Tax (maturity) | Section 10(10D): proceeds exempt subject to premium ≤ 10% of sum assured |
| Lock-in | Typically 5 years minimum (varies by insurer) |
| Surrender value | Regulated by IRDAI; requires clear disclosure since 2024 amendments |

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `education_child` | **Primary** — the canonical use case; milestone payouts synchronized with education costs |
| `children` | **Primary** — general child corpus planning with life protection |
| `marriage` | **Secondary** — some plans designed to fund both education and marriage of girl child |

**Planning note**: The premium waiver benefit is the one feature mutual
funds cannot replicate. For a user who has young children and is the
sole breadwinner, child plans address a genuine risk that the planner's
Monte Carlo model does not — the scenario where the income generator
dies before the goal date. The planner should surface this as a gap:
"Monte Carlo models market risk but not the risk that contributions
stop due to death or disability; consider life insurance coverage sized
to replace the SIP amount for the remaining goal duration."

---

### 3.4 Goal-Linked Fixed Deposits and Recurring Deposits (FDs / RDs)

**Regulator**: RBI (bank deposits); NBFC-deposit rules where applicable  
**Naming rule**: Do not name specific bank products.

| Attribute | Typical range (2025) |
|---|---|
| FD interest rate | 6.5–7.5% p.a. for tenors 1–3 years (major banks); small finance banks offer up to 9% |
| RD interest rate | Broadly comparable to equivalent-tenor FDs; often 0.25–0.5% below for same institution |
| Rate determination | Banks: market-determined, aligned to MCLR / repo-linked benchmarks (tracks RBI repo rate with lag) |
| Tenure | FD: flexible 7 days to 10 years; RD: typically 6 months to 10 years |
| Tax on interest | Taxable as per income slab; TDS at 10% if interest > ₹40,000/year (₹50,000 for senior citizens) |
| Senior citizen benefit | Most banks offer 0.25–0.75% higher rate for senior citizens |
| Safety | Bank deposits insured by DICGC up to ₹5 lakh per bank per depositor |

**Mechanism**: RDs function similarly to SIPs — regular monthly
contribution, fixed tenure, guaranteed return. Zero market risk but
positive inflation risk for long tenors. Most useful for short-horizon
goals (1–5 years) where capital preservation is the priority over
return maximization.

**Goal category mapping**

| Goal | Relevance |
|---|---|
| `housing` (down-payment corpus, < 5 years) | **High** — guaranteed return, no sequence-of-returns risk for a near-term goal |
| `marriage` (< 3 years) | **High** — same rationale; short horizon |
| `education_self` (international course deposit within 1–2 years) | **High** — admission deposits, visa-linked funds needed on a specific date |
| `retirement` (> 20 years) | **Low** — real return after tax and inflation is likely negative or near-zero at current rates |

**Planning note**: The planner's equity glide path already models this
behaviorally — as a goal approaches, equity decreases and debt
(including FD-equivalent instruments) increases. For goals within 2–3
years, the glide path may suggest 80-100% debt, which is practically
equivalent to telling the user to use an FD or short-duration debt fund.
The planner should note this explicitly rather than leaving the user to
infer it from the equity/debt split.

---

### 3.5 Home Loan Products (Private Sector)

**Regulator**: RBI (banks), NHB (housing finance companies)  
**Naming rule**: Do not name specific lenders.

| Attribute | Typical range (2025, post repo rate cuts) |
|---|---|
| Home loan interest rate | 8.5–9.5% p.a. floating (REPO-linked or MCLR-linked + spread) |
| Rate type | Floating; resets on RBI repo rate changes (REPO-linked products) or MCLR review |
| Loan-to-value (LTV) | Up to 90% for loans ≤ ₹30L; up to 80% for ₹30–75L; up to 75% for > ₹75L |
| Maximum tenure | Up to 30 years |
| Processing fees | Typically 0.25–1% of loan amount |
| Prepayment penalty | Nil for floating rate loans (RBI mandated) |
| Tax benefit on interest | Section 24(b): ₹2L deduction on interest for self-occupied property (old regime) |
| Tax benefit on principal | Section 80C: principal repayment within the ₹1.5L ceiling |
| PMAY CLSS overlap | See §2.4 — reduces effective interest cost for qualifying income groups |

**Mechanism for housing goal planning**: A home loan converts a lump-sum
goal (down payment + total property cost) into an EMI stream over 20–30
years. The planner's housing goal currently models the lump sum
(today_cost, inflation-adjusted future cost). For most users the actual
question is "what SIP builds my down-payment corpus, and what income is
needed to service the EMI once I buy?" These are different problems.

**Data model gap**: The housing goal currently captures only the full
property cost as `today_cost`. A more accurate model for housing would
split it into:
- Down-payment component (lump sum needed by target year, savings-funded)
- EMI servicing capacity check (monthly cash-flow constraint from
  target_year onward; reduces investable capacity for other post-housing
  goals)

This is a V2 refinement — the current schema can approximate it by
treating today_cost as the down-payment amount rather than the full
property cost, and leaving the EMI as a note to the user.

---

## 4. News and Macro Signal Categories

This is research output only. **Do not implement live news monitoring
in MVP.** The scope recommendation is at the end of this section.

### 4.1 Signal categories and model impacts

| Signal category | Event types | Which assumption in the data model is affected | Magnitude of impact |
|---|---|---|---|
| **RBI repo rate changes** | MPC meeting decisions (8 per year); rate cut or hike announcements | `debt_mean_pct` in simulation_configs (debt return assumption tracks repo broadly); FD/RD rates used as fixed-income benchmarks; home loan EMI if housing goal is active | **High** — 125 bps of cuts in 2025 have reduced debt fund forward returns from ~8% to ~6.5–7%; users with saved runs computing under 8% debt assumption are now running with stale numbers |
| **Union Budget tax changes** | 80C limit changes; NPS deduction changes; new tax regime changes; LTCG tax rate changes on equity | Tax-adjusted effective return of PPF, ELSS, NPS, ULIP; the after-tax return the user retains from each instrument changes when deduction limits change | **High** — the new tax regime adoption affects whether 80C instruments have any tax advantage at all for a given user; if a majority of users are now under new regime, displaying 80C benefit as default is misleading |
| **CPI print releases** | Monthly MoSPI headline CPI; quarterly sub-category inflation (education, healthcare, housing) | `inflation_rate` defaults per goal category in the goals table; general CPI default (currently 5–6%) | **Medium** — recent CPI of 1.6% (July 2025) is well below the 5–6% default; the gap between CPI and category-specific inflation is what matters (education private: still 10–12%, healthcare: 8–10%, even as headline is low); do not reduce education inflation assumption just because headline CPI is low |
| **Education loan rate trends** | Credila/Avanse base rate revisions; PSB MCLR changes affecting student loan rates | Not currently in data model — education loan rates affect the cost differential between loan-funded and savings-funded education goals | **Medium** — relevant when the planner adds loan-vs-savings modeling for education goals |
| **Real estate policy changes** | State stamp duty revisions (common during Budget sessions, especially Maharashtra, Delhi, Karnataka); GST rate changes on under-construction property; PMAY income bracket changes; circle rate revisions | `today_cost` input guidance for housing goals; PMAY CLSS eligibility thresholds | **Medium** — stamp duty can add 3–7% to effective property cost; a Maharashtra stamp duty cut changes the effective today_cost for housing goals in Mumbai; this is city-specific and frequent |
| **SEBI regulatory changes** | LTCG tax rate changes on equity mutual funds; new fund category creation; regulation of robo advisors | `equity_mean_pct` post-tax assumption; compliance posture of the platform itself | **Low to High** (depends on change) — the 2024 LTCG rate increase on equity (from 10% to 12.5% on gains above ₹1.25L) changed post-tax equity return assumptions; a future change would require re-running all saved simulations |
| **SGB issuance status** | RBI announcement of new tranche calendar | Whether SGB is presentable as an available gold instrument | **Low for planning math, High for UX** — if a new tranche opens, the catalog note in §2.7 becomes outdated; the planner should not suggest SGB purchase when no tranche is open |
| **IRDAI regulatory changes** | ULIP cost structure changes; surrender value regulations; GST on insurance products | Not directly a model input, but affects whether ULIPs remain cost-competitive vs. mutual funds for the same goal; the September 2025 GST-to-zero change improved ULIP economics meaningfully | **Low to Medium** — affects the catalog §3.2, not the simulation model |

### 4.2 Current state of the key signals (as of June 2026)

| Signal | Current value | Direction | Model implication |
|---|---|---|---|
| RBI repo rate | 5.25% (cut from 6.5% via 5 cuts across 2025) | Hold expected through 2026 | Debt mean return default should be updated to ~6.5–7.0%; the default 7% in ARCHITECTURE.md §3.4 is at the top of the realistic range |
| CPI inflation | 1.6% (July 2025, 8-year low); RBI FY 2025-26 forecast: 2.6% | Declining | Do not update the general CPI planning default (5–6%) based on this — the recalibrated basket is not comparable to the prior series, and 30-year planning should use long-run averages, not current readings |
| Equity LTCG tax | 12.5% for gains above ₹1.25L (since Budget 2024) | Stable | Equity post-tax return assumption should account for this; not currently captured explicitly in simulation_configs |
| 80CCD(2) employer NPS | 14% of salary (raised from 10% for private sector from April 2025) | Stable for now | Significant for retirement goal planning for salaried users; model should capture employer NPS separately |

### 4.3 Scope decision — live news monitoring

**Recommendation: V2 feature, not MVP. Address the staleness problem in
MVP through the UI pattern already identified in COMPETITOR_ANALYSIS.md
§4.8, not through a live content pipeline.**

Rationale:

**The staleness problem is a UX problem, not a data problem.** A user
whose saved run is 8 months old does not need a live news feed — they
need a clear indication that the plan is 8 months old and may be stale,
and a one-click re-run with current defaults. This is a timestamp +
"re-run" button, not a news integration. It costs a day to build, not
a sprint.

**Live news monitoring is a content + NLP + notification pipeline.**
To do it properly: ingest MPC meeting minutes and budget documents,
parse rate-change announcements, identify which simulation_configs
defaults are affected, version defaults over time, identify which saved
runs used now-stale defaults, notify affected users, and offer re-run.
This is a non-trivial data engineering task: multiple ingestion sources
(RBI website, MoSPI, Ministry of Finance, SEBI, IRDAI), NLP/parsing
for structured event extraction, a versioned defaults system, and a
notification layer. None of this exists in the current architecture.

**The real signal frequency is low.** The events that materially change
planning assumptions happen roughly 4–8 times per year (8 MPC meetings,
1 Union Budget, quarterly CPI prints). A quarterly manual review of the
hardcoded defaults by a maintainer is sufficient for MVP — this is a
process, not infrastructure.

**Concrete MVP implementation of the staleness pattern (from
COMPETITOR_ANALYSIS.md §4.8):**

1. Every simulation_run stores `created_at` and `config_snapshot` (both
   already in the schema).
2. The frontend compares `created_at` to current date. If > 90 days old
   (configurable), show a banner: "This plan was computed [N days] ago.
   Market conditions and policy rates may have changed. [Re-run with
   current defaults →]"
3. The re-run creates a new simulation_run with the current
   simulation_config (updated defaults), preserving the original run for
   comparison.
4. A quarterly maintainer task: review the signal table in §4.1, update
   relevant defaults in the simulation_config default values, increment
   a `defaults_version` field, and document what changed and why.

**When to promote to V2 live monitoring:** If the product grows to
thousands of active users and the quarterly manual review becomes a
bottleneck, or if a user cohort explicitly requests "alert me when my
plan assumptions go stale," then building the pipeline is justified.
At MVP scale with one maintainer and tens to hundreds of users, the
process solution is correct.
