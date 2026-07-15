# Developer Guide

**Status:** Canonical · **Last verified against code:** 2026-07-13
**Supersedes:** `CONTRIBUTING.md` (archived — preserved almost verbatim, since it was already accurate and complete), `AGENTS.md`, `CLAUDE.md` (both preserved as project-root AI-agent instructions — cross-referenced, not duplicated).

---

## 1. Development Setup

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env       # fill in JWT_SECRET_KEY at minimum
uvicorn app.main:app --reload
```

### Frontend
```bash
cd code
bun install
bun run dev
```
The frontend works without a backend — leave `VITE_API_BASE_URL` unset to use mock data (`docs/06_Frontend/FrontendArchitecture.md` §1).

---

## 2. Test Requirements

All PRs must maintain ≥80% backend test coverage:
```bash
cd backend
pytest --cov=app --cov-fail-under=80
```

**Test-driven workflow:** RED (write a failing test) → GREEN (minimal code to pass) → IMPROVE (refactor without breaking tests).

**New endpoints require:** at least one happy-path integration test, at least one test per validation error (422), at least one auth-failure test (401/403).

---

## 3. Git Workflow

**Branch naming:** `feat/short-description`, `fix/short-description`, `chore/short-description`, `docs/short-description`.

**Commit messages (Conventional Commits):** `feat: add goal priority field`, `fix: clamp probability to 0-100 range`, `chore: upgrade numpy to 2.2.1`, `docs: add optimizer section to backend.md`, `test: cover auth token refresh path`.

**PR checklist:**
- [ ] `pytest` passes with ≥80% coverage
- [ ] `ruff check .` returns no errors
- [ ] `mypy app` returns no errors
- [ ] No secrets committed (`git diff --cached`)
- [ ] New endpoints documented in `docs/04_API/RESTAPI.md`
- [ ] DB schema changes have an Alembic migration

---

## 4. Adding a New Feature — the Short Version

1. **Plan** — open an issue describing the feature and intended API shape.
2. **Schema** — add Pydantic models in `backend/app/schemas/`.
3. **Model** — update SQLAlchemy models + create an Alembic migration.
4. **Service** — implement business logic in `backend/app/services/`.
5. **Router** — add the HTTP handler in `backend/app/routers/` and register in `main.py`.
6. **Tests** — cover happy path + error cases.
7. **Frontend** — add the API call to `code/src/lib/api.ts` and wire to UI.
8. **Docs** — update the relevant canonical doc under `docs/`.

For the detailed, subsystem-specific version of this checklist (what exactly to touch for a new scheme, a new Dashboard card, a new notification source, etc.), see `docs/03_Engineering/EngineeringHandbook.md` §2.

---

## 5. Reporting Issues

Include: environment (OS, Python version, Node version), steps to reproduce, expected vs. actual behavior, relevant logs/error messages.

---

## Related Documents
`docs/03_Engineering/EngineeringHandbook.md` (the detailed playbooks, safe-modification guide, and debugging guide this short version points to) · `docs/03_Engineering/CodingStandards.md` · `docs/08_Testing/TestingStrategy.md`


## Related Tests
The full backend suite (`pytest --cov=app --cov-fail-under=80`) and the CI pipeline (`.github/workflows/ci.yml`) that runs it on every PR.

---

*Archived original: `docs/13_Archive/ArchivedReports/CONTRIBUTING.md`. `AGENTS.md` and `CLAUDE.md` remain at the repository root as the canonical AI-agent instruction files — referenced here, not moved, since that's their established, expected location.*
