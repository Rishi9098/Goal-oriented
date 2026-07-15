# Testing — Milestone 2.1-P0 (Risk Profile Persistence Bug)

**Date:** 2026-07-07

No backend files changed (Dependency Validation confirmed no schema/endpoint ever existed for this field), so no backend test suite run is required for this finding — re-confirmed anyway that the full 317-test backend suite is unaffected (no backend file touched).

**Frontend (this project has no frontend test runner — a standing, pre-existing condition, not introduced by this fix):**
- `tsc --noEmit` — clean, 0 errors.
- `eslint` on `code/src/routes/app.profile.tsx` — clean.
- Grep confirms zero remaining references to `riskProfile`/`RISK_OPTIONS` anywhere in `app.profile.tsx`.
- `git status` confirms exactly one file changed (`code/src/routes/app.profile.tsx`) — no unintended blast radius.

**Live verification** (see `PR_REPORT_M2.1-P0.md` for full detail): fresh test account, confirmed the Risk Profile field and its header summary are gone; confirmed the one real field this form saves (Full Name) still saves correctly and persists across a page reload — the fix did not regress the form's genuine functionality.
