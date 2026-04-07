"""
Main experiment runner for Stage 2.
Runs all three models, computes losses, and compares results.

Usage:
    python run_experiment.py [--quick]
    
    --quick : reduced parameter search (20 samples × 3 seeds) for testing
"""
import sys
import time
import numpy as np

from models.config import TOTAL_MONTHS, TRAIN_END, VALID_END, PARAM_BOUNDS
from models.environment import generate_synthetic_environment
from models.loss import (
    generate_synthetic_targets, train_loss, valid_loss, test_loss,
)
from models.model_a import run_model_a
from models.model_b import run_model_b
from models.model_c import run_model_c
from models.calibration import (
    latin_hypercube_sample, sample_to_params, enforce_constraints,
    run_search, select_top_candidates,
)


def main():
    quick = "--quick" in sys.argv
    medium = "--medium" in sys.argv
    if quick:
        n_samples, n_seeds, n_agents = 20, 3, 2000
    elif medium:
        n_samples, n_seeds, n_agents = 100, 5, 3000
    else:
        n_samples, n_seeds, n_agents = 200, 10, 5000

    print("=" * 70)
    print("  LABOR MARKET ABM — STAGE 2 EXPERIMENT")
    mode = 'QUICK' if quick else ('MEDIUM' if medium else 'FULL')
    print(f"  Mode: {mode}")
    print(f"  Params: {n_samples} samples × {n_seeds} seeds × {n_agents} agents")
    print("=" * 70)

    # ── Step 1: Generate environment and targets ──
    print("\n[1] Generating synthetic environment and targets...")
    env = generate_synthetic_environment(TOTAL_MONTHS)
    targets = generate_synthetic_targets(TOTAL_MONTHS)
    print(f"    Environment: {env.n_months} months")
    print(f"    Targets: {list(targets.keys())}")

    # ── Step 2: Quick baseline with default params ──
    default_params = {
        "mu_rw_E": 11.0, "sigma_rw_E": 0.6,
        "mu_rw_N": 10.5, "sigma_rw_N": 0.7,
        "alpha_oab_E": 1.5, "beta_oab_E": 8.0,
        "alpha_oab_N": 2.0, "beta_oab_N": 6.0,
        "p_search_mid": 0.15, "p_search_high": 0.13,
        "pp_delta": 0.0,
    }

    print("\n[2] Running baseline comparison (default params)...")
    t0 = time.time()

    sim_a = run_model_a(env, default_params, seed=0)
    loss_a = train_loss(sim_a, targets)
    print(f"    Model A (Traditional): train_loss = {loss_a['total_loss']:.4f}")

    sim_b = run_model_b(env, default_params, seed=0, n_agents=n_agents)
    loss_b = train_loss(sim_b, targets)
    print(f"    Model B (Standard ABM): train_loss = {loss_b['total_loss']:.4f}")

    sim_c = run_model_c(env, default_params, seed=0, n_agents=n_agents)
    loss_c = train_loss(sim_c, targets)
    print(f"    Model C (Heterogeneous): train_loss = {loss_c['total_loss']:.4f}")
    print(f"    Baseline run time: {time.time()-t0:.1f}s")

    # ── Step 3: Parameter search for Models B and C ──
    best_by_model = {}

    search_seeds = {"B": 42, "C": 137}
    for model_label, run_fn in [("B", run_model_b), ("C", run_model_c)]:
        print(f"\n[3-{model_label}] Parameter search for Model {model_label} "
              f"({n_samples} × {n_seeds})...")
        t0 = time.time()
        search_results = run_search(
            run_model_fn=run_fn, env=env, targets=targets,
            loss_fn=lambda sim, tgt: train_loss(sim, tgt),
            n_samples=n_samples, n_seeds=n_seeds, n_agents=n_agents,
            search_seed=search_seeds[model_label],
            verbose=True,
        )
        print(f"    Search time: {time.time()-t0:.1f}s")
        print(f"    Best train loss: {search_results[0]['mean_loss']:.4f}")

        # Validation selection
        print(f"\n[4-{model_label}] Validation selection (top-5)...")
        valid_results = select_top_candidates(
            train_results=search_results,
            run_model_fn=run_fn, env=env, targets=targets,
            valid_loss_fn=lambda sim, tgt: valid_loss(sim, tgt),
            top_n=min(5, len(search_results)),
            n_seeds=n_seeds, n_agents=n_agents,
        )

        print(f"\n    Rank | Train Loss | Valid Loss | Overfit Ratio")
        print("    " + "-" * 52)
        for i, r in enumerate(valid_results[:3]):
            print(f"    {i+1:4d} | {r['train_loss']:10.4f} | {r['valid_loss']:10.4f} "
                  f"| {r['overfit_ratio']:13.2f}")

        best_by_model[model_label] = valid_results[0]

    # ── Step 5: Final comparison ──
    print(f"\n[5] Final comparison: each model with its own best params...")

    results_summary = {}
    # Model A: use Model B's best params (representative agent)
    best_b_params = best_by_model["B"]["params"]
    best_c_params = best_by_model["C"]["params"]

    for model_name, run_fn, params in [
        ("A", run_model_a, best_b_params),
        ("B", run_model_b, best_b_params),
        ("C", run_model_c, best_c_params),
    ]:
        losses_train = []
        losses_valid = []
        per_target_train = {}
        for s in range(n_seeds):
            if model_name == "A":
                sim = run_fn(env, params, seed=s)
            else:
                sim = run_fn(env, params, seed=s, n_agents=n_agents)
            tl = train_loss(sim, targets)
            vl = valid_loss(sim, targets)
            losses_train.append(tl["total_loss"])
            losses_valid.append(vl["total_loss"])
            for k, v in tl.items():
                if k not in per_target_train:
                    per_target_train[k] = []
                per_target_train[k].append(v)

        results_summary[model_name] = {
            "train_mean": np.mean(losses_train),
            "train_std": np.std(losses_train),
            "valid_mean": np.mean(losses_valid),
            "valid_std": np.std(losses_valid),
            "per_target": {k: np.mean(v) for k, v in per_target_train.items()},
        }

    print("\n" + "=" * 70)
    print("  FINAL COMPARISON (each model with its own best params)")
    print("=" * 70)
    print(f"  {'Model':<25} {'Train Loss':>12} {'Valid Loss':>12} {'Δ vs A (Train)':>15}")
    print("  " + "-" * 65)
    base_train = results_summary["A"]["train_mean"]
    for m in ["A", "B", "C"]:
        r = results_summary[m]
        delta = (r["train_mean"] - base_train) / max(base_train, 1e-10) * 100
        label = {"A": "Traditional", "B": "Standard ABM", "C": "Heterogeneous ABM"}[m]
        print(f"  {label:<25} {r['train_mean']:10.4f}±{r['train_std']:.3f}"
              f" {r['valid_mean']:10.4f}±{r['valid_std']:.3f}"
              f" {delta:+13.1f}%")

    # Per-target breakdown for best models
    print("\n  Per-target loss breakdown (Train):")
    print(f"  {'Target':<22} {'Model A':>10} {'Model B':>10} {'Model C':>10} {'C vs B':>10}")
    print("  " + "-" * 65)
    for key in ["loss_unemployment_rate", "loss_lfpr", "loss_epop",
                "loss_flow_EU", "loss_flow_UE", "loss_flow_EN",
                "loss_flow_NE", "loss_flow_UN", "loss_flow_NU",
                "loss_hires_rate", "loss_quits_rate", "loss_layoffs_rate"]:
        la = results_summary["A"]["per_target"].get(key, 0)
        lb = results_summary["B"]["per_target"].get(key, 0)
        lc = results_summary["C"]["per_target"].get(key, 0)
        diff = (lc - lb) / max(lb, 1e-10) * 100
        print(f"  {key[5:]:<22} {la:10.2f} {lb:10.2f} {lc:10.2f} {diff:+9.1f}%")

    print(f"\n[Done] Stage 2 experiment complete.")
    print(f"Best Model B params: { {k: round(v, 4) for k, v in best_b_params.items()} }")
    print(f"Best Model C params: { {k: round(v, 4) for k, v in best_c_params.items()} }")


if __name__ == "__main__":
    main()
