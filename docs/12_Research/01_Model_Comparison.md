# 01 — Model Comparison

**Date:** 2026-07-08
**Author role:** Principal AI Research Engineer / LLM Architect
**Status:** Research only. No code, no downloads, no implementation.

**Evidence discipline used throughout:** three evidence tiers, marked inline —
- **[verified-web]** — confirmed via live web search this session (source linked)
- **[training-knowledge]** — from model training data (cutoff January 2026); may be stale by up to 6 months and should be re-verified before any procurement or download decision
- **[assumption]** — explicitly an assumption or estimate, with reasoning shown

---

## 1. The Constraint That Frames Everything

Before comparing models, the deployment constraint must be stated, because it eliminates most of the field immediately:

**Northstar's current hardware is a MacBook M4 with 16 GB unified memory.** A 16 GB Mac has roughly **11–11.5 GB of practical room for model weights** once macOS, the inference runtime, and safety headroom are accounted for, and Q4_K_M quantization costs roughly **0.6 GB per billion parameters** [verified-web: [willitrunai.com](https://willitrunai.com/blog/best-llm-for-16gb-mac), [atomic.chat](https://atomic.chat/blog/guides/best-local-llm-16gb-mac)]. That means:

- **≤ 9B models at 4-bit:** run comfortably (~5–7 GB weights + KV cache)
- **14B at 4-bit:** ~9.5 GB — "tight" per the same sources; workable for short contexts only
- **≥ 30B (even MoE):** out of reach locally; cloud-only

So the real question is not "what is the best open model" — it is **"what is the best ≤ 9B open model for tool calling and grounded narration, with a clean upgrade path to a larger sibling in the cloud."** The comparison below still covers the full field (as instructed), but rankings weight the deployable size class heavily.

---

## 2. The Field (July 2026 state)

| Family | Current generation | Sizes relevant here | License | Evidence tier |
|---|---|---|---|---|
| **Qwen 3 / 3.5 / 3.6** (Alibaba) | Qwen3 (0.6B–235B, Apr 2025); Qwen3.5 (Feb 2026, multimodal, up to 397B); Qwen3.6 continues as the open-weight line; Qwen3.7 flagship (May/Jun 2026) | 4B, 8B (Qwen3); 4B, 9B (Qwen3.5) | **Apache 2.0** across the core open-weight line | [verified-web: [GitHub QwenLM](https://github.com/qwenLM/qwen3), [InsiderLLM](https://insiderllm.com/guides/qwen3-complete-guide/), [RemoteOpenClaw](https://www.remoteopenclaw.com/blog/best-qwen-models-2026)] |
| **Llama 3.x / 4** (Meta) | Llama 3.3 70B; Llama 4 (MoE, 2025) | 3.x: 8B, 70B; Llama 4 smallest variants are large MoE | **Meta Community License** — 700M-MAU clause; derivative naming requirement ("Llama" must appear in derivative names) | [verified-web: [SitePoint 2026 guide](https://www.sitepoint.com/opensource-vs-commercial-llms-the-complete-guide-2026/), [Lushbinary comparison](https://lushbinary.com/blog/gemma-4-vs-llama-4-vs-qwen-3-5-open-weight-model-comparison/)] |
| **Mistral** | Mistral Small 3.x (24B, Apache 2.0); Ministral 8B (research license — commercial requires agreement); larger models under Mistral Research License | 7B (legacy, Apache), 8B (restricted), 24B (Apache but too big for 16GB) | Mixed — **per-model**, must be checked individually | [training-knowledge — verify per model before use] |
| **Gemma 3 / 4** (Google) | Gemma 3 (1B–27B, 2025, custom Gemma terms); **Gemma 4 moved to Apache 2.0** | Gemma 4 E4B (efficient ~4B-class) | Gemma 3: custom terms with use restrictions; **Gemma 4: Apache 2.0** | [verified-web: [MindStudio on Gemma 4 Apache 2.0](https://www.mindstudio.ai/blog/gemma-4-apache-2-license-commercial-use)] |
| **Phi-4** (Microsoft) | Phi-4 14B, Phi-4-mini 3.8B | 3.8B, 14B | **MIT** | [training-knowledge] |
| **DeepSeek** | V3 (671B MoE), R1 + R1-Distill series (1.5B–70B) | R1-Distill-Qwen-7B/8B | **MIT** (R1 line) | [training-knowledge] |
| **GLM-4.5** (Zhipu) | GLM-4.5 — currently the **top-scoring model on BFCL v3 at 76.7%**, beating closed APIs | Flagship is large; smaller GLM variants exist | Mixed open licenses per model [training-knowledge — verify] | [verified-web for BFCL score: [pricepertoken BFCL](https://pricepertoken.com/leaderboards/benchmark/bfcl-v3)] |
| **Granite** (IBM) | Granite 3.x; **Granite-20B noted as leading openly-licensed models on BFCL v4 function calling** | 2B, 8B, 20B | **Apache 2.0** | [verified-web: [Awesome Agents leaderboard summary](https://awesomeagents.ai/leaderboards/function-calling-benchmarks-leaderboard/)] |
| **InternLM** | InternLM 2.5/3 (7B, 20B) | 7B | Weights free incl. commercial after registration form [training-knowledge — verify current terms] | [training-knowledge] |
| **Yi** (01.AI) | Yi-1.5 (6B–34B) | 6B, 9B | Apache 2.0 (1.5 series) [training-knowledge] | [training-knowledge] |
| **MiniCPM** (OpenBMB) | MiniCPM 3/4 (~4B class) | 4B | Apache 2.0 for recent releases [training-knowledge — verify] | [training-knowledge] |
| **LFM2.5** (Liquid AI) | LFM2.5 8B-A1B — fast MoE, cited as a strong 16GB-Mac option | 8B-A1B | License must be verified — Liquid has used custom licenses [assumption flag] | [verified-web appearance: [InsiderLLM Mac guide](https://insiderllm.com/guides/best-local-llms-mac-2026/)] |

---

## 3. Dimension-by-Dimension Assessment

Scores are qualitative (Strong / Good / Adequate / Weak) for the **≤ 9B deployable class** of each family, because that is the class Northstar can actually run. Where a judgment relies on training knowledge rather than a live benchmark, it is marked.

### 3.1 Reasoning
- **Qwen3-8B / Qwen3.5-9B: Strong.** Qwen3 introduced dual-mode operation (fast answers vs. explicit thinking traces) preserved across multi-turn conversations [verified-web: [RockB lineup guide](https://baeseokjae.github.io/posts/qwen-3-full-lineup-guide-2026/)]. Qwen3.5 9B "rivals 30B-class models from a year ago" [verified-web: [modelfit.io](https://modelfit.io/blog/best-llm-macbook-air-m4-16gb/)].
- **DeepSeek-R1-Distill-8B: Strong on chain-of-thought math/logic** [training-knowledge], but reasoning traces are verbose — a latency cost for a chat product.
- **Phi-4-mini: Good** — punches above weight on textbook-style reasoning; weaker on open-ended multi-turn [training-knowledge].
- **Llama 3.1-8B: Adequate** — a 2024-generation model now clearly behind [training-knowledge].
- **Gemma 4 E4B: Good** for its size class [verified-web appearance in 16GB recommendations].

### 3.2 Tool / Function Calling — **the decisive dimension for Northstar**
Phase 6's architecture makes the LLM an orchestrator of Northstar's engines. Tool-calling reliability matters more than any knowledge benchmark, because knowledge comes from RAG and engines, not the model.

- **Qwen3: Strong — best-in-class for open weights.** On BFCL v3, "GLM 4.5 and Qwen3 32B beat every closed API in the table" [verified-web: [pricepertoken](https://pricepertoken.com/leaderboards/benchmark/bfcl-v3)]. The 8B sibling shares the same training recipe and tool-format conventions; native support in vLLM, llama.cpp, Ollama, SGLang [verified-web: [GitHub QwenLM](https://github.com/qwenLM/qwen3)].
- **Granite: Strong** — Granite-20B leads openly-licensed models on BFCL v4 [verified-web], but 20B doesn't fit the Mac; Granite-8B is good but less battle-tested in community tooling [training-knowledge].
- **GLM-4.5: Strong** but the strong variant is large; cloud-only.
- **Llama 3.x-8B: Adequate** — works, but a generation behind on BFCL-style multi-turn tool use [training-knowledge].
- **DeepSeek-R1 distills: Weak-to-Adequate for structured tool calling** — reasoning-tuned, not agent-tuned; known format drift under strict JSON schemas [training-knowledge].
- **Phi-4-mini: Adequate** [training-knowledge].

### 3.3 Instruction Following
Qwen3/3.5: Strong. Gemma 4: Strong. Phi-4: Good. Llama 3.x: Good. DeepSeek distills: Adequate (thinking-mode bleed-through into answers is a known nuisance). [training-knowledge for all; consistent with the tool-calling evidence above.]

### 3.4 RAG Performance (grounded answer synthesis, citation faithfulness)
- **Qwen3 family: Strong** — long-context grounding is a headline capability (native 262K context, extendable) [verified-web: [InsiderLLM](https://insiderllm.com/guides/qwen3-complete-guide/)]. There is also a matching first-party embedding family (Qwen3-Embedding tops the open MTEB leaderboard at ~70.58) [verified-web: [BentoML embedding guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)] — a full retrieval stack from one vendor with consistent tokenization.
- Gemma 4 / Llama 3.x / Phi-4: Good. DeepSeek distills: Good but verbose. [training-knowledge]

### 3.5 Long Context
Qwen3: 262K native / 1M extended [verified-web]. Llama 3.1+: 128K [training-knowledge]. Gemma 3/4: 128K class [training-knowledge]. Phi-4-mini: 128K [training-knowledge]. For Northstar's workload (a plan snapshot + tool results + a few retrieved policy chunks — realistically < 16K tokens per turn), **every candidate is sufficient**; long context is not a differentiator here. What matters on 16 GB is that KV cache grows with context — long contexts eat the same unified memory as weights [assumption: standard inference arithmetic].

### 3.6 Multilingual (English + Hindi and Indic languages matter for an Indian финtech)
- **Qwen3: 119 languages; Qwen3.5: 201 languages** [verified-web: [InsiderLLM](https://insiderllm.com/guides/qwen3-complete-guide/), [RemoteOpenClaw](https://www.remoteopenclaw.com/blog/best-qwen-models-2026)]. Hindi quality specifically should be evaluated with Northstar's own eval set before promising Hindi support [assumption — no Hindi-specific benchmark was verified this session].
- Gemma: strong multilingual heritage [training-knowledge]. Llama: good but English-weighted [training-knowledge].

### 3.7 Finance Capability
No small open model has meaningful *reliable* parametric finance knowledge, and **Northstar must not rely on parametric finance knowledge at all** (Engineering Constitution Rule 10; see `00_Knowledge_Architecture.md` — the engines provide truth). What matters is: numeric copying fidelity, table reading, and refusal discipline. Qwen3's structured-output support and math performance make it Good-to-Strong here; all others Adequate-to-Good. FinGPT's published result — LoRA-adapted open models surpassing BloombergGPT on financial tasks at <$300/training vs ~$3M — demonstrates the base-model choice is not where finance capability comes from anyway [verified-web: [FinGPT paper](https://arxiv.org/pdf/2306.06031), [EmergentMind FinGPT summary](https://www.emergentmind.com/topics/fingpt)].

### 3.8 Inference Speed on the Target Machine
- Q4 8–9B on M4 16GB: community guidance puts this squarely in the comfortable zone; Qwen3.5-9B fits in ~7 GB [verified-web: [modelfit.io](https://modelfit.io/blog/best-llm-macbook-air-m4-16gb/)]. **[assumption/estimate]** Decode speed for an 8B Q4 model on a base M4 (~120 GB/s memory bandwidth) is bandwidth-bound at roughly 120 ÷ ~4.5 GB ≈ **~25 tok/s**, before speculative decoding — acceptable for chat, and MoE options (LFM2.5 8B-A1B, ~1B active) trade quality for 3–5× speed. Must be benchmarked, not assumed.
- Ollama added an MLX backend on Apple Silicon in March 2026, closing most of the gap with native MLX-LM [verified-web: [DEV comparison](https://dev.to/bspann/running-llms-locally-on-macos-the-complete-2026-comparison-48fc)].

### 3.9 Licensing & Commercial Usage
This is where the field separates hard:

| License class | Families | Fitness for a fintech product |
|---|---|---|
| **Apache 2.0** — unrestricted commercial use, modification, redistribution | **Qwen (entire core line), Gemma 4, Granite, Phi (MIT — equivalent freedom), DeepSeek R1 (MIT), Yi 1.5** | ✅ Clean. No MAU thresholds, no naming requirements, no revocation ambiguity |
| **Meta Community License** | Llama 3.x / 4 | ⚠️ Usable today, but: 700M-MAU clause, derivative-naming requirement, and "legal ambiguity for enterprise teams" [verified-web: [Lushbinary](https://lushbinary.com/blog/gemma-4-vs-llama-4-vs-qwen-3-5-open-weight-model-comparison/)]. For a regulated-adjacent financial product, avoidable friction is worth avoiding |
| **Custom / research / registration licenses** | Ministral 8B, Mistral large line, Gemma 3, InternLM (registration), LFM | ⚠️–❌ Case-by-case legal review required |

### 3.10 Fine-tuning / LoRA / QLoRA Support
Qwen, Llama, Gemma, Phi, Granite are all first-class citizens in the standard tuning stacks (HF PEFT, Axolotl, LLaMA-Factory, Unsloth) and in **MLX-LM's LoRA support on Apple Silicon** [training-knowledge — ecosystem facts, stable]. Qwen additionally publishes official fine-tuning recipes. No differentiation problem for any leading candidate; DeepSeek R1 distills are less commonly tuned for tool use.

---

## 4. Rankings

### Overall, for Northstar's specific job (local ≤9B, tool-calling orchestrator + grounded narrator, clean license)

1. **Qwen3-8B / Qwen3.5-9B** — Apache 2.0; top-tier tool calling for the size class (family evidence from BFCL); 119–201 languages; fits in ~5.2–7 GB at Q4; first-party embedding family; every runtime supports it. The only candidate with **no** weak dimension for this use case.
2. **Gemma 4 E4B** — Apache 2.0 (new for this generation), efficient, strong instruction following; smaller effective capacity than a dense 8–9B; weaker tool-calling evidence trail.
3. **Granite-8B** — Apache 2.0, IBM's function-calling pedigree (Granite-20B leads open models on BFCL v4); smaller community ecosystem; the excellent 20B doesn't fit the Mac.
4. **Phi-4-mini (3.8B)** — MIT, exceptional quality-per-parameter; best *fallback/speed tier* candidate rather than primary; tool calling adequate not strong.
5. **Llama 3.1/3.3-8B** — capable but a generation behind, and the license adds friction with zero offsetting advantage.
6. **DeepSeek-R1-Distill-7/8B** — best raw reasoning traces, weakest structured tool discipline; wrong shape for this product (the *engines* do the reasoning; the model narrates).
7. **Mistral (7B legacy / Ministral 8B)** — license fragmentation; 7B Apache model is old.
8. **Yi-1.5-9B, InternLM-7B, MiniCPM-4B** — competent but no dimension where they beat the top three, and thinner tooling/community.
9. **GLM-4.5** — arguably the single best open tool-caller in absolute terms [verified-web], but no variant fits the deployment constraint; relevant only as a future *cloud tier* candidate.

### By single dimension (deployable class)
- **Tool calling:** Qwen3 > Granite > Gemma 4 > Phi-4 > Llama 3.x > DeepSeek distill
- **Reasoning:** Qwen3.5 ≈ DeepSeek distill > Phi-4 > Gemma 4 > Llama 3.x
- **License cleanliness:** (tie) Qwen / Gemma 4 / Granite / Phi / DeepSeek — all unrestricted
- **Mac fit & speed:** Phi-4-mini > Gemma 4 E4B > Qwen3.5-9B ≈ Qwen3-8B > Llama-8B
- **Multilingual:** Qwen3.5 > Qwen3 > Gemma 4 > Llama > Phi
- **Ecosystem & tooling:** Qwen ≈ Llama > Gemma > Phi > Granite > rest

---

## 5. Conclusion (input to `12_Final_Recommendation.md`)

The instruction was: do not immediately recommend Qwen — research first. The research was done, and the field genuinely converges: **Qwen3-8B (conservative, battle-tested) or Qwen3.5-9B (newer, stronger, verify maturity) is the correct starting model**, with **Phi-4-mini as the small/fast tier** and **GLM-4.5-class or Qwen3 32B+ as the future cloud tier**. The reasons are structural, not fashionable: it is the only family that is simultaneously (a) Apache 2.0 end-to-end, (b) demonstrably top-of-class at tool calling in its open-weight generation, (c) sized for the actual hardware, and (d) shipped with a matching first-party embedding model for the RAG stack.

**What must be re-verified before acting** (knowledge-cutoff and fast-moving facts): exact current Qwen3.5/3.6 checkpoint availability and their per-checkpoint licenses; Gemma 4 E4B tool-calling benchmark results; Granite-8B BFCL v4 score; LFM2.5 license; M4 tokens/s measured (not estimated).

**Sources:** [Qwen3 GitHub](https://github.com/qwenLM/qwen3) · [InsiderLLM Qwen3 guide](https://insiderllm.com/guides/qwen3-complete-guide/) · [RemoteOpenClaw Qwen 2026](https://www.remoteopenclaw.com/blog/best-qwen-models-2026) · [RockB Qwen3 lineup](https://baeseokjae.github.io/posts/qwen-3-full-lineup-guide-2026/) · [BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) · [pricepertoken BFCL v3](https://pricepertoken.com/leaderboards/benchmark/bfcl-v3) · [Awesome Agents function-calling leaderboard](https://awesomeagents.ai/leaderboards/function-calling-benchmarks-leaderboard/) · [modelfit.io 16GB M4 guide](https://modelfit.io/blog/best-llm-macbook-air-m4-16gb/) · [atomic.chat 16GB guide](https://atomic.chat/blog/guides/best-local-llm-16gb-mac) · [willitrunai 16GB guide](https://willitrunai.com/blog/best-llm-for-16gb-mac) · [DEV macOS comparison 2026](https://dev.to/bspann/running-llms-locally-on-macos-the-complete-2026-comparison-48fc) · [MindStudio Gemma 4 license](https://www.mindstudio.ai/blog/gemma-4-apache-2-license-commercial-use) · [Lushbinary Gemma/Llama/Qwen comparison](https://lushbinary.com/blog/gemma-4-vs-llama-4-vs-qwen-3-5-open-weight-model-comparison/) · [SitePoint open vs commercial LLMs 2026](https://www.sitepoint.com/opensource-vs-commercial-llms-the-complete-guide-2026/) · [FinGPT paper](https://arxiv.org/pdf/2306.06031)
