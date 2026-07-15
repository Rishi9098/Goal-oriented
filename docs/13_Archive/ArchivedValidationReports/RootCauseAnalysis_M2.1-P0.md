# Root Cause Analysis — Milestone 2.1-P0 (Risk Profile Persistence Bug)

**Date:** 2026-07-07

## Symptom (as certified, live-reproduced)

A user changes "Risk Profile" on `/app/profile`, clicks Save, the UI shows "✓ Saved," and the value silently reverts to "Balanced (60/40)" on next page load.

## Root Cause

**This is not a wiring bug — it is a UI element that was never connected to anything real, because there is nothing real for it to connect to.**

Traced every place `risk_profile` exists in this codebase (`DependencyValidation_M2.1-P0.md`):

- `Goal.risk_profile` — real, persisted, per-goal, used by the Monte Carlo engine. Editable on `/app/goals` and during onboarding's "first goal" step. **Working correctly.**
- `Simulation.risk_profile` — real, per-simulation-run. **Working correctly, unrelated to this bug.**
- **No account-level, no `User`, no `UserProfile`, no `FinancialAssumptions` field named or resembling `risk_profile` has ever existed in this schema.**

`code/src/routes/app.profile.tsx` presents a "Risk Profile" selector as if it were a fourth, account-level instance of this concept — a single default that applies across the account. It never was. The field's initial value is a hardcoded literal (`riskProfile: "balanced"`, line 60), set unconditionally after `auth.me()` resolves, **never read from any field `auth.me()` returns**. `handleSubmit` sends only `{ full_name: form.fullName }` to `PUT /auth/me` — not because of an oversight in that one line, but because there is no corresponding field on `UserUpdate` to send it to in the first place.

**Likely origin:** the three `RISK_OPTIONS` arrays in this codebase (`app.profile.tsx`, `app.goals.tsx`, `wizard-steps.tsx`) are near-identical copies. It appears the Profile screen's form was scaffolded from the goal-creation form's shape (same three options, same labels) without verifying a corresponding backend field existed for the *account* context — the per-goal version's real persistence was carried over in appearance, not in substance.

## Why "✓ Saved" appears anyway

`handleSubmit` unconditionally calls `setSaved(form)` and `setStatus("saved")` immediately after the `auth.updateMe({ full_name })` promise resolves successfully — it does not check whether every *changed* field was actually included in that request. `full_name` is genuinely saved; `riskProfile`'s change is silently absorbed into local state (`saved = form`) and then discarded the moment the component remounts and re-fetches from `auth.me()`, which was never asked about it.

## Failure Mode Classification

- **Not data loss in the "irreversible corruption" sense** — no real data is destroyed, because no real data ever existed to hold this value.
- **Is** a **misleading UI** violation: a false success confirmation for a field the product cannot actually save.
- **Is** a **Product Principle #7** violation ("never claim capability the data model doesn't actually have") and a **UX Principle #7** violation ("honesty over polish") — the exact same failure class as PCA-1 and PCA-2, both already fixed in this codebase by *removing the false claim*, not by building the missing capability under time pressure.

## Two Possible Fix Shapes (for Design Review)

1. **Remove the false capability.** Delete the editable Risk Profile field from Profile's form (and its now-orphaned save logic). Pure subtraction — no schema change, no new endpoint, no new feature. Matches the precedent PCA-1/PCA-2 set exactly.
2. **Make the capability real.** Add a genuine account-level "default risk profile" field (new column, new migration, new `UserUpdate` field, new `GET /auth/me` response field, wire it as the default when creating a new goal). This is new-feature work — a new persisted concept that has never existed in this product — not a bug fix in the narrow sense.

Both fully close "silently doesn't save" and "misleading UI." They are not equivalent in scope. This fork is resolved in `DesignReview_M2.1-P0.md`.
