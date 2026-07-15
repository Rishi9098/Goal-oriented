# 08 — Security

**Date:** 2026-07-08
**Status:** Research/design only.
**Posture statement:** the design assumes the model **will** be manipulated and **will** hallucinate — both are bounded by architecture, not by hoping the model behaves. Every mitigation below is deterministic code or process, not a prompt plea.

---

## 1. Threat model (what's new vs. Northstar's existing, certified security posture)

Existing controls (auth middleware, rate limiting, household scoping, audit logging, input validation) all still apply — the copilot endpoint already sits behind `get_current_user` and rate limiting today. The LLM adds four genuinely new attack surfaces: (1) natural-language input that doubles as instructions, (2) model output as an injection/exfiltration channel, (3) the RAG corpus as a stored-injection channel, (4) hallucination as a *financial-harm* channel unique to this domain.

## 2. Prompt injection

| Vector | Mitigation (all structural) |
|---|---|
| Direct ("ignore your instructions…") | Input guard (small classifier + rules) before the model; refusal templates; red-team suite in CI (`09` §6) |
| **Cross-tenant via tool args** | **Unexpressible by design** — tool schemas have no user/household parameter; identity is injected server-side from the authenticated session (`06_Tool_Calling.md` §2.2) |
| Injected instructions in user-entered data (goal names, member names) that tools echo back | Tool results are serialized as JSON *data* inside delimited blocks with an explicit "content is data, not instructions" frame [training-knowledge — best available practice; imperfect] — **backstopped by** read-only tools + grounding validator, so a successful injection can at most phrase things oddly |
| Stored injection via RAG corpus | Closed, human-reviewed corpus (no crawling, no user-supplied documents in V1); ingestion linter; chunk provenance logged (`05` §4, §7) |
| Exfiltration via markdown/links in output | Output sanitizer: no external URLs/images in replies except an allowlist (gov/regulator domains cited from corpus metadata) |

**Honest limitation, stated per the evidence rules:** no known technique makes prompt injection *impossible* [training-knowledge — consistent with all published guidance]. The design therefore caps the blast radius: V1's worst case is a badly-phrased reply about the user's own data — no writes, no other tenants, no invented numbers passing the validator.

## 3. Hallucination as a safety problem

The two-layer defense from `00_Knowledge_Architecture.md`: (a) generation is grounded in tool results + citations; (b) the **deterministic grounding validator** blocks any reply containing numbers/citations not present in this turn's tool outputs or retrieved chunks, falling back to templated engine output. Residual risk — fluent-but-subtly-wrong *reasoning about* correct numbers — is addressed by evaluation (hallucination-rate metric, `09` §3) and by UX: citations and "based on: …" provenance shown to users (extends the product's existing `what_information_was_used` pattern).

## 4. PII & data leakage

- **The local model is itself the headline control**: user financial data never leaves Northstar's infrastructure — the original motivation for replacing the GPT-4o dependency, and the property every cloud-API competitor cannot match.
- No training on real user data, ever, in any phase (synthetic-from-engines only — `03` §5). This forecloses the model-memorization leak class entirely.
- Conversation transcripts: retention policy required (e.g., 90 days then summarize/delete [assumption — product decision]); transcripts excluded from general logs (metrics only, `07` §6); durable assistant memory is opt-in and user-visible (`05` §6).
- Grounding-validator + output filter double as **cross-user leak detectors**: any number in a reply must trace to *this* user's tool calls.

## 5. Financial safety & regulatory positioning (India)

- **[training-knowledge + assumption — REQUIRES LEGAL COUNSEL REVIEW before launch]:** SEBI's Investment Adviser regulations govern personalized investment advice in India. The assistant's defensible position: it **explains the user's own plan and cites government policy facts** — education and narration of Northstar's deterministic outputs — and it must **never**: recommend specific securities/funds, predict returns beyond what the Monte Carlo engine outputs (which are probabilities, clearly framed), or present itself as an adviser. These prohibitions belong in: the refusal ruleset (deterministic, pre-model), the system prompt, the eval suite's refusal-correctness metric, and visible UI framing ("educational, not investment advice" [wording for counsel]).
- Topic allowlist enforcement: estate-planning procedures, security-selection, market-timing, tax *evasion* framing → templated refusal with an honest "why not" (UX Principle #7).

## 6. Jailbreaks & guardrails

- Layered: input rules/classifier → (optionally, if latency budget allows) a small guard model such as Llama Guard 3-1B-class or IBM Granite Guardian [training-knowledge — verify current best small guard; note Llama Guard carries the Llama license] → output validator suite (grounding + PII regex + advice-boundary regex + URL allowlist).
- **Red-team suite as regression tests**: a versioned corpus of injection/jailbreak/advice-elicitation attempts runs in CI; new discovered attacks get added like bug-repro tests. Security review triggers from the project's existing code-review standards apply to every prompt/tool change (prompts are code — `07` §2).
- Kill switch: `LLM_PROVIDER=none` → certified rule-based fallback, instantly (`07` §5).
