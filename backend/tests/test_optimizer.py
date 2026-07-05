"""Unit tests for the optimization engine."""

import pytest

from app.services.optimizer import GoalSnapshot, generate_suggestions


class TestGenerateSuggestions:
    BASE_SNAPSHOT = GoalSnapshot(
        initial_amount=50_000,
        monthly_contribution=500,
        years_to_goal=10,
        risk_profile="conservative",
        target_amount=200_000,
        current_probability=45.0,
    )

    def test_returns_at_least_one_suggestion(self):
        suggestions = generate_suggestions(self.BASE_SNAPSHOT, target_probability=80.0)
        assert len(suggestions) >= 1

    def test_returns_at_most_five_suggestions(self):
        suggestions = generate_suggestions(self.BASE_SNAPSHOT, target_probability=80.0)
        assert len(suggestions) <= 5

    def test_suggestions_sorted_by_probability_descending(self):
        suggestions = generate_suggestions(self.BASE_SNAPSHOT)
        probs = [s.projected_probability for s in suggestions]
        assert probs == sorted(probs, reverse=True)

    def test_all_suggestions_have_descriptions(self):
        for s in generate_suggestions(self.BASE_SNAPSHOT):
            assert s.description
            assert s.impact_summary

    def test_no_risk_adjustment_when_disabled(self):
        suggestions = generate_suggestions(
            self.BASE_SNAPSHOT, allow_risk_adjustment=False
        )
        for s in suggestions:
            assert s.risk_profile_change is None

    def test_aggressive_profile_cannot_go_higher(self):
        snap = GoalSnapshot(
            **{**self.BASE_SNAPSHOT.__dict__, "risk_profile": "aggressive"}
        )
        suggestions = generate_suggestions(snap, allow_risk_adjustment=True)
        # No suggestion should try to go above aggressive
        for s in suggestions:
            assert s.risk_profile_change != "super_aggressive"

    def test_max_monthly_increase_respected(self):
        suggestions = generate_suggestions(
            self.BASE_SNAPSHOT, max_monthly_increase=50.0
        )
        for s in suggestions:
            assert s.monthly_contribution_delta <= 50.0
