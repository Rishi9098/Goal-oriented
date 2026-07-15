# Implementation Report

**Date:** 2026-07-05
**Scope:** All code changes made during this session's validation pass.

---

## Summary

This session did not implement new features (per instructions). It found and fixed 12 Ruff violations and 18 `mypy --strict` errors in the backend — both real, reproducible, and pre-existing — plus 2 documentation-drift items and (from the QA pass immediately preceding this one) 4 frontend bugs. Every fix is minimal and scoped to the verified issue; no working code was refactored beyond what each fix required.

---

## Changes Made

### Backend — Ruff (12 violations → 0)

| File | Issue | Fix |
|------|-------|-----|
| `app/models/user.py`, `goal.py`, `simulation.py` | F821 undefined-name ×6 — `Mapped["Goal"]`-style forward references had no corresponding import anywhere, not even under `TYPE_CHECKING`, so the `# type: ignore[name-defined]` comments were papering over a real gap | Added `if TYPE_CHECKING:` import blocks for the cross-referenced models in all three files; removed the now-unnecessary `type: ignore` comments |
| `app/logging_config.py:17` | E501 line too long | Wrapped the JSON log-format string in parens |
| `app/schemas/simulation.py:42` | E501 | Wrapped the `Field(...)` call across lines |
| `app/services/planning_service.py:72,133` | E501 ×2 | Wrapped a string literal and a `select()` `.where()` call |
| `app/middleware/auth.py:31` | B904 — `raise credentials_exc` inside `except ValueError:` without explicit chaining | Changed to `except ValueError as exc: raise credentials_exc from exc` |
| `app/models/__init__.py` | I001 unsorted imports | Auto-fixed via `ruff check --fix` |

### Backend — mypy `--strict` (18 errors → 0)

| File | Issue | Fix |
|------|-------|-----|
| `app/services/auth_service.py` | 8 errors: `passlib`/`python-jose` are untyped third-party libraries, so every call into them leaked `Any` into functions declared to return `str`/`bool`/`dict`; `dict` used without type parameters in 3 places | Added explicit `cast()` at each untyped-library boundary (`hash_password`, `verify_password`, `_create_token`, `decode_token`) with a one-line comment explaining why; changed bare `dict` → `dict[str, Any]`; **also** replaced a blind `return user_id` (typed `Any` from `payload.get("sub")`) with an `isinstance(user_id, str)` check before returning — this is a genuine (small) security hardening, not just a type-checker appeasement: it stops a JWT with a non-string `sub` claim from being silently accepted |
| `app/services/monte_carlo.py:38` | `terminal_values: np.ndarray` — missing type parameters | Changed to `npt.NDArray[np.float64]` |
| `app/models/simulation.py:44` | `distribution: Mapped[dict]` — missing type parameters | Changed to `Mapped[dict[str, float]]` (matches the actual schema type used elsewhere: `app/schemas/simulation.py`'s `distribution: dict[str, float]`) |
| `app/middleware/request_id.py`, `app/middleware/rate_limit.py` | `call_next: object` — wrong type entirely (should be Starlette's actual endpoint type), producing "object not callable" + unused-ignore errors at 4 call sites total | Changed the parameter type to `starlette.middleware.base.RequestResponseEndpoint` in both files; removed the now-unnecessary `# type: ignore[...]` comments |

### Documentation

- `docs/architecture.md`: corrected router list, table list, JWT storage description, and observability claim (see `ArchitectureReport.md` for detail).

### Frontend (from the QA pass immediately preceding this session, included here for completeness)

- `code/src/components/dashboard/GoalSimPanel.tsx`: wired the previously-inert "Switch to {risk profile}" suggestion to a real `api.updateGoal` call.
- `code/src/routes/app.profile.tsx`: loads real profile data instead of hardcoding household defaults, fixing silent data corruption on save.
- `code/src/routes/app.reports.tsx`: fixed negative-number currency formatting.
- `backend/alembic/versions/004_password_reset_tokens.py`: new migration for a table that existed only as an ORM model with no migration.

---

## Validation Evidence

```
ruff check app/           →  All checks passed!
mypy --strict app/        →  Success: no issues found in 40 source files
pytest -q                 →  164 passed, 96.43% coverage (threshold 80%)
tsc --noEmit (frontend)   →  clean
vite build (frontend)     →  clean
eslint (3 touched files)  →  clean
```

No test was modified, skipped, or deleted to make any of the above pass — all 164 backend tests are unchanged from before this session's fixes and still pass identically after.

---

## Remaining Risks

- The `cast()` calls at the `passlib`/`python-jose` boundary are correct given current library behavior, but silently trust the library's runtime contract — if either library's return type ever changes shape, mypy will not catch it (this is the inherent tradeoff of using `cast()` at an untyped-library boundary rather than writing full runtime validation). This is standard practice and proportionate here; flagging so it isn't forgotten if either dependency is upgraded.

---

## Recommendations

- None beyond what's already captured in `ArchitectureReport.md` and `TechnicalDebt.md` — this was a fix pass, not a feature pass, per the task's own constraints.
