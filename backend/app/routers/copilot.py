"""
AI Copilot endpoint.

When OPENAI_API_KEY is set, uses GPT-4o with a system prompt that anchors
the model to the user's current financial plan.  Falls back to a rule-based
responder when no key is configured so the endpoint is always functional.
"""

import json
import uuid

from fastapi import APIRouter, Depends
from openai import AsyncOpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.logging_config import get_logger
from app.middleware.auth import get_current_user
from app.models.goal import Goal
from app.models.user import User
from app.schemas.simulation import ChatRequest, ChatResponse

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])

# Reuse a single client instance across requests to avoid creating a new
# HTTP connection pool on every call.
_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI | None:
    global _openai_client
    if not settings.openai_api_key:
        return None
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            # The SDK's own retry loop (exponential backoff) handles
            # transient failures; `timeout` bounds how long a single
            # request — and the DB session held open for it — can hang.
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
    return _openai_client

_SYSTEM_PROMPT = """
You are Northstar Copilot, an expert AI financial planner.
You have access to the user's goals, their Monte Carlo probabilities, and their
portfolio snapshot.  Speak in plain English — no jargon without explanation.
Keep responses under 200 words unless a detailed analysis is explicitly requested.
Always ground advice in the user's actual data.

User's financial goals (JSON):
{goals_json}
"""


async def _fallback_response(message: str, goals: list[Goal]) -> str:
    """Rule-based fallback when no OpenAI key is configured."""
    low_prob = [g for g in goals if g.probability < 70]
    if low_prob:
        names = ", ".join(g.name for g in low_prob[:2])
        return (
            f"Based on your plan, {names} "
            f"{'are' if len(low_prob) > 1 else 'is'} below 70% confidence. "
            "I can run an optimization to suggest the smallest contribution "
            "increase that gets you back on track. Want me to model that?"
        )
    return (
        "Your plan looks healthy — all goals are above 70% confidence. "
        "Is there a specific goal or scenario you'd like me to stress-test?"
    )


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    result = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
    )
    goals = list(result.scalars().all())
    conversation_id = body.conversation_id or str(uuid.uuid4())

    client = _get_openai_client()
    reply: str | None = None
    if client is not None:
        goals_json = json.dumps(
            [
                {
                    "name": g.name,
                    "category": g.category,
                    "target_amount": g.target_amount,
                    "current_amount": g.current_amount,
                    "probability": g.probability,
                    "on_track": g.on_track,
                    "monthly_contribution": g.monthly_contribution,
                }
                for g in goals
            ],
            indent=2,
        )
        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT.format(goals_json=goals_json),
                    },
                    {"role": "user", "content": body.message},
                ],
                max_tokens=400,
                temperature=0.4,
            )
            reply = response.choices[0].message.content or ""
        except OpenAIError as exc:
            # Covers timeouts, rate limits, connection failures, and API
            # errors alike — the endpoint stays functional via the
            # rule-based fallback instead of surfacing a raw 500.
            logger.warning("copilot_openai_error user_id=%s error=%s", current_user.id, exc)

    if reply is None:
        reply = await _fallback_response(body.message, goals)

    return ChatResponse(reply=reply, conversation_id=conversation_id)
