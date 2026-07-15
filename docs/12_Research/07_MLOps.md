# 07 — MLOps

**Date:** 2026-07-08
**Status:** Research/design only. Sized for a small team shipping a product — not a platform team. Every component below defaults to "reuse what Northstar already operates" (Postgres, pytest, structured logging, CI) before adding anything new.

---

## 1. Inference pipeline (the only pipeline V1 actually needs)

- **Development / single-machine (M4):** llama.cpp server or Ollama (which gained an MLX backend on Apple Silicon in March 2026, closing most of the speed gap with native MLX-LM [verified-web: [DEV comparison](https://dev.to/bspann/running-llms-locally-on-macos-the-complete-2026-comparison-48fc)]) exposing an **OpenAI-compatible endpoint**. The existing `copilot.py` client then needs only a `base_url` + model-name setting — the provider-optional pattern (`OPENAI_API_KEY` present/absent) already in production generalizes to a `LLM_PROVIDER` setting with `local | openai | none(rule-based fallback)`.
- **Production / server:** vLLM on a cloud GPU (continuous batching, prefix caching for the shared system prompt, guided/structured decoding for tool JSON) [training-knowledge — vLLM feature set, stable]. Same wire format ⇒ zero application changes between dev and prod.
- **Config as settings, not code:** model name, quantization, temperature, max tool iterations, prompt version — all in `config.py`/env per the project's existing settings discipline.

## 2. Versioning — four independently-versioned artifacts

| Artifact | Store | Version identity |
|---|---|---|
| Base model checkpoint | HF Hub reference (pinned revision hash) — no re-hosting needed until fine-tunes exist | `model_id@revision` |
| Adapters (when V2+ tuning happens) | Private HF repo or MLflow registry | semver + training-run link |
| **System prompts** | **In the git repo** — prompts are code; they go through PR review like code | git SHA + explicit `prompt_version` string logged per turn |
| RAG corpus + embeddings | Postgres rows with `embedding_model_version` + ingestion audit fields (`05_RAG_Architecture.md` §4) | per-chunk metadata |

Every assistant turn logs the full quadruple. A behavior change is then always attributable — the same property `AuditLog` gives writes today.

## 3. Evaluation pipeline (built **before** any training pipeline — see `04` §decision-rule)

- Eval suite runs as **pytest** (`09_Evaluation.md` defines content) against a running local model — same runner, same CI mental model as the existing 330-test suite.
- Two speeds: **PR gate** (deterministic checks only: tool selection, argument validation, grounding-validator pass rate on golden transcripts — minutes, no GPU) and **nightly/pre-release** (full generation quality suite on the target model).
- Regression policy mirrors the constitution's Rule 6: a failing eval blocks the change; evals are never loosened to pass without a documented decision.

## 4. Training pipeline (dormant until V2's evidence gate opens)

When (if) QLoRA is justified: dataset built by deterministic generator scripts from the engines (`03` §5) with dataset hash recorded; config-as-code (Axolotl/LLaMA-Factory YAML or MLX-LM config committed to repo); one cloud GPU (L4/A10G — `10_Hardware_Analysis.md`); **experiment tracking: MLflow self-hosted** (fits the local-first posture; W&B acceptable if hosted telemetry is tolerable [judgment]); output adapter registered with eval-suite scores attached; promotion to prod requires the full nightly suite green.

## 5. CI/CD

- PRs touching prompts/tools/RAG code → PR-gate evals + existing lint/type/test gates.
- Model or adapter version bumps → nightly suite + a manual approval step (model changes are product changes).
- Rollout: the `LLM_PROVIDER` setting doubles as an instant kill switch → rule-based fallback (already exists, already tested — `copilot.py`'s `_fallback_response`). Canary = enable for a user allowlist first (dogfooding cohort, per the Morgan Stanley staging lesson).

## 6. Monitoring

Extend the existing structured logging (`logging_config.py` conventions) with per-turn records: latency (total + per tool + tokens/s), token counts, tools called + failures, grounding-validator verdicts (**the headline safety metric: validator-block rate**), retrieval hit/empty rates, fallback activations, user feedback (thumbs). Aggregate into the ops dashboard of choice; alert on validator-block-rate spikes (model/prompt regression signal) and latency p95 breaches. Conversation content retention policy per `08_Security.md` §4 (metrics ≠ transcripts).
