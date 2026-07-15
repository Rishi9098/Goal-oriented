# Competitor Analysis — Goal-Based Financial Planning

Research conducted 2026-06-20. This document covers business model,
customer segmentation, automation level (cross-checked against SEBI
registration, not marketing copy), genuine advantages, real user
complaints, and how our planned architecture from ARCHITECTURE.md
addresses each gap. Followed by an honest self-critique of our own
architecture.

---

## Table of Contents

1. [SEBI Registration Reference Table](#1-sebi-registration-reference-table)
2. [Competitor Deep Dives](#2-competitor-deep-dives)
   - [calcwise.finance](#21-calcwisefinance)
   - [ET Money / 360 One](#22-et-money--360-one)
   - [Scripbox](#23-scripbox)
   - [INDmoney / Finzoom](#24-indmoney--finzoom)
   - [Recipe / Finology](#25-recipe--finology)
   - [Groww](#26-groww)
   - [ClearTax](#27-cleartax)
   - [Dhan](#28-dhan)
   - [Nippon India MF](#29-nippon-india-mf)
   - [Walnut / Axio](#210-walnut--axio)
3. [Competitor Summary Table](#3-competitor-summary-table)
4. [Self-Critique of Our Architecture](#4-self-critique-of-our-architecture)

---

## 1. SEBI Registration Reference Table

Registration type is a harder signal than marketing copy for what a
product is actually allowed to do and whether humans must be in the loop.

| Competitor | Entity | SEBI Registration | Type | What this permits |
|---|---|---|---|---|
| ET Money | ET Money (now 360 One) | INA100001718 | Investment Adviser (IA) | Personalised advice, named product recommendations; human-in-loop compliance required |
| Scripbox | Scripbox Wealth Managers | INA200001041 | Investment Adviser (IA, Non-Individual) | Same as above; non-individual = corporate IA |
| INDmoney | Finzoom Investment Advisors | INA100012190 | Investment Adviser (IA) | Same as above |
| Finology / Recipe | Finology Ventures Pvt Ltd | INA000012218 (IA) + INH000024277 (RA) | Both IA and Research Analyst | Personalised advice + published research reports |
| Groww | NextBillion Technology | INZ000208032 (broker) + AMFI ARN | Stock broker + MFD | Execution only; distribution commissions; no advice |
| ClearTax | Defmacro Software | AMFI ARN110027 | Mutual Fund Distributor (MFD) | Fund distribution; no regulated advice |
| Dhan | Raise Financial / Raise Securities | INZ000006031 (broker) | Stock broker + AMFI member | Execution only; brokerage; no advice |
| Nippon India MF | Nippon Life India AM | AMC (SEBI-regulated AMC) | Asset Management Company | Manages own funds; no independent advice |
| calcwise.finance | Unknown | None identified | Unregistered calculator tool | No regulated advice; output is mathematical only |
| Walnut / Axio | Axio Biosciences / Capital Float | RBI NBFC (lending) | NBFC, not SEBI-regulated for investment | Expense tracking, credit only |

**Key implication:** ET Money, Scripbox, and INDmoney all hold IA
registration. Under SEBI IA rules, a registered investment adviser
providing personalised algorithmic advice must still maintain a "human-
in-loop" governance structure — the algorithm selects or recommends, a
qualified human principal signs off on suitability and policy. "AI-
powered" in their marketing does not mean there is no human oversight;
for IA registrants it is a compliance requirement, not a feature choice.
Groww, ClearTax, and Dhan cannot give advice by registration type alone.

---

## 2. Competitor Deep Dives

---

### 2.1 calcwise.finance

**Business / operating model**

Free, ad-supported or growth-stage with no visible monetization yet. All
computation runs client-side in the browser. No backend, no database,
no server costs. Revenue model not publicly disclosed — likely an SEO/
content traffic play, possibly planning a freemium upsell or affiliate
referral layer in future. The "no data stored" positioning is a feature
but also a constraint that prevents any subscription model without a
major architecture rethink.

**Customer segmentation**

Single tier: free, self-serve, anonymous. No login, no account. Aimed
at DIY retail investors doing quick planning checks. Not segmented by
sophistication — the same tool serves a 22-year-old doing a rough
estimate and a 45-year-old planning retirement. No HNI tier, no adviser-
facing module, no B2B offering.

**Automation level**

Fully algorithmic, client-side. No registration, no human in the loop,
no SEBI oversight. This is legally safe because the output is
mathematical projection with no named-product recommendation. The
Monte Carlo runs entirely in the browser in JavaScript. Because there
is no IA registration, calcwise cannot say "invest in X" and does not
attempt to. The "feasibility status" label and "priority tier" system
are algorithmic outputs with no human review.

**Genuine advantages**

- Zero friction: no login, no KYC, immediate results. Best time-to-
  first-value of any product in this space.
- Privacy positioning ("your data never leaves your device") is a real
  differentiator for privacy-conscious users and resonates strongly.
- Monte Carlo is correctly implemented as 1,000 scenario simulations
  rather than a deterministic point estimate — this is the methodolo-
  gically honest choice.
- Inflation-adjusted goal costing is correctly done (future cost =
  present cost × (1 + inflation)^years) rather than ignoring inflation.
- PDF export works; downloadable offline artifact is a genuine feature.
- Clean, focused UX — does not try to be a brokerage or aggregator.

**Real drawbacks (from product analysis; no Reddit community found)**

1. Session-only: all data is lost on tab close. Users cannot return to
   a plan they worked on last week. For a 30-year planning horizon, this
   is a fundamental usability failure — no one makes a multi-decade plan
   in a single sitting.
2. No cross-goal constraint solver. When total SIP need exceeds income
   capacity, lower-priority goals simply fail. The tool cannot tell the
   user "delay goal X by 2 years and goal Y becomes 85% probable." It
   reports infeasibility without resolving it.
3. No income trajectory. Salary is a static input. A 22-year-old's
   income at 30, 40, and 50 is not the same; the plan that ignores this
   gives wrong numbers for every intermediate goal.
4. No goal existence/probability. Every goal is treated as certain. A
   user cannot model "I am 60% sure I will pursue a masters degree —
   show me the plan under both branches."
5. Static allocation formula (100 − age ± risk adjustment) applied to
   all goals equally. A housing goal 4 years out and a retirement goal
   38 years out should have radically different equity exposure; one
   formula produces wrong allocations for at least one of them.
6. Goals calculated in isolation. Over-funding an early goal does not
   reduce the modeled available cash for later goals — the math is not
   connected across goals.
7. No named user community or review corpus found on Reddit or app
   stores. This suggests either very early stage or very low engagement
   beyond a first visit. Likely high bounce; users do a calculation and
   leave rather than building a relationship with the tool.

**How our architecture addresses each drawback**

1. Persistent named simulation runs in PostgreSQL; users return to saved
   plans across sessions and across devices.
2. Cross-goal constrained allocation solver (scipy.linprog against
   piecewise-linear success-probability approximations) explicitly
   generates trade-off suggestions (delay by N years, reduce target by
   Z%) when infeasible.
3. income_segments table models salary trajectory as a step function —
   job switches, career breaks, salary growth within each segment.
4. confidence_pct per goal enables "optional goal" modeling; optimizer
   weights goals by confidence; side-by-side plan variants show the
   plan with and without a probabilistic goal.
5. Per-goal equity glide paths: each goal gets its own equity allocation
   that steps down linearly from a starting percentage to 20% equity in
   the 5-year window before the goal's target date.
6. Cross-goal cash flow is modeled: the monthly capacity constraint
   applies across all goals simultaneously, not per-goal in isolation.

---

### 2.2 ET Money / 360 One

**Business / operating model**

Acquired by 360 One WAM (formerly IIFL Wealth) in June 2024 for ₹366
crore (part cash, part 360 One stock). Pre-acquisition revenue mix:
MF distribution commissions + ET Money Genius subscription (₹249/month)
+ insurance lead generation. At acquisition: 900,000 transacting clients,
76,000 active paying Genius subscribers, ₹70,000 crore AUM tracked.

Post-acquisition, 360 One intends to cross-sell its institutional wealth
management (PMS, AIF, credit) to ET Money's retail base, and move ET
Money's mass-market users toward the 360 One advisory ecosystem. This is
a retail-to-HNI funnel play, not a standalone product vision.

**Customer segmentation**

- Free tier: mutual fund tracking, SIP setup, portfolio health check.
  Open to all retail users. Revenue from MF distribution commissions.
- Genius (₹249/month): personalised model portfolio under IA license,
  rebalancing alerts, dynamic asset allocation. Quant-driven, target
  market is retail investors who want "done-for-you" without full wealth
  management fees.
- Post-360 One acquisition: potential HNI tier with PMS/AIF access.
  ET Money's existing infrastructure is the mass-market acquisition funnel.

**Automation level**

ET Money holds SEBI IA registration (INA100001718). The Genius service
uses a proprietary quant model for dynamic asset allocation across equity,
debt, and gold. Under SEBI IA rules, the IA entity (as a non-individual/
corporate IA) must have qualified investment advisers who are responsible
for the suitability framework and investment policy — human professionals
set the model parameters and sign off on portfolio policy; the algorithm
executes within those parameters. This is not a purely algorithmic robo
that operates without any human governance. The ₹249/month price point
means there is no per-client human review of individual portfolios, but
qualified investment advisers govern the model. **Human-in-loop here is a
compliance structure, not a client-facing feature.**

**Genuine advantages**

- Only product in this comparison with a scaled, paying subscription
  advisory tier (76,000 Genius subscribers at acquisition — evidence that
  Indians will pay ₹249/month for algorithmically-delivered advice).
- IA registration cleanly separates advisory (Genius) from distribution
  in the same app — SEBI prohibits giving both to the same client, and ET
  Money managed this bifurcation rather than conflating them.
- Acquired by 360 One gives the platform institutional backing, credibil-
  ity, and a cross-sell path to PMS/AIF that no pure fintech can match.
- Portfolio health check across 100+ parameters provides a genuine post-
  investment engagement layer that keeps users active beyond the initial SIP.

**Real drawbacks**

1. Post-acquisition strategic uncertainty. 360 One's core business is
   HNI wealth management. ET Money's 22-year-old first-time investor is
   not 360 One's typical client. Whether the platform continues to be
   developed for mass-market retail or quietly becomes a funnel for HNI
   upsell is unclear and creates product direction risk.
2. SEBI's adviser/distributor conflict-of-interest rule means a Genius
   (advisory) customer cannot also be a distribution customer of 360 One.
   This structural constraint limits how ET Money and 360 One can be
   integrated without regulatory complications.
3. Goal planning remains a labeling system, not a simulation engine.
   Genius's quant model handles portfolio allocation but does not solve
   the multi-goal trade-off problem — a user with five competing goals
   still gets one portfolio, not a goal-sequenced allocation plan.
4. Algorithmic rebalancing creates implicit strategy changes that
   generate capital gains — a complaint that also appears in Scripbox
   reviews, and is inherent to any model portfolio service that
   rebalances frequently.

**How our architecture addresses each drawback**

1. We are a neutral planning engine with no acquisition agenda. The
   output (probability, SIP amount, trade-offs) is in the user's
   interest by construction; there is no HNI upsell we're steering
   toward.
2. Our MVP holds no IA registration and gives no named product advice —
   so the adviser/distributor conflict does not arise. The architecture
   cleanly avoids this structural problem by design.
3. Cross-goal constrained optimization is the core of our computation
   layer, not a portfolio feature bolted on afterward.
4. We produce a plan, not a portfolio. The user invests wherever they
   choose. No algorithmic rebalancing means no unintended capital gains
   events. This is not a drawback to exploit but a structural difference.

---

### 2.3 Scripbox

**Business / operating model**

Founded 2012. SEBI IA registration (INA200001041, Non-Individual/
Corporate). Holds AMFI MFD registration. Revenue: 91.3% brokerage and
commission (₹77 crore of ₹84 crore operating revenue in FY24), 7.4%
advisory fees (₹6.2 crore), 1.3% PMS fees. Commission rate 0.6–1.2% of
client AUM. FY24 revenue ₹84 crore, FY25 ₹107 crore — first profitable
year after 12 years. AUM ₹18,500 crore.

In August 2024, introduced subscription-based advisory (direct plans
where users pay Scripbox a fee rather than Scripbox earning commission
from the fund). This mirrors Zerodha's model shift. Dual-track: regular
plan distribution (commission) and direct plan advisory (fee).

Has acquired 10 wealth management firms in recent years including Wealth
Managers India — explicitly building toward a hybrid human+algorithm
model targeting multi-generational wealth management.

**Customer segmentation**

- Mass retail: goal-based SIP setup for five standard goals (education,
  car, vacation, retirement, custom). This is the entry product.
- Scripbox Wealth (separate subdomain, ria.scripbox.com): full advisory
  service under IA registration for HNI clients, with wealth managers
  involved. Minimum ticket implied (not publicly stated).
- Late-2024 unified portfolio redesign: moved mass-market from per-goal
  portfolios to one unified SIP across all goals — a simplification that
  reduces operational complexity but removes goal-level granularity.

**Automation level**

Hybrid with meaningful human involvement at the policy level. Fund
selection is algorithmic (2,000+ funds evaluated across 14 categories,
no stated human involvement in ranking). But "recommendations are shaped
by expert advisors" per their own marketing. IA registration requires
qualified investment advisers to be responsible for suitability — these
are real employees setting policy. The 10 wealth management firm acqui-
sitions are not window dressing; they are bringing in human advisers for
the HNI segment. Mass-market retail gets the algorithm; HNI gets humans.

**Genuine advantages**

- Only peer-reviewed track record: 12 years of actual fund selection
  performance published publicly, including a 14.5% 3-year CAGR on the
  Long Term Portfolio.
- Unified portfolio model (post-2024) genuinely simplifies operations
  for users who don't want to manage multiple accounts and SIPs per goal.
- Revenue profitable as of FY25 — validates that a fee/commission hybrid
  model for MF advisory can reach profitability, which most fintech
  competitors have not achieved.
- Backtested asset allocation across equity/debt/gold is methodologically
  more honest than a single return-rate assumption.

**Real drawbacks (from app store and forum reviews)**

1. Frequent strategy changes. Users report that Scripbox periodically
   changes fund recommendations, requiring redemption and reinvestment.
   This triggers capital gains tax events and breaks the compounding
   narrative. Direct quotes from Play Store: "Every year change in
   strategy, fund recommendations, and withdrawal recommendations for
   reinvestment is not letting the fund compound and attracting Capital
   Gains."
2. Broken KYC processes. Users report "endless formalities" for simple
   changes (bank account number, email address) with different reasons
   given each contact: logo mismatch, signature not matching, etc.
   Customer support's inability to resolve standard onboarding operations
   is a structural problem.
3. Tax reporting failure. The tax report format Scripbox generates is
   reportedly not accepted by leading tax filing apps. This is a critical
   failure for a product aimed at disciplined long-term investors who must
   file taxes on gains.
4. The unified portfolio model (post-2024) removes goal-level granularity.
   A user cannot see "what percentage of my corpus is earmarked for
   housing vs. retirement." Everything is one pool — simpler to manage
   but loses the planning visibility that goal-based investing is
   supposed to provide.
5. Customer service response time. 7-day non-response windows reported;
   IVR broken. For a platform managing ₹18,500 crore of client assets,
   this is reputational risk.

**How our architecture addresses each drawback**

1. We produce a plan, not a managed portfolio. We never recommend
   selling and buying — we output required SIP amounts. No algorithmic
   rebalancing means no strategy-change-triggered capital gains events.
2. MVP does not require KYC for planning output. The planner works
   before any account creation, and any saved scenarios are lightweight
   (no financial account linking in MVP). KYC-related friction does not
   arise.
3. We do not generate tax reports in MVP. We explicitly do not manage
   investments. Tax events do not exist because we are not executing
   transactions.
4. Per-goal corpus tracking is in the data model by design (goal_results,
   goal_allocations tables). Users see their plan at the goal level.
   We do not adopt the unified pool approach.

---

### 2.4 INDmoney / Finzoom

**Business / operating model**

Entity: Finzoom Investment Advisors Pvt Ltd. SEBI IA registration
(INA100012190). Revenue: 76% distribution commissions (₹53.6 crore FY24),
brokerage fees, subscription/premium services, affiliate referrals.
FY24 operating revenue ₹70 crore. FY25 ₹164 crore (2.3x YoY) — the
fastest-growing player in this comparison. Less than 10% of FY25 revenue
from F&O, which is strategically notable: INDmoney has deliberately
avoided the F&O trading trap that is now under SEBI scrutiny.

International investing (US stocks) runs through GIFT City IFSCA, not
SEBI, allowing INDmoney to serve US-market investors without SEBI IA
complications for that product.

**Customer segmentation**

- Free tier: multi-asset aggregation, goal tracker, US stock investing,
  SIP setup. Target: urban young professional who wants one dashboard
  for all financial accounts (the app's primary differentiation).
- Premium subscription: advanced analytics, personalized advice sessions,
  portfolio optimization tools.
- Family accounts: reported several hundred thousand linked family
  accounts as of 2025. Family-level net worth aggregation is a unique
  positioning.
- No explicit HNI tier; platform is mass-market focused.

**Automation level**

Semi-robo with human escalation. INDmoney holds full IA registration
(Finzoom), so algorithmic advice is permissible under compliance. The
system described in available sources: AI-driven portfolio construction
for standard queries; human adviser access for complex situations (tax,
goal conflicts, market crash counseling). The IA license means human
investment advisers are employed and accountable for the advice layer,
even if most interactions are algorithmic. This is the genuine "hybrid"
model, not a marketing claim.

Note from independent analysis: "INDmoney is not a SEBI-registered
investment advisor" has been stated in some sources, referring to the
fact that INDmoney (the brand) and Finzoom (the registered entity) are
separately branded — but Finzoom IS INDmoney's operating entity. The
registration is real; the brand separation creates confusion in public
discourse.

**Genuine advantages**

- Best-in-class multi-asset aggregation: automatically syncs bank, EPF,
  Demat, and investment accounts. For a user who wants to see their whole
  financial picture in one place, no competitor matches this.
- 2.3x revenue growth in FY25 with <10% F&O exposure — demonstrates
  sustainable unit economics without trading volatility.
- Family account feature is genuinely unique: linking multiple family
  members' accounts and showing household-level net worth is a product
  angle none of the other competitors in this list have pursued.
- GIFT City structure for US investing provides a regulatory workaround
  that lets them serve a segment (US-market exposure) that most Indian
  fintech cannot easily reach.

**Real drawbacks (Trustpilot, app stores)**

1. Withdrawal failures. Multiple verified reports of funds held for 10+
   days, money stuck in "switch" status for over a year with no
   explanation, UPI transactions failing with money deducted and not
   refunded. These are not UI complaints — they are functional failures
   that affect real money.
2. Support closes tickets without resolution. The pattern documented on
   Trustpilot: user raises issue, ticket is closed with a boilerplate
   response, funds remain stuck. This is the highest-severity complaint
   category because it involves real money at risk.
3. Buggy app surface. Described as "very buggy" across multiple
   independent review sources. The UPI failure problem suggests
   infrastructure reliability issues, not just UI polish problems.
4. Goal planning is tracking, not simulation. Despite holding IA
   registration, INDmoney's goal planner shows alignment of existing
   investments to stated goals — it does not forward-simulate, does not
   run Monte Carlo, and does not surface trade-offs. The goal tracker is
   a dashboard, not a planning engine.

**How our architecture addresses each drawback**

1 and 2. We do not handle money. MVP explicitly executes no transactions.
  There is no mechanism for funds to get stuck because no funds pass
  through the platform. The withdrawal failure problem is structural to
  any brokerage/execution platform and is not a risk we inherit.
3. We hold no financial accounts and do not touch transactions; the
   reliability risk profile is a standard web application rather than
   a financial infrastructure operator.
4. Monte Carlo forward simulation with cross-goal optimization is the
   core engine, not an overlay on tracked investments.

---

### 2.5 Recipe / Finology

**Business / operating model**

Entity: Finology Ventures Pvt Ltd. Dual SEBI registration: IA
(INA000012218) and Research Analyst (INH000024277). Revenue model:
freemium with two subscription tiers — Finology ONE at ₹499/month (all
tools: Recipe, Quest, Ticker, Finology 30 stock basket) or ₹299/month
(Quest + Ticker only). FY24 revenue: ₹4.69 crore. YouTube channel at 5
million subscribers is a significant organic acquisition channel. 20,000+
investors self-reported.

Recipe (goal planning) is free; paid revenue comes from stock research
(Finology 30 basket), stock screening (Quest), and fundamental analysis
(Ticker). The goal planner is a user acquisition surface that monetizes
through the premium stock research.

**Customer segmentation**

- Free (Recipe): DIY goal planners who want multi-goal prioritization
  and an SIP structure. Target: young retail investors building their
  first financial plan.
- Finology ONE (₹299–499/month): active individual investors who want
  stock research and a curated 30-stock portfolio. Different persona
  from the goal planner user — more experienced, more engaged.
- No HNI tier. No B2B or advisory-for-hire model.

**Automation level**

IA + RA registered. Recipe Goal Tracker is algorithmic: it takes
priority ordering from the user and generates an SIP structure. The
Finology 30 stock basket is human-curated by a registered Research
Analyst — human analysts select the 30 stocks. Advisory output (for
the IA-registered service) would require human oversight, but the
goal planner specifically is presented as DIY and mathematical, not
advisory. The dual registration gives them flexibility: Goal Tracker
operates as a DIY tool (no advice trigger), Finology 30 is research
output (RA), and any personalised stock advice would fall under IA.

**Genuine advantages**

- IA + RA dual registration gives the most comprehensive regulatory
  coverage of any competitor reviewed — can do goal planning, research
  publication, and personalised advice under one entity.
- Recipe is genuinely free with no login friction for basic planning.
- Multi-goal priority structure is ahead of Groww/ClearTax/Dhan in
  planning sophistication.
- YouTube audience of 5 million subscribers is a distribution advantage
  that cannot be replicated quickly — organic trust capital.
- Revenue from stock research decouples the planning tool from
  commission conflicts: Finology has no incentive to push users toward
  any particular mutual fund to earn trail commissions.

**Real drawbacks (Trustpilot reviews)**

1. Premium subscription quality. Finology 30 stock basket and Quest
   research are described by paying subscribers as "utterly
   disappointing" and "useless" with stock recommendations that are
   2 years out of date. This is the product's primary revenue generator
   and its most visible failure.
2. Recipe's goal planning is priority ordering, not constraint
   optimization. As documented in ARCHITECTURE.md §1.2: when goals
   exceed income capacity, lower-priority goals simply aren't funded.
   No trade-off surfacing, no "delay X by N years to make Y feasible."
3. No Monte Carlo. Projections use a deterministic return assumption.
   A single return number for a 30-year projection is not credible for
   serious planning.
4. Small revenue base (₹4.69 crore FY24) relative to product ambition.
   At ₹499/month, that implies ~780 active subscribers — a thin paying
   user base for a five-million-subscriber YouTube channel. Conversion
   from free audience to paid product is very low.

**How our architecture addresses each drawback**

1. We have no premium stock research product. The planning engine is
   the product, not a cross-sell surface. No stale research problem.
2. Cross-goal constrained solver with explicit trade-off generation
   is our primary differentiator over Recipe — see ARCHITECTURE.md §4.4.
3. Monte Carlo (1,000 simulations, server-side vectorized) is
   foundational to our output — success probability, not a point number.
4. Our product is the plan itself, not a vehicle to sell stock research.
   The revenue question for us is deliberately deferred (see open
   question 1 in ARCHITECTURE.md §6).

---

### 2.6 Groww

**Business / operating model**

SEBI broker registration (INZ000208032), AMFI MFD, DP with CDSL.
Revenue (FY25 estimated): brokerage ~70% (~₹2,800 crore), MF
distribution commissions ~20% (~₹800 crore), subscriptions/advisory
~7% (~₹300 crore), other ~3%. Total FY25 revenue estimated ₹4,000+
crore. Launched Groww AMC in 2023 — now earns management fees in
addition to distribution commissions, shifting from transaction-based
to recurring AUM-based income. Preparing for IPO at reported ₹7 billion
valuation.

**Customer segmentation**

- Mass retail, first-time investor: zero-commission mutual funds, direct
  plans, ₹100 minimum SIP. Designed to onboard India's first-time
  investor at the lowest possible friction.
- Active trader: equity brokerage (₹20/trade flat), F&O, margin trading.
  This is the primary revenue segment.
- No HNI tier. No advisory product.

**Automation level**

Execution platform only. AMFI MFD registration permits distribution,
not advice. Groww explicitly disclaims: "Groww does not advise or
recommend any stocks, mutual funds or portfolios." The SIP calculator
and goal labels are fully automated computation with zero advisory
component. No human is in the loop because no advice is being given —
the user selects and executes. SEBI compliance for MFD requires KYC
and suitability disclosure, but no investment adviser oversight.

**Genuine advantages**

- Distribution scale: largest MF distributor by number of new accounts
  in India. Network effects and brand recognition that no new entrant
  can approach.
- Zero-commission direct plan investing. Genuinely free distribution,
  better for users than regular plan commissions.
- Lowest onboarding friction in the market. A new investor can go from
  zero to first SIP in minutes.
- Groww AMC adds long-term strategic depth — it is no longer purely a
  distributor but also a fund manufacturer.

**Real drawbacks (Play Store, Trustpilot, Reddit)**

1. Technical reliability failures. A 2024 trading platform outage led
   to complete service unavailability. SEBI settlement of ₹34 lakh paid.
   GTT orders triggered at wrong prices (users report orders executing
   far below the set trigger level). For a trading platform these are
   serious.
2. AI-only customer support. Users report receiving only AI-generated
   responses to complaints. For issues involving real money, this is
   unacceptable — documented in multiple independent reviews.
3. 150% fee hike on low-value trades in 2024, implemented without clear
   user notification. Perception of opaque pricing changes.
4. Goal planning is a label on a SIP, not a planning engine. "Goal-based
   investing" on Groww means naming your SIP "Education Fund" — there is
   no simulation, no inflation adjustment in the SIP setup, no multi-
   goal conflict resolution.

**How our architecture addresses each drawback**

1. We are not a trading platform. Infrastructure reliability for a
   planning tool (read-heavy, computation-heavy, not transaction-heavy)
   is a different and simpler problem than exchange connectivity and order
   routing.
2. Planning results are deterministic and auditable. A wrong SIP
   calculation can be explained step-by-step; there is no GTT order that
   executes unexpectedly.
3. No transaction execution means no fee structure to change or hide.
4. Multi-goal simulation with inflation-adjusted goal costs and cross-
   goal conflict resolution is the fundamental product, not a label.

---

### 2.7 ClearTax

**Business / operating model**

AMFI MFD registration (ARN110027). SEBI BASL member. Primary revenue:
tax filing (₹~$19.8M / ~₹165 crore in 2024), which is the core business.
Investment product (ELSS mutual funds, goal planner calculator) is
secondary — it exists to cross-sell tax-saving investment products to
ClearTax's large tax-filing user base. MF distribution commissions are
supplemental revenue. Freemium: basic tax filing free, premium at a fee;
investment product free (monetized via MFD commissions).

**Customer segmentation**

- Salaried employees filing ITR: the primary, dominant user. Goal
  planner is a secondary surface for this person.
- ELSS investor: tax-saving mutual fund buyer drawn in by the ITR filing
  relationship. The goal planner calculator is specifically designed to
  push toward ELSS ("Save taxes with Clear by investing in tax saving
  mutual funds (ELSS) online").
- No HNI product. No goal-conflict or multi-goal planning depth.

**Automation level**

No advisory automation. MFD registration only — ClearTax distributes
funds but cannot advise. The goal planner is a pure calculator (static
formula, no simulation). Recommends specific fund categories ("ELSS")
via the platform but relies on its MFD status for distribution, not IA
status for advice. Human involvement exists only in the tax advisory
consultation tier (premium service), not in investment guidance.

**Genuine advantages**

- Massive existing user base: India's largest tax filing platform. The
  distribution advantage is structural — ClearTax sits at the most
  common financial touchpoint (tax season) and can cross-sell investment
  products to a captive, already-verified (KYC via PAN) audience.
- ITR filing integrates PAN-linked financial data, which means ClearTax
  has visibility into income and existing investments that no pure
  investment platform can match without explicit account linking.
- Trusted brand for a boring-but-necessary task, which transfers to
  credibility for adjacent financial products.

**Real drawbacks**

1. Goal planner is a single-goal calculator with no planning depth —
   a marketing surface for ELSS distribution, not a financial planning
   tool. Users who arrive expecting planning will find a SIP estimator.
2. ELSS bias is structural and transparent: the goal planner explicitly
   routes to tax-saving funds. This is appropriate for the tax season
   context but useless for goals where ELSS is not the right instrument
   (housing, overseas education).
3. Investment product is secondary to the core tax business. Product
   investment (engineering, UX) goes to the tax product; investment
   planning is under-resourced by construction.

**How our architecture addresses each drawback**

1. Multi-goal, category-specific inflation, Monte Carlo — the product is
   the planning depth ClearTax lacks.
2. No product-level recommendation means no instrument bias. Asset-class
   guidance only; user chooses their own vehicle.
3. Planning is the core product, not an attached funnel.

---

### 2.8 Dhan

**Business / operating model**

SEBI broker (INZ000006031), AMFI member. Revenue: 88% brokerage and
commissions (₹769 crore of ₹877 crore FY25 operating revenue). FY25
net profit 2.6x to ₹408 crore. Unicorn at $1.2 billion valuation post
$120M Hornbill Capital round. Franchise-led distribution expansion to
Tier-II and Tier-III cities. SIP Goal Calculator is a marketing tool
for user acquisition into the brokerage platform — it exists to convert
a retirement-planner search into a Dhan account opening.

**Customer segmentation**

- Primary: active retail trader (equity, F&O, commodities). 88% of
  revenue confirms this.
- Secondary: passive mutual fund investor reached via SIP calculators
  as acquisition funnel.
- Women investor initiative: 50% lower brokerage for women — a
  deliberate segment play.
- No planning depth for any segment.

**Automation level**

None for planning. The SIP Goal Calculator is a static formula
(FV = PV × (1+r)^n) with a goal input. No simulation, no multi-goal
modeling. Execution is algorithmic (order routing, settlement). Advice
is not given; SEBI broker registration does not permit it.

**Genuine advantages**

- Unicorn-scale brokerage with strong Tier-II/III reach through
  franchises — distribution width that a startup cannot match.
- Flat ₹20 brokerage is clean, transparent pricing.
- Strong FY25 financials validate the business model.

**Real drawbacks**

1. SIP Goal Calculator is a calculator, not a planner. Single goal,
   deterministic return, no inflation — it answers "how much SIP for
   this target?" and nothing more.
2. The platform's interest is active trading, not long-term goal-based
   investing. F&O is more profitable than SIP facilitation. The planning
   tool is content marketing, not a product investment.
3. No planning depth for any user persona. Dhan is not trying to solve
   the problem this product addresses.

**How our architecture addresses each drawback**

Not directly competitive on any dimension — Dhan is a brokerage, not a
planner. Our addressable user on Dhan is the investor who has an account
but no forward simulation of whether their SIP will actually reach
their goals.

---

### 2.9 Nippon India MF

**Business / operating model**

AMC. Revenue from management fees on ₹5.73 lakh crore AUM (Dec 2024).
FY24 net profit ₹1,106 crore (53% YoY growth). 596 schemes. The goal
planner is a retention and AUM growth tool — it keeps existing investors
inside the Nippon ecosystem by showing them their fund's projected
performance. It is not a neutral planning tool; by construction it
points users toward Nippon funds.

**Customer segmentation**

- Existing Nippon MF investors: goal planner shows performance of their
  existing holdings toward stated goals.
- Prospective retail investors: the planner is also a top-of-funnel
  acquisition tool for new SIPs, all of which land in Nippon funds.
- No HNI or multi-fund planning. Single-AMC bias by construction.

**Automation level**

None for planning. The goal planner calculator is static formula-based.
No simulation, no multi-goal modeling, no Monte Carlo. Full automation
for fund operations (NAV calculation, SIP processing) but that is AMC
operations, not financial planning. No SEBI IA registration — AMCs are
not investment advisers.

**Genuine advantages**

- Scale and trust: ₹5.73 lakh crore AUM is a credibility signal that no
  planning-only startup can match. When Nippon's goal planner says "your
  SIP will reach ₹X," users trust it more than a startup's identical
  calculation.
- Existing distribution network of lakhs of MFDs who already use Nippon
  planner as a client-facing tool. The B2B2C distribution already exists
  — it just does not use sophisticated planning.
- Data advantage: Nippon has historical SIP redemption and goal
  achievement data across its entire AUM that no external planner can
  access.

**Real drawbacks**

1. Single-AMC bias makes neutral planning impossible by design. A goal
   planner that only considers Nippon funds is useful to Nippon, not to
   the investor.
2. Static calculator, no simulation. Deterministic return, no inflation
   adjustment visible in the tool, no goal conflict resolution.
3. The planner exists to sell Nippon funds, not to plan the user's life.
   These incentives are structurally misaligned with honest planning.

**How our architecture addresses each drawback**

1. No fund-level recommendation means no single-AMC bias. Asset-class
   guidance only.
2. Monte Carlo + category-specific inflation are architecturally central.
3. Explicit non-advice disclaimer and no revenue from fund distribution
   in MVP means no incentive misalignment with the user.

---

### 2.10 Walnut / Axio

**Business / operating model**

Walnut was acquired by Capital Float (NBFC lender) in 2018 for $30M and
merged with Walnut369 and Capital Float to become Axio. Revenue model:
credit products (BNPL, personal credit), not investment distribution.
NBFC registration with RBI, not SEBI-regulated for investments.

**Customer segmentation**

Expense tracker users who want SMS-based spending categorization. Not
a planning or investment product. The "financial goals" feature in
Walnut/Axio is savings goal tracking (budget target), not investment
simulation.

**Automation level**

SMS parsing is automated (rule-based NLP for transaction categorization).
Credit decisioning is algorithmic (NBFC underwriting model). No
investment advice — not in scope for the product or the regulation.

**Assessment**

Walnut/Axio is not a competitor to this product and was included in the
brief's research list to be verified rather than assumed. Confirmed: it
is an expense tracker and BNPL product, not a financial planning engine.
The only overlap is the user persona (urban young professional tracking
spending), not the product function.

---

## 3. Competitor Summary Table

| Competitor | Revenue model | SEBI reg. type | Customer tier | Automation level | Strongest point | Worst real complaint | Our counter |
|---|---|---|---|---|---|---|---|
| **calcwise.finance** | None / early stage | None | Free, anonymous, single-tier | Fully algorithmic, client-side | Zero friction; Monte Carlo; privacy | Session-only; no persistence; no cross-goal solver | Persistent saved runs; constrained optimizer; income trajectory |
| **ET Money / 360 One** | MFD commission + Genius subscription (₹249/mo) | IA (INA100001718) | Free + Genius paid | Algo quant model; human IA oversight at policy level (compliance requirement of IA reg.) | Only scaled paying advisory tier in this set (76K subscribers) | Post-acquisition direction unclear; goals are labels not simulation | Neutral planning engine; no acquisition agenda; multi-goal solver |
| **Scripbox** | 91% MFD commissions; 7% advisory fees | IA (INA200001041) | Mass retail + HNI (ria.scripbox.com) | Algo fund selection; human advisers shape policy; hybrid via acquisitions | 12yr track record; first profitable year; unified portfolio model | Strategy changes trigger CGT; broken KYC flows; tax reports rejected by filing apps | No rebalancing events; no account linking; per-goal corpus visibility |
| **INDmoney** | 76% distribution + brokerage + subscription | IA (INA100012190) | Mass retail + family accounts | Semi-robo; algo + human escalation for complex queries | Best multi-asset aggregation; 2.3x FY25 growth; family account unique | Withdrawal failures; funds stuck; tickets closed without resolution | No money handling; planning only; zero financial infrastructure risk |
| **Recipe / Finology** | Freemium + ₹299–499/mo subscription | IA + RA (INA000012218 + INH000024277) | Free planners + active stock-research subscribers | Algo goal tracker; human-curated stock basket (RA requirement) | Dual IA+RA; YouTube distribution moat; no commission conflict | Paid stock research stale and "useless" per subscribers; no Monte Carlo | Planning is the product, not a cross-sell; Monte Carlo core; solver not ordering |
| **Groww** | 70% brokerage + 20% MF commissions + 7% subscriptions | MFD + broker (no IA) | Mass retail, first-time investor | Execution only; no advice; no automation of planning | Scale; zero-commission direct plans; lowest friction onboarding | GTT orders at wrong prices; AI-only support; fee hikes without notice | Not a brokerage; no order execution; no GTT; planning only |
| **ClearTax** | Tax filing (primary) + MFD commissions | MFD (ARN110027) | Salaried tax-filer, ELSS buyer | None; static calculator | Captive tax-season audience; PAN-linked income data | Goal planner is ELSS marketing, not planning | No tax-product bias; multi-goal multi-instrument |
| **Dhan** | 88% brokerage | Broker + AMFI (no IA) | Active trader, Tier-II/III | None; static calculator | Unicorn scale; Tier-II distribution | Calculator not a planner; F&O is the real business | Not competing on brokerage; planning depth vs. marketing surface |
| **Nippon India MF** | AMC management fees on ₹5.73L crore AUM | AMC (not IA) | Existing Nippon investors | None; static formula | Trust via scale; B2B2C distribution through MFDs already exists | Single-AMC bias; no neutral planning | No fund bias; asset-class only; neutral planning output |
| **Walnut / Axio** | BNPL/credit (NBFC) | RBI NBFC (not SEBI) | Expense-tracker users | SMS parsing automation | Not relevant | Not a planning competitor | N/A |

---

## 4. Self-Critique of Our Architecture

The following are the genuine weakest points in the architecture
described in ARCHITECTURE.md, with a realistic fix for each. These are
not theoretical concerns — each one is a real failure mode.

---

### 4.1 Return distribution assumption is wrong for tail risk

**The problem:** The Monte Carlo engine uses a multivariate normal
distribution for equity and debt returns. Historical equity returns are
not normally distributed — they have fat tails (excess kurtosis), mild
negative skewness, and volatility clustering (bad years cluster). A
normal distribution systematically underestimates the frequency and
severity of bad outcomes. The P25 corridor on a probability fan chart
built from a normal distribution will be optimistic compared to actual
historical outcomes.

This matters most for near-term goals (3–7 years) where a bad sequence
of returns in the early years cannot be recovered. For a 40-year
retirement goal, the law of large numbers provides some cover. For
"housing in 5 years," it does not.

**The fix:** Use block bootstrap on actual historical Nifty 50 annual
returns (available from NSE, ~24 years of data) rather than a parametric
normal distribution. Resample 40-year blocks with replacement from the
actual return series. This preserves the true distribution shape
including fat tails and serial correlation without needing to parameterize
it. Slightly more complex to implement (requires a historical return
dataset), but the methodological honesty is a genuine differentiator over
competitors that use parametric assumptions.

**Interim fix if bootstrapping is deferred:** Use a Student-t distribution
with degrees of freedom ~4–5 (matches the fat-tail kurtosis of equity
returns reasonably well), not a normal distribution. This is a single
parameter change.

---

### 4.2 The LP relaxation for the cross-goal solver may misfire on non-linear cases

**The problem:** The solver approximates the success-probability function
p_j(sip) as piecewise linear from 5 MC sample points per goal, then
uses scipy.linprog. This is fast but:
- 5 sample points may miss significant non-linearity near the knee of
  the SIP→probability curve (where small SIP increases produce large
  probability gains).
- For goals with very different horizon lengths (3-year housing vs.
  40-year retirement), the success-probability functions have radically
  different shapes that are harder to approximate linearly.
- The LP may allocate all remaining capacity to the goal with the highest
  marginal probability gain per rupee, leaving other goals at zero, when
  a more balanced allocation would actually maximize total weighted
  success. This is a solver artifact of the linear approximation, not a
  genuine optimal solution.

**The fix:** Use 10–15 MC sample points per goal for the piecewise linear
approximation, and constrain the LP to ensure no goal receives less than
a minimum floor allocation (e.g., 20% of its required SIP) unless the
user has marked it as deferrable. Add a post-LP verification pass that
re-runs the full Monte Carlo under the LP-output allocation and checks
whether the actual achieved probabilities match the LP's predictions; if
they diverge by >5%, re-run the LP with the corrected sample points.

---

### 4.3 Annual Monte Carlo timestep is wrong for short-horizon goals

**The problem:** Annual simulation is 12× faster than monthly but
introduces meaningful error for goals with a horizon of 3–6 years. With
only 3–6 annual draws, the variance of the simulated outcome distribution
is dominated by the sampling variance of a small number of draws, not the
underlying market risk. The practical effect: success probabilities for
short-horizon goals will be miscalibrated. A 4-year housing goal is
likely to show either higher or lower probability than it should.

**The fix:** Detect goals with target_year − current_year ≤ 7 and run
monthly simulation (12× per year per simulation) for those goals only.
Vectorized numpy monthly simulation for 1,000 simulations × 7 years ×
12 months is still under 1 second. The performance cost is acceptable
and isolated to short-horizon goals.

---

### 4.4 Income trajectory UX may kill the feature before it lands

**The problem:** The income_segments schema is powerful, but the UX to
enter "I'll take a 2-year career break from 2031 to 2033 at zero income,
then restart at ₹1.2L/month growing at 7%" is not obvious or easy to
build well. If the UI exposes the full schema complexity, most users will
skip it and use the simplest possible input — a single salary + growth
rate — rendering the segments capability unused for the majority. If the
UI doesn't expose it at all, a real differentiator disappears.

**The fix:** Ship two modes:
- Simple (default, on the main form): "Current salary" + "Annual growth
  rate" + one optional "Career break" toggle (yes/no, start year,
  end year, income during break). Covers the 80% case.
- Advanced (accessible but not prominent): full segment editor in a
  separate sheet/modal. For users planning around job switches, major
  salary changes, or RSU events.

The schema already supports both modes. The engineering cost is only in
the UI — design the simple case first and treat the advanced editor as
a separate feature milestone.

---

### 4.5 The B2B2C V2 path is incompatible with a public B2C MVP by default

**The problem:** ARCHITECTURE.md §5.2 lists white-label API licensing
to RIAs/AMCs as a V2 monetization path (SimpliFin model). But if we
first build a public B2C product, an AMC or RIA will not want to license
an engine that also powers a consumer product their clients might find
directly — it cannibalizes their client relationship. The B2B2C path
works well when the engine is API-first from day 1 and the consumer
surface is private or non-competing.

**The fix:** Design the computation layer as an internal Python module
with a clean HTTP API (as specified in the stack), but do not treat the
FastAPI endpoint as purely internal. Document it as a first-class API
from day 1 with authentication. The cost of doing this upfront is
minimal (a few extra hours writing API docs and adding an API key layer).
The cost of retrofitting it from an internal-only monolith to a licensable
API later is a substantial rewrite. This makes V2 possible without a new
codebase.

---

### 4.6 Goal confidence percentage is mathematically underspecified

**The problem:** The schema has confidence_pct (0–100) and ARCHITECTURE.md
says it "feeds into the optimizer as a weight." But there are three
different things this could mean:
- A: Allocate (confidence/100) × full_required_sip to the goal —
  underfunds the goal if it happens.
- B: Show the plan as-if the goal is certain but display its probability
  — purely informational.
- C: Probabilistically weight the goal in the optimizer objective
  function — mathematically clean but hard to explain to users.

None of these is specified. A developer implementing this without further
direction will pick one arbitrarily, and the wrong choice creates a
confusing user experience.

**The fix:** The correct UX behavior is B + branch comparison: for any
goal with confidence_pct < 100%, compute the plan twice — once with the
goal included at full cost (plan if it happens), once with the goal
excluded (plan if it doesn't). Show both side by side and let the user
decide which plan they want to fund toward. Confidence percentage then
becomes a labeling device, not an optimizer input, which is both simpler
to implement and far easier to explain.

---

### 4.7 Server-side PDF generation will have cold-start latency on low-cost hosting

**The problem:** WeasyPrint is a heavy Python dependency (Pango, Cairo,
fontconfig). On Railway or Render free/hobby plans, the Python container
cold-starts after inactivity (10–30 seconds). A user who clicks "Generate
PDF" after a period of inactivity will encounter a blank screen for 30
seconds before anything happens. This is a poor experience for a feature
that should feel like a document delivery.

**The fix:** Pre-generate the PDF as part of the simulation run
completion step, not on-demand when the user clicks the button. Store
the PDF bytes in object storage (Supabase Storage, or an S3-compatible
bucket on Railway) and serve it as a pre-signed URL. "Download PDF"
becomes an instant link to an already-generated artifact, not a
synchronous generation trigger. This also means the PDF is reproducible
from stored run data and does not require the Python container to be
warm at click time.

---

### 4.8 Saved scenarios will become stale without an explicit staleness model

**The problem:** A simulation run saved 8 months ago was computed with
the inflation defaults and return distribution parameters current at that
time. If defaults change (e.g., education inflation updated from 10% to
12%), old runs look wrong compared to new ones but are not labeled as
outdated. A user might show their Plan A from 6 months ago alongside a
new Plan B and compare them as if they are on the same basis, when
they are not.

**The fix:** Store config_snapshot as a frozen JSON blob on every run
(already in the schema). Add a UI indicator: "Computed with settings from
[date]. Re-run with current defaults?" Provide a one-click re-run that
creates a new SimulationRun with the current config but the same goal
inputs. Never present old runs as reflecting current planning state
without a staleness warning. Implement this before launch, not as a
follow-up — once users have saved runs, the migration is harder.

---

### 4.9 The SEBI disclaimer must be a hard component constraint, not a page prop

**The problem:** ARCHITECTURE.md §5.1 says "prominent disclaimer on
every output page." This is an intention, not an architecture. If the
disclaimer is implemented as a prop that pages optionally include, a
developer will eventually ship an output page without it — either by
mistake, because they thought it was optional, or because the layout
felt crowded. SEBI's digital compliance rules for intermediaries specify
legibility requirements (font size, placement). "Prominent" is not
enforceable without a hard technical constraint.

**The fix:** Build the disclaimer as a required layout wrapper component
that every output surface must use — not a component they can choose to
import. The exact SEBI-mandated text ("This is a mathematical projection
and not investment advice. Consult a SEBI-registered Investment Adviser
before making financial decisions.") should be hardcoded inside the
component, not passed as a prop. Wrap every result page with this
component at the router level, not at the page level, so it cannot be
accidentally omitted. Add a lint rule or CI check that fails if an
output route renders without the wrapper.

---

### 4.10 The product has no engagement loop after the first plan

**The problem:** A user comes, builds a plan, sees their results, and
leaves. A week later, nothing prompts them to return. A year later, when
their salary has changed, their housing goal has shifted, or markets have
had a bad year, they have no reason to update the plan. The value of
persistent scenarios is zero if users never return.

Calcwise's session-only model makes this a non-problem — it never claims
to be a long-term relationship. We claim to be a planning partner over
a 20–40 year horizon, which means retention is essential to the product
promise.

**The fix:** Two mechanisms, both technically simple:
1. Annual "plan review" email: on the anniversary of the user's last
   simulation run, send an email ("Your plan is now 12 months old. A
   lot may have changed — your income, your goals, market returns. Click
   to update your plan."). This is a cron job + transactional email, not
   a product feature.
2. In-app "plan health" indicator: show a banner on returning login that
   shows how many months ago the plan was computed, and whether the
   user's target years have moved closer. Simple date arithmetic, no
   re-computation required. Creates a nudge without being intrusive.

Neither of these is in ARCHITECTURE.md. Both should be in the MVP scope,
not V2. The plan without a return mechanism is a one-shot calculator
with a database attached.
