"""Financial profile tables — user_profiles, income_sources, expenses, assets, liabilities, financial_assumptions

Revision ID: 002
Revises: 001
Create Date: 2026-06-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            date_of_birth       DATE,
            gender              VARCHAR(50),
            marital_status      VARCHAR(50),
            dependents          INTEGER NOT NULL DEFAULT 0,
            country             VARCHAR(100),
            state_province      VARCHAR(100),
            employment_status   VARCHAR(50),
            employer            VARCHAR(255),
            occupation          VARCHAR(255),
            onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
            current_step        INTEGER NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS income_sources (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source_type    VARCHAR(50) NOT NULL,
            description    VARCHAR(255),
            annual_amount  FLOAT NOT NULL,
            is_active      BOOLEAN NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_income_sources_user_id ON income_sources(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category        VARCHAR(50) NOT NULL,
            description     VARCHAR(255),
            monthly_amount  FLOAT NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_user_id ON expenses(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            asset_type    VARCHAR(50) NOT NULL,
            institution   VARCHAR(255),
            description   VARCHAR(255),
            current_value FLOAT NOT NULL,
            is_active     BOOLEAN NOT NULL DEFAULT TRUE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_assets_user_id ON assets(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS liabilities (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            liability_type  VARCHAR(50) NOT NULL,
            institution     VARCHAR(255),
            description     VARCHAR(255),
            balance         FLOAT NOT NULL,
            interest_rate   FLOAT,
            monthly_payment FLOAT NOT NULL DEFAULT 0,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_liabilities_user_id ON liabilities(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS financial_assumptions (
            id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                         UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            inflation_rate                  FLOAT NOT NULL DEFAULT 0.03,
            expected_return_conservative    FLOAT NOT NULL DEFAULT 0.05,
            expected_return_balanced        FLOAT NOT NULL DEFAULT 0.07,
            expected_return_aggressive      FLOAT NOT NULL DEFAULT 0.09,
            tax_rate                        FLOAT NOT NULL DEFAULT 0.22,
            retirement_age                  INTEGER NOT NULL DEFAULT 65,
            social_security_monthly         FLOAT NOT NULL DEFAULT 0,
            created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_financial_assumptions_user_id ON financial_assumptions(user_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS financial_assumptions;")
    op.execute("DROP TABLE IF EXISTS liabilities;")
    op.execute("DROP TABLE IF EXISTS assets;")
    op.execute("DROP TABLE IF EXISTS expenses;")
    op.execute("DROP TABLE IF EXISTS income_sources;")
    op.execute("DROP TABLE IF EXISTS user_profiles;")
