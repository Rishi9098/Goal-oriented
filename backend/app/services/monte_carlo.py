"""
Monte Carlo simulation engine for goal-based financial planning.

Each simulation runs a path of monthly returns sampled from a log-normal
distribution parameterised by the chosen risk profile. The ensemble of
10 000 paths gives a probability distribution over terminal wealth.

CPU-bound work is offloaded to a thread pool via `run_simulation_async` so
it does not block the async event loop.
"""

import asyncio
from dataclasses import dataclass
from functools import partial

import numpy as np

# Annual return / volatility assumptions per risk profile
PROFILE_PARAMS: dict[str, dict[str, float]] = {
    "conservative": {"mu": 0.055, "sigma": 0.07},
    "balanced": {"mu": 0.075, "sigma": 0.12},
    "aggressive": {"mu": 0.095, "sigma": 0.18},
}

# Inflation rate applied to real-term comparisons
ANNUAL_INFLATION: float = 0.03


@dataclass
class SimulationResult:
    success_rate: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    distribution: dict[str, float]
    terminal_values: np.ndarray


def run_simulation(
    *,
    initial_amount: float,
    monthly_contribution: float,
    years_to_goal: float,
    risk_profile: str,
    target_amount: float,
    num_simulations: int = 10_000,
    seed: int | None = None,
) -> SimulationResult:
    """
    Run `num_simulations` Monte Carlo paths.

    Parameters
    ----------
    initial_amount : float
        Current savings toward the goal.
    monthly_contribution : float
        Constant monthly addition (assumed inflation-adjusted).
    years_to_goal : float
        Investment horizon in decimal years.
    risk_profile : str
        One of 'conservative', 'balanced', 'aggressive'.
    target_amount : float
        Dollar amount the goal requires at maturity.
    num_simulations : int
        Number of independent paths to simulate (default 10 000).
    seed : int | None
        Optional RNG seed for reproducibility.
    """
    params = PROFILE_PARAMS.get(risk_profile, PROFILE_PARAMS["balanced"])
    mu_annual = params["mu"]
    sigma_annual = params["sigma"]

    months = max(1, round(years_to_goal * 12))
    monthly_mu = mu_annual / 12
    monthly_sigma = sigma_annual / (12**0.5)

    rng = np.random.default_rng(seed)

    # Sample monthly log-returns: shape (num_simulations, months)
    log_returns = rng.normal(
        loc=monthly_mu - 0.5 * monthly_sigma**2,
        scale=monthly_sigma,
        size=(num_simulations, months),
    )
    monthly_returns = np.exp(log_returns)  # multiplicative returns

    # Compound portfolio value month by month
    portfolio = np.full(num_simulations, initial_amount, dtype=np.float64)
    for t in range(months):
        portfolio = portfolio * monthly_returns[:, t] + monthly_contribution

    terminal_values = portfolio

    # Success rate
    success_mask = terminal_values >= target_amount
    success_rate = float(success_mask.mean() * 100)

    # Percentiles
    p10, p25, p50, p75, p90 = np.percentile(terminal_values, [10, 25, 50, 75, 90])

    # Histogram for distribution chart (50 bins)
    counts, edges = np.histogram(terminal_values, bins=50)
    total = float(counts.sum())
    distribution: dict[str, float] = {
        f"{edges[i + 1]:.0f}": float(counts[i]) / total
        for i in range(len(counts))
    }

    return SimulationResult(
        success_rate=success_rate,
        p10=float(p10),
        p25=float(p25),
        p50=float(p50),
        p75=float(p75),
        p90=float(p90),
        distribution=distribution,
        terminal_values=terminal_values,
    )


def quick_probability(
    *,
    initial_amount: float,
    monthly_contribution: float,
    years_to_goal: float,
    risk_profile: str,
    target_amount: float,
) -> float:
    """Fast probability estimate using 2 000 simulations for inline updates."""
    result = run_simulation(
        initial_amount=initial_amount,
        monthly_contribution=monthly_contribution,
        years_to_goal=years_to_goal,
        risk_profile=risk_profile,
        target_amount=target_amount,
        num_simulations=2_000,
    )
    return result.success_rate


async def run_simulation_async(
    *,
    initial_amount: float,
    monthly_contribution: float,
    years_to_goal: float,
    risk_profile: str,
    target_amount: float,
    num_simulations: int = 10_000,
    seed: int | None = None,
) -> SimulationResult:
    """Async wrapper — runs `run_simulation` in the default thread pool so CPU
    work does not block the event loop."""
    fn = partial(
        run_simulation,
        initial_amount=initial_amount,
        monthly_contribution=monthly_contribution,
        years_to_goal=years_to_goal,
        risk_profile=risk_profile,
        target_amount=target_amount,
        num_simulations=num_simulations,
        seed=seed,
    )
    return await asyncio.get_running_loop().run_in_executor(None, fn)


async def quick_probability_async(
    *,
    initial_amount: float,
    monthly_contribution: float,
    years_to_goal: float,
    risk_profile: str,
    target_amount: float,
) -> float:
    """Async fast probability estimate — offloads NumPy work to thread pool."""
    fn = partial(
        quick_probability,
        initial_amount=initial_amount,
        monthly_contribution=monthly_contribution,
        years_to_goal=years_to_goal,
        risk_profile=risk_profile,
        target_amount=target_amount,
    )
    return await asyncio.get_running_loop().run_in_executor(None, fn)
