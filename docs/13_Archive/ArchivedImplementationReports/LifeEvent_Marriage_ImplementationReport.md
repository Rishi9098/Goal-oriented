# LIFE EVENT ENGINE — MARRIAGE IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #7 of the 17-event sequence requested, and the first **family-domain** event (every prior event touched only financials/goals). `LifeEventEngineArchitecture.md` §5.3's Marriage — a spouse `HouseholdMember` create + cascading `Dependent` create, via `family_service.create_member` unmodified. **No other event type was implemented.**

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/marriage_handler.py` | New (79 lines) | `MarriageHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `MarriageHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added `_LIFE_EVENT_SKIP_TYPES` (a fix for a real duplicate-notification bug found while building this event — see below); **no** `_LIFE_EVENT_COPY` entry added, per the architecture's own "Notifications: Free" design |
| `backend/tests/test_marriage_handler.py` | New (14 tests) | The full Marriage test suite, including a regression test for the notification fix |

**Not touched:** `family_service.py` itself — `create_member` is reused completely unmodified, no extraction needed, since it already returns the two rows the handler needs.

---

## HANDLER DESIGN

```python
class MarriageHandler:
    async def apply(self, db, user, inputs):
        household, _created = await family_service.get_or_create_household(db, user)
        raw_date_of_birth = inputs.get("date_of_birth")

        try:
            member, dependent = await family_service.create_member(
                db, user, household,
                FamilyMemberCreate(
                    relationship_type="spouse",
                    name=inputs["name"],
                    date_of_birth=date.fromisoformat(raw_date_of_birth) if raw_date_of_birth is not None else None,
                    gender=inputs.get("gender"),
                    relationship_detail=inputs.get("relationship_detail"),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return [
            EntityEffect("household_members", member.id, "create", None, life_event_service.snapshot(member, ...)),
            EntityEffect("dependents", dependent.id, "create", None, life_event_service.snapshot(dependent, ...)),
        ]
```

79 lines including the module docstring, imports, and the class's own docstring — this event needed **zero** new service-layer extraction, unlike every prior financial event. `family_service.create_member` already does everything required: creates the `HouseholdMember`, creates the cascading `Dependent`, validates via `validate_member_fields`, and writes its own `family_member_added` AuditLog row — all pre-existing behavior from before the Life Event Engine existed.

1. **Existing validation reused, not duplicated or bypassed.** `date_of_birth` is required for `relationship_type="spouse"` per `validate_member_fields` — even though §5.3's own prose calls it optional. Rather than the handler inventing a stricter or looser rule of its own, `date_of_birth` is passed through as `None` when absent from `inputs`, letting `create_member`'s own existing check raise the `ValueError` it always has, translated to the same `422` shape `POST /family/members` already returns.
2. **No calculation.** Marriage moves no money; `CALCULATION_CONTEXT_FIELDS` is never touched, matching §5.3 exactly.
3. **Single request-scoped transaction** — `create_member` never calls `db.commit()` (flush only, for the generated ids `record_life_event` needs).
4. **Generic undo, no event-specific code — and no need for `family_service.remove_member` at all.** Both `household_members` and `dependents` were already present in `life_event_service._ENTITY_MODELS` since Phase A, and both models have an `is_active` column. The generic engine's existing "create effect + `is_active` column → soft-delete on undo" rule (already proven for `income_sources`, `assets`, `liabilities`) handles both rows directly — `remove_member` is never called by undo.

---

## BUG FOUND AND FIXED: duplicate notification

Building this event's notification-verification test surfaced a genuine collision the architecture's own "Notifications: Free" claim didn't anticipate having to guard against: `family_service.create_member` writes a `family_member_added` AuditLog row, which the **pre-existing** `notification_service._collect_family_member_added_facts` collector (built long before the Life Event Engine) already turns into a notification. But `record_life_event` **also** always creates a `LifeEvent` row, which the **generic** `_collect_life_event_facts` collector (built for Salary Raise, in this same task sequence) reads unconditionally for every event type — with a different `dedupe_key` than the family-member collector's. Recording a Marriage through the engine would therefore have produced **two** notifications for one real-world action, not the "free," single notification §5.3 describes.

**Fix:** added `notification_service._LIFE_EVENT_SKIP_TYPES = frozenset({"marriage"})`, and excluded it from `_collect_life_event_facts`'s query (`LifeEvent.event_type.notin_(_LIFE_EVENT_SKIP_TYPES)`). This is additive and narrowly scoped — it only suppresses the *generic* collector for an event type whose handler's own underlying write already has a dedicated, pre-existing collector; it does not touch `_collect_family_member_added_facts` or any other event type's notification. Verified by `TestNotificationDoesNotDuplicate::test_exactly_one_notification_appears_for_a_marriage_event`, asserting `source="life_event"` produces zero items and `source="family_member_added"` produces exactly one, over the real HTTP `/notifications` endpoint.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_marriage_handler.py` — 14 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates the spouse member and dependent with two correctly-shaped `create` effects; raises 422 when `date_of_birth` is missing (reusing `validate_member_fields`'s own rule, not a new one); creates the household on first use if none exists yet |
| **Integration (full workflow)** | `record_life_event` end-to-end produces both effects; **both** the pre-existing `family_member_added` AuditLog row and the generic `life_event_recorded` row are written (two rows, by design — this is what makes the notification free) |
| **Rollback** | A wrapper handler runs the *real* `MarriageHandler.apply()` then raises; after rollback, no spouse-typed member or dependent exists at all, and no `LifeEvent` row exists |
| **Undo** | Soft-deletes both the member and dependent (the "create + `is_active`" generic rule, now proven for a fourth and fifth entity type — `household_members`/`dependents` — with zero event-specific code); writes the generic undo `AuditLog` row; **blocked** if the member changed independently after the event; rejects undoing another user's event |
| **Notification collision fix** | Exactly one notification (`source="family_member_added"`) appears for a Marriage event, and zero appear with `source="life_event"` — the regression test for the bug above |

**Result:** 14/14 pass. `marriage_handler.py`: **100%** coverage.

---

## ROLLBACK VERIFICATION

Directly exercised by `TestRollback::test_partial_failure_leaves_no_durable_change`:

1. A test-only wrapper calls the real `MarriageHandler.apply()` — the spouse member and dependent are genuinely created and flushed inside the uncommitted transaction — then raises.
2. The caller calls `db.rollback()`.
3. Verified: no spouse-typed `HouseholdMember` or `Dependent` exists for this user; zero `LifeEvent` rows exist.

---

## UNDO VERIFICATION

- **Clean undo:** `undo_life_event` soft-deletes both the member and dependent via the generic create-effect rule — no call to `family_service.remove_member` at all, proving the generic engine is sufficient for this event without any bespoke reversal code.
- **Guarded/blocked undo:** after recording, the member's `name` is independently changed; `undo_life_event` returns `blocked=True` naming `household_members`.
- **Ownership:** another user cannot undo this user's Marriage (`LookupError`).

**Named limitation, not resolved here:** §5.3's own "Undo/edit" row describes a more sophisticated guard than the generic engine provides — blocking undo if the spouse is now referenced by a `HealthPolicyCoverage` row or a tagged goal, surfaced as a specific list. Building that would require either extending the generic engine with entity-specific referential checks (breaking the "no event-specific undo code" invariant every event in this sequence has held to) or a first bespoke per-event undo override. Consistent with how Phase A's own engine already documents "a known limitation, not resolved here" for an analogous gap (an unrestorable create with no `is_active` column), this is named explicitly rather than silently built around: the current guard only detects the spouse's own row changing since the event, not downstream references to it.

---

## PERFORMANCE

No new query shape beyond what `POST /family/members` already issued — one household lookup/create, one member insert, one dependent insert, no N+1.

---

## BACKWARD COMPATIBILITY

- **Full suite: 513 passed**, zero skipped, zero failures.
- **`test_family_router.py`** (family member CRUD): unchanged, all pass — `create_member` was not modified.
- **`test_notifications.py`** (13 tests, +1 new here counted separately in the Marriage suite): unchanged, all pass — the `_LIFE_EVENT_SKIP_TYPES` filter is additive and scoped to exactly one event type.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 75 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Marriage is the first family-domain event and required zero new service-layer extraction — `family_service.create_member` was reusable as-is, and the generic undo engine's pre-existing "create + `is_active`" rule (built for financial entities) generalized correctly to `household_members`/`dependents` with no changes. The one genuine gap found — a duplicate-notification collision between the pre-existing family collector and the newer generic Life Event collector — was caught by test-writing discipline before shipping, not after, and fixed with a narrowly-scoped, documented exclusion rather than a broader mechanism change. Birth of Child (§5.5) and Adoption (§5.6) are structurally identical to this event and will need the same `_LIFE_EVENT_SKIP_TYPES` treatment.

Proceeding automatically to event #8 (Birth of Child), per standing instruction.
