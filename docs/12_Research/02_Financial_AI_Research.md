# 02 — How Production Financial AI Assistants Are Actually Built

**Date:** 2026-07-08
**Status:** Research only.
**Evidence tiers:** [verified-web] / [training-knowledge] (cutoff Jan 2026 — re-verify before citing externally) / [assumption]

---

## 1. Case Studies

### 1.1 BloombergGPT — the cautionary tale
- 50B parameters, trained **from scratch**: 363B tokens of financial documents + 345B general tokens; ~1.3M GPU-hours ≈ **$3M per training run**; model never publicly released; no published latency, inference-cost, or hallucination metrics [verified-web: [FinGPT paper](https://arxiv.org/pdf/2306.06031), [survey](https://arxiv.org/pdf/2401.02981)].
- **Lesson for Northstar:** from-scratch domain pretraining is the approach with the worst cost-to-outcome ratio for an application company. Within a year of release, LoRA-adapted open models were beating it on financial benchmarks at ~1/10,000th the cost [verified-web: same sources]. Even Bloomberg — with unmatched proprietary financial text — has publicly deployed nothing built on it that is externally visible; their product AI features use retrieval over their terminal data [training-knowledge — mark as inference, verify].

### 1.2 FinGPT — the open-source counter-example
- LoRA fine-tuning on open base models with financial instruction data; adaptation cost estimated **< $300 per training run**; measured improvement over base and over BloombergGPT on sentiment/financial-NLP tasks [verified-web: [FinGPT paper](https://arxiv.org/pdf/2306.06031), [EmergentMind](https://www.emergentmind.com/topics/fingpt)].
- Later FinGPT work added **search agents with RAG** for real-time grounding [verified-web: [Customized FinGPT Search Agents](https://arxiv.org/pdf/2410.15284)].
- **Lesson:** the winning recipe in the open literature is *open base model + light adaptation + retrieval*, not weight-encoded knowledge.

### 1.3 Morgan Stanley — the gold standard for the "engine narrates truth" pattern
[training-knowledge — the deployment is publicly documented but details should be re-verified before external citation]
- "AI @ Morgan Stanley Assistant": GPT-4 with **retrieval over a human-curated corpus of ~100,000 internal research documents**. The model answers *only* from retrieved, firm-approved content.
- Deployed **advisor-facing first, not client-facing** — a human professional between the model and the end customer during the trust-building phase.
- Heavy evaluation regime: reported extensive prompt/response grading by advisors before rollout.
- **Lessons:** (a) curate the corpus, don't crawl; (b) constrain the model to approved sources; (c) stage the exposure — internal/expert users before end customers; (d) evaluation is a program, not a step.

### 1.4 Intuit (TurboTax / QuickBooks "Intuit Assist")
[training-knowledge — verify current architecture]
- Built **GenOS**, an internal platform: LLM orchestration layer + guardrails + their **deterministic tax knowledge engine**. The tax calculations come from their rules engine (decades old, legally reviewed); the LLM explains, summarizes, and navigates.
- **This is the closest public analogue to what Northstar needs** — a regulated-domain product where a deterministic engine owns the numbers and the LLM owns the language. Directly congruent with Northstar's Engineering Constitution Rule 10 ("The AI Advisor computes nothing; it narrates what was already computed").

### 1.5 Wealthfront / Betterment
[training-knowledge — public evidence is thin; treat as directional]
- Their "advice" cores remain **deterministic**: MPT-based allocation, tax-loss harvesting rules, glide paths. LLM features (where shipped) are support/explanation layers. Neither company has published evidence of an LLM making allocation decisions.
- **Lesson:** even AI-forward robo-advisors keep the LLM out of the decision path. The regulatory line (fiduciary/RIA obligations in the US; SEBI IA regulations in India) makes an LLM *deciding* untenable; an LLM *explaining a deterministic decision* is defensible.

### 1.6 Ramp / Stripe
[training-knowledge]
- Ramp: agents over **structured spend data** — categorization, policy checks, anomaly explanation. Stripe: internal + product copilots over payments data and docs; early adopter of LLM-native docs search.
- **Lesson:** in both, the LLM's inputs are structured records retrieved by conventional queries — the LLM never aggregates raw data itself. Mirrors Northstar's dashboard: `get_dashboard()` computes, LLM describes.

### 1.7 Nubank
[training-knowledge]
- LLM assistants for customer service and in-app money queries at very large scale; published engineering posts describe strict guardrail layers and intent routing in front of the model, with deterministic handlers for anything transactional.
- **Lesson:** intent routing *before* the LLM (cheap classifier decides: FAQ / tool call / human handoff) keeps cost and risk down at scale.

### 1.8 Copilot Money / Perplexity Finance / OpenBB
[training-knowledge]
- Copilot Money ("Intelligence"): on-device/small-model categorization + templated insights — LLM used narrowly, not as an open chat.
- Perplexity Finance: RAG over market data providers with citation-first UX; numbers come from data APIs, prose from the model.
- OpenBB: open-source terminal whose copilot narrates data returned by **adapters/functions** — an open reference implementation of tool-calling-over-financial-data worth studying (Apache/AGPL components — check per component).

---

## 2. The Convergent Architecture

Every successful deployment above, without exception, decomposes the same way:

```
User ↔ [Intent router / guardrails]
          ↓
       LLM (orchestrator + narrator)
          ↓ tool calls              ↓ retrieval
   Deterministic engines       Curated document corpus
   (calculations, rules,       (policies, explanations,
    eligibility, simulations)   firm-approved content)
          ↓                         ↓
        TRUTH  ————————————————→  LLM composes the answer,
                                   citing both
```

The division of labor is always:

| Component | Owns | Never does |
|---|---|---|
| **Engines** (Monte Carlo, tax rules, eligibility, optimizer) | Every number, every decision, every eligibility verdict | Natural language |
| **Retrieval** | Every factual claim about policies/products; time-varying facts | Calculations |
| **Rules/guardrails** | Compliance boundaries, refusals, intent routing | Open-ended generation |
| **LLM** | Language: explanation, summarization, question understanding, tool selection | Originating a number, rate, or eligibility verdict |

The academic literature says the same thing: RAG is preferred for "precise, time-varying financial evidence," because "encoding such facts only in model parameters risks unverifiable knowledge"; fine-tuning alone "is insufficient for the time-sensitiveness of financial data"; the strongest results combine light fine-tuning (style/format) **with** RAG (facts) [verified-web: [FinRAG-12B](https://arxiv.org/pdf/2605.05482), [domain-LLM survey](https://arxiv.org/pdf/2401.02981), [knowledge-injection survey](https://arxiv.org/pdf/2502.10708)].

---

## 3. What This Means for Northstar Specifically

Northstar is unusually well-positioned, because **the hard part is already built and certified**:

| Convergent-architecture component | Northstar's existing asset (verified in codebase) |
|---|---|
| Deterministic calculation engine | `services/monte_carlo.py` (`run_simulation`, `quick_probability`), `services/optimizer.py` |
| Rules/eligibility engine | `services/scheme_eligibility_service.py` over versioned `scheme_eligibility_rules` |
| Recommendation engine w/ explanations | `family_recommendations_service`, `compute_insurance_recommendation` — every recommendation already carries `why`, `why_now`, `what_information_was_used`, `what_information_is_missing`, `confidence_score` |
| Versioned, effective-dated fact store | `tax_sections`, `scheme_rates`, `tax_slabs` tables (Engineering Constitution Rule 2) |
| Audit trail | `AuditLog` model + established write pattern |
| Governance doctrine | Engineering Constitution Rule 10 — *already mandates* the convergent architecture |
| LLM integration seam | `routers/copilot.py` — thin router, provider-pluggable, graceful fallback already proven |

The recommendation schema is the single most important asset: Product Principle #2 requires every recommendation to carry reasoning, citations, confidence, and alternatives **as structured data**. That structured data is *exactly* the grounding payload an LLM narration layer needs. Most companies have to build this; Northstar already enforces it at the schema level.

**The gap** is equally clear: no retrieval corpus, no tool-calling layer, no local inference runtime, no LLM evaluation harness, and a `calculate_tax()`-style engine exists only partially (versioned tax *data* exists; a full personal-tax computation engine does not — see `06_Tool_Calling.md` §4).

---

## 4. Anti-Patterns Observed in the Field (what *not* to copy)

1. **From-scratch pretraining** (BloombergGPT) — $3M to be beaten by a $300 LoRA.
2. **LLM-computed numbers** — every public financial-LLM embarrassment traces to a model doing arithmetic or "remembering" a rate. Northstar's Rule 10 already forbids this; the architecture must make it *impossible*, not just discouraged (see `05` and `08`).
3. **Client-facing on day one** — Morgan Stanley went advisor-first. Northstar's analogue: developer/founder-facing dogfooding phase before default-on for users.
4. **Unversioned knowledge** — a RAG corpus without effective-dating will confidently cite last year's 80C limit. Northstar's versioned-fact discipline must extend into the corpus metadata (see `05_RAG_Architecture.md`).
5. **One giant model for everything** — production systems route: cheap classifier → small model for chat → engines for math → (optionally) big model for complex synthesis. Latency and cost force this eventually; designing for it now is free.

**Sources:** [FinGPT: Open-Source Financial LLMs](https://arxiv.org/pdf/2306.06031) · [EmergentMind FinGPT overview](https://www.emergentmind.com/topics/fingpt) · [FinGPT Search Agents](https://arxiv.org/pdf/2410.15284) · [Fine-tuning & utilization of domain-specific LLMs](https://arxiv.org/pdf/2401.02981) · [Knowledge-injection survey](https://arxiv.org/pdf/2502.10708) · [FinRAG-12B production recipe](https://arxiv.org/pdf/2605.05482) · [InvestLM](https://arxiv.org/pdf/2309.13064) · [FinLoRA benchmark](https://arxiv.org/pdf/2505.19819) — plus Northstar codebase files cited inline; Morgan Stanley / Intuit / Wealthfront / Ramp / Stripe / Nubank details are [training-knowledge] and marked as requiring re-verification before external citation.
