# 10 — Hardware Analysis

**Date:** 2026-07-08
**Status:** Research only. Evidence tiers: [verified-web] / [training-knowledge] / [assumption]. All cloud prices are **[assumption — spot-check current provider pricing before budgeting]**; they move monthly.

---

## 1. The current machine: MacBook M4, 16 GB unified memory

**What it can RUN (inference):**
- Practical weight budget ≈ **11–11.5 GB** after macOS + runtime headroom; Q4_K_M ≈ 0.6 GB/B params [verified-web: [willitrunai](https://willitrunai.com/blog/best-llm-for-16gb-mac), [atomic.chat](https://atomic.chat/blog/guides/best-local-llm-16gb-mac)].
- Community-verified sweet spot for this exact configuration: **Qwen3.5 9B (~7 GB), Gemma 4 E4B, Qwen3 8B, LFM2.5 8B-A1B** [verified-web: [modelfit.io](https://modelfit.io/blog/best-llm-macbook-air-m4-16gb/), [InsiderLLM](https://insiderllm.com/guides/best-local-llms-mac-2026/)]. 14B Q4 (~9.5 GB) is possible but tight — short contexts only, and it starves the KV cache + the embedding model + the app itself.
- **Estimated decode speed [assumption — must benchmark]:** base M4 ≈ 120 GB/s memory bandwidth; 8B-Q4 ≈ ~4.5–5 GB effective read per token ⇒ **~20–28 tok/s** dense; MoE options (LFM2.5 8B-A1B, ~1B active) several× faster. Adequate for a streaming chat UX.
- Realistic co-residency matters: generator (≈5–7 GB) + BGE-M3 embedder (≈1–2 GB) + Postgres + backend + browser is a **full** 16 GB machine. Development works; it is not a serving platform.

**What it can FINE-TUNE:** MLX-LM supports LoRA/QLoRA on Apple Silicon [training-knowledge]; on 16 GB this is realistic only for **≤4B models, small batches, slowly** — a capability for experimentation, not the training plan. The training plan (when the `04` evidence gate opens) is one rented cloud GPU.

**What requires cloud:** any tuning of 8B+; any serving beyond single-user dev; any 30B+ evaluation.

## 2. Cloud GPU comparison (for QLoRA tuning runs and future serving)

| GPU | VRAM | Fit for Northstar | Approx. on-demand $/hr [assumption] |
|---|---|---|---|
| **L4** | 24 GB | QLoRA 8–9B comfortably; vLLM serving of 8B-AWQ for a small user base. **The default workhorse for both first jobs** | ~$0.4–0.9 |
| **A10G** | 24 GB | Same class as L4 (slightly different perf profile); whichever is cheaper/available | ~$0.6–1.2 |
| **A100 40/80 GB** | 40/80 | bf16 LoRA 8–14B; QLoRA up to 70B (80 GB); faster iterations when tuning becomes routine | ~$1.3–3 |
| **H100 80 GB** | 80 | Same jobs ~2–3× faster; economic only when GPU-hours, not engineer-hours, dominate — not Northstar's regime | ~$2.5–6 |
| **B200** | ~192 | Frontier-scale training/serving. **No Northstar workload on any roadmap version justifies it** | premium/limited |

**Cost reality check:** a QLoRA run on ~5K examples over 8B is a **few GPU-hours** ⇒ **$5–30 per experiment** on L4-class hardware [assumption arithmetic; consistent with FinGPT's published "<$300 per adaptation" upper bound at larger scale — verified-web: [FinGPT](https://arxiv.org/pdf/2306.06031)]. Training cost is negligible; **dataset curation and evaluation engineering are the real costs.**

## 3. Serving-tier options when the assistant ships to real users

1. **Per-user local (long-term differentiator):** the product's privacy story ("your financial data never leaves your machine") — viable for a desktop/self-hosted offering; constrained by users' own RAM.
2. **Northstar-hosted GPU (realistic default):** 1× L4/A10G + vLLM (continuous batching, prefix-cached system prompt) serves an early user base on an 8B-AWQ model; scale horizontally later. **[assumption]** tens of concurrent chat sessions per L4 at acceptable latency — verify with load tests.
3. **Hybrid routing (`02` §4 anti-pattern 5):** local/small for chat + narration; burst to a bigger hosted model (Qwen3-32B/GLM-class) only for rare complex-synthesis turns, still under the same validator. Design the provider abstraction (`07` §1) so this is a config change, not a rewrite.

## 4. Practical recommendation

Do all V1 development on the M4 exactly as constrained above (it is genuinely sufficient: 8–9B Q4 + pgvector + BGE-M3 all fit); rent an L4 by the hour for the first QLoRA experiment **only after** the `04_Training_Strategy.md` evidence gate opens; budget serving hardware when V1 dogfooding proves demand — not before. A RAM upgrade on the next laptop refresh (32–64 GB) would open 14B–30B-class local models and painless co-residency, and is worth more to this project than any cloud commitment today [judgment].
