"""
Stage 3: Out-of-Sample Evaluation, Ablation & Robustness.
Runs on the frozen Stage-2 baseline.

Usage:
    python run_stage3.py [--quick]
"""
import sys, time
import numpy as np
from models.config import TOTAL_MONTHS, TRAIN_END, VALID_END
from models.environment import generate_synthetic_environment
from models.loss import (
    generate_synthetic_targets, train_loss, valid_loss, test_loss,
    compute_loss, DEFAULT_WEIGHTS,
)
from models.model_a import run_model_a
from models.model_b import run_model_b
from models.model_c import run_model_c

# ══════════════════════════════════════════════════════════════
# Frozen Stage-2 Baseline Parameters (from Medium Run)
# ══════════════════════════════════════════════════════════════
BASELINE_PARAMS_B = {
    "mu_rw_E": 10.58, "sigma_rw_E": 0.46, "mu_rw_N": 11.42, "sigma_rw_N": 0.99,
    "alpha_oab_E": 4.88, "beta_oab_E": 7.75, "alpha_oab_N": 4.68, "beta_oab_N": 8.00,
    "p_search_mid": 0.10, "p_search_high": 0.16, "pp_delta": -0.032,
}
BASELINE_PARAMS_C = {
    "mu_rw_E": 10.32, "sigma_rw_E": 0.93, "mu_rw_N": 11.06, "sigma_rw_N": 1.10,
    "alpha_oab_E": 3.09, "beta_oab_E": 3.37, "alpha_oab_N": 3.52, "beta_oab_N": 10.94,
    "p_search_mid": 0.20, "p_search_high": 0.10, "pp_delta": 0.040,
}

# Ablation definitions
ABLATIONS = {
    "baseline":          {},
    "no_rw_hetero":      {"no_rw_hetero": True},
    "no_si_hetero":      {"no_si_hetero": True},
    "no_pp_hetero":      {"no_pp_hetero": True},
    "no_oab_hetero":     {"no_oab_hetero": True},
    "no_type_behavior":  {"no_type_behavior": True},
    "no_matching_mkt":   {"no_matching_market": True},
    "no_declining_rw":   {"no_declining_rw": True},
}


def eval_model(run_fn, params, env, targets, loss_fn, n_seeds, n_agents,
               ablation=None, model_name=""):
    """Evaluate a model across multiple seeds. Returns summary dict."""
    losses = []
    per_target_accum = {}
    for s in range(n_seeds):
        kwargs = dict(env=env, params=params, seed=s, n_agents=n_agents)
        if ablation is not None:
            kwargs["ablation"] = ablation
        if run_fn == run_model_a:
            kwargs.pop("n_agents", None)
            kwargs.pop("ablation", None)
        sim = run_fn(**kwargs)
        ld = loss_fn(sim, targets)
        losses.append(ld["total_loss"])
        for k, v in ld.items():
            per_target_accum.setdefault(k, []).append(v)
    return {
        "name": model_name,
        "mean_loss": float(np.mean(losses)),
        "std_loss": float(np.std(losses)),
        "per_target": {k: float(np.mean(v)) for k, v in per_target_accum.items()},
    }


def print_comparison(results, title=""):
    """Pretty-print a comparison table."""
    print(f"\n{'='*70}\n  {title}\n{'='*70}")
    base = results[0]["mean_loss"]
    print(f"  {'Model':<30} {'Loss':>10} {'Std':>8} {'vs Base':>10}")
    print("  " + "-" * 60)
    for r in results:
        delta = (r["mean_loss"] - base) / max(base, 1e-10) * 100
        print(f"  {r['name']:<30} {r['mean_loss']:10.1f} {r['std_loss']:8.1f}"
              f" {delta:+9.1f}%")


def print_per_target(results, keys=None):
    """Print per-target breakdown."""
    if keys is None:
        keys = [k for k in results[0]["per_target"] if k.startswith("loss_")]
    header = f"  {'Target':<22}" + "".join(f" {r['name'][:12]:>12}" for r in results)
    print(f"\n{header}")
    print("  " + "-" * (22 + 13 * len(results)))
    for key in sorted(keys):
        row = f"  {key[5:]:<22}"
        for r in results:
            row += f" {r['per_target'].get(key, 0):12.1f}"
        print(row)


def main():
    quick = "--quick" in sys.argv
    n_seeds = 3 if quick else 10
    n_agents = 2000 if quick else 3000
    print(f"Stage 3 | Mode: {'QUICK' if quick else 'FULL'} | Seeds: {n_seeds}")

    env = generate_synthetic_environment(TOTAL_MONTHS)
    targets = generate_synthetic_targets(TOTAL_MONTHS)

    # ═══ TASK A: Test Set Final Comparison ════════════════════
    print("\n[A] TEST SET FINAL COMPARISON")
    results_test = []
    for name, fn, params in [
        ("A_Traditional", run_model_a, BASELINE_PARAMS_B),
        ("B_Standard_ABM", run_model_b, BASELINE_PARAMS_B),
        ("C_Heterogeneous", run_model_c, BASELINE_PARAMS_C),
    ]:
        r = eval_model(fn, params, env, targets, test_loss, n_seeds, n_agents,
                       model_name=name)
        results_test.append(r)
    print_comparison(results_test, "TEST SET (Out-of-Sample)")
    print_per_target(results_test)

    # Also compute train and valid for context
    for loss_name, lfn in [("TRAIN", train_loss), ("VALIDATION", valid_loss)]:
        ctx = []
        for name, fn, params in [
            ("A_Traditional", run_model_a, BASELINE_PARAMS_B),
            ("B_Standard_ABM", run_model_b, BASELINE_PARAMS_B),
            ("C_Heterogeneous", run_model_c, BASELINE_PARAMS_C),
        ]:
            r = eval_model(fn, params, env, targets, lfn, n_seeds, n_agents,
                           model_name=name)
            ctx.append(r)
        print_comparison(ctx, f"{loss_name} (context)")

    # ═══ TASK B: Ablation ═════════════════════════════════════
    print("\n\n[B] ABLATION EXPERIMENTS")
    abl_results = []
    for abl_name, abl_dict in ABLATIONS.items():
        r = eval_model(run_model_c, BASELINE_PARAMS_C, env, targets,
                       test_loss, n_seeds, n_agents,
                       ablation=abl_dict, model_name=f"C_{abl_name}")
        abl_results.append(r)
        print(f"  {abl_name:<25} test_loss = {r['mean_loss']:10.1f}"
              f"  Δ vs baseline = {(r['mean_loss'] - abl_results[0]['mean_loss']) / max(abl_results[0]['mean_loss'], 1e-10) * 100:+8.1f}%")
    print_per_target(abl_results[:4])  # first 4 for readability
    print_per_target(abl_results[4:])  # remaining


    # ═══ TASK C: Robustness ═══════════════════════════════════
    print("\n\n[C] ROBUSTNESS EXPERIMENTS")

    # C1: Weight robustness
    print("\n  [C1] Loss weight robustness")
    weight_variants = {
        "baseline_weights": DEFAULT_WEIGHTS,
        "high_flow_weights": {k: (v * 2 if "flow" in k else v)
                              for k, v in DEFAULT_WEIGHTS.items()},
        "high_jolts_weights": {k: (v * 2 if k in ("hires_rate", "quits_rate", "layoffs_rate") else v)
                               for k, v in DEFAULT_WEIGHTS.items()},
        "equal_weights": {k: 1.0 for k in DEFAULT_WEIGHTS},
    }
    for wname, weights in weight_variants.items():
        r_b = eval_model(run_model_b, BASELINE_PARAMS_B, env, targets,
                         lambda s, t, w=weights: compute_loss(s, t, w, VALID_END, None),
                         n_seeds, n_agents, model_name="B")
        r_c = eval_model(run_model_c, BASELINE_PARAMS_C, env, targets,
                         lambda s, t, w=weights: compute_loss(s, t, w, VALID_END, None),
                         n_seeds, n_agents, model_name="C")
        delta = (r_c["mean_loss"] - r_b["mean_loss"]) / max(r_b["mean_loss"], 1e-10) * 100
        print(f"    {wname:<25}  B={r_b['mean_loss']:8.1f}  C={r_c['mean_loss']:8.1f}"
              f"  C vs B = {delta:+7.1f}%")

    # C2: Seed robustness
    print("\n  [C2] Seed robustness (20 seeds)")
    seed_losses_b, seed_losses_c = [], []
    for s in range(20):
        sim_b = run_model_b(env=env, params=BASELINE_PARAMS_B, seed=s, n_agents=n_agents)
        sim_c = run_model_c(env=env, params=BASELINE_PARAMS_C, seed=s, n_agents=n_agents)
        seed_losses_b.append(test_loss(sim_b, targets)["total_loss"])
        seed_losses_c.append(test_loss(sim_c, targets)["total_loss"])
    wins_c = sum(1 for lb, lc in zip(seed_losses_b, seed_losses_c) if lc < lb)
    print(f"    B: mean={np.mean(seed_losses_b):.1f} std={np.std(seed_losses_b):.1f}")
    print(f"    C: mean={np.mean(seed_losses_c):.1f} std={np.std(seed_losses_c):.1f}")
    print(f"    C wins {wins_c}/20 seeds ({wins_c/20*100:.0f}%)")

    # C3: Split robustness
    print("\n  [C3] Split robustness")
    splits = {
        "baseline(114-131)": (VALID_END, None),
        "early_test(108-131)": (108, None),
        "late_test(120-131)": (120, None),
    }
    for sname, (s_start, s_end) in splits.items():
        r_b = eval_model(run_model_b, BASELINE_PARAMS_B, env, targets,
                         lambda s, t, a=s_start, b=s_end: compute_loss(s, t, None, a, b),
                         n_seeds, n_agents, model_name="B")
        r_c = eval_model(run_model_c, BASELINE_PARAMS_C, env, targets,
                         lambda s, t, a=s_start, b=s_end: compute_loss(s, t, None, a, b),
                         n_seeds, n_agents, model_name="C")
        delta = (r_c["mean_loss"] - r_b["mean_loss"]) / max(r_b["mean_loss"], 1e-10) * 100
        print(f"    {sname:<25} B={r_b['mean_loss']:8.1f}  C={r_c['mean_loss']:8.1f}"
              f"  C vs B = {delta:+7.1f}%")

    # ═══ SUMMARY ══════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STAGE 3 COMPLETE")
    print("=" * 70)
    base_c = abl_results[0]["mean_loss"]
    print(f"\n  Test: A={results_test[0]['mean_loss']:.1f}  "
          f"B={results_test[1]['mean_loss']:.1f}  C={results_test[2]['mean_loss']:.1f}")
    print(f"  C vs A: {(results_test[2]['mean_loss']-results_test[0]['mean_loss'])/max(results_test[0]['mean_loss'],1e-10)*100:+.1f}%")
    print(f"  C vs B: {(results_test[2]['mean_loss']-results_test[1]['mean_loss'])/max(results_test[1]['mean_loss'],1e-10)*100:+.1f}%")
    worst_abl = max(abl_results[1:], key=lambda r: r["mean_loss"])
    print(f"\n  Most critical mechanism: {worst_abl['name']}"
          f" (+{(worst_abl['mean_loss']-base_c)/max(base_c,1e-10)*100:.1f}% when removed)")
    print(f"  Seed robustness: C wins {wins_c}/20 seeds")


if __name__ == "__main__":
    main()
