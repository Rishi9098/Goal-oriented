# LIFE EVENT ENGINE — DIVORCE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #10 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.4's Divorce — the spouse `HouseholdMember` and cascading `Dependent` soft-deleted, plus two new purely-live "review" notification prompts. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/family_service.py` | Modified | `remove_member()` extended to accept and cascade-deactivate the dependent, returning both rows — a real, pre-existing gap this event surfaced (see below) |
| `backend/app/routers/family.py` | Modified | `delete_family_member` now passes the already-looked-up `dependent` through to `remove_member`, instead of discarding it |
| `backend/app/services/divorce_handler.py` | New (85 lines) | `DivorceHandler` — the concrete `LifeEventHandler` |
| `backend/app/services/notification_service.py` | Modified | Added `_collect_divorce_review_facts` — the two new live "review" prompts §5.4 calls for; wired into `_collect_facts`; added a normal `_LIFE_EVENT_COPY["divorce"]` entry (unlike Marriage/Birth of Child/Adoption, this is a soft-delete, not a create, so there is no pre-existing free collector to lean on) |
| `backend/app/schemas/notification.py` | Modified | Added `"divorce_review"` to `NotificationSource` |
| `backend/app/main.py` | Modified | Registers `DivorceHandler` against the engine |
| `backend/tests/test_divorce_handler.py` | New (16 tests) | The full Divorce test suite, including the two new notification prompts |

---

## BUG FOUND AND FIXED: `remove_member` never deactivated the dependent

§5.4 states the entities changed are "the spouse's `household_members` row soft-deleted... the cascading `dependents` row soft-deleted with it." Inspecting `family_service.remove_member` (the function the architecture itself names) showed it only ever set `member.is_active = False` — the dependent row was never touched, by any caller, ever. This predates the Life Event Engine entirely; `DELETE /family/members/{id}` had this same gap since the endpoint was first written (it already looks up the dependent via `get_member_and_dependent`, then discards it with `_dependent`).

No existing test asserted the dependent's `is_active` state after removal (`test_family_router.py`'s `TestDeleteFamilyMember` only checks the member's own state via the API surface), so nothing currently depends on the old, incomplete behavior. **Fixed** by extending `remove_member` to accept an optional `dependent: Dependent | None = None` parameter, deactivating it alongside the member when given, and returning `(member, dependent)` for a caller (the router, or this handler) that already has both in scope. The one pre-existing caller (`DELETE /family/members/{id}`) now passes its already-looked-up `dependent` through instead of discarding it — a one-line change, verified behavior-preserving by the full, unmodified `test_family_router.py` suite passing unchanged (no test asserted the old, incomplete behavior, so there was nothing to break).

---

## HANDLER DESIGN

```python
class DivorceHandler:
    async def apply(self, db, user, inputs):
        member_id = uuid.UUID(inputs["member_id"])
        household, _created = await family_service.get_or_create_household(db, user)

        found = await family_service.get_member_and_dependent(db, household, member_id)
        if found is None:
            raise HTTPException(404, "Member not found")
        member, dependent = found
        if member.relationship_type == "self":
            raise HTTPException(400, "Cannot remove the household creator")

        member_before = life_event_service.snapshot(member, ...)
        dependent_before = life_event_service.snapshot(dependent, ...) if dependent else None

        await family_service.remove_member(db, user, member, dependent)

        member_after = life_event_service.snapshot(member, ...)
        effects = [EntityEffect("household_members", member.id, "soft_delete", member_before, member_after)]
        if dependent is not None:
            dependent_after = life_event_service.snapshot(dependent, ...)
            effects.append(EntityEffect("dependents", dependent.id, "soft_delete", dependent_before, dependent_after))
        return effects
```

85 lines including the module docstring, imports, and the class's own docstring — structurally the mirror image of Marriage/Birth of Child (soft-delete instead of create), reusing `family_service.get_member_and_dependent` and the newly-fixed `remove_member` rather than duplicating either.

1. **Same "self" guard as the router** — `DELETE /family/members/{id}`'s own check (`relationship_type == "self"` → 400) is reused verbatim rather than re-derived, since the handler calls the identical lookup function the router does.
2. **Snapshots built by the handler, around `remove_member`'s plain `(member, dependent)` return** — the same convention Marriage/Birth of Child already established for `create_member`'s equally plain return shape.
3. **Single request-scoped transaction** — `remove_member` never calls `db.commit()` (added `flush()` as part of this event's fix, since a caller reading the rows again within the same transaction — as this handler's own after-snapshot does — needs the mutation visible).
4. **Generic undo, no event-specific code** — both effects are `soft_delete` with populated `before_state`; undo restores both rows exactly via the already-proven generic rule.

**Named limitation, carried over from Marriage:** §5.4's own "Undo/edit" row wants undo blocked specifically if a `HealthPolicyCoverage`/`Nominee` row referencing the member changed independently — beyond the generic engine's simple "did this row's own state change" check. Not built here for the same reason given in the Marriage report (no event-specific undo code, by design, in this engine as it stands today).

---

## NEW NOTIFICATION LOGIC: two live "review" prompts

Unlike every other notification added in this sequence (one `_LIFE_EVENT_COPY` line, reusing the generic collector), §5.4 calls for genuinely new, purely-live logic — the first and only such addition in the sequence so far:

```python
async def _collect_divorce_review_facts(db, user) -> list[_Fact]:
    # 1. Any inactive spouse-typed HouseholdMember still referenced by an
    #    active HealthPolicyCoverage row -> "Review insurance coverage for [name]"
    # 2. Any active spouse-relationship Nominee row (via Asset ownership)
    #    -> "Review beneficiary/nominee designations"
```

Both follow the exact philosophy `_collect_insurance_fact`/`_collect_scheme_facts` already established: `event_at=None`, no recency window — these are "you still need to resolve this" prompts, not "something just happened" ones, so they persist across reads for as long as the underlying condition holds, exactly like the existing insurance/scheme recommendations do.

**Interpretive design decision:** §5.4's own prose describes prompt (2) as firing for "any active Nominee row... whose relationship_type was 'spouse'" — read completely literally, that would fire for *any* currently-married user with a spouse-designated nominee, which makes no sense as a divorce-review prompt (a happily married person doesn't need to be told to review their spouse's nominee status). Both prompts are instead scoped to *an inactive spouse-typed `HouseholdMember` existing at all* — i.e., they only ever appear after an actual divorce (via this event, or in principle any other path that deactivates a spouse), never for a still-married user. This is documented directly in the collector's own docstring and verified by `test_nominee_review_prompt_does_not_fire_without_an_inactive_spouse`.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_divorce_handler.py` — 16 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Soft-deletes both member and dependent with correctly-shaped effects; raises 404 for a nonexistent member; raises 400 for the "self" member |
| **Integration (full workflow)** | `record_life_event` end-to-end produces both effects; writes the generic `AuditLog` row |
| **Rollback** | A wrapper handler runs the *real* `DivorceHandler.apply()` then raises; after rollback, both member and dependent are still fully active |
| **Undo** | Reactivates both rows; writes the generic undo `AuditLog` row; **blocked** if the member changed independently after the event; rejects undoing another user's event |
| **New review notifications** | The generic `life_event` notification fires with the new `_LIFE_EVENT_COPY["divorce"]` copy; no `divorce_review` prompts exist before any divorce; the insurance-coverage prompt fires and names the ex-spouse when an active `HealthPolicyCoverage` still references them; the nominee prompt fires when an active spouse-designated `Nominee` exists; the nominee prompt does **not** fire for a still-married user (the interpretive scoping decision above) |

**Result:** 16/16 pass. `divorce_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`:

1. A spouse member and dependent are created and committed (the pre-existing state).
2. A test-only wrapper calls the real `DivorceHandler.apply()` — both rows genuinely deactivated and flushed inside the uncommitted transaction — then raises.
3. The caller calls `db.rollback()`.
4. Verified: both the member and dependent are fully active again; zero `LifeEvent` rows exist.

---

## UNDO VERIFICATION

- **Clean undo:** `undo_life_event` reactivates both the member and dependent via the generic soft-delete-effect rule.
- **Guarded/blocked undo:** after recording, the member's `name` is independently changed; `undo_life_event` returns `blocked=True` naming `household_members`.
- **Ownership:** another user cannot undo this user's Divorce (`LookupError`).

---

## PERFORMANCE

No new query shape beyond what `DELETE /family/members/{id}` already issued, plus the two new review-prompt queries — each a single indexed join (`HealthPolicyCoverage`↔`HouseholdMember`↔`HealthPolicy`; `Nominee`↔`Asset`), gated behind an early return when no inactive spouse exists at all, so the cost is zero for the overwhelming majority of users who have never recorded a Divorce.

---

## BACKWARD COMPATIBILITY

- **Full suite: 546 passed**, zero skipped, zero failures.
- **`test_family_router.py`** (family member CRUD, including delete): unchanged, all pass — confirms `remove_member`'s extended signature preserves `DELETE /family/members/{id}`'s exact externally observable behavior.
- **`test_notifications.py`, `test_household_policy_models.py`**: unchanged, all pass.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 77 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Divorce is the first soft-delete-shaped family event (the mirror of Marriage's create) and the first event in this sequence to require genuinely new notification logic rather than a one-line `_LIFE_EVENT_COPY` addition or an existing-collector reuse — handled by following the exact same purely-live, no-persistence philosophy every prior notification source already uses, with an explicit, tested interpretive decision recorded where the architecture's own prose was ambiguous. It also fixed a real, previously-untested gap in `family_service.remove_member` that predates this entire task.

Proceeding automatically to event #11 (Dependent Parent), per standing instruction.
