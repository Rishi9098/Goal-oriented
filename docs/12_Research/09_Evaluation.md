# 09 — Evaluation

**Date:** 2026-07-08
**Status:** Research/design only.
**Core insight:** Northstar can evaluate its assistant **against ground truth, deterministically** — because the engines that generate the eval data are the same certified engines the assistant narrates. Most LLM products must rely on LLM-as-judge for everything; here, judge-based scoring is needed only for prose quality, the least critical dimension. This makes the eval suite behave like the existing pytest suite: objective, repeatable, CI-gateable.

---

## 1. Golden dataset construction (from engines — `03` §5)

Synthetic personas × goals × households → run engines → known-correct: probabilities, optimizer strategies, eligibility buckets + reasons, insurance recommendations, dashboard aggregates. From each, generate: the natural question a user would ask, the correct tool call(s), and the facts a correct answer must (and must not) contain. Sizes **[assumption — right order of magnitude, tune empirically]**: ~300–500 tool-routing cases, ~300 grounding cases, ~150 refusal cases, ~100 multi-turn scripts, ~100 policy-citation cases pinned to versioned table rows, plus the red-team corpus (`08` §6). Every case is data in the repo, versioned, reviewed like code.

## 2. Deterministic metrics (PR-gateable, no judge, no GPU beyond one local model run)

| Metric | Definition | Gate [assumption — initial targets, revise with data] |
|---|---|---|
| **Tool selection accuracy** | correct tool chosen when one is required; no tool when none is | ≥ 95% |
| **Argument accuracy** | args validate + match expected values | ≥ 95% |
| **Numeric fidelity** | every number in reply appears in tool output/chunks (normalized ₹/lakh/percent formats) | **100% post-validator by construction; pre-validator rate is the model-quality signal, target ≥ 97%** |
| **Citation validity** | cited chunk/section IDs were actually retrieved this turn; effective-date correct for the as-of date | 100% post-validator |
| **Refusal correctness** | refuses the full prohibited list (security selection, market prediction, tax computation until engine exists, estate procedures); does NOT refuse legitimate questions (over-refusal is also a failure) | ≥ 98% / over-refusal ≤ 2% |
| **Retrieval quality** (component-level) | recall@5 / MRR on question→chunk pairs; measured separately so retrieval and generation regressions are distinguishable | recall@5 ≥ 0.9 |
| **Format compliance** | valid tool-call JSON; length discipline | ≥ 99% |

## 3. Measured (non-gate) quality metrics

- **Hallucination rate** = pre-validator grounding failures ÷ turns (the honest number, tracked over time and per prompt/model version) + a periodic human audit of 50 sampled production turns for *reasoning-level* errors the validator can't see (correct numbers, wrong implication).
- **Prose quality**: small human-rated sample per release (clarity, tone per UX Principles #3/#10, one-explained-term rule); LLM-as-judge only as a trend indicator, never a gate [judgment: judge models drift; gates must be stable].
- **Multi-turn coherence**: scripted conversations checking the model re-uses tool results correctly across turns rather than re-guessing.

## 4. Performance & cost metrics

Latency p50/p95 per turn class (chat-only / read-tools / simulation-tool turns get separate budgets — `run_simulation` legitimately takes engine time); tokens/s on target hardware (M4 dev, GPU prod); tokens per turn (context bloat detector); for the cloud tier, cost per conversation. Initial targets **[assumption]**: p50 ≤ 4s chat-only local, p95 ≤ 15s tool turns (excluding full-simulation compute), context ≤ 8K tokens typical.

## 5. External benchmarks — used for model *selection*, not product gating

BFCL (tool calling), FinQA/ConvFinQA-style numeric-fidelity probes, and (if Hindi ships) Indic eval sets: run once per candidate base model to rank candidates (`01` §4), then rely on the product-specific suite above. Rationale: public-benchmark scores don't measure Northstar's actual task, and benchmark contamination makes them unreliable as absolute signals [training-knowledge — widely documented].

## 6. Cadence

PR gate (minutes, deterministic subset on quantized local model) → nightly (full suite incl. generation-quality trends) → pre-release (full suite + red-team + human prose sample) → production (continuous monitoring metrics from `07` §6, monthly human audit). Eval-set changes follow Constitution Rule 6 discipline: assertions are never loosened to make a red run green without a documented decision.
