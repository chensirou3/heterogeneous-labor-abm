"""
Exogenous environment path for the Labor Market ABM.
Provides vacancy rate, layoff shock, and wage offer distribution
that are shared across all three models.

In production: loaded from BLS API (JOLTS + CPS).
For MVP: generates a plausible synthetic path based on stylized facts.
"""
import numpy as np
from dataclasses import dataclass
from models.config import TOTAL_MONTHS


@dataclass
class EnvironmentPath:
    """Monthly exogenous environment shared by all models."""
    n_months: int
    vacancy_rate: np.ndarray        # JOLTS job openings rate (%)
    layoff_rate_env: np.ndarray     # JOLTS layoffs & discharges rate (%)
    mean_offer_wage: np.ndarray     # Mean of log offer wage distribution
    sd_offer_wage: float = 0.6      # Std of log offer wage (constant for MVP)


def generate_synthetic_environment(
    n_months: int = TOTAL_MONTHS,
    seed: int = 42,
) -> EnvironmentPath:
    """
    Generate a plausible synthetic environment path.
    Calibrated to approximate 2014–2024 US labor market:
    - Vacancy rate: ~3-4.5% (JOLTS JOR mean ~4.2%, range 3-7)
    - Layoff rate: ~1.0-1.2% (JOLTS LDR mean ~1.1%)
    - Mean offer wage: ~log(55K) ≈ 10.9 with mild growth trend
    """
    rng = np.random.RandomState(seed)

    t = np.arange(n_months)

    # ── Vacancy rate: trend + cycle + noise ──
    # Mild uptrend 2014-2019, spike 2021-2022, then decline
    vacancy_base = 3.5
    vacancy_trend = 0.01 * t / 12  # slow uptrend
    # Business cycle: ~5 year period
    vacancy_cycle = 0.5 * np.sin(2 * np.pi * t / 60)
    # COVID shock: dip around month 72-78 (2020), then overshoot
    covid_dip = np.zeros(n_months)
    if n_months > 72:
        for i in range(min(6, n_months - 72)):
            covid_dip[72 + i] = -2.0 * np.exp(-i / 2)
    covid_overshoot = np.zeros(n_months)
    if n_months > 78:
        for i in range(min(30, n_months - 78)):
            covid_overshoot[78 + i] = 2.5 * np.exp(-i / 10)
    vacancy_noise = rng.normal(0, 0.1, n_months)
    vacancy_rate = np.clip(
        vacancy_base + vacancy_trend + vacancy_cycle
        + covid_dip + covid_overshoot + vacancy_noise,
        1.0, 8.0
    )

    # ── Layoff rate: counter-cyclical to vacancy ──
    layoff_base = 1.1
    layoff_cycle = -0.15 * np.sin(2 * np.pi * t / 60)
    covid_layoff_spike = np.zeros(n_months)
    if n_months > 72:
        for i in range(min(4, n_months - 72)):
            covid_layoff_spike[72 + i] = 1.5 * np.exp(-i / 1.5)
    layoff_noise = rng.normal(0, 0.05, n_months)
    layoff_rate_env = np.clip(
        layoff_base + layoff_cycle + covid_layoff_spike + layoff_noise,
        0.3, 4.0
    )

    # ── Mean offer wage: mild uptrend ──
    mean_offer_wage = 10.9 + 0.005 * t / 12  # ~0.5% annual growth in log

    return EnvironmentPath(
        n_months=n_months,
        vacancy_rate=vacancy_rate,
        layoff_rate_env=layoff_rate_env,
        mean_offer_wage=mean_offer_wage,
    )


def compute_offer_probability(
    search_intensity: float,
    offer_arrival_belief: float,
    vacancy_rate: float,
    baseline_vacancy: float = 4.0,
) -> float:
    """
    Compute probability of receiving at least one offer this month.
    P(offer) = search_intensity × offer_arrival_belief × (V/V_baseline)
    Clamped to [0, 0.95].
    """
    p = search_intensity * offer_arrival_belief * (vacancy_rate / baseline_vacancy)
    return float(np.clip(p, 0.0, 0.95))


def draw_offer_wage(
    mean_log_wage: float,
    sd_log_wage: float = 0.6,
    rng: np.random.RandomState = None,
) -> float:
    """Draw an offer wage from log-normal distribution."""
    if rng is None:
        rng = np.random.RandomState()
    return float(np.exp(rng.normal(mean_log_wage, sd_log_wage)))
