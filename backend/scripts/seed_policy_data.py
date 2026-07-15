"""
Government Policy Engine reference-data seed.

Unlike scripts/seed_data.py (a dev-only demo user), this seeds real
reference data every environment needs to function correctly — the app has
no fallback for missing scheme/tax data, so this should run in every
environment, including production, not just local dev.

Every figure below was independently verified via live web search in
GovernmentPolicyReport.md (2026-07-06) and is cited with its source. This
script deliberately does NOT seed:
  - The old tax regime's slab structure beyond its ₹2.5L basic exemption —
    GovernmentPolicyReport.md verified only the exemption threshold, not the
    full old-regime slab breakdown. Seeding fabricated slab boundaries would
    violate this project's "never invent financial policies" rule.
  - Section 80CCD(1B)'s mapping under the new Income-tax Act, 2025 — flagged
    in GovernmentPolicyReport.md as "not yet independently verified."
  - Section 80D's senior-citizen-enhanced ₹50,000 tier — this is an
    age-conditional limit the current schema's single-limit-per-TaxSection
    shape doesn't cleanly represent; seeding it as an unconditional second
    row would misrepresent it as unconditional.
  - SCSS's two special-case eligibility routes verified in
    GovernmentPolicyReport.md ("55+ if retired under superannuation/VRS",
    "retired defense personnel 50+") — this app captures no field anywhere
    (household_members, dependents, user_profiles) recording retirement or
    defense-service status, so a rule for either fact could never be
    evaluated. Only the base "60+" case is seeded. See
    Milestone2ImplementationContract.md Task 3 / DesignReview.md for the
    full reasoning — this is a documented gap, not an oversight.

Idempotent — re-running skips any scheme whose code already exists.

Milestone 2 Task 3 addition (2026-07-06): seeds `scheme_eligibility_rules`,
which Milestone 1's original seed pass never populated (the table existed
but had zero rows — see DependencyValidationReport.md). Only two rules are
seeded, both directly quoting GovernmentPolicyReport.md:
  - SSY: "Girl child must be under 10 at account opening" -> max_age < 10
  - SCSS: "Individuals 60+" (base case only) -> min_age >= 60
"""

import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.policy import (
    Scheme,
    SchemeEligibilityRule,
    SchemeRate,
    TaxAct,
    TaxRegime,
    TaxSection,
    TaxSlab,
)

_VERIFIED_AT = datetime(2026, 7, 6, tzinfo=UTC)

# (code, name, governing_authority, status, category)
_SCHEMES: list[tuple[str, str, str, str, str]] = [
    ("PPF", "Public Provident Fund", "Ministry of Finance / RBI", "active", "general_savings"),
    ("EPF", "Employees' Provident Fund", "EPFO", "active", "retirement"),
    ("NPS", "National Pension System", "PFRDA", "active", "retirement"),
    ("SSY", "Sukanya Samriddhi Yojana", "Ministry of Finance", "active", "child"),
    ("SCSS", "Senior Citizens' Savings Scheme", "Ministry of Finance", "active", "senior"),
    ("NSC", "National Savings Certificate", "Ministry of Finance", "active", "general_savings"),
    ("KVP", "Kisan Vikas Patra", "Ministry of Finance", "active", "general_savings"),
    ("APY", "Atal Pension Yojana", "PFRDA", "active", "retirement"),
    (
        "PMVVY",
        "Pradhan Mantri Vaya Vandana Yojana",
        "LIC / Ministry of Finance",
        "closed_to_new",
        "senior",
    ),
]

# (scheme_code, field_name, value, effective_from, source_citation)
_SCHEME_RATES: list[tuple[str, str, float, date, str]] = [
    (
        "PPF", "interest_rate", 7.1, date(2026, 4, 1),
        "Bajaj Finserv PPF Interest Rate 2026-27; ClearTax PPF — verified 2026-07-06",
    ),
    ("PPF", "min_contribution", 500.0, date(2026, 4, 1), "ClearTax PPF — verified 2026-07-06"),
    ("PPF", "max_contribution", 150_000.0, date(2026, 4, 1), "ClearTax PPF — verified 2026-07-06"),
    (
        "EPF", "interest_rate", 8.25, date(2025, 4, 1),
        "ClearTax EPF Interest Rate; Bajaj Finserv EPF Interest Rate — "
        "verified 2026-07-06 (FY 2025-26; FY 2026-27 rate not yet announced)",
    ),
    (
        "SSY", "interest_rate", 8.2, date(2026, 4, 1),
        "ClearTax SSY; BankBazaar SSY — verified 2026-07-06 (Q1 FY 2026-27)",
    ),
    ("SSY", "min_contribution", 250.0, date(2026, 4, 1), "ClearTax SSY — verified 2026-07-06"),
    ("SSY", "max_contribution", 150_000.0, date(2026, 4, 1), "ClearTax SSY — verified 2026-07-06"),
    (
        "SCSS", "interest_rate", 8.2, date(2026, 7, 1),
        "Upstox — SCSS Jul-Sep 2026 — verified 2026-07-06",
    ),
    ("SCSS", "min_contribution", 1_000.0, date(2026, 4, 1), "ClearTax SCSS — verified 2026-07-06"),
    (
        "SCSS", "max_contribution", 3_000_000.0, date(2026, 4, 1),
        "ClearTax SCSS — verified 2026-07-06",
    ),
    ("NSC", "interest_rate", 7.7, date(2026, 4, 1), "ClearTax NSC — verified 2026-07-06"),
    ("KVP", "interest_rate", 7.5, date(2026, 4, 1), "ClearTax KVP — verified 2026-07-06"),
    (
        "PMVVY", "interest_rate", 7.4, date(2016, 1, 1),
        "Right to Information Wiki / BankBazaar PMVVY — verified 2026-07-06 "
        "(legacy locked-in rate for existing policyholders only; "
        "closed to new subscriptions since 2023-03-31)",
    ),
]

# (scheme_code, rule_type, operator, value, effective_from)
# operator convention matches SchemeEligibilityRule's own docstring: eq/gte/lte/in.
# Citations for each row (not a column on this table): SSY —
# GovernmentPolicyReport.md "Resident parent/legal guardian of a girl child
# under 10" (both the age and gender clauses are separately verified facts,
# seeded as two rules rather than folding "girl child" into one rule, so the
# evaluation service stays data-driven — it never hardcodes "SSY is
# girls-only" itself, it just checks whatever rules exist for the scheme);
# SCSS — GovernmentPolicyReport.md "Individuals 60+" (base case only; see
# module docstring for the deliberately-unseeded 55+/50+ special cases).
_SCHEME_ELIGIBILITY_RULES: list[tuple[str, str, str, str, date]] = [
    ("SSY", "max_age", "lt", "10", date(2015, 1, 1)),
    ("SSY", "gender", "eq", "female", date(2015, 1, 1)),
    ("SCSS", "min_age", "gte", "60", date(2004, 1, 1)),
]

_TAX_ACTS: list[tuple[str, date, date | None]] = [
    ("Income-tax Act, 1961", date(1962, 4, 1), date(2026, 3, 31)),
    ("Income-tax Act, 2025", date(2026, 4, 1), None),
]

# (act_name, section_number, purpose, limit_amount, effective_from, effective_to)
_TAX_SECTIONS: list[tuple[str, str, str, float | None, date, date | None]] = [
    (
        "Income-tax Act, 1961", "80C", "general_savings_deduction", 150_000.0,
        date(1962, 4, 1), date(2026, 3, 31),
    ),
    (
        "Income-tax Act, 2025", "123", "general_savings_deduction", 150_000.0,
        date(2026, 4, 1), None,
    ),
    (
        "Income-tax Act, 1961", "80CCD(1B)", "nps_additional_deduction", 50_000.0,
        date(1962, 4, 1), date(2026, 3, 31),
    ),
    (
        "Income-tax Act, 1961", "80D", "health_insurance_premium_deduction", 25_000.0,
        date(1962, 4, 1), date(2026, 3, 31),
    ),
]

# New-regime slabs, Tax Year 2026-27 — fully verified table.
_NEW_REGIME_SLABS: list[tuple[float, float | None, float]] = [
    (0.0, 400_000.0, 0.0),
    (400_000.0, 800_000.0, 5.0),
    (800_000.0, 1_200_000.0, 10.0),
    (1_200_000.0, 1_600_000.0, 15.0),
    (1_600_000.0, 2_000_000.0, 20.0),
    (2_000_000.0, 2_400_000.0, 25.0),
    (2_400_000.0, None, 30.0),
]

# Old regime — ONLY the verified basic exemption. Remaining brackets are
# intentionally not seeded; see module docstring.
_OLD_REGIME_SLABS: list[tuple[float, float | None, float]] = [
    (0.0, 250_000.0, 0.0),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        scheme_by_code: dict[str, Scheme] = {}
        for code, name, authority, status, category in _SCHEMES:
            existing = await session.execute(select(Scheme).where(Scheme.code == code))
            scheme = existing.scalar_one_or_none()
            if scheme is None:
                scheme = Scheme(
                    code=code,
                    name=name,
                    governing_authority=authority,
                    status=status,
                    category=category,
                )
                session.add(scheme)
                await session.flush()
            scheme_by_code[code] = scheme

        for code, field_name, value, effective_from, citation in _SCHEME_RATES:
            existing_rate = await session.execute(
                select(SchemeRate).where(
                    SchemeRate.scheme_id == scheme_by_code[code].id,
                    SchemeRate.field_name == field_name,
                    SchemeRate.effective_from == effective_from,
                )
            )
            if existing_rate.scalar_one_or_none() is None:
                session.add(
                    SchemeRate(
                        scheme_id=scheme_by_code[code].id,
                        field_name=field_name,
                        value=value,
                        effective_from=effective_from,
                        source_citation=citation,
                    )
                )

        for code, rule_type, operator, rule_value, eff_from_rule in _SCHEME_ELIGIBILITY_RULES:
            existing_rule = await session.execute(
                select(SchemeEligibilityRule).where(
                    SchemeEligibilityRule.scheme_id == scheme_by_code[code].id,
                    SchemeEligibilityRule.rule_type == rule_type,
                )
            )
            if existing_rule.scalar_one_or_none() is None:
                session.add(
                    SchemeEligibilityRule(
                        scheme_id=scheme_by_code[code].id,
                        rule_type=rule_type,
                        operator=operator,
                        value=rule_value,
                        effective_from=eff_from_rule,
                    )
                )

        act_by_name: dict[str, TaxAct] = {}
        for name, effective_from, effective_to in _TAX_ACTS:
            existing_act = await session.execute(select(TaxAct).where(TaxAct.name == name))
            act = existing_act.scalar_one_or_none()
            if act is None:
                act = TaxAct(name=name, effective_from=effective_from, effective_to=effective_to)
                session.add(act)
                await session.flush()
            act_by_name[name] = act

        for act_name, section_number, purpose, limit_amount, eff_from, eff_to in _TAX_SECTIONS:
            existing_section = await session.execute(
                select(TaxSection).where(
                    TaxSection.tax_act_id == act_by_name[act_name].id,
                    TaxSection.section_number == section_number,
                )
            )
            if existing_section.scalar_one_or_none() is None:
                session.add(
                    TaxSection(
                        tax_act_id=act_by_name[act_name].id,
                        section_number=section_number,
                        purpose=purpose,
                        limit_amount=limit_amount,
                        effective_from=eff_from,
                        effective_to=eff_to,
                    )
                )

        regime_by_name: dict[str, TaxRegime] = {}
        for regime_name, slabs in (("new", _NEW_REGIME_SLABS), ("old", _OLD_REGIME_SLABS)):
            existing_regime = await session.execute(
                select(TaxRegime).where(TaxRegime.name == regime_name)
            )
            regime = existing_regime.scalar_one_or_none()
            if regime is None:
                regime = TaxRegime(name=regime_name, effective_from=date(2026, 4, 1))
                session.add(regime)
                await session.flush()
            regime_by_name[regime_name] = regime

            for income_from, income_to, rate_percent in slabs:
                existing_slab = await session.execute(
                    select(TaxSlab).where(
                        TaxSlab.tax_regime_id == regime.id,
                        TaxSlab.income_from == income_from,
                    )
                )
                if existing_slab.scalar_one_or_none() is None:
                    session.add(
                        TaxSlab(
                            tax_regime_id=regime.id,
                            income_from=income_from,
                            income_to=income_to,
                            rate_percent=rate_percent,
                            effective_from=date(2026, 4, 1),
                        )
                    )

        await session.commit()
        print(
            f"Seeded {len(_SCHEMES)} schemes, {len(_SCHEME_RATES)} scheme rates, "
            f"{len(_SCHEME_ELIGIBILITY_RULES)} scheme eligibility rules, "
            f"{len(_TAX_ACTS)} tax acts, {len(_TAX_SECTIONS)} tax sections, "
            f"{len(_NEW_REGIME_SLABS) + len(_OLD_REGIME_SLABS)} tax slabs "
            "(idempotent — existing rows left untouched)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
