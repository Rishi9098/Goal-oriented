# Dependency Validation — Milestone 2.1-P0 (Risk Profile Persistence Bug)

**Date:** 2026-07-07
**Source:** `Milestone2CertificationReport.md` §14, Known Risk #1 — the single highest-priority finding from the Milestone 2 Certification.
**Performed before any code was written**, per instruction.

## Checklist

| Requirement | Status |
|---|---|
| Bug location confirmed | ✅ `code/src/routes/app.profile.tsx` — `handleSubmit` (line 86-99), `FormState` initial value (line 41-45, 60). |
| Backend endpoint this screen calls | ✅ `PUT /api/v1/auth/me` → `auth_service` → `User` model. Confirmed via `backend/app/routers/auth.py:219` (`update_me`) and `backend/app/schemas/user.py` (`UserUpdate`). |
| Does `UserUpdate` schema accept a risk-profile field? | ❌ **No.** `UserUpdate` (schemas/user.py) has no `risk_profile` field. |
| Does the `User` model have a risk-profile column? | ❌ **No.** `backend/app/models/user.py` has no `risk_profile` column — confirmed by reading every `Mapped[...]` field on the model. |
| Does `UserProfile` (onboarding profile) have one? | ❌ **No.** Confirmed by reading every field on `backend/app/models/profile.py`. |
| Does `FinancialAssumptions` have one? | ❌ **No.** Confirmed by reading every field on `backend/app/models/assumptions.py`. |
| Where does `risk_profile` genuinely exist in this schema? | Only on `Goal.risk_profile` (per-goal, used by Monte Carlo) and `Simulation.risk_profile` (per-simulation run). Confirmed via `backend/app/models/goal.py:61` and `backend/app/models/simulation.py:40`. |

## Dependencies for a fix

- **No new migration is required for the "remove the false capability" fix path** — there is no column to remove; only frontend state and markup are involved.
- **A new migration (and a new backend field + endpoint) would be required for a "make it real" fix path** — this is a materially different scope of work, discussed in `RootCauseAnalysis_M2.1-P0.md` and resolved in the Design Review.
- Reused reference: `code/src/routes/app.goals.tsx`'s existing per-goal risk-profile selector (`RISK_OPTIONS` is duplicated verbatim in `app.profile.tsx` — confirmed identical three-item array) already provides the real, working, per-goal equivalent of this concept — any fix must not duplicate that selector's logic, only decide what (if anything) Profile should show.

## Conclusion

**No blocker.** The two backend models this bug could plausibly touch (`User`, `UserProfile`) are both read; neither has ever had a `risk_profile` column. This is not a wiring oversight where an endpoint exists and the frontend forgot to call it — no such endpoint or column has ever existed. Proceeding to Root Cause Analysis to determine the correct fix shape before any Design Review decision.
