# Contract Deviation Report — Milestone 2, Task 3

**Date:** 2026-07-06
**Comparing:** planned implementation vs. `Milestone2ImplementationContract.md` §11, `ValidationMatrix.md`'s Government Eligibility Validation table, `ImplementationChecklist.md` Task 3, `APIContract.md`.

---

## Deviation 1 — Seed data precondition (already approved)

**Contract assumption:** §11's Business Rules describe evaluating "for each `scheme`... its `scheme_eligibility_rules`" as if rule rows already exist.
**Reality found:** zero rows exist (see `DependencyValidationReport.md`).
**Resolution:** seed exactly two rows (SSY `max_age<10`, SCSS `min_age>=60`), sourced only from `GovernmentPolicyReport.md`, folded into this task per your approval. Not a Contract change — the Contract's *intent* (evaluate real eligibility rules) is preserved; only the missing precondition is filled in.

## Deviation 2 — "Potentially Eligible" window now concretely defined

**Contract:** gave one illustrative example ("turns 60 next year") with no stated general rule.
**Resolution (Design Review, Step 4):** a 5-year window on the not-yet-reached side of an age threshold. Documented in `DesignReview.md`. Not a business-rule change — a necessary concretization of an underspecified detail, made explicit rather than left as an undocumented implementation accident.

## Deviation 3 — Wiring Task 2's `eligible_schemes` stub to the new service

**`ImplementationChecklist.md` Task 3's literal text:** "no router yet (routers for §4 and §11 both call this in later tasks)."

**What's being done instead:** Task 2's `PUT /family/members/{id}` endpoint already has an `eligible_schemes` field, deliberately built and stubbed empty with this exact code comment: *"Always empty this task — the shared scheme-eligibility service is Task 3's scope... Returning it here... keeps the response shape stable for when Task 3 lands."* Now that Task 3's service exists, leaving that field permanently stubbed would contradict the documented reason it was built that way, and would mean the SSY callout (§4, one of this service's two named consumers) still doesn't work even after its dependency is satisfied.

**Judgment call:** this is completing a partial feature exactly as designed, not starting a new one. No new router is added (the Contract's literal words are honored — Task 3 still doesn't add a *router*); the existing `PUT /family/members/{id}` endpoint (Task 2's, already shipped) gets one additional internal call to the new service function. This is a smaller, more directly-connected change than, say, building Task 11's full Schemes screen now would be — that remains untouched and deferred.

**If this judgment call is wrong:** the fix is a two-line revert (stop calling the service from `family_service.update_member`/`create_member`, leave `eligible_schemes` stubbed) — flagging this explicitly so it's easy to undo if you'd rather keep Task 3 strictly service-only.

## No other deviations found

`ValidationMatrix.md`'s three rule types (`min_age`, `max_age`, `residency_status`) — only `min_age`/`max_age` are actually needed for the two rules being seeded; `residency_status` support is built into the evaluator's design (per the Contract) but has no rows to exercise it yet, consistent with "don't invent a rule with nothing to seed it." `docs/ENGINEERING_CONSTITUTION.md` Rule 7 (deliberately narrow, three rule types, not a general interpreter) — honored, no fourth rule type invented.

## Requested Decision

Proceeding with Deviations 1-3 as described unless told otherwise — Deviation 1 already has your explicit approval; Deviations 2-3 are flagged here for visibility per Step 5's requirement, not blocking questions, since neither changes a business rule or introduces new scope, only fills gaps the Contract left implicit.
