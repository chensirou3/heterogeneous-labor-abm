"""
Parameter search and calibration module.
Implements Latin Hypercube Sampling for the 11-dimensional parameter space.
"""
import numpy as np
from typing import List, Dict, Callable, Optional
from models.config import PARAM_BOUNDS, ParameterBounds, DEFAULT_N_SEEDS


def latin_hypercube_sample(
    bounds: np.ndarray,
    n_samples: int,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate Latin Hypercube samples within given bounds.
    
    Parameters
    ----------
    bounds : (n_dims, 2) array of [lower, upper]
    n_samples : number of parameter sets to generate
    seed : random seed
    
    Returns
    -------
    samples : (n_samples, n_dims) array
    """
    rng = np.random.RandomState(seed)
    n_dims = bounds.shape[0]
    samples = np.zeros((n_samples, n_dims))

    for d in range(n_dims):
        # Create n_samples equally-spaced intervals
        lo, hi = bounds[d]
        cuts = np.linspace(lo, hi, n_samples + 1)
        # Sample uniformly within each interval
        for i in range(n_samples):
            samples[i, d] = rng.uniform(cuts[i], cuts[i + 1])
        # Shuffle to break correlations between dimensions
        rng.shuffle(samples[:, d])

    return samples


def sample_to_params(sample: np.ndarray) -> dict:
    """Convert a 11-dim sample vector to a named parameter dict."""
    names = ParameterBounds.dim_names()
    return {name: float(sample[i]) for i, name in enumerate(names)}


def enforce_constraints(params: dict) -> dict:
    """Enforce logical constraints on parameter values."""
    p = params.copy()
    # search_intensity tiers must sum to <= 1
    p_mid = p["p_search_mid"]
    p_high = p["p_search_high"]
    if p_mid + p_high > 0.95:
        total = p_mid + p_high
        p["p_search_mid"] = p_mid * 0.95 / total
        p["p_search_high"] = p_high * 0.95 / total
    return p


def run_search(
    run_model_fn: Callable,
    env,
    targets: Dict[str, np.ndarray],
    loss_fn: Callable,
    n_samples: int = 200,
    n_seeds: int = DEFAULT_N_SEEDS,
    n_agents: int = 5000,
    search_seed: int = 42,
    verbose: bool = True,
) -> List[dict]:
    """
    Run parameter search using Latin Hypercube Sampling.
    
    Parameters
    ----------
    run_model_fn : function(env, params, seed, n_agents) -> SimulationOutput
    env : EnvironmentPath
    targets : dict of target time series
    loss_fn : function(sim, targets) -> dict with 'total_loss'
    n_samples : number of parameter sets to try
    n_seeds : number of random seeds per parameter set
    n_agents : number of agents per simulation
    
    Returns
    -------
    results : list of dicts sorted by mean total_loss, each containing:
        params, mean_loss, std_loss, per_target_losses
    """
    bounds = PARAM_BOUNDS.to_bounds_array()
    samples = latin_hypercube_sample(bounds, n_samples, search_seed)

    results = []
    for idx in range(n_samples):
        params = enforce_constraints(sample_to_params(samples[idx]))
        seed_losses = []
        per_target_accum = {}

        for s in range(n_seeds):
            sim = run_model_fn(env=env, params=params, seed=s, n_agents=n_agents)
            loss_dict = loss_fn(sim, targets)
            seed_losses.append(loss_dict["total_loss"])

            for k, v in loss_dict.items():
                if k not in per_target_accum:
                    per_target_accum[k] = []
                per_target_accum[k].append(v)

        mean_loss = float(np.mean(seed_losses))
        std_loss = float(np.std(seed_losses))
        mean_per_target = {k: float(np.mean(v)) for k, v in per_target_accum.items()}

        results.append({
            "params": params,
            "mean_loss": mean_loss,
            "std_loss": std_loss,
            "per_target": mean_per_target,
            "sample_idx": idx,
        })

        if verbose and (idx + 1) % 20 == 0:
            print(f"  [{idx+1}/{n_samples}] best so far: "
                  f"{min(r['mean_loss'] for r in results):.4f}")

    results.sort(key=lambda x: x["mean_loss"])
    return results


def select_top_candidates(
    train_results: List[dict],
    run_model_fn: Callable,
    env,
    targets: Dict[str, np.ndarray],
    valid_loss_fn: Callable,
    top_n: int = 10,
    n_seeds: int = DEFAULT_N_SEEDS,
    n_agents: int = 5000,
) -> List[dict]:
    """
    Take top-N from train search and evaluate on validation set.
    Returns results sorted by validation loss.
    """
    candidates = train_results[:top_n]
    valid_results = []

    for cand in candidates:
        params = cand["params"]
        vloss_list = []
        for s in range(n_seeds):
            sim = run_model_fn(env=env, params=params, seed=s + 1000, n_agents=n_agents)
            vl = valid_loss_fn(sim, targets)
            vloss_list.append(vl["total_loss"])

        valid_results.append({
            "params": params,
            "train_loss": cand["mean_loss"],
            "valid_loss": float(np.mean(vloss_list)),
            "valid_std": float(np.std(vloss_list)),
            "overfit_ratio": float(np.mean(vloss_list)) / max(cand["mean_loss"], 1e-10),
        })

    valid_results.sort(key=lambda x: x["valid_loss"])
    return valid_results
