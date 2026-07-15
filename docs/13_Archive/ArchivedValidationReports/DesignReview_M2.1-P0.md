# Design Review — Milestone 2.1-P0 (Risk Profile Persistence Bug)

**Date:** 2026-07-07
**Decision (user-confirmed):** Remove the false capability. No schema change, no new endpoint.

## What changes

`code/src/routes/app.profile.tsx`:

- Remove the "Risk Profile" form section entirely (the `<select>`, its label, and the header summary's `riskLabel` display).
- Remove `riskProfile` from `FormState`, the initial-state literal, the `isDirty` comparison, and `handleSubmit`'s payload consideration (it was never in the payload, but the dirty-check and local state both currently reference it).
- Remove the now-unused `RISK_OPTIONS` constant from this file (the real, working equivalent lives in `app.goals.tsx` and `wizard-steps.tsx` — untouched).

## What does not change

- `app.goals.tsx`'s per-goal risk profile selector — the genuine, working, persisted version of this concept. Untouched.
- `wizard-steps.tsx`'s onboarding risk-profile step (part of first-goal creation) — untouched.
- No backend file changes — `routers/auth.py`, `schemas/user.py`, `models/user.py` are all untouched, since none of them ever had a risk-profile field to remove.
- No migration.

## Why this is the minimal, correct fix (not a workaround)

This mirrors the exact precedent `ProductConsistencyRoadmap.md` already set for PCA-1 (onboarding's false "Family" destination promise — fixed by removing the claim, not building the destination under time pressure) and PCA-2 (Profile's Household field — fixed by making it an honest, real-data-sourced display, not by inventing a second household representation). A field that never had a real backing fact is not "half-built" — it's a claim that should never have been made on this screen. Removing it is not deferring work; it is completing the correction PCA-1/PCA-2 already modeled.

## Alternative considered and rejected (per user decision)

Adding a real account-level default risk profile was considered and explicitly rejected for this finding — it is new-feature work (new column, new migration, new endpoint field, a new "what does this default apply to" design question) that belongs in its own reviewed task, not a stabilization-sprint bug fix. If a future task wants this capability, it should be scoped and reviewed on its own terms, not smuggled in as a "fix" for a bug that was actually never-built, not broken.

## Blast radius

Frontend-only, one file. No other screen reads or writes `app.profile.tsx`'s local `riskProfile` state (confirmed: it is component-local `useState`, never exported or read by any other module).
