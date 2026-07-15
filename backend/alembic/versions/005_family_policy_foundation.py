"""Family, Household, Government Policy Engine, Estate/Nominee, Insurance,
Recommendation, and Audit foundation tables

Revision ID: 005
Revises: 004
Create Date: 2026-07-06 00:00:00.000000

Purely additive: creates 20 new tables, touches zero existing tables or
columns. Existing users, goals, financials, simulations, and auth flows are
unaffected — this migration has no effect on any currently-running feature.

Table groups (see DatabaseDesignReport.md for full rationale):
  - Household/Family: households, household_members, dependents
  - Government Policy Engine: schemes, scheme_rates, scheme_eligibility_rules,
    tax_acts, tax_sections, tax_regimes, tax_slabs, policy_citations
  - Estate/Nominee: huf_entities, huf_coparceners, nominees, estate_documents
  - Insurance: health_policies, health_policy_coverage
  - Recommendation: recommendations, recommendation_citations
  - Audit: audit_logs
"""

from collections.abc import Sequence

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Household / Family ───────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS households (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name               VARCHAR(255) NOT NULL,
            created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_active          BOOLEAN NOT NULL DEFAULT TRUE,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_households_created_by_user_id "
        "ON households(created_by_user_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS household_members (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id      UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            user_id           UUID REFERENCES users(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            role              VARCHAR(20) NOT NULL DEFAULT 'member',
            is_active         BOOLEAN NOT NULL DEFAULT TRUE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_household_members_household_id "
        "ON household_members(household_id, is_active);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_household_members_user_id "
        "ON household_members(user_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS dependents (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_member_id  UUID NOT NULL UNIQUE
                                 REFERENCES household_members(id) ON DELETE CASCADE,
            date_of_birth        DATE,
            dependent_type       VARCHAR(50) NOT NULL,
            is_tax_dependent     BOOLEAN NOT NULL DEFAULT FALSE,
            is_active            BOOLEAN NOT NULL DEFAULT TRUE,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # ── Government Policy Engine ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code                 VARCHAR(20) NOT NULL UNIQUE,
            name                 VARCHAR(255) NOT NULL,
            governing_authority  VARCHAR(255) NOT NULL,
            status               VARCHAR(20) NOT NULL DEFAULT 'active',
            category             VARCHAR(50) NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_schemes_code ON schemes(code);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheme_rates (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scheme_id        UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
            field_name       VARCHAR(50) NOT NULL,
            value            FLOAT NOT NULL,
            effective_from   DATE NOT NULL,
            effective_to     DATE,
            source_citation  TEXT NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scheme_rates_lookup "
        "ON scheme_rates(scheme_id, field_name, effective_from, effective_to);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheme_eligibility_rules (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scheme_id       UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
            rule_type       VARCHAR(50) NOT NULL,
            operator        VARCHAR(10) NOT NULL,
            value           VARCHAR(255) NOT NULL,
            effective_from  DATE NOT NULL,
            effective_to    DATE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scheme_eligibility_rules_scheme_id "
        "ON scheme_eligibility_rules(scheme_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS tax_acts (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(255) NOT NULL,
            effective_from  DATE NOT NULL,
            effective_to    DATE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tax_sections (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tax_act_id      UUID NOT NULL REFERENCES tax_acts(id) ON DELETE CASCADE,
            section_number  VARCHAR(20) NOT NULL,
            purpose         VARCHAR(255) NOT NULL,
            limit_amount    FLOAT,
            effective_from  DATE NOT NULL,
            effective_to    DATE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tax_sections_tax_act_id ON tax_sections(tax_act_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS tax_regimes (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            VARCHAR(20) NOT NULL,
            effective_from  DATE NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tax_slabs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tax_regime_id   UUID NOT NULL REFERENCES tax_regimes(id) ON DELETE CASCADE,
            income_from     FLOAT NOT NULL,
            income_to       FLOAT,
            rate_percent    FLOAT NOT NULL,
            effective_from  DATE NOT NULL,
            effective_to    DATE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tax_slabs_tax_regime_id ON tax_slabs(tax_regime_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS policy_citations (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scheme_id        UUID REFERENCES schemes(id) ON DELETE CASCADE,
            tax_section_id   UUID REFERENCES tax_sections(id) ON DELETE CASCADE,
            citation_text    TEXT NOT NULL,
            source_url       VARCHAR(500) NOT NULL,
            verified_at      TIMESTAMPTZ NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policy_citations_scheme_id ON policy_citations(scheme_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policy_citations_tax_section_id "
        "ON policy_citations(tax_section_id);"
    )

    # ── Estate / Nominee ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS huf_entities (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            karta_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            huf_pan          VARCHAR(10) UNIQUE,
            formation_date   DATE,
            funding_source   VARCHAR(50) NOT NULL,
            is_active        BOOLEAN NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_huf_entities_karta_user_id ON huf_entities(karta_user_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS huf_coparceners (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            huf_entity_id            UUID NOT NULL REFERENCES huf_entities(id) ON DELETE CASCADE,
            household_member_id      UUID NOT NULL
                                     REFERENCES household_members(id) ON DELETE CASCADE,
            became_coparcener_date   DATE,
            is_active                BOOLEAN NOT NULL DEFAULT TRUE,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_huf_coparceners_huf_entity_id "
        "ON huf_coparceners(huf_entity_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_huf_coparceners_household_member_id "
        "ON huf_coparceners(household_member_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS nominees (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            asset_id               UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            name                   VARCHAR(255) NOT NULL,
            relationship_type      VARCHAR(50) NOT NULL,
            percentage_share       FLOAT NOT NULL,
            nominee_date_of_birth  DATE,
            opted_out              BOOLEAN NOT NULL DEFAULT FALSE,
            is_active              BOOLEAN NOT NULL DEFAULT TRUE,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_nominees_percentage_share_range
                CHECK (percentage_share > 0 AND percentage_share <= 100)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_nominees_asset_id ON nominees(asset_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS estate_documents (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            document_type  VARCHAR(50) NOT NULL,
            status         VARCHAR(20) NOT NULL DEFAULT 'not_started',
            last_updated   DATE,
            is_active      BOOLEAN NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_estate_documents_user_id ON estate_documents(user_id);"
    )

    # ── Insurance ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS health_policies (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            primary_holder_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            policy_type            VARCHAR(30) NOT NULL,
            sum_insured            FLOAT NOT NULL,
            annual_premium         FLOAT NOT NULL,
            insurer                VARCHAR(255),
            is_active              BOOLEAN NOT NULL DEFAULT TRUE,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_health_policies_primary_holder_user_id "
        "ON health_policies(primary_holder_user_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS health_policy_coverage (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            health_policy_id      UUID NOT NULL REFERENCES health_policies(id) ON DELETE CASCADE,
            household_member_id   UUID NOT NULL
                                  REFERENCES household_members(id) ON DELETE CASCADE,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_health_policy_coverage_health_policy_id "
        "ON health_policy_coverage(health_policy_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_health_policy_coverage_household_member_id "
        "ON health_policy_coverage(household_member_id);"
    )

    # ── Recommendation ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            recommendation_type      VARCHAR(50) NOT NULL,
            reasoning                TEXT NOT NULL,
            confidence_score         FLOAT NOT NULL,
            alternatives_considered  JSON,
            assumptions_used         JSON,
            generated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendations_user_id ON recommendations(user_id);"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_citations (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recommendation_id  UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
            scheme_id          UUID REFERENCES schemes(id) ON DELETE CASCADE,
            tax_section_id     UUID REFERENCES tax_sections(id) ON DELETE CASCADE,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendation_citations_recommendation_id "
        "ON recommendation_citations(recommendation_id);"
    )

    # ── Audit ─────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            action        VARCHAR(100) NOT NULL,
            before_state  JSON,
            after_state   JSON,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id_created_at "
        "ON audit_logs(user_id, created_at);"
    )


def downgrade() -> None:
    # Reverse FK dependency order.
    op.execute("DROP TABLE IF EXISTS audit_logs;")
    op.execute("DROP TABLE IF EXISTS recommendation_citations;")
    op.execute("DROP TABLE IF EXISTS recommendations;")
    op.execute("DROP TABLE IF EXISTS health_policy_coverage;")
    op.execute("DROP TABLE IF EXISTS health_policies;")
    op.execute("DROP TABLE IF EXISTS estate_documents;")
    op.execute("DROP TABLE IF EXISTS nominees;")
    op.execute("DROP TABLE IF EXISTS huf_coparceners;")
    op.execute("DROP TABLE IF EXISTS huf_entities;")
    op.execute("DROP TABLE IF EXISTS policy_citations;")
    op.execute("DROP TABLE IF EXISTS tax_slabs;")
    op.execute("DROP TABLE IF EXISTS tax_regimes;")
    op.execute("DROP TABLE IF EXISTS tax_sections;")
    op.execute("DROP TABLE IF EXISTS tax_acts;")
    op.execute("DROP TABLE IF EXISTS scheme_eligibility_rules;")
    op.execute("DROP TABLE IF EXISTS scheme_rates;")
    op.execute("DROP TABLE IF EXISTS schemes;")
    op.execute("DROP TABLE IF EXISTS dependents;")
    op.execute("DROP TABLE IF EXISTS household_members;")
    op.execute("DROP TABLE IF EXISTS households;")
