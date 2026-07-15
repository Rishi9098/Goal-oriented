# AGENTS.md — AI Development Guide

This file is the canonical guide for Codex (and any AI coding assistant) working on the Northstar codebase. Read it before touching any file.

---

## Project Summary

**Northstar** is a goal-based financial planning SaaS. Users define financial goals (retirement, home, education, etc.), and the platform runs Monte Carlo simulations to compute a probability of success, then proposes optimisations.

- **Frontend:** TanStack Start (React 19, TanStack Router, Vite 8, Tailwind CSS v4, shadcn/ui)
- **Backend:** FastAPI 0.115 (Python 3.12, SQLAlchemy async, asyncpg, PostgreSQL 16)
- **AI:** GPT-4o via OpenAI SDK — **optional**; the app works without an API key

---

## Critical Rules

### Never change the UI design system
`src/styles.css` and the Deep Navy Premium palette are frozen. Do not introduce new colour values, font families, or utility classes without explicit instruction.

### Keep routers thin
Routers in `backend/app/routers/` must contain no business logic. All logic lives in `backend/app/services/`. A router imports a service function, calls it, and returns a schema.

### Mock fallback must always work
`src/lib/api.ts` exports two behaviours: real API calls (when `VITE_API_BASE_URL` is set) and mock fallbacks (when it is not). Never remove or break the mock path — it is the primary development mode.

### Soft-delete goals
Never hard-delete a row from the `goals` table. Set `is_active = false`.

### Tests first
Any new backend endpoint requires integration tests before the PR is opened. Target ≥ 80% coverage (`pytest --cov=app --cov-fail-under=80`).

---

## Key File Map

| File | Purpose |
|------|---------|
| `backend/app/main.py` | App factory, router registration |
| `backend/app/config.py` | All settings (loaded from `.env`) |
| `backend/app/services/monte_carlo.py` | Simulation engine — touch carefully |
| `backend/app/services/optimizer.py` | Optimisation strategy generation |
| `backend/app/services/planning_service.py` | Goal refresh + dashboard aggregation |
| `backend/app/middleware/auth.py` | `get_current_user` FastAPI dependency |
| `code/src/lib/api.ts` | Frontend API client (real + mock) |
| `code/src/lib/mock-data.ts` | Development fixtures |
| `code/src/styles.css` | Design tokens — do not modify casually |
| `code/src/components/app-shell.tsx` | Sidebar layout used by all app routes |

---

## Monte Carlo Engine

Located at `backend/app/services/monte_carlo.py`.

- Uses NumPy log-normal path simulation
- `run_simulation()` — full 10 000-path run, returns `SimulationResult`
- `quick_probability()` — 2 000-path fast probe for optimizer and inline goal refresh
- Risk parameters are in `PROFILE_PARAMS` dict — change with caution, they affect all plans

---

## Adding an Endpoint — Checklist

1. Add Pydantic schema to `backend/app/schemas/`
2. Implement logic in `backend/app/services/`
3. Add thin router in `backend/app/routers/`
4. Register router in `backend/app/main.py`
5. Write integration tests in `backend/tests/`
6. Add the call to `code/src/lib/api.ts` (real + mock fallback)
7. Update `docs/backend.md`
8. Add a Changelog entry under `[Unreleased]`

---

## Environment Variables

See `backend/.env.example`. Minimum required:

```
DATABASE_URL=postgresql+asyncpg://northstar:northstar@localhost:5432/northstar
JWT_SECRET_KEY=<64-byte hex>
```

Generate the secret with:

```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

## Running the Test Suite

```bash
cd backend
pytest -v                          # all tests
pytest tests/test_monte_carlo.py   # simulation unit tests only
pytest --cov=app --cov-report=html # HTML coverage report
```

---

## Common Pitfalls

| Mistake | Correct approach |
|---------|-----------------|
| Importing `goals` fixture directly in a component | Use `api.getGoals()` and let the mock handle it |
| Adding `any` to TypeScript | Use explicit types or `unknown` with narrowing |
| Hard-deleting a goal | Set `is_active = false` |
| Calling the OpenAI SDK without checking for the API key | The copilot router already handles the fallback — follow that pattern |
| Putting business logic in a router | Move it to a service function |
| Animating `width` or `height` with Motion | Use `transform: scaleX()` instead (compositor-friendly) |
