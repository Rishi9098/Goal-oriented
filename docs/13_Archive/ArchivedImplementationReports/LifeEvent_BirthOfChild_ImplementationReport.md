# LIFE EVENT ENGINE — BIRTH OF CHILD IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #8 of the 17-event sequence requested. `LifeEventEngineArchitecture.md` §5.5's Birth of Child — a child `HouseholdMember` + `Dependent` create (structurally identical to Marriage), with an optional linked education `Goal` create ("start a college fund?"). **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/planning_service.py` | Modified | Added `create_goal()` — the exact mutation `POST /goals` performs, including its unconditional Monte Carlo run on create, returning an after_state snapshot for a `LifeEventEffect` |
| `backend/app/routers/goals.py` | Modified | `create_goal` endpoint now calls `planning_service.create_goal()` instead of its own inline mutation; removed the now-unused `calculate_goal_probability` import |
| `backend/app/services/birth_of_child_handler.py` | New (110 lines) | `BirthOfChildHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `BirthOfChildHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added `"birth_of_child"` to `_LIFE_EVENT_SKIP_TYPES` (the same fix Marriage's own implementation found and applied) |
| `backend/tests/test_birth_of_child_handler.py` | New (13 tests) | The full Birth of Child test suite |

**Not touched:** `family_service.py` — `create_member` reused completely unmodified, the second event in a row (after Marriage) to do so.

---

## HANDLER DESIGN

```python
class BirthOfChildHandler:
    async def apply(self, db, user, inputs):
        household, _created = await family_service.get_or_create_household(db, user)
        raw_date_of_birth = inputs.get("date_of_birth")

        try:
            member, dependent = await family_service.create_member(
                db, user, household,
                FamilyMemberCreate(
                    relationship_type="child", name=inputs["name"],
                    date_of_birth=date.fromisoformat(raw_date_of_birth) if raw_date_of_birth is not None else None,
                    gender=inputs.get("gender"), is_tax_dependent=True,
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        effects = [
            EntityEffect("household_members", member.id, "create", None, member_after),
            EntityEffect("dependents", dependent.id, "create", None, dependent_after),
        ]

        if inputs.get("goal_target_amount") is not None and inputs.get("goal_target_date") is not None:
            goal, goal_after = await planning_service.create_goal(
                db, user, GoalCreate(
                    name=inputs.get("goal_name", f"{inputs['name']}'s College Fund"),
                    category="education",
                    target_amount=float(inputs["goal_target_amount"]),
                    target_date=date.fromisoformat(inputs["goal_target_date"]),
                    ...
                ),
            )
            effects.append(EntityEffect("goals", goal.id, "create", None, goal_after))

        return effects
```

110 lines including the module docstring, imports, and the class's own docstring — structurally a direct sibling of Marriage's handler with one addition: the optional education-goal step.

1. **Existing validation and defaults reused, not reinvented.** Same `date_of_birth`-required-for-relationship-type pattern as Marriage (now proven for "child" too, via the same `validate_member_fields` rule). `is_tax_dependent=True` is passed explicitly by the handler (the schema's own generic default is `False`) — this is the one handler-specific default the architecture calls for ("`is_tax_dependent=true` by default"), set at the call site rather than by changing the shared schema's default for every relationship type.
2. **Optional education goal, explicit opt-in only** — `goal_target_amount` + `goal_target_date` must both be present, matching the "never assume an optional step" rule from every prior event with an optional sub-step (Salary Raise, Job Change, New Loan, House Purchase). Tested explicitly (`test_apply_ignores_goal_target_amount_without_a_target_date`).
3. **The goal creation reuses `planning_service.create_goal`, extracted here for exactly this purpose** — unlike `update_goal_fields` (an update, conditionally recalculating), goal *creation* unconditionally runs Monte Carlo every time, matching `POST /goals`'s existing, always-on trigger. The extraction changes zero observable behavior of that endpoint (verified by `test_goals.py`/`test_goal_inflation.py` passing unchanged).
4. **Single request-scoped transaction across up to three writes** — none of `create_member` or `create_goal` call `db.commit()`.
5. **Generic undo, no event-specific code** — all three possible effects (`household_members`, `dependents`, `goals`) are `create` effects on rows with `is_active` columns; undo soft-deletes all three via the already-proven generic rule, now confirmed for a sixth entity type (`goals`, alongside `income_sources`, `assets`, `liabilities`, `household_members`, `dependents`).
6. **Notification collision reused, not re-derived.** The exact same fix Marriage's own implementation built — `notification_service._LIFE_EVENT_SKIP_TYPES` — gets one more entry (`"birth_of_child"`), since this event shares the identical "free" notification path via `family_member_added`. No second bug needed discovering: the mechanism the prior event built generalizes directly.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_birth_of_child_handler.py` — 13 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates the child member and dependent only (`is_tax_dependent=True` confirmed on the row, not just the effect); also creates an education goal when both `goal_target_amount`/`goal_target_date` are given, with `probability` present in its `after_state`; ignores `goal_target_amount` without a target date; raises 422 when `date_of_birth` is missing |
| **Integration (full workflow)** | `record_life_event` end-to-end produces all three effects when a goal is linked; both the pre-existing `family_member_added` and generic `life_event_recorded` `AuditLog` rows are written |
| **Rollback** | A wrapper handler runs the *real* `BirthOfChildHandler.apply()` with the goal step engaged, then raises; after rollback, no child-typed member, dependent, or goal exists at all |
| **Undo** | Reverses all three effects (soft-deletes member, dependent, and goal); writes the generic undo `AuditLog` row; rejects undoing another user's event |
| **Notification collision fix** | Exactly one notification (`source="family_member_added"`) appears, zero with `source="life_event"` — confirms the shared fix generalizes correctly to a second event type |

**Result:** 13/13 pass. `birth_of_child_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`, the first rollback proof spanning all three of `household_members`/`dependents`/`goals` in one event:

1. A test-only wrapper calls the real `BirthOfChildHandler.apply()` with the education-goal step engaged — the member, dependent, and goal are all genuinely created and flushed (including the goal's own Monte Carlo-computed `probability`) inside the uncommitted transaction — then raises.
2. The caller calls `db.rollback()`.
3. Verified: no child-typed member, dependent, or goal exists for this user; zero `LifeEvent` rows exist.

---

## UNDO VERIFICATION

- **Clean undo, all three effects:** `undo_life_event` soft-deletes the member, dependent, and goal via the generic create-effect rule — the first time this event catalog's generic undo has reversed a `goals` create, not just a `goals` update (House Purchase) or a financial entity create.
- **Ownership:** another user cannot undo this user's Birth of Child (`LookupError`).

Same named limitation as Marriage applies here too: §5.5's own "Undo/edit" row anticipates a guard for whether the education goal has since received contributions or been tagged elsewhere — beyond what the generic engine's simple state-mismatch check currently detects. Not resolved in this event either, for the identical reason given in the Marriage report.

---

## PERFORMANCE

No new query shape beyond what `POST /family/members` and `POST /goals` already issued individually — the goal step's one Monte Carlo run is the exact cost that endpoint already incurs on every creation, not a new one.

---

## BACKWARD COMPATIBILITY

- **Full suite: 524 passed**, zero skipped, zero failures.
- **`test_goals.py`, `test_goal_inflation.py`** (goal CRUD, including create): unchanged, all pass — proves `create_goal`'s extraction preserves `POST /goals`'s exact behavior.
- **`test_family_router.py`, `test_notifications.py`**: unchanged, all pass.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 76 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Birth of Child confirms both of Marriage's own contributions — the family-member creation pattern and the notification-skip mechanism — generalize cleanly to a second, structurally similar event, and extends the generic engine's proven "create + `is_active`" undo rule to a sixth entity type (`goals`, via a create rather than House Purchase's update). Adoption (§5.6, next) is described by the architecture as nearly identical to this event.

Proceeding automatically to event #9 (Adoption), per standing instruction.
