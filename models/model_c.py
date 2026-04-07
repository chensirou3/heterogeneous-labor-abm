"""
Model C: Heterogeneous ABM with Worker Types.

Multiple worker agents with heterogeneous parameters drawn from
survey-constrained distributions. Three worker types:
  Type 0 (Active Searcher): high search, high belief
  Type 1 (Low-threshold):   low reservation wage, high acceptance
  Type 2 (Marginal):        low participation, low search
"""
import numpy as np
from models.config import (
    EMPLOYED, UNEMPLOYED, NILF, SimulationOutput,
    DEFAULT_N_AGENTS, BASELINE_LFPR,
    TYPE_ACTIVE_SEARCHER, TYPE_LOW_THRESHOLD, TYPE_MARGINAL,
)
from models.environment import EnvironmentPath
from models.worker import Worker


def _assign_type(rw: float, si: float, oab: float, pp: float,
                 median_rw: float, median_oab: float) -> int:
    """Rule-based worker type assignment (MVP version)."""
    if si > 0.3 and oab > median_oab:
        return TYPE_ACTIVE_SEARCHER
    elif rw < median_rw * 0.8 and pp > 0.5:
        return TYPE_LOW_THRESHOLD
    else:
        return TYPE_MARGINAL


def run_model_c(
    env: EnvironmentPath,
    params: dict,
    seed: int = 0,
    n_agents: int = DEFAULT_N_AGENTS,
    ablation: dict = None,
) -> SimulationOutput:
    """
    Run the Heterogeneous ABM.

    Parameters
    ----------
    ablation : dict, optional
        Keys: no_rw_hetero, no_si_hetero, no_pp_hetero, no_oab_hetero,
              no_type_behavior, no_matching_market, no_declining_rw.
        If a key is True, that feature is disabled.
    """
    if ablation is None:
        ablation = {}
    abl = {
        "no_rw_hetero": False, "no_si_hetero": False,
        "no_pp_hetero": False, "no_oab_hetero": False,
        "no_type_behavior": False, "no_matching_market": False,
        "no_declining_rw": False,
    }
    abl.update(ablation)
    rng = np.random.RandomState(seed)
    T = env.n_months

    # ── Draw heterogeneous parameters ──
    # Determine initial E/N split to assign different distributions
    pp_delta = params["pp_delta"]
    avg_pp = float(np.clip(
        np.mean([v + pp_delta for v in BASELINE_LFPR.values()]), 0.01, 0.99
    ))

    # Assign demographic groups uniformly for now
    age_groups = rng.choice([0, 1, 2], size=n_agents, p=[0.30, 0.40, 0.30])
    edu_groups = rng.choice([0, 1], size=n_agents, p=[0.55, 0.45])
    sexes = rng.choice([0, 1], size=n_agents, p=[0.50, 0.50])

    # Participation propensity per agent
    if abl["no_pp_hetero"]:
        pp_arr = np.full(n_agents, avg_pp)
    else:
        pp_arr = np.array([
            np.clip(BASELINE_LFPR.get((a, e, s), 0.65) + pp_delta, 0.01, 0.99)
            for a, e, s in zip(age_groups, edu_groups, sexes)
        ])

    # Initial state based on individual pp
    init_states = np.zeros(n_agents, dtype=int)
    for i in range(n_agents):
        r = rng.random()
        if r < pp_arr[i] * 0.96:
            init_states[i] = EMPLOYED
        elif r < pp_arr[i]:
            init_states[i] = UNEMPLOYED
        else:
            init_states[i] = NILF

    # Reservation wage
    rw_arr = np.zeros(n_agents)
    for i in range(n_agents):
        if init_states[i] == EMPLOYED:
            rw_arr[i] = np.exp(rng.normal(params["mu_rw_E"], params["sigma_rw_E"]))
        else:
            rw_arr[i] = np.exp(rng.normal(params["mu_rw_N"], params["sigma_rw_N"]))
    if abl["no_rw_hetero"]:
        rw_arr[:] = np.mean(rw_arr)

    # Offer arrival belief
    oab_arr = np.zeros(n_agents)
    for i in range(n_agents):
        if init_states[i] == EMPLOYED:
            oab_arr[i] = rng.beta(params["alpha_oab_E"], params["beta_oab_E"])
        else:
            oab_arr[i] = rng.beta(params["alpha_oab_N"], params["beta_oab_N"])
    if abl["no_oab_hetero"]:
        oab_arr[:] = np.mean(oab_arr)

    # Search intensity
    p_mid = params["p_search_mid"]
    p_high = params["p_search_high"]
    p_low = max(0.0, 1.0 - p_mid - p_high)
    si_tiers = rng.choice(
        [0.0, 0.3, 0.8], size=n_agents, p=[p_low, p_mid, p_high]
    )
    if abl["no_si_hetero"]:
        si_tiers[:] = np.mean(si_tiers)

    # ── Assign worker types ──
    median_rw = float(np.median(rw_arr))
    median_oab = float(np.median(oab_arr))
    types = np.array([
        _assign_type(rw_arr[i], si_tiers[i], oab_arr[i], pp_arr[i],
                     median_rw, median_oab)
        for i in range(n_agents)
    ])

    # ── Create worker objects ──
    workers = [
        Worker(
            state=int(init_states[i]),
            reservation_wage=float(rw_arr[i]),
            offer_arrival_belief=float(oab_arr[i]),
            search_intensity=float(si_tiers[i]),
            participation_propensity=float(pp_arr[i]),
            worker_type=int(types[i]),
            age_group=int(age_groups[i]),
            edu_group=int(edu_groups[i]),
            sex=int(sexes[i]),
        )
        for i in range(n_agents)
    ]

    # ── Output arrays ──
    ur = np.zeros(T); lfpr_out = np.zeros(T); epop_out = np.zeros(T)
    f_EU = np.zeros(T); f_UE = np.zeros(T)
    f_EN = np.zeros(T); f_NE = np.zeros(T)
    f_UN = np.zeros(T); f_NU = np.zeros(T)
    hires_r = np.zeros(T); quits_r = np.zeros(T); layoffs_r = np.zeros(T)

    use_matching = not abl["no_matching_market"]
    use_type_beh = not abl["no_type_behavior"]
    use_decl_rw = not abl["no_declining_rw"]

    # ── Simulate ──
    for t in range(T):
        states = np.array([w.state for w in workers])
        n_E = np.sum(states == EMPLOYED)
        n_U = np.sum(states == UNEMPLOYED)
        n_N = np.sum(states == NILF)
        lf = n_E + n_U

        ur[t] = n_U / lf if lf > 0 else 0.0
        lfpr_out[t] = lf / n_agents
        epop_out[t] = n_E / n_agents

        old_states = states.copy()
        lr = env.layoff_rate_env[t] / 100.0

        # ── Matching market (can be disabled by ablation) ──
        offer_set = set()
        if use_matching:
            n_openings = max(1, int(env.vacancy_rate[t] / 100.0 * n_E * 2.5))
            searcher_indices = []
            searcher_scores = []
            for i, w in enumerate(workers):
                if w.state == UNEMPLOYED:
                    eff_si = max(w.search_intensity, 0.5)
                    score = eff_si * w.offer_arrival_belief
                    searcher_indices.append(i)
                    searcher_scores.append(score)
                elif w.state == NILF and rng.random() < w.participation_propensity * 0.06:
                    score = 0.4 * w.offer_arrival_belief * 0.5
                    searcher_indices.append(i)
                    searcher_scores.append(score)
            if searcher_indices:
                scores = np.array(searcher_scores)
                total_score = scores.sum()
                if total_score > 0 and n_openings > 0:
                    probs = scores / total_score
                    n_to_offer = min(n_openings, len(searcher_indices))
                    chosen = rng.choice(
                        len(searcher_indices), size=n_to_offer,
                        replace=False, p=probs,
                    )
                    offer_set = {searcher_indices[c] for c in chosen}

        # Step all workers
        for i, w in enumerate(workers):
            w.step(env.vacancy_rate[t], lr, env.mean_offer_wage[t],
                   env.sd_offer_wage, rng,
                   offer_received=(i in offer_set),
                   use_type_behavior=use_type_beh,
                   use_declining_rw=use_decl_rw)

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

        new_hires = np.sum((old_states != EMPLOYED) & (new_states == EMPLOYED))
        hires_r[t] = new_hires / max(n_E, 1)
        layoffs_r[t] = f_EU[t]
        # Quits: E workers who left but were not laid off (high search = voluntary)
        quits_r[t] = np.sum(
            (old_states == EMPLOYED) & (new_states != EMPLOYED)
            & np.array([w.search_intensity > 0.3 for w in workers])
        ) / max(n_E, 1)

    return SimulationOutput(
        n_months=T, unemployment_rate=ur, lfpr=lfpr_out, epop=epop_out,
        flow_EU=f_EU, flow_UE=f_UE, flow_EN=f_EN, flow_NE=f_NE,
        flow_UN=f_UN, flow_NU=f_NU,
        hires_rate=hires_r, quits_rate=quits_r, layoffs_rate=layoffs_r,
        model_name="Model_C_Heterogeneous_ABM",
    )
