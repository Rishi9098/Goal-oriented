# Database Reference

## Engine

PostgreSQL 16. All connections go through asyncpg via SQLAlchemy's async session.

## Schema

### `users`

| Column           | Type                  | Constraints              |
|------------------|-----------------------|--------------------------|
| id               | UUID (PK)             | default uuid_generate_v4 |
| email            | VARCHAR(255)          | UNIQUE NOT NULL          |
| hashed_password  | VARCHAR(255)          | NOT NULL                 |
| full_name        | VARCHAR(255)          | nullable                 |
| is_active        | BOOLEAN               | NOT NULL default true    |
| is_verified      | BOOLEAN               | NOT NULL default false   |
| created_at       | TIMESTAMPTZ           | NOT NULL default now()   |
| updated_at       | TIMESTAMPTZ           | NOT NULL default now()   |

Index: `ix_users_email` on `email`.

### `goals`

| Column               | Type                          | Constraints                     |
|----------------------|-------------------------------|----------------------------------|
| id                   | UUID (PK)                     | default uuid_generate_v4        |
| user_id              | UUID (FK → users.id CASCADE)  | NOT NULL                        |
| name                 | VARCHAR(255)                  | NOT NULL                        |
| category             | ENUM goal_category            | NOT NULL                        |
| target_amount        | FLOAT                         | NOT NULL                        |
| current_amount       | FLOAT                         | NOT NULL default 0              |
| target_date          | DATE                          | NOT NULL                        |
| monthly_contribution | FLOAT                         | NOT NULL default 0              |
| risk_profile         | ENUM risk_profile             | NOT NULL default 'balanced'     |
| priority             | INTEGER                       | NOT NULL default 1              |
| on_track             | BOOLEAN                       | NOT NULL default true           |
| probability          | FLOAT                         | NOT NULL default 0              |
| is_active            | BOOLEAN                       | NOT NULL default true           |
| created_at           | TIMESTAMPTZ                   | NOT NULL default now()          |
| updated_at           | TIMESTAMPTZ                   | NOT NULL default now()          |

Indexes: `ix_goals_user_id`.

**Enum `goal_category`:** `retirement` | `education` | `home` | `travel` | `wealth` | `emergency`

**Enum `risk_profile`:** `conservative` | `balanced` | `aggressive`

### `simulations`

| Column               | Type                           | Constraints                       |
|----------------------|--------------------------------|-----------------------------------|
| id                   | UUID (PK)                      | default uuid_generate_v4         |
| user_id              | UUID (FK → users.id CASCADE)   | NOT NULL                         |
| goal_id              | UUID (FK → goals.id CASCADE)   | nullable                         |
| num_simulations      | INTEGER                        | NOT NULL                         |
| initial_amount       | FLOAT                          | NOT NULL                         |
| monthly_contribution | FLOAT                          | NOT NULL                         |
| years_to_goal        | FLOAT                          | NOT NULL                         |
| risk_profile         | VARCHAR(50)                    | NOT NULL                         |
| success_rate         | FLOAT                          | NOT NULL                         |
| p10                  | FLOAT                          | NOT NULL                         |
| p25                  | FLOAT                          | NOT NULL                         |
| p50                  | FLOAT                          | NOT NULL                         |
| p75                  | FLOAT                          | NOT NULL                         |
| p90                  | FLOAT                          | NOT NULL                         |
| distribution         | JSONB                          | NOT NULL default '{}'            |
| created_at           | TIMESTAMPTZ                    | NOT NULL default now()           |

Indexes: `ix_simulations_user_id`, `ix_simulations_goal_id`.

## Relationships

```
users ──< goals ──< simulations
users ──< simulations
```

- A user owns many goals (1:N, cascade delete)
- A goal owns many simulations (1:N, cascade delete)
- A simulation may belong to a user without a specific goal (for ad-hoc what-if runs)

## Migrations

Migrations are managed by Alembic. All schema changes must be expressed as Alembic revisions.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after changing a model
alembic revision --autogenerate -m "add risk_tolerance column"

# Roll back one step
alembic downgrade -1

# Show migration history
alembic history --verbose
```

Never modify the database schema manually in production.

## Soft Delete Pattern

Goals are never hard-deleted. Setting `is_active = false` hides a goal from all API responses while preserving simulation history. This avoids FK violations and supports undo.

## Connection Pooling

Production pool settings (configurable via `.env`):

| Setting              | Default |
|----------------------|---------|
| pool_size            | 10      |
| max_overflow         | 20      |

Total max connections: 30 per application instance.

## Backup

Recommended: `pg_dump` to S3 nightly with point-in-time recovery enabled on managed PostgreSQL (e.g. AWS RDS, Supabase).

```bash
pg_dump -Fc northstar > northstar_$(date +%Y%m%d).dump
```
