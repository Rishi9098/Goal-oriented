# Contributing to Northstar

Thank you for investing time in Northstar. This document covers the development workflow, coding standards, and PR process.

---

## Development Setup

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

The frontend works without a backend — leave `VITE_API_BASE_URL` unset to use mock data.

---

## Coding Standards

### Python (backend)

- Python 3.12+, fully type-annotated
- `ruff` for linting and formatting (`line-length = 100`)
- `mypy --strict` must pass
- No mutable default arguments, no bare `except`
- Async-first: all DB calls use `await`

### TypeScript (frontend)

- Strict TypeScript — no `any`
- PascalCase components, `useCamelCase` hooks
- No inline business logic in route files — extract to `lib/`
- No comments explaining what code does — only the why

---

## Test Requirements

All PRs must maintain ≥ 80% test coverage on the backend.

```bash
cd backend
pytest --cov=app --cov-fail-under=80
```

### Test-driven workflow

1. **RED** — write a failing test
2. **GREEN** — write minimal code to pass
3. **IMPROVE** — refactor without breaking tests

New endpoints require:
- At least one happy-path integration test
- At least one test for each validation error (422)
- At least one auth failure test (401/403)

---

## Git Workflow

### Branch naming

```
feat/short-description
fix/short-description
chore/short-description
docs/short-description
```

### Commit messages (Conventional Commits)

```
feat: add goal priority field
fix: clamp probability to 0-100 range
chore: upgrade numpy to 2.2.1
docs: add optimizer section to backend.md
test: cover auth token refresh path
```

### PR checklist

Before opening a PR, verify:

- [ ] `pytest` passes with ≥ 80% coverage
- [ ] `ruff check .` returns no errors
- [ ] `mypy app` returns no errors
- [ ] No secrets committed (check with `git diff --cached`)
- [ ] New endpoints documented in `docs/backend.md`
- [ ] DB schema changes have an Alembic migration

---

## Adding a New Feature

1. **Plan** — open a GitHub issue describing the feature and intended API shape
2. **Schema** — add Pydantic models in `backend/app/schemas/`
3. **Model** — update SQLAlchemy models + create an Alembic migration
4. **Service** — implement business logic in `backend/app/services/`
5. **Router** — add the HTTP handler in `backend/app/routers/` and register in `main.py`
6. **Tests** — cover happy path + error cases
7. **Frontend** — add the API call to `code/src/lib/api.ts` and wire to UI
8. **Docs** — update the relevant `docs/*.md` file

---

## Reporting Issues

Please include:
- Environment (OS, Python version, Node version)
- Steps to reproduce
- Expected vs actual behaviour
- Relevant logs or error messages
