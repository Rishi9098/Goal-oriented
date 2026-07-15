# 05 — RAG Architecture

**Date:** 2026-07-08
**Status:** Research/design only. Evidence tiers: [verified-web] / [training-knowledge] / [assumption]

**Scope reminder:** RAG here serves Tier-2 of the truth hierarchy (`00_Knowledge_Architecture.md`) — *explanatory and procedural* content. Numbers and eligibility verdicts come from T0/T1 tools, never from retrieved prose. This sharply shrinks the corpus problem: quality and metadata over volume.

---

## 1. Vector store — **pgvector on the existing PostgreSQL 16. Decided by infrastructure reality, not benchmarks.**

| Option | Assessment |
|---|---|
| **pgvector (Postgres extension)** | ✅ **Recommended.** Northstar already runs PostgreSQL 16 with async SQLAlchemy; corpus scale is thousands of chunks, not millions — pgvector's HNSW handles this trivially [training-knowledge — pgvector HNSW is mature since 0.5.x]. Zero new infrastructure, chunks live in the same transactional world as the versioned fact tables they annotate, one backup story, and the team's migration/testing discipline (additive migrations, real-DB verification) applies unchanged |
| Qdrant / Milvus / Weaviate | Excellent engines; justified at millions of vectors or heavy multi-tenant filtering — **overkill + new operational surface** here |
| Chroma / LanceDB | Fine for prototypes; embedded stores add a second persistence layer with weaker operational guarantees than the Postgres already in production |
| Managed (Pinecone etc.) | Sends financial-adjacent corpus data to a third party — works against the local-first privacy rationale of this whole project |

## 2. Embeddings

- **Primary recommendation: BGE-M3** — MIT license, 100+ languages (Hindi included), and uniquely produces **dense + sparse (lexical) + multi-vector signals in one model**, which is why "most production RAG stacks in 2026 default to BGE-M3 paired with BGE-reranker-v2" [verified-web: [KnowledgeSDK](https://knowledgesdk.com/blog/open-source-embedding-models-rag-2026), [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)]. Runs comfortably on the M4 (0.6B-class encoder).
- **Alternative: Qwen3-Embedding family** — tops the open MTEB leaderboard (8B variant ≈ 70.58 composite) [verified-web: [BentoML](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)]; the 0.6B variant [training-knowledge] would keep the whole stack single-vendor with the recommended generator. Choose by running both against the eval set (`09_Evaluation.md`) — a one-day experiment, not a debate.
- Embedding model version is **recorded per chunk row**; changing models triggers a full re-embed migration (an additive re-index, not an in-place mutation — consistent with the migration constitution).

## 3. Corpus & chunking

Corpus (per `03_Dataset_Research.md`): government/regulator primary documents + Northstar-authored explainers around the versioned tables + the recommendation engines' own `why` text patterns. Deliberately small (hundreds of documents), curated like Morgan Stanley's approved corpus, never crawled.

- **Structure-aware chunking**: legal/policy documents split on section/rule boundaries (they are naturally hierarchical), not fixed token windows; explainers split by heading. Target ~300–500 token children.
- **Parent-document retrieval**: index small chunks for precision; return the enclosing section for context [training-knowledge — standard, well-evidenced pattern].
- Tables inside documents are extracted to structured rows *or* dropped in favor of a T1 pointer — never chunked as prose (numeric truth must not enter T2).

## 4. Metadata schema — where the project's versioning discipline enters RAG

Every chunk carries, non-optionally: `source_authority` (e.g., CBDT circular / RBI / IRDAI / Northstar-explainer), `verification_tier` (verified / convention / unverified — mirroring the existing `best_practice_rules` confidence enum), **`effective_from` / `effective_to`**, `document_date`, `scheme_or_section_codes` (links to `tax_sections`/`schemes` rows), `language`, `embedding_model_version`, `ingested_by` + review status (human-approved flag).

**Retrieval-time rule:** filter `effective_from ≤ as_of ≤ effective_to` *before* similarity ranking. A corpus document without effective dates is rejected at ingestion. This is Engineering Constitution Rule 2 extended to prose — and it is the single design choice most responsible for preventing "confidently cites last year's limit," the canonical financial-RAG failure.

## 5. Retrieval pipeline

```
query → (rewrite w/ conversation context, small model) 
      → hybrid search: dense (BGE-M3) + lexical (Postgres FTS / BGE-M3 sparse)
        with metadata filters (effective date, language, authority)
      → RRF fusion of the two lists                 [training-knowledge: standard]
      → cross-encoder rerank (BGE-reranker-v2) of top ~20 → top 3–5
      → relevance floor: below threshold ⇒ return NOTHING
        (the model must then say what it doesn't know — an empty retrieval
         is a correct answer, not a failure; Product Principle #8)
      → chunks + chunk IDs + tier metadata into context
```

Hybrid matters specifically because this domain is **exact-token-heavy** — "80D", "SSY", "54EC", "ELSS" are lexical items dense embeddings under-serve [training-knowledge — well-documented hybrid-search motivation; consistent with BGE-M3's design rationale, verified-web above].

## 6. Memory (distinct from RAG, stored in Postgres alongside everything else)

- **Working memory:** the current conversation, truncated by turn budget.
- **Episodic summary:** rolling per-conversation summary generated at turn thresholds, stored on the conversation row (the existing `ChatRequest.conversation_id` seam in `copilot.py` already anticipates conversation persistence).
- **Durable user memory (facts the user tells the assistant):** V2+, opt-in, visible/editable in the UI, stored as structured rows — never silently accumulated (trust posture; see `08_Security.md` §4). Plan data itself is **not** "memory" — it is always re-read live through tools, so the assistant can never hold a stale copy of the user's goals.

## 7. Failure modes designed against

| Failure | Countermeasure |
|---|---|
| Stale policy cited | Effective-date filtering (§4) + quarterly corpus review calendar tied to small-savings rate cycle |
| Retrieval misses an exact code | Hybrid lexical leg (§5) |
| Chunk contradicts a T1 row | Ingestion linter cross-checks chunk text against linked `tax_sections`/`scheme_rates` values; contradiction blocks ingestion |
| Confident answer from weak retrieval | Relevance floor + "empty retrieval is an answer" (§5) |
| Injected instructions inside a corpus doc | Corpus is closed + human-reviewed at ingestion; retrieved text is delimited and declared as data in the prompt; grounding validator limits blast radius (`08_Security.md` §2) |
