# Data Source Migration Report — PCA-2

**Date:** 2026-07-07
**Scope:** Investigation only, per instruction. No code written. Recommends the minimum change; awaiting approval before implementation.

---

## 1. Which Deprecated Fields Are Currently Read

`user_profiles.marital_status` and `user_profiles.dependents` — both marked deprecated in the Foundation Reconciliation (2026-07-06), each carrying an inline code comment naming their replacement and instructing that no new logic depend on them (`backend/app/models/profile.py`).

Confirmed via `grep` across the entire frontend (`code/src/`): exactly one file reads or writes either field — `code/src/routes/app.profile.tsx`. Two distinct touch points, not one:

- **Read** (line 77): `householdFromProfile(profile?.marital_status ?? null, profile?.dependents ?? 0)` — computed once, on mount, into a display string.
- **Write** (lines 110-115): on Save, the reverse operation — the currently-selected canned "Household" string is pattern-matched (`form.household.includes("Single parent")`, a regex `match(/(\d+)\s*child/)`) back into `marital_status`/`dependents` values and sent to `PUT /profile`.

This second point is a discovery beyond the audit's original finding: PCA-2 was reported as a *read* inconsistency (Profile shows "2 adults" when onboarding said otherwise), but the *write* path is equally broken in the opposite direction — saving the Profile form today re-derives and overwrites `marital_status`/`dependents` from a hand-picked dropdown string that has no connection to the real household/family data either. Fixing only the read side would leave a user able to "edit" their household in a way that silently writes to the deprecated fields and still never touches the real data.

## 2. Which Certified Household Entities Contain the Authoritative Data

`households`, `household_members`, `dependents` (Foundation Milestone 1, certified) — populated via the onboarding Family step (Milestone 2 Task 4) and readable via `GET /api/v1/family` (built and tested in Milestone 2 Task 2), which returns:

```json
{ "household": { "id": "...", "name": "My Household" },
  "members": [{ "id": "...", "relationship_type": "spouse", "name": "Priya", "is_complete": true }, ...] }
```

This endpoint already has a lazy-provision fallback for pre-Milestone-2 accounts (creates a self-only household on first call rather than erroring), so it is always safe to call regardless of when a given user registered.

## 3. Whether Any Intermediate Mapping Layer Exists

Yes — `householdFromProfile()` (`app.profile.tsx:48-58`) is the only mapping layer, and it predates Milestone 2 entirely. It buckets `(marital_status, dependents)` into one of seven canned strings ("2 adults, 1 child," etc.) using assumptions that don't hold today:

- Treats any non-`"single"` `marital_status` as "2 adults" — cannot represent a single person who is not literally recorded as `marital_status="single"` (e.g., the common Milestone 2 case: a new user whose `marital_status` is `null` because Task 4 never writes it).
- Has no concept of a dependent parent at all — one of the three questions onboarding now asks.
- Caps children at "3+" and has no path to represent, e.g., a spouse with zero children but a dependent parent.

This mapping layer is not a reusable utility anything else calls — it exists solely inside this one component, for this one field, and cannot be extended to correctly represent post-Milestone-2 household data no matter what it's fed, because its whole output vocabulary (seven fixed strings) was designed around the two now-deprecated fields' value space, not the real household model's.

## 4. Whether Multiple Screens Compute Household Summaries Independently

No. Confirmed via `grep -rln "household|Household" code/src/ --include="*.tsx" --include="*.ts"` — exactly two files match: `api.ts` (type definitions only, no computation) and `app.profile.tsx` (the one screen). Dashboard, Goals, Reports, Settings, and AI Copilot contain no household-summary logic of any kind. There is nothing to de-duplicate — only one call site to fix.

## 5. Adjacent Finding, Explicitly Out of Scope

While tracing `handleSubmit`, found that the Profile form's "Risk profile" field is fully editable and shows a "Saved" confirmation, but `handleSubmit` never sends `riskProfile` to any API call — it's tracked in local form state (`isDirty` includes it) but silently discarded on save. This is a real, separate defect, unrelated to PCA-2 (it doesn't involve deprecated fields or the Household model at all). Per this sprint's "Resolve ONLY PCA-2" and "never combine unrelated fixes" instructions, this is flagged here for the record and **not** fixed as part of this change.

---

## Recommended Minimum Change

**Read path:** Add one new frontend API client function, `api.getFamilyHome()`, calling the existing `GET /api/v1/family` endpoint (Milestone 2 Task 2 — no new backend API; this is the one addition needed since no frontend caller of this endpoint exists yet). Replace the `householdFromProfile()` computation with a direct rendering of the real `members` list returned by this call (e.g., each member's name and relationship, such as "Priya · Spouse," "Ananya · Child"). This avoids inventing a new summary-bucketing function that would just reproduce `householdFromProfile()`'s original mistake in a new form — showing the real members directly is both simpler and strictly more accurate than any categorical string could be.

**Write path:** Remove the Household field's editability. The current dropdown-of-canned-strings-parsed-by-regex mechanism has no accurate way to write back to the real household model, and building one (a real add/edit-member flow) is exactly the Family workspace feature this stabilization sprint is not permitted to build. Converting this one field to a read-only display of the real data, with the edit control removed, is the honest, minimum-scope fix — consistent with `UX_PRINCIPLES.md` #7 (honesty over polish): showing real data without a broken edit affordance is better than keeping a control that silently writes to the wrong place.

**Consequence for `handleSubmit`:** once `marital_status`/`dependents` are removed from the save payload, the `api.upsertProfile(...)` call in `handleSubmit` has nothing left to send (full name is already saved via the separate `auth.updateMe()` call). Removing this now-empty call is a direct, necessary consequence of removing the deprecated-field write path — not unrelated refactoring.

**What stays exactly as-is:** Full name and email fields, their save mechanism (`auth.updateMe`), the risk-profile selector's UI (its pre-existing non-persistence bug is out of scope, per Finding 5), the overall page layout, and every other screen in the app.

### Checklist Against the Required Constraints

- **Remove dependency on deprecated fields:** ✅ both the read and the write side are removed — the more complete fix, since the audit only named the read side.
- **Avoid duplicate household summary logic:** ✅ no new summary-computation function is introduced; the real member list is rendered directly.
- **Reuse existing services where possible:** ✅ reuses the certified, already-tested `GET /api/v1/family` endpoint (Task 2) — zero backend changes.
- **Preserve backward compatibility:** ✅ every other field and save path on this screen is untouched; only the Household field's source and editability change.
- **Not introduce new APIs unless strictly necessary:** ✅ zero new backend endpoints. One new frontend client function wrapping an endpoint that already exists (necessary, since no frontend caller of it currently exists — confirmed via grep).

---

## Requested Decision

Awaiting approval to proceed with implementation as described above (per your instruction: "After the report is approved... implement"). No code has been written.
