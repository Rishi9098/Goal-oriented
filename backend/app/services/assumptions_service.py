"""Service layer for the financial assumptions entity.

Milestone 2 Life Event Engine addition: `update_assumptions_fields` is
the exact create-or-update mutation `PUT /assumptions` performs,
extracted here (not left inline in the router) because Retirement's
handler needs to call it with just the fields it's touching
(`retirement_age`/`social_security_monthly`), the same way
`profile_service.update_profile_fields` was extracted for Job Change.
`routers/assumptions.py`'s `upsert_assumptions` now calls this too, so
there is exactly one implementation of "create-or-update assumptions."

Deliberately does not touch `get_assumptions`'s own commit/rollback
concurrency guard (TransactionConsistencyImplementationPlan.md) — that
remains the one documented exception to the "never commit inside a
service function" rule, unrelated to this extraction.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assumptions import FinancialAssumptions
from app.models.user import User
from app.services import life_event_service

DEFAULTS = {
    "inflation_rate": 0.03,
    "expected_return_conservative": 0.05,
    "expected_return_balanced": 0.07,
    "expected_return_aggressive": 0.09,
    "tax_rate": 0.22,
    "retirement_age": 65,
    "social_security_monthly": 0.0,
}


async def update_assumptions_fields(
    db: AsyncSession, user: User, updates: dict[str, Any]
) -> tuple[FinancialAssumptions, dict[str, Any] | None, dict[str, Any]]:
    """Creates the assumptions row (seeded with `DEFAULTS`, overridden by
    `updates`) if none exists yet, otherwise updates only the given
    fields — the exact create-or-update mutation `PUT /assumptions`
    already performs. Returns the row, before_state (None when this call
    created the row — a "create" effect has no before_state, per the Life
    Event Engine's convention) and after_state, both built via
    `life_event_service.snapshot()` over only the fields this call
    touched."""
    result = await db.execute(
        select(FinancialAssumptions).where(FinancialAssumptions.user_id == user.id)
    )
    assumptions = result.scalar_one_or_none()

    if assumptions is None:
        assumptions = FinancialAssumptions(user_id=user.id, **{**DEFAULTS, **updates})
        db.add(assumptions)
        await db.flush()
        await db.refresh(assumptions)
        after_state = life_event_service.snapshot(assumptions, updates.keys())
        return assumptions, None, after_state

    before_state = life_event_service.snapshot(assumptions, updates.keys())
    for field, value in updates.items():
        setattr(assumptions, field, value)
    db.add(assumptions)
    await db.flush()
    await db.refresh(assumptions)
    after_state = life_event_service.snapshot(assumptions, updates.keys())
    return assumptions, before_state, after_state
