"""
Multi-objective loss function for the Labor Market ABM.
Compares simulated output against target data.

Loss = Σ_k w_k × ( mean(sim_k - data_k)^2 / var(data_k) )

Targets are standardized by their empirical variance so that
different-scale series (e.g., UR ~4% vs LFPR ~62%) are comparable.
"""
import numpy as np
from typing import Dict, Optional
from models.config import SimulationOutput, TRAIN_END, VALID_END


# ── Default target weights ──────────────────────────────────
# Tier 1 (high weight): core labor market aggregates + flows
# Tier 2 (medium-high): JOLTS-side targets
# Tier 3 (medium-low):  secondary flows
DEFAULT_WEIGHTS = {
    "unemployment_rate": 3.0,
    "lfpr":              3.0,
    "epop":              2.0,
    "flow_EU":           2.0,
    "flow_UE":           2.0,
    "flow_EN":           1.5,
    "flow_NE":           1.5,
    "flow_UN":           1.0,
    "flow_NU":           1.0,
    "hires_rate":        1.5,
    "quits_rate":        1.0,
    "layoffs_rate":      1.0,
}


def generate_synthetic_targets(n_months: int, seed: int = 99) -> Dict[str, np.ndarray]:
    """
    Generate synthetic target data for testing.
    In production, this is replaced by real CPS + JOLTS data.
    
    Calibrated to approximate 2014–2024 US labor market:
    - UR ≈ 3.5–6% (lower in expansion, spike in COVID)
    - LFPR ≈ 62–63%
    - EPOP ≈ 59–61%
    """
    rng = np.random.RandomState(seed)
    t = np.arange(n_months)

    # Unemployment rate
    ur_base = 0.045
    ur_trend = -0.001 * t / 12  # declining trend
    ur_cycle = 0.005 * np.sin(2 * np.pi * t / 60)
    ur_covid = np.zeros(n_months)
    if n_months > 72:
        for i in range(min(12, n_months - 72)):
            ur_covid[72 + i] = 0.08 * np.exp(-i / 3)
    ur = np.clip(ur_base + ur_trend + ur_cycle + ur_covid + rng.normal(0, 0.002, n_months),
                 0.02, 0.15)

    # LFPR
    lfpr = np.clip(0.628 - 0.0005 * t / 12 + rng.normal(0, 0.002, n_months), 0.58, 0.66)

    # EPOP
    epop = lfpr * (1 - ur)

    # Flows (monthly transition rates)
    flow_EU = np.clip(0.012 + 0.003 * ur_covid + rng.normal(0, 0.001, n_months), 0.005, 0.08)
    flow_UE = np.clip(0.28 - 0.5 * (ur - 0.04) + rng.normal(0, 0.02, n_months), 0.10, 0.45)
    flow_EN = np.clip(0.025 + rng.normal(0, 0.002, n_months), 0.01, 0.05)
    flow_NE = np.clip(0.04 + rng.normal(0, 0.003, n_months), 0.02, 0.08)
    flow_UN = np.clip(0.20 + rng.normal(0, 0.02, n_months), 0.10, 0.35)
    flow_NU = np.clip(0.02 + rng.normal(0, 0.003, n_months), 0.01, 0.05)

    # JOLTS-side
    hires_rate = np.clip(0.035 + rng.normal(0, 0.002, n_months), 0.02, 0.06)
    quits_rate = np.clip(0.023 + rng.normal(0, 0.002, n_months), 0.01, 0.04)
    layoffs_rate = np.clip(0.011 + 0.005 * ur_covid + rng.normal(0, 0.001, n_months), 0.005, 0.05)

    return {
        "unemployment_rate": ur, "lfpr": lfpr, "epop": epop,
        "flow_EU": flow_EU, "flow_UE": flow_UE,
        "flow_EN": flow_EN, "flow_NE": flow_NE,
        "flow_UN": flow_UN, "flow_NU": flow_NU,
        "hires_rate": hires_rate, "quits_rate": quits_rate,
        "layoffs_rate": layoffs_rate,
    }


def compute_loss(
    sim: SimulationOutput,
    targets: Dict[str, np.ndarray],
    weights: Optional[Dict[str, float]] = None,
    start_month: int = 0,
    end_month: Optional[int] = None,
) -> Dict[str, float]:
    """
    Compute multi-objective loss between simulation and targets.

    Returns dict with per-target losses and total loss.
    Each target is normalized by its empirical variance.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if end_month is None:
        end_month = sim.n_months

    sim_dict = sim.to_dict()
    total_loss = 0.0
    result = {}

    for key, w in weights.items():
        if key not in targets or key not in sim_dict:
            continue
        s = sim_dict[key][start_month:end_month]
        d = targets[key][start_month:end_month]
        n = min(len(s), len(d))
        if n == 0:
            continue
        s, d = s[:n], d[:n]

        # Normalize by variance of target (avoid division by zero)
        var_d = max(np.var(d), 1e-10)
        mse = np.mean((s - d) ** 2) / var_d
        weighted_mse = w * mse

        result[f"loss_{key}"] = float(weighted_mse)
        total_loss += weighted_mse

    result["total_loss"] = float(total_loss)
    return result


def train_loss(sim: SimulationOutput, targets: Dict[str, np.ndarray],
               weights=None) -> Dict[str, float]:
    return compute_loss(sim, targets, weights, 0, TRAIN_END)


def valid_loss(sim: SimulationOutput, targets: Dict[str, np.ndarray],
               weights=None) -> Dict[str, float]:
    return compute_loss(sim, targets, weights, TRAIN_END, VALID_END)


def test_loss(sim: SimulationOutput, targets: Dict[str, np.ndarray],
              weights=None) -> Dict[str, float]:
    return compute_loss(sim, targets, weights, VALID_END, None)
