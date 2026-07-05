"""
Dev-only seed data: one demo user with a couple of goals and a basic
financial picture, so the dashboard/goals/reports pages have something to
show right after setup. Idempotent — re-running skips creation if the demo
user already exists.

Invoked via the repo-root scripts/seed.sh, never imported by the app itself.
"""

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.financials import Asset, Expense, IncomeSource, Liability
from app.models.goal import Goal
from app.models.user import User
from app.services.auth_service import hash_password

DEMO_EMAIL = "demo@northstar.app"
DEMO_PASSWORD = "DemoPass123!"


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Demo user {DEMO_EMAIL!r} already exists — nothing to do.")
            return

        user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Demo User",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        today = date.today()
        session.add_all(
            [
                Goal(
                    user_id=user.id,
                    name="Retirement",
                    category="retirement",
                    target_amount=1_500_000,
                    current_amount=180_000,
                    target_date=today + timedelta(days=365 * 25),
                    monthly_contribution=1_200,
                    risk_profile="balanced",
                    priority=1,
                ),
                Goal(
                    user_id=user.id,
                    name="Emergency Fund",
                    category="emergency",
                    target_amount=30_000,
                    current_amount=12_000,
                    target_date=today + timedelta(days=365 * 2),
                    monthly_contribution=400,
                    risk_profile="conservative",
                    priority=2,
                ),
                Goal(
                    user_id=user.id,
                    name="Home Down Payment",
                    category="home",
                    target_amount=100_000,
                    current_amount=22_000,
                    target_date=today + timedelta(days=365 * 5),
                    monthly_contribution=900,
                    risk_profile="balanced",
                    priority=3,
                ),
                IncomeSource(
                    user_id=user.id,
                    source_type="salary",
                    description="Day job",
                    annual_amount=120_000,
                ),
                Expense(
                    user_id=user.id, category="housing", description="Rent", monthly_amount=2_400
                ),
                Expense(
                    user_id=user.id,
                    category="food",
                    description="Groceries + dining",
                    monthly_amount=650,
                ),
                Asset(
                    user_id=user.id,
                    asset_type="checking",
                    institution="Demo Bank",
                    current_value=15_000,
                ),
                Asset(
                    user_id=user.id,
                    asset_type="brokerage",
                    institution="Demo Invest",
                    current_value=95_000,
                ),
                Liability(
                    user_id=user.id,
                    liability_type="student_loan",
                    balance=18_000,
                    interest_rate=0.045,
                    monthly_payment=250,
                ),
            ]
        )
        await session.commit()

    print(f"Seeded demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
