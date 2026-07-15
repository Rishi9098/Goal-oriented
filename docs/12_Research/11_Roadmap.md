# 11 — Roadmap

**Date:** 2026-07-08
**Status:** Research/design only. Versions are scope contracts in the same spirit as the project's milestone discipline: each has explicit adds, explicit postponements, and an exit gate. Nothing advances without its gate green.

---

## V1 — "Grounded Narrator" (foundation)

**Adds:**
- Local model serving (Qwen3-8B-class Q4, OpenAI-compatible endpoint) behind the existing `copilot.py` seam; `LLM_PROVIDER = local | openai | none` with the certified rule-based fallback retained as kill switch
- Read-only tool registry (~10 tools mapping to existing services — `06` §1) + bounded agent loop
- **Grounding validator** (the non-negotiable piece — `00` §2)
- Minimal RAG: pgvector + BGE-M3 + effective-dated corpus of a curated few-dozen documents (schemes + tax sections explainers)
- Eval harness v1 (deterministic gates + red-team suite) — **built before or alongside, never after**
- Turn-level audit trail
- Exposure: **dogfooding allowlist only** (Morgan Stanley staging lesson)

**Explicitly postponed:** any fine-tuning; write tools; Hindi; memory beyond conversation; report generation; voice/tone tuning beyond prompting.
**Exit gate:** eval targets from `09` §2 met on the dogfooding cohort; validator-block rate < 3% [assumption — tune]; zero cross-tenant/PII incidents.

## V2 — "Reliable Specialist"

**Adds:**
- QLoRA adapter **if and only if** V1 evals show prompt-resistant gaps (`04` decision rule); trained on synthetic-from-engines data
- Corpus expansion (full scheme set, insurance explainers) + quarterly corpus-refresh calendar tied to the small-savings rate cycle
- Conversation persistence + episodic summaries; opt-in durable memory (user-visible)
- Hindi evaluation → Hindi support if quality gate passes (Qwen's multilingual base + BGE-M3 make this cheap to *try*, `01` §3.6)
- Default-on for all users, with visible "educational, not advice" framing (counsel-reviewed — `08` §5)

**Postponed:** writes; proactive features; DPO.
**Exit gate:** default-on stable for a full quarter-cycle including one corpus refresh; hallucination (pre-validator) rate trending down; user feedback net-positive.

## V3 — "Coach"

**Adds:**
- Preference tuning (DPO) from accumulated ratings — tone/verbosity/helpfulness
- Proactive, event-driven insights (probability drop, new eligibility, rate change) — generated through the same tool+validator path, delivered as suggestions; **never** auto-actions
- Report narration (LLM summarizes `reports` output into plain-language briefs)
- `calculate_tax` tool — **contingent on the deterministic tax engine being built as its own milestone first** (`06` §4); the assistant merely gains a new tool when the engine ships

**Postponed:** write tools; multi-model routing.
**Exit gate:** proactive-insight precision audited (no nagging, no false alarms); tax narration matches engine output 100% on eval grid.

## V4 — "Assistant with Hands (carefully)"

**Adds:**
- First write tools (create goal, adjust contribution) with: explicit user confirmation UI on every write, Pydantic-validated payloads, `AuditLog` entries (established pattern), rate limits, and undo where the domain allows (soft-delete discipline already exists)
- Multi-model routing (small local default; larger hosted model for complex synthesis — `10` §3) behind the provider abstraction
- What-if scenario workflows (chained simulations the user steers)

**Exit gate:** zero unauthorized-write incidents across a full quarter; write-confirmation UX passes First-Time-User review (project's existing review discipline).

## V5 — "Platform"

**Adds:** self-hosted/desktop distribution of the fully-local stack (the privacy differentiator productized); household multi-user awareness (pairs with the deferred shared-household feature noted in re-certification); continual-improvement loop (scheduled re-evaluation of new base models against the harness — model upgrades become routine, cheap, evidence-based); public benchmark reporting if marketing wants it.

**Permanently out of scope, all versions (doctrine, not backlog):** LLM-computed financial numbers; security/fund recommendations; market prediction; training on real user data; from-scratch/continual pretraining (`04` §E/F).
