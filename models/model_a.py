"""
Model A: Traditional Labor Market Benchmark.

A representative-agent model with homogeneous parameters.
Uses a 3-state Markov chain (E/U/N) where transition probabilities
are derived from aggregate parameters and environment.
No individual agents — operates on population shares directly.
"""
import numpy as np
from models.config import (
    EMPLOYED, UNEMPLOYED, NILF, SimulationOutput, TOTAL_MONTHS,
    BASELINE_LFPR,
)
from models.environment import EnvironmentPath, compute_offer_probability


def _average_lfpr(delta: float) -> float:
    """Compute population-weighted average LFPR with offset delta."""
    vals = [v + delta for v in BASELINE_LFPR.values()]
    return float(np.clip(np.mean(vals), 0.01, 0.99))


def run_model_a(
    env: EnvironmentPath,
    params: dict,
    seed: int = 0,
) -> SimulationOutput:
    """
    Run the Traditional Benchmark model.

    Parameters
    ----------
    env : EnvironmentPath
    params : dict with keys:
        mu_rw_E, sigma_rw_E      (reservation wage for representative worker)
        alpha_oab_E, beta_oab_E  (offer arrival belief)
        p_search_mid, p_search_high
        pp_delta
    seed : int  (unused for Model A — deterministic)

    Returns
    -------
    SimulationOutput with monthly series.
    """
    T = env.n_months

    # ── Derive representative parameters ──
    # Reservation wage: mean of log-normal
    rw_mean = np.exp(params["mu_rw_E"] + 0.5 * params["sigma_rw_E"] ** 2)

    # Offer arrival belief: mean of Beta
    alpha_e = params["alpha_oab_E"]
    beta_e = params["beta_oab_E"]
    oab_mean = alpha_e / (alpha_e + beta_e)

    # Search intensity: weighted average of 3 tiers
    p_mid = params["p_search_mid"]
    p_high = params["p_search_high"]
    p_low = max(0.0, 1.0 - p_mid - p_high)
    si_mean = p_low * 0.0 + p_mid * 0.3 + p_high * 0.8

    # Participation propensity
    pp = _average_lfpr(params["pp_delta"])

    # ── Initialize population shares ──
    share_E = 0.94   # ~94% employed (of civilian pop)
    share_U = 0.04   # ~4% unemployed
    share_N = 0.02   # rest NILF (simplified — actual NILF is ~37% of pop,
    # but we model labor-force-eligible pop; see note below)

    # NOTE: We model the working-age population.
    # Initial shares approximate: LFPR ~62%, UR ~4%
    # → E = LFPR*(1-UR) ≈ 0.595, U = LFPR*UR ≈ 0.025, N = 1-LFPR ≈ 0.38
    share_E = pp * (1 - 0.04)
    share_U = pp * 0.04
    share_N = 1.0 - pp

    # Output arrays
    ur = np.zeros(T)
    lfpr_out = np.zeros(T)
    epop_out = np.zeros(T)
    f_EU = np.zeros(T); f_UE = np.zeros(T)
    f_EN = np.zeros(T); f_NE = np.zeros(T)
    f_UN = np.zeros(T); f_NU = np.zeros(T)
    hires = np.zeros(T); quits = np.zeros(T); layoffs = np.zeros(T)

    for t in range(T):
        lf = share_E + share_U
        if lf > 0:
            ur[t] = share_U / lf
        lfpr_out[t] = lf
        epop_out[t] = share_E

        # ── Transition probabilities ──
        vr = env.vacancy_rate[t]
        lr = env.layoff_rate_env[t] / 100.0

        # E→U: layoff shock
        p_EU = lr
        # E→N: voluntary exit (aligned with Worker.step fix)
        p_EN = min(0.04, (1.0 - pp) * 0.035 + 0.005)
        # U→E: search → offer → accept
        effective_si = max(si_mean, 0.5)
        p_offer_U = compute_offer_probability(effective_si, oab_mean, vr)
        from scipy.stats import norm
        log_rw = np.log(rw_mean)
        z = (env.mean_offer_wage[t] - log_rw) / env.sd_offer_wage
        p_accept = float(norm.cdf(z))
        p_UE = p_offer_U * p_accept
        # U→N: discouraged workers exit (aligned with Worker.step fix)
        p_UN = min(0.25, (1.0 - pp) * 0.30 + 0.02)
        # N→U: re-enter labor force
        p_NU = pp * 0.04
        # N→E: direct re-entry
        p_NE = pp * 0.06 * p_offer_U * p_accept * 0.5

        # Clip all probabilities
        p_EU = np.clip(p_EU, 0, 0.5)
        p_EN = np.clip(p_EN, 0, 0.05)
        p_UE = np.clip(p_UE, 0, 0.8)
        p_UN = np.clip(p_UN, 0, 0.30)
        p_NU = np.clip(p_NU, 0, 0.1)
        p_NE = np.clip(p_NE, 0, 0.1)

        # Record flows (as rates)
        f_EU[t] = p_EU; f_UE[t] = p_UE
        f_EN[t] = p_EN; f_NE[t] = p_NE
        f_UN[t] = p_UN; f_NU[t] = p_NU

        # ── Update shares ──
        dE = -share_E * (p_EU + p_EN) + share_U * p_UE + share_N * p_NE
        dU = share_E * p_EU - share_U * (p_UE + p_UN) + share_N * p_NU
        dN = share_E * p_EN + share_U * p_UN - share_N * (p_NU + p_NE)

        share_E = np.clip(share_E + dE, 0.01, 0.99)
        share_U = np.clip(share_U + dU, 0.001, 0.5)
        share_N = np.clip(share_N + dN, 0.001, 0.99)
        # Renormalize
        total = share_E + share_U + share_N
        share_E /= total; share_U /= total; share_N /= total

        # Hires ≈ UE + NE flows; Quits ≈ search-driven E→U; Layoffs ≈ p_EU
        hires[t] = (share_U * p_UE + share_N * p_NE) / max(share_E, 0.01)
        quits[t] = si_mean * 0.02  # simplified voluntary quit rate
        layoffs[t] = p_EU

    return SimulationOutput(
        n_months=T, unemployment_rate=ur, lfpr=lfpr_out, epop=epop_out,
        flow_EU=f_EU, flow_UE=f_UE, flow_EN=f_EN, flow_NE=f_NE,
        flow_UN=f_UN, flow_NU=f_NU,
        hires_rate=hires, quits_rate=quits, layoffs_rate=layoffs,
        model_name="Model_A_Traditional",
    )
