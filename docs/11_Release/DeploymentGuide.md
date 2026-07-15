# Deployment Guide

**Status:** Canonical · **Last verified against code:** 2026-07-14
**Note, corrected in V2:** the V1 version of this document (and every prior source document, including `SystemArchitecture.md` §4) claimed no CI/CD pipeline exists in this repository. **This was false** — `.github/workflows/ci.yml` has existed since the repository's initial commit and was simply never checked directly by any prior documentation pass. What genuinely does not exist is *deployment* automation (CD) and a frontend Dockerfile — this document now describes CI accurately and scopes the real gap correctly.

---

## 1. What Exists Today

- `backend/Dockerfile` — a container build for the FastAPI backend.
- **`.github/workflows/ci.yml`** — a real, working CI pipeline, triggered on every push/PR to `main`/`develop`, with three jobs:
  - `backend`: installs `requirements-dev.txt`, runs `ruff check .`, `mypy app/`, then `pytest -v --tb=short` (coverage-gated at 80% via `backend/pyproject.toml`'s own `addopts`, inherited automatically — not a separate CI-level flag).
  - `frontend`: installs via Bun, runs `bun run build --mode development` (the project's type-check mechanism) and `bun run lint`.
  - `docker`: builds the backend Docker image as a build-check (`needs: [backend]`) — does not push or deploy the image anywhere.
- **Not implemented:** no frontend Dockerfile, no CD/deployment step of any kind (the pipeline verifies, it does not ship), no production deployment manifest.
- Environment configuration via `.env` (backend) and `VITE_API_BASE_URL` (frontend) — see `backend/.env.example` for the full variable list.

## 2. Minimum Required Environment Variables

```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
JWT_SECRET_KEY=<64-byte hex — generate with: python -c "import secrets; print(secrets.token_hex(64))">
```

**Before Production, confirm explicitly (not silently defaulted):** `JWT_SECRET_KEY` and `OPENAI_API_KEY` (if used) are real, unique, environment-provided secrets — never the `.env.example` placeholder values. The rate limiter's `trusted_proxy_ips` setting matches your actual deployment topology (empty by default, meaning `X-Forwarded-For` is ignored entirely until explicitly configured).

## 3. Known Production-Readiness Gaps (decide deliberately, don't discover reactively)

- **In-memory rate limiter, single-process** — will not correctly share limits across multiple workers or horizontal scale. Decide whether to accept this limitation or replace it with Redis before scaling past one process (`docs/09_Security/SecurityArchitecture.md` §3).
- **CI verifies; nothing deploys.** CI (§1) catches regressions before merge, but there is no CD step anywhere — getting a merged commit into production is still a manual process today.
- **No frontend Dockerfile or deployment manifest** — the frontend's own deployment story is undocumented in this repository as of this pass, even though its lint/type-check *is* CI-verified.
- **SQLite-tested, Postgres-deployed** — CI's backend job runs the test suite (SQLite-backed, per `docs/08_Testing/TestingStrategy.md`), not against real Postgres; a handful of cascade/`SET NULL` behaviors rest on one-time manual Postgres verification, not continuous CI (`docs/05_Database/DatabaseSchema.md` §4, DB-011).

## 4. Database Migration on Deploy

Run Alembic migrations as a deploy step (`alembic upgrade head`) — every migration in this project's history is additive-only and reversible (`docs/05_Database/MigrationGuide.md` §1), so this is safe to run unconditionally as part of a deploy pipeline once one exists.

---

## Related Documents
`docs/10_Operations/OperationsRunbook.md` · `docs/09_Security/SecurityArchitecture.md` · `docs/05_Database/MigrationGuide.md`

---

*No archived source document — this is new, synthesized content filling a genuine documentation gap the source archive itself never had a dedicated file for (deployment was previously undocumented beyond the Dockerfile and `.env.example` themselves).*


## Related Tests
The `docker` job in `.github/workflows/ci.yml` (backend image build-check) — the one piece of this document's subject matter that is actually CI-verified today.
