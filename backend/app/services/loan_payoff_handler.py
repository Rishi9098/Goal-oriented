"""Life Event Engine, Phase B.1 — Loan Payoff.

The first concrete event type registered with the generic engine built in
Phase A (`life_event_service.py`). Deliberately the simplest event in
`LifeEventEngineArchitecture.md`'s catalog (§5.10) — one entity, one write,
scoped to full closure only (a partial balance reduction is already served
by `PATCH /financials/liabilities/{id}` and does not need a life event).

This handler computes nothing itself: it calls
`financials_service.close_liability` — the exact function
`DELETE /financials/liabilities/{id}` now also calls — and reports the
effect that function already produced. No financial calculation, no
recommendation rule, and no Monte Carlo logic is duplicated here or
anywhere in this module (LifeEventEngineArchitecture.md §2).
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import financials_service
from app.services.life_event_service import EntityEffect


class LoanPayoffHandler:
    """Satisfies `life_event_service.LifeEventHandler` structurally (a
    Protocol — no explicit inheritance needed). `apply()` validates the
    liability exists (via
    `financials_service.close_liability`'s own 404), closes it, and
    reports that one effect. Everything else — recording the LifeEvent
    row, the LifeEventEffect row, the AuditLog row, the transaction
    boundary, and undo — is handled generically by
    `life_event_service.record_life_event`/`undo_life_event`; this class
    adds no logic beyond the one domain-specific write."""

    async def apply(
        self, db: AsyncSession, user: User, inputs: dict[str, Any]
    ) -> list[EntityEffect]:
        liability_id = uuid.UUID(inputs["liability_id"])
        liability, before_state, after_state = await financials_service.close_liability(
            db, user, liability_id
        )
        return [
            EntityEffect(
                entity_table="liabilities",
                entity_id=liability.id,
                change_type="soft_delete",
                before_state=before_state,
                after_state=after_state,
            )
        ]
