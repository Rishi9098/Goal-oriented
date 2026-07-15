# Feature Gap Analysis — Challenge Every Assumption

**Date:** 2026-07-06
**Method:** Every feature candidate surfaced across Phases 0-6 is scored against your explicit framework: user problem, estimated users benefited, implementation complexity, regulatory/compliance implications, required data sources, security/privacy risk, why-prioritize-over-alternatives, and a build now/later/never verdict. **No feature is included "because a competitor has it"** — each verdict is argued independently, and several verdicts below explicitly diverge from what competitor parity alone would suggest.

---

## Scoring Legend

**Complexity:** Low / Medium / High / Very High (relative to this codebase's current size and patterns)
**Users benefited:** estimated % of the 11 Phase 4 personas for whom this is a real, active need (not just "nice to have")

---

## 1. Tax Regime Comparison Engine (Calculation Engine #14)

| | |
|---|---|
| User problem | Every persona in Phase 4 identified regime choice as a real, recurring, high-stakes decision they currently have no tool for |
| Users benefited | ~100% of taxpaying personas (all except Student, APY-eligible non-taxpayers) |
| Complexity | High — requires the full versioned tax-slab/section schema (Phase 5 Group B) to be populated and maintained, not just the calculation logic itself |
| Regulatory implications | High-stakes if wrong — an incorrect tax comparison could cause real financial harm; every figure must trace to a cited, versioned source (Phase 5's `RECOMMENDATION_CITATIONS`), never a hardcoded slab |
| Data sources required | Tax Act sections/slabs (Phase 1, already researched), user's actual recorded income/deductions (partially exists in schema) |
| Security/privacy risk | Low beyond what already exists — no new PII category, just new computation over existing financial data |
| Why prioritize over alternatives | This is the calculation every other Phase-5 policy-engine table exists to serve — building the schema without this calculation leaves it inert |
| **Verdict** | **Build now** — highest-leverage, most-validated-by-research feature in this entire engagement |

## 2. Account Aggregation (bank/broker sync)

| | |
|---|---|
| User problem | Manual entry is tedious and goes stale — the single most visible gap versus every real competitor researched (Competitor Analysis) |
| Users benefited | ~100% — every persona benefits from not re-entering balances |
| Complexity | **Very High** — requires either a licensed Account Aggregator (AA) framework integration (India-specific, RBI-regulated data-sharing framework, not independently researched in this pass) or direct bank/broker API integrations, both involving real security architecture, consent-management flows, and likely a compliance/licensing relationship Northstar doesn't have today |
| Regulatory implications | **High** — handling third-party financial credentials or AA-framework consent artifacts is a materially different compliance posture than the current app's own-data-entry model; RBI's Account Aggregator regulations were not researched this pass and must be before committing to this |
| Data sources required | Either AA-framework licensing/partnership, or per-institution API agreements |
| Security/privacy risk | **High** — this is the single highest-risk feature on this entire list from a security standpoint; a breach here is categorically worse than a breach of manually-entered data, since it implies live credential or consent-token exposure |
| Why prioritize over alternatives | Competitor parity alone doesn't justify this — the complexity and regulatory lift are large enough that this should not be assumed as an early feature just because INDmoney/Kubera/Groww all have it |
| **Verdict** | **Build later** — genuinely high-value, but the regulatory/security groundwork (AA framework research, security architecture review) is a prerequisite research phase in its own right, not a feature to schedule directly into a milestone yet |

## 3. Household/Family Net Worth View

| | |
|---|---|
| User problem | Verified need for 4 of 11 personas (couples, families, seniors, HNIs) |
| Users benefited | Depends heavily on Northstar's actual user base composition — flagged as an open question this report cannot answer (see Risk Register) |
| Complexity | Medium — schema exists (Phase 5 Group A), mostly an aggregation/permissions UI problem, not new financial-calculation complexity |
| Regulatory implications | Low-medium — one member viewing another's financial data requires a real consent/permission model (who can see what), which touches privacy law principles even if not a specific named regulation researched this pass |
| Data sources required | None new — pure aggregation of existing per-user data through the new household schema |
| Security/privacy risk | Medium — the permission model (can a spouse see the other's individual goals, or only aggregates?) needs explicit design, not an afterthought; getting this wrong risks one family member seeing data another didn't consent to share |
| Why prioritize over alternatives | Directly evidenced by INDmoney already shipping this (Competitor Analysis) *and* independently justified by Phase 3/4's structural findings — this is one of the few features where competitor-parity and first-principles research agree |
| **Verdict** | **Build now** (schema first, per Phase 5 — the aggregation UI can follow once the underlying household model exists) |

## 4. HUF Eligibility Assessment / Recommendation

| | |
|---|---|
| User problem | Real, but narrow — Phase 3 established this is a poor fit for most nuclear-family users |
| Users benefited | Small — likely single-digit percentage of users (those with ancestral property or family business income) |
| Complexity | Medium — the gating logic (Phase 5's `company_policies.huf_recommendation_gate`) is more about restraint than computation |
| Regulatory implications | Medium — recommending a legal structure carries more liability than a savings-scheme suggestion; the recommendation should be framed as "consider consulting a CA," not as a directive |
| Data sources required | User-declared funding source (ancestral property / business income) — self-reported, not independently verifiable by Northstar |
| Security/privacy risk | Low |
| Why prioritize over alternatives | **This is a direct test of your "challenge every assumption" instruction**: HUF is a compelling research topic (Phase 3 gave it a full deep-dive) but a narrow-fit *feature*. Building a full HUF-management feature (Phase 5's `huf_entities`/`huf_coparceners` tables) before the much-higher-reach Tax Regime Comparison (#1) would be a clear misprioritization. |
| **Verdict** | **Build later** — worth having the schema ready (already designed, low marginal cost) but not worth prioritizing the recommendation-engine logic or UI ahead of higher-reach features |

## 5. Nominee Management

| | |
|---|---|
| User problem | Real and newly regulatory-mandated (SEBI, effective Sept 2026) for every new demat/MF account |
| Users benefited | High — anyone with a brokerage/MF holding recorded in the app |
| Complexity | Low-medium — schema already designed (Phase 5), mirrors the actual regulation directly |
| Regulatory implications | Directly *responds to* a regulation rather than creating new regulatory exposure — Northstar isn't the entity registering the nomination (the broker/AMC is), it's just tracking/reminding |
| Data sources required | None new beyond user-entered nominee data |
| Security/privacy risk | Low-medium — nominee name/relationship is modest-sensitivity PII, lower risk than credentials or full KYC documents |
| Why prioritize over alternatives | Time-boxed by the actual regulation's September 2026 effective date — this has a real external deadline none of the other features on this list have |
| **Verdict** | **Build now** — low complexity, real deadline, directly responds to verified current regulation |

## 6. Cash-Flow Forecasting (forward projection)

| | |
|---|---|
| User problem | Verified gap versus Monarch Money; current Northstar dashboard shows only current-month snapshot |
| Users benefited | High — every persona with recurring income/expenses benefits from seeing forward trend, not just a point-in-time number |
| Complexity | Medium — requires recurring-transaction modeling (frequency fields) the current `income_sources`/`expenses` tables don't fully capture for irregular items |
| Regulatory implications | None |
| Data sources required | None new beyond richer metadata on existing income/expense records |
| Security/privacy risk | None beyond existing |
| Why prioritize over alternatives | High value, moderate complexity, no regulatory drag — a good "quick win" relative to account aggregation or tax-engine-scale efforts |
| **Verdict** | **Build now** (medium-term, after Tax Regime Comparison) |

## 7. Insurance (Term Life) Adequacy Calculator

| | |
|---|---|
| User problem | Verified need for the Family persona specifically — currently zero insurance-adequacy logic exists |
| Users benefited | High for any persona with dependents (families, married couples with children) |
| Complexity | Medium — Human Life Value formula (Calculation Engine #13) is straightforward once household/dependents schema (Phase 5 Group A) exists |
| Regulatory implications | Low — this is a calculator, not a product sale; must be careful not to appear to be selling/recommending a specific insurer's product (Northstar isn't an insurance distributor per the current architecture) |
| Data sources required | Household composition, existing liabilities, existing goals — all already in scope from Phase 5 |
| Security/privacy risk | Low |
| Why prioritize over alternatives | Directly closes a named, verified gap for a well-populated persona (families) |
| **Verdict** | **Build now** |

## 8. Decumulation / Sustainable Withdrawal (Retirees)

| | |
|---|---|
| User problem | Verified, structurally absent — the entire engine is accumulation-oriented |
| Users benefited | Depends entirely on how many of Northstar's actual users are retirees/near-retirees today versus accumulation-phase — flagged as an open question (Risk Register), since the current onboarding flow and personas suggest an accumulation-phase-skewed user base today |
| Complexity | Medium — reuses the existing Monte Carlo engine's path-generation code almost entirely (Calculation Engine #19), just inverts the cash-flow direction and success condition |
| Regulatory implications | Low |
| Data sources required | None new |
| Security/privacy risk | None |
| Why prioritize over alternatives | High technical leverage (cheap to build given the existing engine) but **should not be built now if Northstar's actual current users are predominantly pre-retirement** — this is exactly the kind of feature that "looks impressive" but may serve few actual current users; verdict below is conditional |
| **Verdict** | **Build later**, contingent on confirming actual user-base age/life-stage distribution first — flagged explicitly as a "don't build until you've checked who's actually asking" case |

## 9. Goal Prioritization (multi-goal surplus allocation)

| | |
|---|---|
| User problem | Verified for the Family persona (highest concurrent goal count) |
| Users benefited | Medium-high — any persona with 2+ active goals competing for limited surplus |
| Complexity | Medium-high — a real constrained-optimization problem (Calculation Engine #18), more algorithmically involved than most items on this list |
| Regulatory implications | None |
| Data sources required | None new — reuses existing `goals.priority` (currently unused) and the existing optimizer |
| Security/privacy risk | None |
| Why prioritize over alternatives | Meaningfully improves the product's core existing strength (the optimizer) rather than adding an adjacent capability — arguably higher-leverage than several "new domain" features on this list precisely because it deepens something Northstar already does better than any competitor researched |
| **Verdict** | **Build now** (after Tax Regime Comparison, alongside Cash-Flow Forecasting) |

## 10. Explainable AI Advisor (confidence scores, citations, alternatives)

| | |
|---|---|
| User problem | Current Copilot gives unstructured, uncited, unexplained text replies |
| Users benefited | High — anyone using Copilot at all, and indirectly everyone, since the same deterministic layer backs every AI-surfaced recommendation |
| Complexity | High — requires most of Phase 5's schema plus the intent-routing/narration architecture (AI Architecture Report) |
| Regulatory implications | **Medium-high, flagged as unresearched**: whether this constitutes "investment advice" under SEBI's Research Analyst/Investment Adviser framework was explicitly not researched this pass and must be checked before this ships anything that could be construed as personalized investment advice rather than general planning support |
| Data sources required | Everything from Phase 5's policy/calculation engines |
| Security/privacy risk | Low-medium — mainly the conversation-memory storage (Phase 5's `AI_MESSAGES`) which is new PII-adjacent data at rest that doesn't exist today |
| Why prioritize over alternatives | This is the feature that makes every *other* feature's output trustworthy and explainable rather than a black box — but it is also the single largest engineering lift on this list |
| **Verdict** | **Build later**, sequenced *after* the underlying Tax/Goal-Prioritization engines exist to narrate (there's nothing to explain yet without them), and *after* the SEBI advice-classification question is resolved |

## 11-21. Remaining Candidates (condensed — full reasoning available in source phase reports)

| Feature | Users benefited | Complexity | Verdict | One-line rationale |
|---|---|---|---|---|
| Debt-to-Income Ratio calc | High (universal) | Low | **Build now** | Data already exists, pure calculation gap |
| Retirement Corpus derivation | High | Medium | **Build now** | Closes a real "user must already know their number" gap |
| Education Planning (category inflation) | Medium (families) | Low | **Build now** | Small addition once category-inflation infra exists for medical (already planned) |
| Family Floater vs. Standalone recommendation | Medium (families, seniors) | Low | **Build now** | Simple rule, already fully specified in Phase 3 |
| NRE/NRO Asset Modeling | Low (NRI persona only) | Medium | **Build later** | Real need, but narrow persona reach; also blocked on unverified DTAA/TDS research (Phase 4) |
| HNI PMS/AIF Holdings | Low (HNI persona only) | Medium | **Build later** | Narrow reach; schema cheap to add now, feature logic can wait |
| Estate/Nominee "Dead Man's Switch" (Kubera-style) | Medium | High | **Build never** *(as Kubera implements it)* / **Build later** *(as a simpler "document status reminder")* | Full automated data-handoff-on-inactivity is a serious trust/liability mechanism (what if inactivity is a vacation, not death?) that a young product shouldn't take on; a much simpler "your will status is X, last reviewed Y" reminder captures most of the planning value at a fraction of the risk — explicitly **not** copying the competitor feature as-is |
| Government Scheme Directory (browse/compare) | High | Low-medium | **Build now** | Directly surfaces Phase 1's research; low complexity given the schema already exists |
| ULIP/REIT/Debt-Fund tax-treatment engine | Medium | Medium-high | **Build later** | Real (Phase 6 private-product findings), but behind the higher-reach Tax Regime Comparison |
| Presumptive taxation (freelancers/business owners) | Low-medium | Unknown | **Research first, build never yet** | Flagged unverified in Phase 4 — cannot size or design against an unverified fact |

---

## Summary: What "Challenge Every Assumption" Actually Changed

Three verdicts above **explicitly diverge from naive competitor-parity logic**:
- **Account Aggregation** — every competitor has it, but the regulatory/security lift is large enough that "build later, research the AA framework first" is the honest verdict, not "build now because everyone else has it."
- **HUF feature depth** — a full research chapter was devoted to it (Phase 3), but the feature verdict is explicitly "narrow, build later" — depth of research does not imply priority of build.
- **Kubera's "Dead Man's Switch"** — explicitly **not** recommended to copy as-implemented; a simpler, lower-liability alternative is recommended instead, directly per your instruction not to add a feature just because a competitor has it.
