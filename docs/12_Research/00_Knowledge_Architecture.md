# 05 — Knowledge Architecture

**Date:** 2026-07-08
**Status:** Research/design only.

**Governing rule, already ratified in this codebase:** Engineering Constitution Rule 10 — *"Any LLM-backed feature receives a fully-computed, fully-cited result from a deterministic service and rephrases it in plain language — it never originates a financial number, a policy citation, or a confidence score itself."* This document designs the machinery that makes Rule 10 **structurally enforced** rather than merely instructed.

---

## 1. The Truth Hierarchy

Every piece of information in an assistant reply is assigned a tier. Lower tier number = higher authority. A claim may only ever be *downgraded* in confidence when moving between tiers, never upgraded.

| Tier | Source | May supply | May never supply |
|---|---|---|---|
| **T0 — Engines** | `monte_carlo.py`, `optimizer.py`, `scheme_eligibility_service`, `family_insurance_service`, `planning_service`, `family_dashboard_service` | Every number, probability, eligibility verdict, recommendation, and their structured explanations (`why`, `what_information_was_used`, `confidence_score`…) | — |
| **T1 — Versioned fact tables** | `tax_sections`, `scheme_rates`, `tax_slabs`, `scheme_eligibility_rules` | Rates, limits, thresholds, effective dates — always read *through* an engine or a dedicated read-tool, with effective-date resolution | Interpretation |
| **T2 — Curated corpus (RAG)** | Government/regulator documents + Northstar-authored explainers, each carrying authority + effective-date metadata (`05_RAG_Architecture.md`) | Explanations, procedures, definitions, context — *quoted or paraphrased with citation* | Numbers that T1 already holds (duplication = drift risk) |
| **T3 — Model parametric knowledge** | The LLM's weights | Language competence: phrasing, structure, translation, empathy, question understanding | **Any financial number, rate, date, eligibility claim, or policy citation.** T3 asserting a fact is, by definition, a hallucination even when correct |

This is Product Principle #8 ("every unverified fact stays visibly unverified") operationalized: tier metadata *is* the verification status, and it survives all the way to the UI.

## 2. Data Flow Per Turn

```
User message
   │
   ▼
[1] Guard + intent router (small classifier / rules)      ── out-of-scope → templated refusal
   │
   ▼
[2] Context assembly (deterministic, not LLM):
      user's plan snapshot (goals + probabilities from DB — already computed,
      per ADR-001 never recomputed on read), conversation memory
   │
   ▼
[3] LLM plans → tool calls (read-only, T0/T1)  ⇄  [4] RAG retrieval (T2)
   │            results return as structured JSON with tier tags
   ▼
[5] LLM composes draft answer — every factual span must reference a
    tool-result field or a retrieved chunk ID
   │
   ▼
[6] GROUNDING VALIDATOR (deterministic, non-LLM):
      • extract every number/date/rate in the draft
      • verify each appears in this turn's T0/T1 tool outputs or T2 chunks
        (normalized comparison: ₹50,000 ≡ 50000 ≡ "0.5 lakh")
      • verify cited chunk IDs exist and were actually retrieved this turn
      • FAIL → one regeneration with the violation named → still failing →
        fall back to a templated rendering of the raw engine output
        (the structured `why`/`what_used` fields are already user-readable —
         the product never degrades below the truth, only below the prose)
   │
   ▼
[7] Response + citations + tier badges → UI; full trace → audit log
```

Two properties make this stronger than prompt-level instructions:

1. **The validator is code, not a request.** A model *cannot* leak an invented number to the user, because the gate is a deterministic string/number matcher, not model self-restraint. This is the same trust move the project made everywhere else (CHECK constraints, versioned rows) applied to generation.
2. **The floor is the engine output, not an apology.** Because every Northstar recommendation already carries structured explanations (Product Principle #2 — enforced at schema level), the worst-case user experience is the un-narrated truth, never silence and never a lie.

## 3. Prompt Architecture (the T3 contract)

The system prompt is versioned (see `07_MLOps.md`) and states the contract in the model's own operational terms — but the design assumption is that **prompts set the mean; validators set the floor**:

- Identity: Northstar's planning assistant, **education not advice** framing (see `08_Security.md` §5 on SEBI positioning — [assumption: requires counsel review]).
- Hard rules restated: numbers only from tool results/citations; unknown → say what's missing (mirrors the engines' own `what_information_is_missing` pattern); never predict markets; never recommend specific securities/funds.
- Tool-use policy: prefer tools over memory always; one clarifying question when required arguments are missing.
- Style: plain English (Hindi later), one explained term per concept (UX Principle #3), ≤200 words unless asked (matches the existing `copilot.py` prompt convention).

## 4. What the LLM is trusted with (and it is genuinely trusted here)

Understanding vague questions ("can I retire early?" → which goal, which tool); choosing tools and arguments; composing multi-source answers; tone (UX Principle #10 — reassuring, scoped errors); translation; asking good clarifying questions. These are language problems — T3's home turf — and no validator constrains them beyond the grounding gate.

## 5. Precedent

This division is not novel — it is the convergent production pattern (`02_Financial_AI_Research.md`): Intuit's deterministic tax engine + LLM explanation layer; Morgan Stanley's approved-corpus-only answers; robo-advisors keeping allocation deterministic. Northstar's advantage is that its Rule 10 predates its LLM — the doctrine is already certified, and this design merely gives it an enforcement mechanism.
