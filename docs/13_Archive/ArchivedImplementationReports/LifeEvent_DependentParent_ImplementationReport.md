# LIFE EVENT ENGINE — DEPENDENT PARENT IMPLEMENTATION REPORT

**Role:** Senior Backend Engineer
**Scope:** Event #11 of the 17-event sequence requested. **Not one of `LifeEventEngineArchitecture.md`'s original 15 catalogued events** — added to this run's ordered list. Modeled directly on Marriage/Birth of Child (§5.3/§5.5): `family_service.create_member` already supports `relationship_type="parent"` → `dependent_type="elderly_parent"` natively; this event is that exact path with parent-specific required inputs. **No other event type was implemented.**

---

## DESIGN DECISION (not in the original 15-event catalog)

Unlike Adoption (which was byte-for-byte identical to Birth of Child in every required input), Dependent Parent cannot literally reuse `MarriageHandler` or `BirthOfChildHandler` unchanged — `validate_member_fields` imposes a **different** required-field set for `relationship_type="parent"`:

- `date_of_birth` is **not** required for a parent (unlike spouse/child) — matching real-world onboarding, where an elderly parent's exact birth date is often not readily on hand.
- `relationship_detail` **must** be `"mother"` or `"father"` for a parent — a field Marriage/Birth of Child never populate.
- `has_own_insurance` (`"yes"`/`"no"`/`"not_sure"`) is **required** for a parent — again, a field the sibling events never touch.

Since the required-input contract genuinely differs, a small new handler (`DependentParentHandler`, 92 lines) was written rather than force-sharing a class the way Adoption did — but it follows the identical structure (resolve household → `create_member` → catch `ValueError` → 422 → build two `create` effects) with zero new mechanism.

---

## FILES CHANGED

| File | Status | Change |
|---|---|---|
| `backend/app/services/dependent_parent_handler.py` | New (92 lines) | `DependentParentHandler` — the concrete `LifeEventHandler` |
| `backend/app/main.py` | Modified | Registers `DependentParentHandler` against the engine |
| `backend/app/services/notification_service.py` | Modified | Added `"dependent_parent"` to `_LIFE_EVENT_SKIP_TYPES` — the same duplicate-notification fix reused a third time (after Birth of Child, Adoption) |
| `backend/tests/test_dependent_parent_handler.py` | New (14 tests) | The full Dependent Parent test suite |

**Not touched:** `family_service.py` — `create_member` and `validate_member_fields` are reused completely unmodified; they already had full support for `relationship_type="parent"` before this event existed.

---

## HANDLER DESIGN

```python
class DependentParentHandler:
    async def apply(self, db, user, inputs):
        household, _created = await family_service.get_or_create_household(db, user)
        raw_date_of_birth = inputs.get("date_of_birth")

        try:
            member, dependent = await family_service.create_member(
                db, user, household,
                FamilyMemberCreate(
                    relationship_type="parent",
                    name=inputs["name"],
                    date_of_birth=date.fromisoformat(raw_date_of_birth) if raw_date_of_birth is not None else None,
                    gender=inputs.get("gender"),
                    relationship_detail=inputs.get("relationship_detail"),
                    has_own_insurance=inputs.get("has_own_insurance"),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return [
            EntityEffect("household_members", member.id, "create", None, member_after),
            EntityEffect("dependents", dependent.id, "create", None, dependent_after),
        ]
```

1. **Existing validation reused, not duplicated.** `relationship_detail`/`has_own_insurance` requirements come entirely from `validate_member_fields`'s pre-existing `relationship_type == "parent"` branch — the handler invents no new required-field logic, just passes inputs through and translates the resulting `ValueError` to the same `422` shape every prior family-domain event uses.
2. **No calculation, no optional goal step** — unlike Birth of Child, nothing in the architecture's own reasoning (or the progress matrix's own design note) calls for a linked goal here, so none was added.
3. **Single request-scoped transaction, generic undo** — identical mechanics to Marriage/Birth of Child, now proven for a third `relationship_type` value.
4. **Notification-skip fix reused a third time** — no new bug to find; the same collision Marriage's implementation discovered and fixed applies identically here, since `create_member`'s own `family_member_added` AuditLog fires regardless of relationship_type.

---

## DATABASE CHANGES

**None.** No migration, no new column, no new table. `alembic current` remains at `010 (head)`.

---

## TESTS ADDED

`tests/test_dependent_parent_handler.py` — 14 tests:

| Category | Tests |
|---|---|
| **Unit (handler in isolation)** | Creates the parent member and dependent with `relationship_detail`/`has_own_insurance` correctly set and `date_of_birth` correctly `None` when omitted; accepts an optional `date_of_birth`; raises 422 when `relationship_detail` is missing; raises 422 when `has_own_insurance` is missing |
| **Integration (full workflow)** | `record_life_event` end-to-end produces both effects; both the pre-existing `family_member_added` and generic `life_event_recorded` `AuditLog` rows are written |
| **Rollback** | A wrapper handler runs the *real* `DependentParentHandler.apply()` then raises; after rollback, no parent-typed member or elderly_parent-typed dependent exists at all |
| **Undo** | Soft-deletes both member and dependent; rejects undoing another user's event |
| **Notification collision fix** | Exactly one notification (`source="family_member_added"`) appears, zero with `source="life_event"` |

**Result:** 14/14 pass. `dependent_parent_handler.py`: **100%** coverage.

---

## ROLLBACK / UNDO VERIFICATION

Identical mechanics to Marriage/Birth of Child, now proven for `relationship_type="parent"`/`dependent_type="elderly_parent"`: a wrapper handler performs the real writes, raises, and rollback confirms neither row survives; undo confirms both rows soft-delete cleanly via the generic engine's existing rule. Not re-derived in detail here since the underlying mechanism (`create_member`, the generic engine) is unchanged from those two events' own reports.

---

## PERFORMANCE

No new query shape — identical cost to Marriage/Birth of Child's member-creation path.

---

## BACKWARD COMPATIBILITY

- **Full suite: 556 passed**, zero skipped, zero failures.
- **`test_family_router.py`, `test_notifications.py`**: unchanged, all pass.
- **`ruff check app/`**: all checks passed. **`mypy --strict app/`**: no issues found in 78 source files.
- No existing endpoint's request/response schema, status code, or URL changed.

---

## READY FOR THE NEXT EVENT?

**Yes.** Dependent Parent confirms the family-domain pattern established by Marriage/Birth of Child generalizes correctly to a third `relationship_type` with a genuinely different required-field contract, without needing any change to `family_service.py` itself — the schema and its validation were already fully general.

Proceeding automatically to event #12 (Retirement), per standing instruction.
