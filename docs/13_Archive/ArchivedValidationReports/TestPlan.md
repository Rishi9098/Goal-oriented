# Test Plan — Milestone 2 (Family Financial Planning)

**Date:** 2026-07-06. Per `rules/ecc/common/testing.md`'s 80% minimum coverage and TDD workflow (write test → red → implement → green → refactor), and `rules/ecc/web/testing.md`'s visual-regression/accessibility/responsive priority order for the frontend half.

---

## 1. Unit Tests (backend, `pytest`)

| Target | Test Cases |
|---|---|
| Household/member completeness logic | `is_complete` true/false for each relationship_type given various field combinations |
| Age-from-DOB calculation | Exact boundary at 10th birthday (SSY), 60th birthday (SCSS) — off-by-one-day cases on both sides |
| Custom inflation rate resolution | Returns `custom_inflation_rate` when set; falls back to `financial_assumptions.inflation_rate` when `null` |
| Scheme eligibility rule evaluator | Each `rule_type` (`min_age`, `max_age`, `residency_status`) in isolation, plus a scheme with multiple rules requiring all to pass (AND) vs. the seed data's actual combinations |
| `closed_to_new` hard filter | A scheme matching every eligibility rule is still excluded when `status='closed_to_new'` |
| Insurance recommendation calculation | Correct ₹25,000/₹50,000 figures selected based on parent's age (senior vs. not) |

## 2. Integration Tests (backend, real test DB per existing `conftest.py` pattern)

| Endpoint | Test Cases |
|---|---|
| `POST /family/onboarding-seed` | Creates correct row counts for every combination of the 3 yes/no + count; idempotent re-call; `422` on missing count |
| `GET /family` | Correct payload shape; lazy-provision path for a zero-household user; ownership isolation (user A never sees user B's household) |
| `POST/PUT /family/members` | Each relationship_type's required-field enforcement; `404` on cross-household `member_id`; SSY `eligible_schemes` inclusion/exclusion at the age boundary |
| `DELETE /family/members/{id}` | Soft-delete only (row persists with `is_active=false`); `400` on removing `self`; cascade behavior on `goal_household_members`/`health_policy_coverage` for the removed member |
| `PUT /goals/{id}/family-tags` | Full-replacement semantics; `422` on cross-household member id; `404` on non-owned goal |
| `PATCH /goals/{id}` (extended) | New `custom_inflation_rate` field accepted and persisted; existing fields' behavior unchanged (regression) |
| `POST /family/insurance/policies` | `422` on empty coverage array; correct recommendation appears/disappears based on parent insurance-status changes |
| `GET /family/schemes` | PMVVY (or seeded `closed_to_new` equivalent) never in eligible/potentially-eligible across a matrix of household compositions |
| `GET /family/dashboard` | Six-card payload shape; figures match the existing `/dashboard` endpoint's equivalent values exactly |

## 3. UI Tests (frontend, Playwright — per `rules/ecc/web/testing.md`'s E2E shape)

```ts
test('user can add a spouse and see them on Family Home', async ({ page }) => {
  await page.goto('/app/family');
  await page.getByRole('button', { name: /add.*spouse/i }).click();
  await page.getByLabel('Full name').fill('Priya');
  await page.getByLabel('Date of birth').fill('1991-03-12');
  await page.getByRole('button', { name: /save.*continue/i }).click();
  await expect(page.getByText('Priya')).toBeVisible();
});
```

| Flow | Test |
|---|---|
| Onboarding family step | Each yes/no combination produces the expected Family Home state after completing onboarding |
| Add each relationship type | Spouse/Child/Parent/Other flows each save correctly and return to Family Home |
| SSY callout | Appears for an eligible daughter, absent otherwise, within the Add Child flow |
| Remove member | Confirm dialog appears, cancel preserves the member, confirm removes it from the visible list |
| Goal tagging + disclosure | Tagging a goal shows the mandatory disclosure text; untagging removes the grouping |
| Schemes bucketing | Not Eligible section starts collapsed; expands on interaction |
| Dashboard card navigation | Each of the six cards navigates to its correct source screen |

## 4. Accessibility Tests (per `rules/ecc/web/testing.md` priority #2)

- Automated: axe-core (or equivalent) run against every new screen (§1-§12), zero violations at the "serious"/"critical" level.
- Keyboard navigation: every flow in §3 completable using Tab/Shift+Tab/Enter/Space only, no mouse.
- Screen reader: VoiceOver/NVDA pass confirming (a) the SSY/recommendation callouts are announced (`role="status"`) without double-announcing the paired emoji+text label (per `UX_REVIEW.md`'s Accessibility Expert finding — `aria-hidden` on decorative emoji verified explicitly), (b) the goal-tagging multi-select is announced as a checkbox group with its legend, (c) the Not-Eligible disclosure's expanded/collapsed state is announced.
- Reduced motion: the recommendation probability bar (§12) and any onboarding-step transition jump directly to end-state under `prefers-reduced-motion: reduce`, verified via Playwright's `page.emulateMedia`.
- Color contrast: automated check across all new card/badge/callout components at both light and dark theme (if dark theme exists for this app — confirm against `src/styles.css`'s frozen palette before assuming both themes apply).
- Responsive: screenshot diff at 320/768/1024/1440 per `rules/ecc/web/testing.md`, specifically the Family Home card list (wrapping behavior) and the six-card Dashboard grid (column count at each breakpoint).

## 5. API Tests (contract-level, distinct from integration tests above)

- Request/response schema validation against `APIContract.md` for every endpoint (a lightweight contract test, e.g., via `schemathesis` or manual Pydantic-schema round-trip tests) — catches drift between the contract document and the actual implementation before it reaches the frontend.
- Auth: every endpoint rejects a missing/expired/malformed bearer token with `401`, matching the existing auth middleware's behavior (regression check, not new behavior).
- Rate limiting: confirm these new endpoints are correctly *not* subject to the sensitive-path stricter limits (per `APIContract.md`'s Cross-Cutting Rules), while still subject to the global limiter.

## 6. Regression Tests

- Full existing backend suite (185 tests as of the Foundation Reconciliation) re-run and passing, unchanged, after every Milestone 2 batch of changes.
- Existing `PATCH /goals/{id}` behavior (every field that existed before `custom_inflation_rate` was added) re-verified unchanged — the one endpoint this milestone extends rather than adds.
- Existing dashboard (`/api/v1/dashboard`) figures unchanged for a user with no household data (a user who never touches Family should see identical dashboard behavior to before Milestone 2 shipped).
- Existing onboarding wizard's other 9 steps unaffected by the Family step's revision.

## 7. Edge Cases

| Case | Expected Behavior |
|---|---|
| `children_count = 10` (upper bound) | Accepted, creates 10 placeholder rows |
| `children_count = 11` | Rejected, `422` |
| Child's DOB exactly 10 years ago (today) | SSY eligibility boundary — resolve definitively whether "under 10" is inclusive or exclusive of the exact 10th birthday and test that exact case (this is a real ambiguity worth pinning down in implementation, not left to whichever way integer age-truncation happens to fall) |
| Removing the only tagged member from a goal | Goal reverts to untagged state, not deleted |
| Tagging a goal with an already-removed (soft-deleted) member | Rejected, `422` — a removed member is not an "active member of caller's household" |
| Household with 0 members besides self, visiting Family Insurance | Empty state, no recommendation, no crash |
| A user with no `financial_assumptions` row at all (should not happen given existing onboarding, but tested defensively) attempting to view an education goal's projection | Falls back to the schema-default inflation rate (0.03), not a 500 error |
| Concurrent tag-replacement requests on the same goal (race condition) | Last-write-wins is acceptable (full-replacement semantics, no merge needed) — verified no deadlock or constraint violation under concurrent `PUT` |

## 8. Performance Tests

- `GET /family/dashboard` response time under realistic household size (2-8 members, 5-20 goals) — target consistent with existing dashboard endpoint's established baseline (`PerformanceReport.md`'s prior benchmarks), no new N+1 query pattern introduced (verified via query-count assertion in the integration test, not just wall-clock time).
- `GET /family/schemes` response time with the full seeded scheme catalog (9 schemes) × a large household (8 members) — confirm the cross-product evaluation (§11's Business Rules) stays well under 100ms server-side, per its own documented expectation of triviality.
- Frontend bundle budget: new Family routes' combined JS stays within the existing "App page" budget (`rules/ecc/web/performance.md`: <300kb gzipped) — measured, not assumed.

## 9. Financial Validation Tests

- SSY, SCSS, and every other scheme figure surfaced anywhere in Milestone 2's UI cross-checked byte-for-byte against `GovernmentPolicyReport.md`'s verified source values — any discrepancy is a defect, not a rounding choice.
- The ₹25,000/₹50,000 80C/123 deduction figures in the Family Insurance recommendation (§10) cross-checked against `FamilyHUFPlanningReport.md`'s verified figures.
- `custom_inflation_rate` bound enforcement (`[0, 0.5]`) tested at both boundaries and just outside them.
- No test in this suite fabricates a scheme rate or tax figure not already present in the certified seed data (`backend/scripts/seed_policy_data.py`) — per `docs/ENGINEERING_CONSTITUTION.md` Rule 4, test fixtures are held to the same non-invention standard as production seed data.

---

## Coverage Target

≥80% on all new backend code (`rules/ecc/common/testing.md`), verified via `pytest --cov=app --cov-fail-under=80` exactly as every prior milestone in this project has been gated.
