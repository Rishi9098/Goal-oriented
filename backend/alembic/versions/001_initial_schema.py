"""Initial schema — users, goals, simulations

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE goal_category AS ENUM (
                'retirement','education','home','travel','wealth','emergency'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE risk_profile AS ENUM (
                'conservative','balanced','aggressive'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email           VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name       VARCHAR(255),
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name                 VARCHAR(255) NOT NULL,
            category             goal_category NOT NULL,
            target_amount        FLOAT NOT NULL,
            current_amount       FLOAT NOT NULL DEFAULT 0,
            target_date          DATE NOT NULL,
            monthly_contribution FLOAT NOT NULL DEFAULT 0,
            risk_profile         risk_profile NOT NULL DEFAULT 'balanced',
            priority             INTEGER NOT NULL DEFAULT 1,
            on_track             BOOLEAN NOT NULL DEFAULT TRUE,
            probability          FLOAT NOT NULL DEFAULT 0,
            is_active            BOOLEAN NOT NULL DEFAULT TRUE,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_goals_user_id ON goals(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            goal_id              UUID REFERENCES goals(id) ON DELETE CASCADE,
            num_simulations      INTEGER NOT NULL,
            initial_amount       FLOAT NOT NULL,
            monthly_contribution FLOAT NOT NULL,
            years_to_goal        FLOAT NOT NULL,
            risk_profile         VARCHAR(50) NOT NULL,
            success_rate         FLOAT NOT NULL,
            p10                  FLOAT NOT NULL,
            p25                  FLOAT NOT NULL,
            p50                  FLOAT NOT NULL,
            p75                  FLOAT NOT NULL,
            p90                  FLOAT NOT NULL,
            distribution         JSONB NOT NULL DEFAULT '{}',
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulations_user_id ON simulations(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulations_goal_id ON simulations(goal_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS simulations;")
    op.execute("DROP TABLE IF EXISTS goals;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP TYPE IF EXISTS goal_category;")
    op.execute("DROP TYPE IF EXISTS risk_profile;")
