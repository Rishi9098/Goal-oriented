# 04 — Training Strategy

**Date:** 2026-07-08
**Status:** Research only. Evidence tiers: [verified-web] / [training-knowledge] / [assumption]

**The question to answer first is not "how to train" but "what problem would training solve."** For Northstar there are exactly three candidate problems: (1) the model doesn't know Indian finance facts → **wrong problem to solve with weights** (facts are time-varying; engines + RAG own them — [verified-web: [FinRAG-12B](https://arxiv.org/pdf/2605.05482), [domain-LLM survey](https://arxiv.org/pdf/2401.02981)]); (2) the model calls tools sloppily or breaks format → **solvable with light tuning**; (3) the model's tone/refusal behavior doesn't fit the product → **solvable with light tuning + preference data**. Nothing on that list requires heavy training.

---

## Option A — Base model + RAG only (no training)

- **Advantages:** zero training cost; instant model upgrades (swap checkpoints as the field improves — significant given a new Qwen generation shipped ~every 3–4 months through 2025–26 [verified-web: [RemoteOpenClaw](https://www.remoteopenclaw.com/blog/best-qwen-models-2026)]); no dataset-curation program; no MLOps training pipeline to build/maintain; facts stay in versioned, auditable stores; failure modes are debuggable (bad retrieval vs. bad prompt).
- **Disadvantages:** tool-call format discipline and product voice depend entirely on prompting; longer system prompts (cost/latency); a small model may need few-shot examples per request that a tuned model would internalize.
- **Cost:** $0 training. **Hardware:** inference only — the M4 suffices for development.
- **Expected quality:** for a top-tier tool-calling base (Qwen3-8B class), the published evidence is that prompted tool use is already strong [verified-web: BFCL family results, `01_Model_Comparison.md`]. **[assumption]** 85–95% of achievable product quality is available here if retrieval and prompts are engineered well.

## Option B — Full fine-tuning (all weights, supervised)

- **Advantages:** maximum plasticity; internalizes format/voice completely.
- **Disadvantages:** catastrophic-forgetting risk degrades the very general abilities (instruction following, safety) the product depends on; every base-model upgrade invalidates the investment; requires serious eval infrastructure to detect regressions; largest dataset requirement.
- **Cost/hardware [training-knowledge — standard practitioner arithmetic]:** 8B full FT in bf16 needs ~8× the parameter memory for weights+grads+optimizer ≈ 120–160 GB GPU RAM → multi-A100/H100 node; realistic runs $500–$5,000+ each, plus engineering time.
- **Expected improvement over A:** marginal for this use case; the knowledge it could add is knowledge the architecture forbids the model from using as authority anyway. **Not recommended at any roadmap stage.**

## Option C — LoRA (adapter tuning, fp16/bf16 base)

- **Advantages:** 100–1000× fewer trainable params; adapters are swappable per task (a "tool-calling adapter" vs. "narration adapter"); preserves base abilities far better than full FT; FinGPT demonstrated LoRA adaptation beating BloombergGPT at **<$300/run** [verified-web: [FinGPT](https://arxiv.org/pdf/2306.06031)]; FinLoRA benchmarks LoRA variants specifically on financial tasks [verified-web: [FinLoRA](https://arxiv.org/pdf/2505.19819)].
- **Disadvantages:** still needs a curated dataset (the real cost); base model in bf16 for 8B ≈ 16 GB weights + activations → does **not** fit the 16 GB Mac for training; adapter must be re-validated on every base upgrade.
- **Cost/hardware:** 1× 24 GB GPU (L4/A10G) for 8B; ~$5–50 per run at current cloud spot/on-demand rates **[assumption — verify current prices; see `10_Hardware_Analysis.md`]**.
- **Expected improvement:** meaningful on format compliance, refusal discipline, product voice; near-zero on factual accuracy (by design).

## Option D — QLoRA (LoRA on a 4-bit quantized base)

- **Advantages:** everything from LoRA, at ~⅓ the training memory — 8B trains on a single 24 GB GPU with headroom, or even 16 GB; quality within ~1–2% of LoRA in most published comparisons [training-knowledge — consistent with FinLoRA's findings on financial tasks, verify exact deltas there].
- **Disadvantages:** slightly slower training step; small quality gap vs bf16 LoRA; same dataset burden.
- **Cost/hardware:** 1× L4/A10G, $5–30/run **[assumption on price]**. On the M4 16 GB: MLX-LM supports LoRA/QLoRA-style tuning; **feasible only for ≤4B models with small batches — a demonstration capability, not a training platform** [training-knowledge; hardware arithmetic in `10_Hardware_Analysis.md`].
- **Expected improvement:** same targets as LoRA. **This is the recommended *first* training technique when training becomes justified.**

## Option E — Continual pretraining (domain corpus, next-token)

- **Advantages:** the only technique that genuinely adds broad domain *fluency* to weights.
- **Disadvantages:** needs tens-to-hundreds of billions of domain tokens to matter (BloombergGPT used 363B financial tokens [verified-web]); Northstar's authoritative corpus is measured in *millions* of tokens — orders of magnitude short; results in a fork that must be re-based on every model generation; the facts it encodes go stale (quarterly rate changes) and **cannot be audited** — directly hostile to Engineering Constitution Rules 2 and 4.
- **Cost:** $10K–$1M+ scale. **Not recommended. Ever, for this product.**

## Option F — Full training from scratch

BloombergGPT: ~1.3M GPU-hours, ~$3M, never released, outperformed within a year by $300 LoRA runs [verified-web: [FinGPT](https://arxiv.org/pdf/2306.06031), [survey](https://arxiv.org/pdf/2401.02981)]. For an application company this is categorically the wrong layer of the stack to compete in. **Not considered further.**

---

## Recommended strategy: **A now → D later, gated by evaluation**

**Stage 1 (V1): Option A.** Ship RAG + tool calling on a strong prompted base. Build the evaluation harness (`09_Evaluation.md`) *first* — it is the instrument that later proves whether training is needed at all.

**Stage 2 (V2+, conditional): Option D (QLoRA)** — only if the V1 eval shows persistent, prompt-resistant gaps in: tool-argument accuracy, JSON/format compliance, refusal correctness, or voice consistency. Train on the synthetic-from-engines dataset (`03_Dataset_Research.md` §5): **[assumption]** 3,000–6,000 high-quality examples (tool traces + grounded narrations + refusals) is the right initial size — small enough to hand-audit, large enough to move format behavior, consistent with instruction-tuning literature where quality dominates quantity [training-knowledge: LIMA-line of evidence].

**Stage 3 (V3+, conditional): preference tuning (DPO on QLoRA)** using human ratings collected from real usage — targets tone, verbosity, and helpfulness trade-offs that SFT can't express.

**Decision rule, stated explicitly so it can be enforced:** *no training run is approved unless a named eval metric is failing under the best-effort prompt, and the run's success criterion is that metric improving without any other gate regressing.* This is the ML equivalent of the project's "no fix without a verified finding" discipline.
