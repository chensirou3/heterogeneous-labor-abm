"""
Model B: Standard ABM with Homogeneous Workers.

Multiple worker agents with identical parameters.
Stochastic individual transitions produce aggregate dynamics.
Shares the same environment path as Models A and C.
"""
import numpy as np
from models.config import (
    EMPLOYED, UNEMPLOYED, NILF, SimulationOutput,
    DEFAULT_N_AGENTS, BASELINE_LFPR,
)
from models.environment import EnvironmentPath
from models.worker import Worker


def _average_lfpr(delta: float) -> float:
    vals = [v + delta for v in BASELINE_LFPR.values()]
    return float(np.clip(np.mean(vals), 0.01, 0.99))


def run_model_b(
    env: EnvironmentPath,
    params: dict,
    seed: int = 0,
    n_agents: int = DEFAULT_N_AGENTS,
) -> SimulationOutput:
    """
    Run Standard ABM with homogeneous workers.

    All agents share the same (mean) parameter values.
    """
    rng = np.random.RandomState(seed)
    T = env.n_months

    # ── Derive representative parameters ──
    rw_mean = float(np.exp(params["mu_rw_E"] + 0.5 * params["sigma_rw_E"]**2))
    alpha_e, beta_e = params["alpha_oab_E"], params["beta_oab_E"]
    oab_mean = alpha_e / (alpha_e + beta_e)
    p_mid = params["p_search_mid"]
    p_high = params["p_search_high"]
    p_low = max(0.0, 1.0 - p_mid - p_high)
    si_mean = p_low * 0.0 + p_mid * 0.3 + p_high * 0.8
    pp = _average_lfpr(params["pp_delta"])

    # ── Initialize agents ──
    workers = []
    for i in range(n_agents):
        # Initial state based on LFPR and UR
        r = rng.random()
        if r < pp * 0.96:
            state = EMPLOYED
        elif r < pp:
            state = UNEMPLOYED
        else:
            state = NILF

        w = Worker(
            state=state,
            reservation_wage=rw_mean,
            offer_arrival_belief=oab_mean,
            search_intensity=si_mean,
            participation_propensity=pp,
            worker_type=1,  # all same type
        )
        workers.append(w)

    # ── Output arrays ──
    ur = np.zeros(T); lfpr_out = np.zeros(T); epop_out = np.zeros(T)
    f_EU = np.zeros(T); f_UE = np.zeros(T)
    f_EN = np.zeros(T); f_NE = np.zeros(T)
    f_UN = np.zeros(T); f_NU = np.zeros(T)
    hires_r = np.zeros(T); quits_r = np.zeros(T); layoffs_r = np.zeros(T)

    # ── Simulate ──
    for t in range(T):
        # Count current states
        states = np.array([w.state for w in workers])
        n_E = np.sum(states == EMPLOYED)
        n_U = np.sum(states == UNEMPLOYED)
        n_N = np.sum(states == NILF)
        n_total = n_agents

        lf = n_E + n_U
        ur[t] = n_U / lf if lf > 0 else 0.0
        lfpr_out[t] = lf / n_total
        epop_out[t] = n_E / n_total

        # Track flows
        old_states = states.copy()

        # Layoff rate from environment
        lr = env.layoff_rate_env[t] / 100.0

        # Step all workers
        for w in workers:
            w.step(
                vacancy_rate=env.vacancy_rate[t],
                layoff_rate=lr,
                mean_log_offer_wage=env.mean_offer_wage[t],
                sd_log_offer_wage=env.sd_offer_wage,
                rng=rng,
            )

        # Compute flow rates
        new_states = np.array([w.state for w in workers])
        if n_E > 0:
            f_EU[t] = np.sum((old_states == EMPLOYED) & (new_states == UNEMPLOYED)) / n_E
            f_EN[t] = np.sum((old_states == EMPLOYED) & (new_states == NILF)) / n_E
        if n_U > 0:
            f_UE[t] = np.sum((old_states == UNEMPLOYED) & (new_states == EMPLOYED)) / n_U
            f_UN[t] = np.sum((old_states == UNEMPLOYED) & (new_states == NILF)) / n_U
        if n_N > 0:
            f_NE[t] = np.sum((old_states == NILF) & (new_states == EMPLOYED)) / n_N
            f_NU[t] = np.sum((old_states == NILF) & (new_states == UNEMPLOYED)) / n_N

        # Hires = all transitions into E
        new_hires = (np.sum((old_states != EMPLOYED) & (new_states == EMPLOYED)))
        hires_r[t] = new_hires / max(n_E, 1)
        # Layoffs = E→U (involuntary)
        layoffs_r[t] = f_EU[t]
        # Quits ≈ 0 for homogeneous model (no on-the-job search variation)
        quits_r[t] = 0.0

    return SimulationOutput(
        n_months=T, unemployment_rate=ur, lfpr=lfpr_out, epop=epop_out,
        flow_EU=f_EU, flow_UE=f_UE, flow_EN=f_EN, flow_NE=f_NE,
        flow_UN=f_UN, flow_NU=f_NU,
        hires_rate=hires_r, quits_rate=quits_r, layoffs_rate=layoffs_r,
        model_name="Model_B_Standard_ABM",
    )
