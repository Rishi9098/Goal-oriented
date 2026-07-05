"""Unit tests for the Monte Carlo simulation engine."""

import pytest

from app.services.monte_carlo import PROFILE_PARAMS, run_simulation


class TestRunSimulation:
    BASE_PARAMS = {
        "initial_amount": 100_000.0,
        "monthly_contribution": 1_000.0,
        "years_to_goal": 20.0,
        "risk_profile": "balanced",
        "target_amount": 500_000.0,
        "num_simulations": 2_000,
        "seed": 42,
    }

    def test_returns_success_rate_in_valid_range(self):
        result = run_simulation(**self.BASE_PARAMS)
        assert 0.0 <= result.success_rate <= 100.0

    def test_percentile_ordering(self):
        result = run_simulation(**self.BASE_PARAMS)
        assert result.p10 <= result.p25 <= result.p50 <= result.p75 <= result.p90

    def test_all_risk_profiles_produce_valid_output(self):
        for profile in PROFILE_PARAMS:
            result = run_simulation(**{**self.BASE_PARAMS, "risk_profile": profile})
            assert result.success_rate >= 0

    def test_higher_risk_produces_wider_distribution(self):
        conservative = run_simulation(**{**self.BASE_PARAMS, "risk_profile": "conservative"})
        aggressive = run_simulation(**{**self.BASE_PARAMS, "risk_profile": "aggressive"})
        spread_c = conservative.p90 - conservative.p10
        spread_a = aggressive.p90 - aggressive.p10
        assert spread_a > spread_c, "Aggressive should have wider spread"

    def test_more_contribution_increases_success_rate(self):
        low = run_simulation(**{**self.BASE_PARAMS, "monthly_contribution": 100})
        high = run_simulation(**{**self.BASE_PARAMS, "monthly_contribution": 5_000})
        assert high.success_rate >= low.success_rate

    def test_longer_horizon_increases_success_rate(self):
        short = run_simulation(**{**self.BASE_PARAMS, "years_to_goal": 5})
        long_ = run_simulation(**{**self.BASE_PARAMS, "years_to_goal": 30})
        assert long_.success_rate >= short.success_rate

    def test_distribution_probabilities_sum_to_one(self):
        result = run_simulation(**self.BASE_PARAMS)
        total = sum(result.distribution.values())
        assert abs(total - 1.0) < 1e-6

    def test_seed_produces_reproducible_results(self):
        r1 = run_simulation(**{**self.BASE_PARAMS, "seed": 99})
        r2 = run_simulation(**{**self.BASE_PARAMS, "seed": 99})
        assert r1.success_rate == r2.success_rate
        assert r1.p50 == r2.p50

    def test_certain_success_high_contribution(self):
        """Very high contribution relative to target should approach 100%."""
        result = run_simulation(
            initial_amount=1_000_000.0,
            monthly_contribution=50_000.0,
            years_to_goal=20.0,
            risk_profile="conservative",
            target_amount=500_000.0,
            num_simulations=1_000,
            seed=0,
        )
        assert result.success_rate > 95.0

    def test_near_zero_success_impossible_goal(self):
        """Impossibly large target with minimal savings should be near 0%."""
        result = run_simulation(
            initial_amount=1_000.0,
            monthly_contribution=10.0,
            years_to_goal=1.0,
            risk_profile="conservative",
            target_amount=1_000_000_000.0,
            num_simulations=1_000,
            seed=0,
        )
        assert result.success_rate < 5.0
