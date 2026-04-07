"""
Shared configuration for the Labor Market ABM.
Defines constants, parameter bounds, and shared data structures.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ── States ──────────────────────────────────────────────────
EMPLOYED = 0        # E
UNEMPLOYED = 1      # U
NILF = 2            # N (Not in Labor Force)
STATE_NAMES = {EMPLOYED: "E", UNEMPLOYED: "U", NILF: "N"}

# ── Simulation defaults ────────────────────────────────────
DEFAULT_N_AGENTS = 10_000
DEFAULT_N_MONTHS = 120      # 10 years
DEFAULT_N_SEEDS = 10

# ── Time split (months from 2014-01 = month 0) ─────────────
# Train:  2014-01 to 2021-12  →  months  0–95   (96 months)
# Valid:  2022-01 to 2023-06  →  months 96–113   (18 months)
# Test:   2023-07 to 2024-12  →  months 114–131  (18 months)
TRAIN_END = 96
VALID_END = 114
TOTAL_MONTHS = 132

# ── Worker type labels ──────────────────────────────────────
TYPE_ACTIVE_SEARCHER = 0
TYPE_LOW_THRESHOLD = 1
TYPE_MARGINAL = 2
TYPE_NAMES = {0: "ActiveSearcher", 1: "LowThreshold", 2: "Marginal"}

# ── Parameter search bounds (11 dimensions) ─────────────────
@dataclass
class ParameterBounds:
    """Bounds for the 11-dimensional search space."""
    # reservation_wage: log-normal params for E and non-E
    mu_rw_E: Tuple[float, float] = (10.3, 11.9)
    sigma_rw_E: Tuple[float, float] = (0.3, 1.2)
    mu_rw_N: Tuple[float, float] = (9.9, 11.5)
    sigma_rw_N: Tuple[float, float] = (0.3, 1.2)
    # offer_arrival_belief: Beta params for E and non-E
    alpha_oab_E: Tuple[float, float] = (0.5, 5.0)
    beta_oab_E: Tuple[float, float] = (2.0, 20.0)
    alpha_oab_N: Tuple[float, float] = (0.5, 5.0)
    beta_oab_N: Tuple[float, float] = (2.0, 20.0)
    # search_intensity: 3-tier discrete (p_mid, p_high; p_low = 1-p_mid-p_high)
    p_search_mid: Tuple[float, float] = (0.05, 0.30)
    p_search_high: Tuple[float, float] = (0.05, 0.25)
    # participation_propensity: uniform offset delta
    pp_delta: Tuple[float, float] = (-0.05, 0.05)

    def to_bounds_array(self) -> np.ndarray:
        """Return (11, 2) array of [lower, upper] bounds."""
        return np.array([
            self.mu_rw_E, self.sigma_rw_E,
            self.mu_rw_N, self.sigma_rw_N,
            self.alpha_oab_E, self.beta_oab_E,
            self.alpha_oab_N, self.beta_oab_N,
            self.p_search_mid, self.p_search_high,
            self.pp_delta,
        ])

    @staticmethod
    def dim_names() -> List[str]:
        return [
            "mu_rw_E", "sigma_rw_E", "mu_rw_N", "sigma_rw_N",
            "alpha_oab_E", "beta_oab_E", "alpha_oab_N", "beta_oab_N",
            "p_search_mid", "p_search_high", "pp_delta",
        ]

PARAM_BOUNDS = ParameterBounds()

# ── Baseline LFPR by group (age3 × edu2 × sex2 = 12 groups) ─
# Order: (age_group, edu_group, sex) → LFPR
# age_group: 0=16-34, 1=35-54, 2=55+
# edu_group: 0=NoCollege, 1=College+
# sex: 0=Male, 1=Female
BASELINE_LFPR = {
    (0, 0, 0): 0.72, (0, 0, 1): 0.63,
    (0, 1, 0): 0.82, (0, 1, 1): 0.78,
    (1, 0, 0): 0.85, (1, 0, 1): 0.70,
    (1, 1, 0): 0.92, (1, 1, 1): 0.80,
    (2, 0, 0): 0.55, (2, 0, 1): 0.40,
    (2, 1, 0): 0.65, (2, 1, 1): 0.52,
}

# ── Simulation output structure ─────────────────────────────
@dataclass
class SimulationOutput:
    """Unified output from any model (A, B, or C)."""
    n_months: int
    unemployment_rate: np.ndarray     # (n_months,)
    lfpr: np.ndarray                  # (n_months,)
    epop: np.ndarray                  # (n_months,)
    flow_EU: np.ndarray               # (n_months,)  E→U rate
    flow_UE: np.ndarray               # (n_months,)  U→E rate
    flow_EN: np.ndarray               # (n_months,)  E→N rate
    flow_NE: np.ndarray               # (n_months,)  N→E rate
    flow_UN: np.ndarray               # (n_months,)  U→N rate
    flow_NU: np.ndarray               # (n_months,)  N→U rate
    hires_rate: np.ndarray            # (n_months,)  new hires / employment
    quits_rate: np.ndarray            # (n_months,)  voluntary separations
    layoffs_rate: np.ndarray          # (n_months,)  involuntary separations
    model_name: str = ""

    def to_dict(self) -> Dict[str, np.ndarray]:
        """Return all series as a dict for loss computation."""
        return {
            "unemployment_rate": self.unemployment_rate,
            "lfpr": self.lfpr,
            "epop": self.epop,
            "flow_EU": self.flow_EU, "flow_UE": self.flow_UE,
            "flow_EN": self.flow_EN, "flow_NE": self.flow_NE,
            "flow_UN": self.flow_UN, "flow_NU": self.flow_NU,
            "hires_rate": self.hires_rate,
            "quits_rate": self.quits_rate,
            "layoffs_rate": self.layoffs_rate,
        }
