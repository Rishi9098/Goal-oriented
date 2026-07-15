# 06 — Tool Calling Architecture

**Date:** 2026-07-08
**Status:** Research/design only.

---

## 1. Mapping the requested tools to what actually exists

The brief named ten example tools. Nine map cleanly onto **already-certified service functions** — the tool layer is a thin, typed façade over existing code, exactly as routers already are ("routers are thin" — Engineering Constitution Rule 1 extends naturally to tools):

| Proposed tool | Backing implementation (verified in codebase) | Status |
|---|---|---|
| `calculate_probability(goal_id)` | `monte_carlo.quick_probability()` (2,000-path probe) | ✅ Exists |
| `run_simulation(goal_id \| params)` | `monte_carlo.run_simulation()` (10,000-path, returns `SimulationResult`) | ✅ Exists |
| `optimize_goal(goal_id)` | `services/optimizer.py` strategy generation | ✅ Exists |
| `evaluate_scheme(scheme_code?) / list_scheme_eligibility()` | `scheme_eligibility_service.evaluate_household_eligibility()` — three buckets with per-scheme reasons | ✅ Exists |
| `family_recommendations()` | `family_recommendations_service.get_family_recommendations()` — returns `why`, `why_now`, `what_information_was_used`, `what_information_is_missing`, `confidence_score` per item | ✅ Exists |
| `insurance_recommendations()` | `family_insurance_service.compute_insurance_recommendation()` | ✅ Exists (also aggregated into the above) |
| `dashboard_summary()` | `planning_service.get_dashboard()` + `family_dashboard_service.get_family_dashboard()` | ✅ Exists |
| `report_generation(...)` | reports router/service | ✅ Exists (expose read/summarize first; file generation later) |
| `portfolio_analysis()` | Partial — financials models (assets/liabilities/income/expenses) exist; no analytic engine beyond dashboard aggregates | ⚠️ Partial — V1 exposes `get_financial_snapshot()`; a real analysis engine is future engine work, **not** LLM work |
| `calculate_tax(...)` | **Does not exist as an engine.** `tax_sections`/`tax_slabs` are versioned *data*, but no personal-tax computation service exists | ❌ Gap — see §4. Until built, the assistant must not answer "what is my tax?" with arithmetic — refusal + explanation of what exists |

Additional read-tools that cost nothing and ground most conversations: `get_goals()`, `get_goal(goal_id)`, `get_family_members()`, `get_policy_fact(section_or_scheme, as_of_date)` (a T1 reader with effective-date resolution — the tool version of Rule 2).

## 2. Architectural decisions

**2.1 Tools call services, not HTTP.** The tool layer imports service functions directly (same process, same `AsyncSession`, same transaction semantics) rather than the backend calling its own REST API. Rationale: no auth-token gymnastics, no double serialization, reuses `get_db()`'s one-commit-per-request pattern, and the 330-test suite already covers the underlying functions.

**2.2 Auth context is injected, never model-supplied.** `user`/`household` come from the authenticated request (`get_current_user`), exactly as routers do today. **The model never passes a user ID** — tool schemas simply don't have that parameter. This forecloses the entire cross-tenant-injection class (`08_Security.md` §2): a prompt-injected "call get_goals for user X" is unexpressible.

**2.3 V1 tools are read-only, enforced by construction.** Every V1 tool wraps a pure-read service call. This inherits ADR-001's hard-won invariant (reads never mutate — recalculation only on Calculation Context changes) and means a fully-compromised model session can, at worst, *read the user's own data and phrase it badly* — a bounded blast radius. Write-capable tools (create goal, update contribution) are a V4 concern with explicit-confirmation UX + `AuditLog` entries per the established audit pattern.

**2.4 Standard OpenAI-compatible tool schema.** Qwen3-class models, and every serving runtime considered (Ollama, llama.cpp server, vLLM, SGLang), speak the OpenAI tools/function-calling wire format [verified-web: [Qwen3 GitHub](https://github.com/qwenLM/qwen3) lists tool use via vLLM/SGLang/llama.cpp/Ollama; ecosystem standard]. Adopting it means: the existing `copilot.py` OpenAI-SDK plumbing is reusable **as-is** with a swapped `base_url`, the GPT-4o fallback path keeps working (the current router's provider-optional design generalizes), and models can be swapped without rewriting the tool layer.

**2.5 Tool definitions live in a registry.** One module: name → Pydantic input schema → service callable → result schema → tier tag (T0/T1) → docstring (the model-facing description). Schemas generate from Pydantic (the project's existing validation idiom), keeping tool docs and validation from drifting apart.

## 3. The agent loop (bounded, boring, auditable)

```
context → model → (tool_calls?) → validate args (Pydantic) → execute (asyncio.gather
for independent calls — same pattern as the dispatch-concurrency work in
planning_service) → append structured results → model → … 
bounds: max 4 tool iterations/turn, per-tool timeout (2s reads; simulation tools
get a "working…" streaming affordance), total turn budget ~20s
→ grounding validator (00_Knowledge_Architecture §2) → reply
```

Failure semantics mirror the Family Dashboard's `_safe()` discipline: a failed tool returns a structured `{"error": ..., "what_this_means": ...}` payload to the model (never a stack trace), the model acknowledges the gap honestly (UX Principle #10), and the turn still completes.

Every turn's full trace — prompt version, tools called, arguments, result hashes, validator verdict — is persisted for audit (append-only, same table family as `AuditLog`; see `07_MLOps.md` monitoring and `08_Security.md`).

## 4. The `calculate_tax` gap (flagged, not silently absorbed)

A real personal-tax engine (slab computation, regime comparison, deduction application) is **engine work under the existing constitution** — deterministic, versioned-data-driven, fully tested — and belongs to a future milestone as its own project. What must NOT happen: the LLM filling this gap with arithmetic. Until the engine exists, tax questions get: what the versioned data *does* verify (via `get_policy_fact`), plus an honest "Northstar doesn't compute personal tax liability yet." Honesty over polish — UX Principle #7 verbatim.

## 5. Why not a framework (LangChain/LlamaIndex/CrewAI)?

The loop in §3 is ~200 lines around an OpenAI-compatible client the project already uses. Frameworks would add: dependency surface in a security-sensitive path, obscured control flow where the grounding validator must sit, and version churn — for a loop this simple. Decision: **hand-rolled loop, standard wire format** (keeps every framework's *models* and *servers* compatible anyway). [assumption/judgment — revisit if V4 multi-agent workflows genuinely emerge]
